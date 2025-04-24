from flask import Flask, render_template, request, jsonify
from twilio.rest import Client
import sqlite3
import hashlib
import cv2
import os
import time

app = Flask(__name__)

# Twilio credentials
TWILIO_SID = 'ACccf75ffdc544a3a64169f1858cb3ecb7'
TWILIO_AUTH_TOKEN = '9d5eba9d5b8f0b339a9519b997138b67'
TWILIO_PHONE_NUMBER = '+917797715343'
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            codes TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Database helpers
def get_user_by_phone(phone):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(name, phone):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (name, phone, codes) VALUES (?, ?, ?)', (name, phone, ""))
    conn.commit()
    conn.close()

def update_user_codes(phone, codes):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET codes = ? WHERE phone = ?', (codes, phone))
    conn.commit()
    conn.close()

# Code generation using camera frame
def generate_code_from_frame():
    # Trying to initialize the camera with a simple backend (0 for default camera)
    cap = cv2.VideoCapture(0)  # Try using 0 for the default camera

    if not cap.isOpened():
        print("Camera not accessible")
        return "ERROR: Cannot open camera"

    print("Warming up camera for 3 seconds...")
    time.sleep(3)  # Shorter wait for camera to adjust

    ret, frame = cap.read()  # Capture a frame
    cap.release()  # Release the camera

    if not ret:
        print("Failed to read frame from camera")
        return "ERROR: Frame not captured"

    # Resize the captured frame to 64x64
    small = cv2.resize(frame, (64, 64))
    encoded = small.tobytes()  # Convert the frame to bytes
    code = hashlib.sha256(encoded).hexdigest()[:8]  # Create a hash-based code
    return code

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register_page')
def register_page():
    return render_template('register.html')

@app.route('/visual_code')
def visual_code():
    return render_template('visual_code.html')

@app.route('/live_code')
def live_code():
    code = generate_code_from_frame()
    if code.startswith("ERROR"):
        return jsonify({"error": code}), 500
    return jsonify({"code": code})

@app.route('/register', methods=['POST'])
def register():
    name = request.json.get('name')
    phone = request.json.get('phone')

    if get_user_by_phone(phone):
        return jsonify({"error": "Phone number already registered."}), 400

    add_user(name, phone)
    return jsonify({"message": "Registration successful."})

@app.route('/start_detection', methods=['POST'])
def start_detection():
    phone = request.json.get("phone")
    if not phone:
        return jsonify({"error": "Phone number is required."}), 400

    user = get_user_by_phone(phone)
    if not user:
        return jsonify({"error": "User not registered."}), 400

    code = generate_code_from_frame()
    if code.startswith("ERROR"):
        return jsonify({"error": code}), 500

    update_user_codes(phone, code)

    try:
        client.messages.create(
            body=f"Your login code is: {code}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
    except Exception as e:
        print("SMS failed:", e)
        return jsonify({"error": "Failed to send SMS"}), 500

    return jsonify({"message": "Code sent successfully."})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone')
    entered_code = data.get('code')

    user = get_user_by_phone(phone)
    if not user:
        return jsonify({"error": "User not found."}), 404

    stored_codes = user[3]
    if entered_code in stored_codes.split(','):
        return jsonify({"message": "Login successful!"})
    else:
        return jsonify({"error": "Invalid code."}), 400

if __name__ == '__main__':
    app.run(debug=True)
