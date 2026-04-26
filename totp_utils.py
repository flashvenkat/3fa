import pyotp
import qrcode
import base64
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def generate_totp_secret():
    """Generates a new base32 TOTP secret."""
    return pyotp.random_base32()

def get_totp_uri(username, secret, issuer_name="3FA_App"):
    """Generates the provisioning URI for Google Authenticator / Authy."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer_name)

def generate_qr_code_base64(uri):
    """Generates a QR code image from the URI and returns it as a base64 string for embedding in HTML."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None

def verify_totp(secret, user_input_otp):
    """Verifies a 6-digit TOTP code against the secret."""
    try:
        totp = pyotp.TOTP(secret)
        # Verify the OTP. pyotp handles timing automatically.
        return totp.verify(user_input_otp)
    except Exception as e:
        logger.error(f"Error verifying TOTP: {e}")
        return False
