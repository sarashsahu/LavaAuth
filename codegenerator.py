from flask import Flask, render_template, request, jsonify, redirect, url_for
from twilio.rest import Client
import sqlite3
import hashlib
import time
from datetime import datetime

# Initialize the Flask application
app = Flask(__name__)

# Twilio credentials (use your actual credentials here)
TWILIO_SID = 'ACccf75ffdc544a3a64169f1858cb3ecb7'
TWILIO_AUTH_TOKEN = '9d5eba9d5b8f0b339a9519b997138b67'
TWILIO_PHONE_NUMBER = '+91 77977 15343'

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# SQLite database functions
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

# Initialize the database
init_db()

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    phone = request.form.get('phone')

    # Check if the phone number is already registered
    if get_user_by_phone(phone):
        return jsonify({"error": "Phone number already registered."}), 400

    # Add the user to the database
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

    # Generate a unique code
    code = generate_code(phone)

    # Store the code for the user in the database
    update_user_codes(phone, code)

    # Send the code via SMS using Twilio
    try:
        client.messages.create(
            body=f"Your login code is: {code}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
    except Exception as e:
        print("SMS failed:", e)

    return jsonify({"message": "Code sent successfully."})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data.get('phone')
    entered_code = data.get('code')

    if not phone or not entered_code:
        return jsonify({"error": "Phone number and code are required."}), 400

    user = get_user_by_phone(phone)
    if not user:
        return jsonify({"error": "User not found."}), 404

    stored_codes = user[3]  # Get the stored codes (comma-separated)

    if entered_code in stored_codes.split(','):
        return jsonify({"message": "Login successful!"})
    else:
        return jsonify({"error": "Invalid code."}), 400

def generate_code(phone):
    """Generate a unique code based on user phone number and current time."""
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    phone_string = phone + current_datetime
    hashed_code = hashlib.sha256(phone_string.encode()).hexdigest()[:8]
    return hashed_code

if __name__ == '__main__':
    app.run(debug=True)
