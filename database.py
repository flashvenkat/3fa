import sqlite3
import logging
import json
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

DB_PATH = '3fa_app.db'
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def init_db():
    """Initializes the SQLite database with the necessary schema."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    totp_secret TEXT,
                    face_encoding TEXT,
                    failed_attempts INTEGER DEFAULT 0,
                    lockout_until DATETIME
                )
            ''')
            
            # Add new columns if they don't exist
            new_columns = [
                ('email', 'TEXT'),
                ('full_name', 'TEXT'),
                ('dob', 'TEXT'),
                ('state', 'TEXT'),
                ('country', 'TEXT'),
                ('phone', 'TEXT')
            ]
            for col_name, col_type in new_columns:
                try:
                    cursor.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
            
            conn.commit()
            logger.info("Database initialized successfully with new profile schema.")
    except sqlite3.Error as e:
        logger.error(f"Database error during initialization: {e}")
        raise

def get_db_connection():
    """Returns a new SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_user(username, password_hash, totp_secret, face_encoding_list, profile_data):
    """Creates a new user in the database with extended profile info."""
    try:
        face_encoding_str = json.dumps(face_encoding_list) if face_encoding_list else None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password_hash, totp_secret, face_encoding, email, full_name, dob, state, country, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username, password_hash, totp_secret, face_encoding_str,
                profile_data.get('email'), profile_data.get('full_name'),
                profile_data.get('dob'), profile_data.get('state'),
                profile_data.get('country'), profile_data.get('phone')
            ))
            conn.commit()
            logger.info(f"User '{username}' created successfully.")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Registration failed: Username '{username}' already exists.")
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error during user creation: {e}")
        return False

def get_user(username):
    """Retrieves a user by username."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"Database error fetching user: {e}")
        return None

def check_rate_limit(username):
    """
    Checks if a user is currently locked out.
    Returns (is_locked, remaining_minutes).
    """
    user = get_user(username)
    if not user:
        return False, 0
        
    if user['lockout_until']:
        lockout_time = datetime.fromisoformat(user['lockout_until'])
        if datetime.now() < lockout_time:
            delta = lockout_time - datetime.now()
            return True, int(delta.total_seconds() / 60)
        else:
            # Lockout expired, reset attempts
            reset_failed_attempts(username)
            return False, 0
            
    return False, 0

def increment_failed_attempts(username):
    """Increments the failed login attempt counter and locks out if necessary."""
    user = get_user(username)
    if not user:
        return
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            new_attempts = user['failed_attempts'] + 1
            
            if new_attempts >= MAX_FAILED_ATTEMPTS:
                lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                cursor.execute('''
                    UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE username = ?
                ''', (new_attempts, lockout_until.isoformat(), username))
                logger.warning(f"User '{username}' locked out for {LOCKOUT_DURATION_MINUTES} minutes.")
            else:
                cursor.execute('''
                    UPDATE users SET failed_attempts = ? WHERE username = ?
                ''', (new_attempts, username))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error updating failed attempts: {e}")

def reset_failed_attempts(username):
    """Resets failed attempts after a successful login or lockout expiration."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE username = ?
            ''', (username,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error resetting failed attempts: {e}")

def parse_face_encoding(user_row):
    """Parses the JSON face encoding from the DB row back into a numpy array."""
    if user_row and user_row['face_encoding']:
        try:
            encoding_list = json.loads(user_row['face_encoding'])
            return np.array(encoding_list)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse face encoding for user ID {user_row['id']}")
            return None
    return None
