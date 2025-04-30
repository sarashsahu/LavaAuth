import os
import time
import hashlib
import sqlite3
import smtplib
import cv2
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

current_code = None
last_generated_time = 0

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            codes TEXT,
            code_time INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Database Helpers ---
def get_user_by_email(email):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        return cursor.fetchone()

def add_user(name, email):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, codes, code_time) VALUES (?, ?, ?, ?)',
                       (name, email, "", 0))
        conn.commit()

def update_user_codes(email, code):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET codes = ?, code_time = ? WHERE email = ?',
                       (code, int(time.time()), email))
        conn.commit()

# --- Email Code Sender ---
def send_email_code(to_email, code):
    sender_email = os.getenv("EMAIL_ADDRESS", "").strip()
    password     = os.getenv("EMAIL_PASSWORD", "").strip()

    if not sender_email or not password:
        print("❌ EMAIL_ADDRESS or EMAIL_PASSWORD not set in .env")
        return

    user = get_user_by_email(to_email)
    if not user:
        print(f"❌ No user found with email {to_email}")
        return

    username = user[1]  # name column

    msg = MIMEText(f"""\
        Hello {username}!,

        Your login code is: {code}

        Please note that this code will expire in 30 seconds.

        Thank you,
        LavaAuth Team
        """)

    msg['Subject'] = "Your Authentication Code"
    msg['From']    = sender_email
    msg['To']      = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.send_message(msg)
        print(f"✅ Code sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")



# --- Bubble Detection and Code Generation ---
def generate_code(bubble_data):
    bubble_string = "".join([f"{x}_{y}_{r}" for x, y, r in bubble_data])
    hashed_code = hashlib.sha256(bubble_string.encode()).hexdigest()[:8]
    return hashed_code

def detect_bubbles(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    _, thresh = cv2.threshold(blurred, 50, 255, cv2.THRESH_BINARY)
    edges = cv2.Canny(thresh, 30, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bubble_data = []
    for contour in contours:
        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        area = cv2.contourArea(contour)
        if radius > 20 and area > 300:
            bubble_data.append((int(x), int(y), int(radius)))
            cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)

    return frame, bubble_data

def generate_code_from_frame():
    cap = None
    for i in range(5):
        temp_cap = cv2.VideoCapture(i)
        if temp_cap.isOpened():
            cap = temp_cap
            break
        temp_cap.release()

    if not cap or not cap.isOpened():
        print("❌ Camera not accessible.")
        return None

    print("📷 Warming up camera...")
    for _ in range(20):
        ret, _ = cap.read()
        if not ret:
            continue
        time.sleep(0.05)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("❌ Failed to read final frame.")
        return None

    processed_frame, bubble_data = detect_bubbles(frame)
    if bubble_data and len(bubble_data) >= 3:
        code = generate_code(bubble_data)
        print("Generated Code:", code)
        return code
    else:
        print("❌ No valid bubble data detected.")
        return None

def generate_random_code():
    return hashlib.sha256(os.urandom(64)).hexdigest()[:8]

# --- Routes ---
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
    now = time.time()

    if not current_code or (now - last_generated_time > 30):
        code = generate_code_from_frame()
        if code:
            print("✅ Code generated from camera.")
        else:
            code = generate_random_code()
            print("⚠️ Fallback: Code generated from random entropy.")
        current_code = code
        last_generated_time = now

    return jsonify({"code": current_code})

@app.route('/register', methods=['POST'])
def register():
    try:
        name = request.json.get('name')
        email = request.json.get('email', '').strip().lower()

        if get_user_by_email(email):
            return jsonify({"error": "Email already registered."}), 400

        add_user(name, email)
        return jsonify({"message": "Registration successful."})
    except Exception as e:
        print(f"Error in /register: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/start_detection', methods=['POST'])
def start_detection():
    try:
        email = request.json.get("email")
        if not email:
            return jsonify({"error": "Email is required."}), 400

        if not get_user_by_email(email):
            return jsonify({"status": "unregistered"}), 200

        global current_code, last_generated_time
        now = time.time()

        if not current_code or (now - last_generated_time > 30):
            code = generate_code_from_frame()
            if code:
                print("✅ Code generated from camera.")
            else:
                code = generate_random_code()
                print("⚠️ Fallback: Code generated from random entropy.")
            current_code = code
            last_generated_time = now

        update_user_codes(email, current_code)
        send_email_code(email, current_code)

        return jsonify({"status": "success", "message": "Code sent successfully via email."})
    except Exception as e:
        print(f"Error in /start_detection: {e}")
        return jsonify({"error": "Failed to send code"}), 500

@app.route('/admin_users')
def admin_users():
    try:
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, email, codes FROM users')
            users = cursor.fetchall()
        return render_template('admin_users.html', users=users)
    except Exception as e:
        print(f"Error in /admin_users: {e}")
        return "Error loading admin dashboard."

@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        user_id = request.form.get('user_id')
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
        return '<script>window.location.href="/admin_users";</script>'
    except Exception as e:
        print(f"Error in /delete_user: {e}")
        return "Error deleting user."

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        entered_code = data.get('code')

        user = get_user_by_email(email)
        if not user:
            return jsonify({"error": "User not found."}), 404

        stored_code = user[3]  # codes column

        if not stored_code:
            return jsonify({"error": "No code stored for user."}), 400

        if entered_code.strip() == stored_code.strip():
            return jsonify({"message": "Login successful!"})
        else:
            return jsonify({"error": "Invalid code."}), 400
    except Exception as e:
        print(f"Error in /login: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
