from flask import Flask, render_template, request, jsonify, Response
import cv2
import numpy as np
import hashlib
import time
from datetime import datetime
import os

app = Flask(__name__)

# Store generated codes
generated_codes = []

def generate_code(bubble_data):
    """Generate a unique code based on detected bubbles."""
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bubble_string = "".join([f"{x}_{y}_{r}" for x, y, r in bubble_data]) + current_datetime
    hashed_code = hashlib.sha256(bubble_string.encode()).hexdigest()[:8]
    return hashed_code

def detect_bubbles(frame):
    """Detect bubbles and return their properties."""
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
    
    return bubble_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    global generated_codes
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        return jsonify({"error": "Unable to access camera."})
    
    start_time = time.time()
    latest_code = None

    while time.time() - start_time <= 5:
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return jsonify({"error": "Unable to capture video."})
        
        bubble_data = detect_bubbles(frame)
        if bubble_data and len(bubble_data) >= 3:
            code = generate_code(bubble_data)
            if code not in generated_codes:
                generated_codes.insert(0, code)  # Store latest code
                latest_code = code
    
    cap.release()
    return jsonify({"generated_codes": generated_codes, "latest_code": latest_code})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    entered_code = data.get('code')
    if entered_code in generated_codes:
        return jsonify({"message": "Login Successful!"})
    return jsonify({"error": "Invalid Code!"}), 400

@app.route('/video_feed')
def video_feed():
    def generate():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Detect bubbles and draw circles
            bubble_data = detect_bubbles(frame)
            for (x, y, r) in bubble_data:
                cv2.circle(frame, (x, y), r, (0, 255, 0), 2)

            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        cap.release()

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"  # Fix multiprocessing issue in MacOS
    app.run(debug=True, threaded=True)
