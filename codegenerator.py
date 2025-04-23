from flask import Flask, render_template, request, jsonify
from twilio.rest import Client
import sqlite3
import hashlib
import time
from datetime import datetime
import os

app = Flask(__name__)

# Twilio credentials
TWILIO_SID = 'ACccf75ffdc544a3a64169f1858cb3ecb7'
TWILIO_AUTH_TOKEN = '9d5eba9d5b8f0b339a9519b997138b67'
TWILIO_PHONE_NUMBER = '+917797715343'

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# Initialize the database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            code TEXT,
            code_expiry REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Database operations
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
    cursor.execute('INSERT INTO users (name, phone) VALUES (?, ?)', (name, phone))
    conn.commit()
    conn.close()

def update_user_code(phone, code):
    expiry = time.time() + 300  # 5 minutes from now
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET code = ?, code_expiry = ? WHERE phone = ?', (code, expiry, phone))
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')

    if not name or not phone:
        return jsonify({"error": "Name and phone number are required."}), 400

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

    code = generate_code(phone)
    update_user_code(phone, code)

    try:
        client.messages.create(
            body=f"Your login code is: {code}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
    except Exception as e:
        return jsonify({"error": "Failed to send SMS."}), 500

    return jsonify({"message": "Code sent successfully."})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone')
    code = data.get('code')

    if not phone or not code:
        return jsonify({"error": "Phone and code are required."}), 400

    user = get_user_by_phone(phone)
    if not user:
        return jsonify({"error": "User not found."}), 404

    stored_code = user[3]
    expiry = user[4]

    if code == stored_code and time.time() < expiry:
        return jsonify({"message": "Login successful!"})
    else:
        return jsonify({"error": "Invalid or expired code."}), 400

def generate_code(phone):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hash_input = phone + current_datetime
    return hashlib.sha256(hash_input.encode()).hexdigest()[:6]

if __name__ == '__main__':
    app.run(debug=True)
