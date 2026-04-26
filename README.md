# 3FA Secure Web Portal

This project is a 3-Factor Authentication (3FA) system built with Flask, integrating:
1. **Knowledge Factor**: Password (`bcrypt`)
2. **Possession Factor**: Authenticator App / TOTP (`pyotp`, `qrcode`)
3. **Inherence Factor**: Facial Recognition (`face_recognition`, `opencv-python`)

## Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Python 3.8+**
- **Git**
- A webcam (required for the facial recognition feature)

## Setup and Installation

Follow these steps to set up the project on your local machine:

### 1. Clone the Repository
Open your terminal or command prompt and run the following command to clone the project:
```bash
git clone https://github.com/flashvenkat/3fa.git
```

Move into the project directory:
```bash
cd 3fa
```

### 2. Create a Virtual Environment (Recommended)
It's best practice to use a virtual environment to manage dependencies so they don't interfere with other Python projects.
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all the required libraries using `pip`:
```bash
pip install -r requirements.txt
```

**Libraries Installed:**
- `Flask`: Web Framework
- `bcrypt`: Password Hashing
- `pyotp` & `qrcode`: Time-Based One-Time Passwords (Google Authenticator)
- `opencv-python` & `face_recognition`: Facial Biometrics
- `PyJWT`: JSON Web Tokens
- `numpy` & `Pillow`: Image Processing

> **Note on Windows**: Installing the `face_recognition` library might require you to have **CMake** and **Visual Studio C++ Build Tools** installed on your system.

### 4. Run the Application
Start the Flask development server by running:
```bash
python app.py
```
*(Note: If the main execution file is `project.py`, run `python project.py` instead).*

### 5. Access the Web Portal
Open your web browser and navigate to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)
