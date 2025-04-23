# lava_lamp_auth/app.py

from flask import Flask, render_template, request, jsonify
from twilio.rest import Client
import sqlite3
import hashlib
import cv2
import os

app = Flask(__name__)

# Twilio credentials (replace with your actual ones)
TWILIO_SID = 'your_sid_here'
TWILIO_AUTH_TOKEN = 'your_auth_token_here'
TWILIO_PHONE_NUMBER = '+91xxxxxxxxxx'
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

camera = cv2.VideoCapture(0)

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

# Helpers for database

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

# Generate code from camera

def generate_code_from_frame():
    ret, frame = camera.read()
    if not ret:
        return "ERROR"
    small = cv2.resize(frame, (64, 64))
    encoded = small.tobytes()
    code = hashlib.sha256(encoded).hexdigest()[:8]
    return code

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

