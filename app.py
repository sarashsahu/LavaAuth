from flask import Flask, render_template, request, jsonify
import requests  # Fast2SMS API integration
import sqlite3
import hashlib
import cv2
import os
import time

app = Flask(__name__)

# Global code and timer
current_code = None
last_generated_time = 0

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
    cap = None
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            break

    if not cap or not cap.isOpened():
        print("Camera not accessible. Falling back to random code.")
        return None

    print("Warming up camera...")
    for _ in range(20):
        ret, frame = cap.read()
        if not ret:
            continue
        time.sleep(0.1)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Failed to read frame from camera. Falling back to random code.")
        return None

    small = cv2.resize(frame, (64, 64))
    encoded = small.tobytes()
    code = hashlib.sha256(encoded).hexdigest()[:8]
    print(f"Generated code from camera: {code}")
    return code

# Fallback random code generator
def generate_random_code():
    random_bytes = os.urandom(64)
    code = hashlib.sha256(random_bytes).hexdigest()[:8]
    print(f"Generated random code: {code}")
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
    global current_code, last_generated_time
    try:
        now = time.time()
        if not current_code or (now - last_generated_time > 30):
            code = generate_code_from_frame()
            if not code:
                code = generate_random_code()
            current_code = code
            last_generated_time = now
            print(f"New code generated at {time.ctime(now)}: {current_code}")
        else:
            print(f"Returning cached code at {time.ctime(now)}: {current_code}")

        return jsonify({"code": current_code})
    
    except Exception as e:
        print(f"Error in /live_code: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/register', methods=['POST'])
def register():
    try:
        name = request.json.get('name')
        phone = request.json.get('phone')

        if get_user_by_phone(phone):
            return jsonify({"error": "Phone number already registered."}), 400

        add_user(name, phone)
        return jsonify({"message": "Registration successful."})
    except Exception as e:
        print(f"Error in /register: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/start_detection', methods=['POST'])
def start_detection():
    try:
        phone = request.json.get("phone")
        if not phone:
            return jsonify({"error": "Phone number is required."}), 400

        user = get_user_by_phone(phone)
        if not user:
            return jsonify({"error": "User not registered."}), 400

        code = generate_code_from_frame()
        if not code:
            code = generate_random_code()

        update_user_codes(phone, code)

        # Send SMS using Fast2SMS
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "sender_id": "TXTIND",  # Sender ID you have or can set on Fast2SMS
            "message": f"Your login code is: {code}",
            "language": "english",
            "route": "v3",
            "numbers": phone
        }
        headers = {
            "authorization": "JN0uiE3jFzfPUtv6mln78xabh1WGAOpQd2sZHDcXyqMw5VLCIgCXKziyo3lYcs9BArb6M4H2jVtF1mI5",  # Replace with your Fast2SMS API Key
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(url, data=payload, headers=headers)

        if response.status_code == 200:
            print("Fast2SMS Response:", response.json())
            return jsonify({"message": "Code sent successfully."})
        else:
            print("Fast2SMS Error:", response.text)
            return jsonify({"error": "Failed to send SMS"}), 500

    except Exception as e:
        print(f"Error in /start_detection: {e}")
        return jsonify({"error": "Failed to send code"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
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
    except Exception as e:
        print(f"Error in /login: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
