import bcrypt
import jwt
import datetime
import logging
import os

logger = logging.getLogger(__name__)

# In a real production environment, load this from a secure environment variable.
# Example: os.environ.get('JWT_SECRET', 'fallback-dev-secret')
# We generate a random one for this demo if not set.
JWT_SECRET = os.environ.get('JWT_SECRET', 'super-secret-key-for-3fa-demo-12345')

def hash_password(password):
    """Hashes a password using bcrypt with a generated salt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed_password):
    """Verifies a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError as e:
        logger.error(f"Bcrypt verification error: {e}")
        return False

def generate_jwt(username):
    """Generates a JWT session token for the authenticated user."""
    payload = {
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2), # Token expires in 2 hours
        'iat': datetime.datetime.utcnow()
    }
    
    try:
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        return token
    except Exception as e:
        logger.error(f"Error generating JWT: {e}")
        return None

def verify_jwt(token):
    """Verifies a JWT token and returns the payload if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT validation failed: Token expired.")
        return None
    except jwt.InvalidTokenError:
        logger.warning("JWT validation failed: Invalid token.")
        return None
