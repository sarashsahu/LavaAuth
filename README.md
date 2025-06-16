# 🔥 LavaAuth — Lava Lamp-Based Authentication System

**LavaAuth** is a unique authentication system that uses visual randomness from a lava lamp or webcam feed to generate secure one-time codes (OTPs) for user login. Built using Python, OpenCV, Flask, and SQLite, it merges computer vision with secure code-based login mechanisms, perfect for academic demos or experimental security systems.

---

## 📌 Features

* 🧪 **Visual Code Generation** via webcam (lava lamp detection or fallback random hashing)
* 🧠 **Bubble Detection** from webcam to seed secure login codes
* 🔐 **OTP Login Flow** via Email (codes expire in 30 seconds)
* 🧾 **Registration & Session Handling**
* 📬 **HTML Email Template** using `smtplib` with SSL
* 🛠️ **Admin Panel** for managing users
* 🎥 **Visual Code Feed Page**
* 🧼 Secure session and cache handling

---

## 🗂️ Project Structure

```
lavaauth/
├── templates/
│   ├── index.html
│   ├── register.html
│   ├── visual_code.html
│   ├── dashboard.html
│   └── admin_users.html
├── users.db
├── .env
├── requirements.txt
├── app.py  ← (main Flask application)
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/lavaauth.git
cd lavaauth
```

### 2. Set up the virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory with the following:

```
EMAIL_ADDRESS=youremail@example.com
EMAIL_PASSWORD=yourpassword
```

> ⚠️ Ensure less secure apps are enabled or use App Passwords for Gmail.

### 5. Run the application

```bash
python lavaauth.py
```

The app will be live at `http://127.0.0.1:5000`

---

## 🔑 Login Flow

1. **Register** with your name and email on `/register_page`
2. **Start Detection** (lava lamp/randomized visual) → Generates a one-time code
3. **Code sent to your email**
4. **Login with the code** within 30 seconds
5. **Session-based dashboard access**
6. Admin view: `/admin_users` to manage registered users

---

## 🧪 Visual Code Generation

* Uses OpenCV to capture frames from your webcam
* Detects **bubbles** (via contour detection) in the image
* Generates an 8-character hash code based on bubble positions
* If no valid data, falls back to secure `os.urandom` code

---

## 🛡 Security Notes

* Codes expire after 30 seconds
* Session and cache control enabled to prevent replay attacks
* Email/password kept in environment variables (`.env`)
* Basic input sanitization included

---

## 🧑‍💻 Author

**Sarash Sahu**
🎓 MCA Final Year 2025
🔗 [LinkedIn](https://www.linkedin.com/in/sarashsahu)

---

## 📜 License

This project is for educational and demonstration purposes. Feel free to fork and modify.

