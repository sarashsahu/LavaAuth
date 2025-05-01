import os
import time
import hashlib
import sqlite3
import smtplib
import cv2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from email.utils import formataddr

# Load environment variables
load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global code and timer
current_code = None
last_generated_time = 0

# --- Database Setup ---
def init_db():
    with sqlite3.connect('users.db') as conn:
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
    password = os.getenv("EMAIL_PASSWORD", "").strip()

    if not sender_email or not password:
        print("❌ EMAIL_ADDRESS or EMAIL_PASSWORD not set in .env")
        return

    user = get_user_by_email(to_email)
    if not user:
        print(f"❌ No user found with email {to_email}")
        return

    username = user[1]

    msg = MIMEMultipart("alternative")
    msg['Subject'] = "🔐 Your One-Time Login Code"
    msg['From'] = formataddr(("LavaAuth Team", sender_email))
    msg['To'] = to_email

    text = f"""
Hi {username},

Your login code is: {code}

This code will expire in 30 seconds.

If you did not request this, you can safely ignore it.

Thanks,
LavaAuth Team
"""
    html = f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
    <div style="max-width: 500px; margin: auto; background-color: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 0 10px #ccc;">
      <h2 style="color: #333;">Hello <span style="color: #4CAF50;">{username}</span> 👋,</h2>
      <p style="font-size: 16px;">Here is your one-time login code:</p>
      <div style="font-size: 24px; font-weight: bold; background-color: #e8f5e9; padding: 10px; border-radius: 5px; text-align: center; color: #2e7d32;">
        {code}
      </div>
      <p style="margin-top: 20px; font-size: 14px; color: #666;">
        ⚠️ This code will expire in <strong>30 seconds</strong>.
      </p>
      <hr />
      <p style="font-size: 12px; color: #999;">If you didn’t request this code, you can safely ignore this message.<br>If you found this in Spam Kindly Unspam it.</p>
      <p style="font-size: 14px; color: #333;">Cheers,<br><strong>LavaAuth Team</strong></p>
    </div>
  </body>
</html>
"""
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.send_message(msg)
        print(f"✅ Code sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Bubble Detection ---
def generate_code(bubble_data):
    bubble_string = "".join([f"{x}_{y}_{r}" for x, y, r in bubble_data])
    return hashlib.sha256(bubble_string.encode()).hexdigest()[:8]

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
        return generate_code(bubble_data)
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
        if not code:
            code = generate_random_code()
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
            if not code:
                code = generate_random_code()
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

@app.route('/dashboard')
def dashboard():
    email = session.get('email')
    if not email:
        return redirect(url_for('index'))
    
    user = get_user_by_email(email)
    if not user:
        return redirect(url_for('index'))
    
    username = user[1]
    return render_template('dashboard.html', username=username)


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

        stored_code = user[3]
        code_time = user[4]

        if not stored_code:
            return jsonify({"error": "No code stored for user."}), 400

        if int(time.time()) - int(code_time) > 30:
            return jsonify({"error": "Code has expired."}), 400

        if entered_code.strip() == stored_code.strip():
            username = user[1]
            session['email'] = email
            return jsonify({"message": "Login successful!", "username": username})
        else:
            return jsonify({"error": "Invalid code."}), 400
    except Exception as e:
        print(f"Error in /login: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logout')
def logout():
    try:
        email = session.get('email')
        if email:
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET codes = ?, code_time = ? WHERE email = ?',
                               ("", 0, email))
                conn.commit()
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error in /logout: {e}")
        return "Error during logout."

@app.after_request
def add_cache_control_headers(response):
    if request.endpoint in ['dashboard', 'admin_users']:
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
    return response

if __name__ == '__main__':
    app.run(debug=True)