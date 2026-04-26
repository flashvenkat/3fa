import cv2
import face_recognition
import numpy as np
import base64
import logging

logger = logging.getLogger(__name__)

def get_face_encoding_from_base64(base64_img):
    """
    Decodes a base64 Data URL image, extracts the face, and returns its 128D encoding.
    Expected format: "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    """
    try:
        # Strip header
        if ',' in base64_img:
            base64_img = base64_img.split(',')[1]
            
        img_data = base64.b64decode(base64_img)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Could not decode image from base64.")
            return None

        # Convert image from BGR (OpenCV) to RGB (face_recognition)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Find all the faces in the image
        face_locations = face_recognition.face_locations(rgb_img)
        
        if not face_locations:
            logger.warning("No face detected in the provided image.")
            return None
            
        if len(face_locations) > 1:
            logger.warning("Multiple faces detected. Only the first one will be used.")

        # Compute facial encodings for the faces found
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        
        # We take the first one
        if len(face_encodings) > 0:
            return face_encodings[0]
            
        return None

    except Exception as e:
        logger.error(f"Error extracting face encoding: {e}")
        return None

def verify_face(known_encoding, base64_img_to_test, tolerance=0.6):
    """
    Compares a stored 128D encoding with a new base64 image.
    Returns True if they match, False otherwise.
    tolerance: Lower is stricter. 0.6 is typical for face_recognition.
    """
    try:
        unknown_encoding = get_face_encoding_from_base64(base64_img_to_test)
        
        if unknown_encoding is None:
            logger.warning("Verification failed: No face found in the live capture.")
            return False
            
        # compare_faces expects a list of known encodings and the single unknown encoding
        results = face_recognition.compare_faces([known_encoding], unknown_encoding, tolerance=tolerance)
        
        if results[0]:
            logger.info("Face verified successfully.")
            return True
        else:
            logger.warning("Face verification failed: Mismatch.")
            return False
            
    except Exception as e:
        logger.error(f"Error during face verification: {e}")
        return False
