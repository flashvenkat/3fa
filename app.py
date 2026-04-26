import os
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import database
import auth_logic
import totp_utils
import face_utils

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
# In production, use a secure, randomly generated secret key.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-for-session')

# Initialize DB on startup
with app.app_context():
    database.init_db()

def require_jwt(f):
    """Decorator to protect routes requiring JWT."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('jwt_token')
        if not token:
            return redirect(url_for('login'))
        
        payload = auth_logic.verify_jwt(token)
        if not payload:
            session.pop('jwt_token', None)
            return redirect(url_for('login'))
            
        return f(payload['username'], *args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET'])
def register_get():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        face_image_base64 = data.get('face_image')

        profile_data = {
            'email': data.get('email'),
            'full_name': data.get('full_name'),
            'dob': data.get('dob'),
            'state': data.get('state'),
            'country': data.get('country'),
            'phone': data.get('phone')
        }

        if not username or not password or not face_image_base64:
            return jsonify({'error': 'Missing required fields (username, password, or face scan)'}), 400

        # 1. Process Face
        face_encoding = face_utils.get_face_encoding_from_base64(face_image_base64)
        if face_encoding is None:
            return jsonify({'error': 'Could not detect a face. Please try again in better lighting.'}), 400

        # 2. Hash Password
        password_hash = auth_logic.hash_password(password)

        # 3. Generate TOTP Secret
        totp_secret = totp_utils.generate_totp_secret()

        # 4. Save to DB
        face_encoding_list = face_encoding.tolist()
        success = database.create_user(username, password_hash, totp_secret, face_encoding_list, profile_data)

        if not success:
            return jsonify({'error': 'Username already exists or database error.'}), 400

        # 5. Generate QR Code for TOTP setup
        totp_uri = totp_utils.get_totp_uri(username, totp_secret)
        qr_code_b64 = totp_utils.generate_qr_code_base64(totp_uri)

        logger.info(f"User '{username}' registered successfully.")
        
        # Return success and QR code so the user can scan it immediately
        return jsonify({
            'message': 'Registration successful! Please scan this QR code with Google Authenticator.',
            'qr_code': qr_code_b64
        })
    except Exception as e:
        logger.error(f"Server error during registration: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/api/register/verify_totp', methods=['POST'])
def register_verify_totp():
    """Verify that the user successfully scanned the QR code."""
    data = request.json
    username = data.get('username')
    totp_code = data.get('totp_code')

    if not username or not totp_code:
        return jsonify({'error': 'Missing username or OTP.'}), 400

    user = database.get_user(username)
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    if totp_utils.verify_totp(user['totp_secret'], totp_code):
        return jsonify({'message': 'TOTP setup verified successfully!'})
    else:
        return jsonify({'error': 'Invalid TOTP code. Please try again.'}), 400

@app.route('/api/login/step1', methods=['POST'])
def login_step1():
    """Step 1: Verify Knowledge (Username/Password)"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required.'}), 400

    is_locked, lockout_mins = database.check_rate_limit(username)
    if is_locked:
        return jsonify({'error': f'Account locked. Try again in {lockout_mins} minutes.'}), 403

    user = database.get_user(username)
    if not user or not auth_logic.verify_password(password, user['password_hash']):
        database.increment_failed_attempts(username)
        logger.warning(f"Failed login step 1 (credentials) for user: {username}")
        return jsonify({'error': 'Invalid username or password.'}), 401

    # Store temp state in session for step 2
    session['temp_login_user'] = username
    return jsonify({'message': 'Step 1 complete. Proceed to TOTP.'})

@app.route('/api/login/step2', methods=['POST'])
def login_step2():
    """Step 2: Verify Possession (TOTP)"""
    data = request.json
    totp_code = data.get('totp_code')
    username = session.get('temp_login_user')

    if not username or not totp_code:
        return jsonify({'error': 'Session expired or missing OTP.'}), 400

    is_locked, lockout_mins = database.check_rate_limit(username)
    if is_locked:
        return jsonify({'error': f'Account locked. Try again in {lockout_mins} minutes.'}), 403

    user = database.get_user(username)
    if not user or not totp_utils.verify_totp(user['totp_secret'], totp_code):
        database.increment_failed_attempts(username)
        logger.warning(f"Failed login step 2 (TOTP) for user: {username}")
        return jsonify({'error': 'Invalid TOTP code.'}), 401

    return jsonify({'message': 'Step 2 complete. Proceed to Face Verification.'})

@app.route('/api/login/step3', methods=['POST'])
def login_step3():
    """Step 3: Verify Inherence (Face) and Issue JWT"""
    data = request.json
    face_image_base64 = data.get('face_image')
    username = session.get('temp_login_user')

    if not username or not face_image_base64:
        return jsonify({'error': 'Session expired or missing face image.'}), 400

    is_locked, lockout_mins = database.check_rate_limit(username)
    if is_locked:
        return jsonify({'error': f'Account locked. Try again in {lockout_mins} minutes.'}), 403

    user = database.get_user(username)
    known_encoding = database.parse_face_encoding(user)

    if known_encoding is None:
        return jsonify({'error': 'Server configuration error (missing face encoding).'}), 500

    if not face_utils.verify_face(known_encoding, face_image_base64):
        database.increment_failed_attempts(username)
        logger.warning(f"Failed login step 3 (Face Verification) for user: {username}")
        return jsonify({'error': 'Face verification failed.'}), 401

    # Success! All 3 factors passed.
    database.reset_failed_attempts(username)
    session.pop('temp_login_user', None)

    # Issue JWT
    token = auth_logic.generate_jwt(username)
    session['jwt_token'] = token
    
    logger.info(f"User '{username}' successfully logged in (3FA completed).")
    return jsonify({'message': 'Login successful!', 'redirect': url_for('dashboard')})

@app.route('/dashboard')
@require_jwt
def dashboard(username):
    user = database.get_user(username)
    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.pop('jwt_token', None)
    session.pop('temp_login_user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Ensure templates and static folders exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5000)
