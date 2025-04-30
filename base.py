import cv2
import numpy as np
import hashlib
import time
from datetime import datetime

# Store generated codes (only in memory)
generated_codes = []

def generate_code(bubble_data):
    """Generate a unique 8-character code based on bubble data (no datetime in the code)."""
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Used internally for randomness
    bubble_string = "".join([f"{x}_{y}_{r}" for x, y, r in bubble_data]) + current_datetime
    hashed_code = hashlib.sha256(bubble_string.encode()).hexdigest()[:8]
    return hashed_code

def detect_bubbles(frame):
    """Detect bubbles in the given frame and return their properties."""
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

def start_detection():
    """Start video capture, detect bubbles, and generate a new code every 5 seconds."""
    global generated_codes
    cap = cv2.VideoCapture(0)
    print("Starting continuous detection...")

    start_time = time.time()  # Track time
    code_generation_interval = 5  # 5 seconds interval

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Unable to capture video.")
            break

        processed_frame, bubble_data = detect_bubbles(frame)

        # Generate code every 5 seconds if valid bubble data is detected
        if bubble_data and len(bubble_data) >= 3:
            current_time = time.time()
            if current_time - start_time >= code_generation_interval:
                code = generate_code(bubble_data)
                print("Generated Code:", code)
                generated_codes.append(code)
                start_time = current_time  # Reset the timer

        cv2.imshow("Lava Lamp Bubble Detector", processed_frame)

        # Wait for 'T' key to terminate the detection
        key = cv2.waitKey(1) & 0xFF
        if key == ord('t') or key == 27:  # 'T' or 'Esc' key to terminate
            print("Exiting detection...")
            break

    cap.release()
    cv2.destroyAllWindows()

def view_codes():
    """Display all previously generated codes."""
    print("\nGenerated Codes:")
    if generated_codes:
        for i, code in enumerate(generated_codes, start=1):
            print(f"{i}. {code}")
    else:
        print("No codes generated yet.")
    print("\n")

def login_with_code():
    """Allow user to log in using a generated code."""
    print("\n--- Login with Code ---")
    if not generated_codes:
        print("No codes available. Please generate codes first.")
        return

    print("You have 15 seconds to input the correct code.")
    start_time = time.time()

    while True:
        entered_code = input("Enter Code: ").strip()

        if time.time() - start_time > 15:
            print("Session timed out. Kindly regenerate the code and try to log in again.")
            break
        
        if entered_code in generated_codes:
            print("Login Successful! Welcome!")
            break

        print("Invalid Code. Try again.")

def main_menu():
    """Display a menu to interact with the program."""
    while True:
        print("\n--- Lava Lamp Code Generator ---")
        print("1. Start Detection")
        print("2. View Generated Codes")
        print("3. Login with Code")
        print("4. Exit")

        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            start_detection()
        elif choice == '2':
            view_codes()
        elif choice == '3':
            login_with_code()
        elif choice == '4':
            print("Exiting program. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main_menu()
