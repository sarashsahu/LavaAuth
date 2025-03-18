import cv2
import numpy as np
import hashlib
import time
from datetime import datetime

# Store generated codes (only in memory, not in a file)
generated_codes = []
code_generation_start_time = None  # Track when code generation started

def generate_code(bubble_data):
    """Generate a unique code based on the bubble data (position, size, etc.) and the current date-time."""
    # Get the current date and time
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create a string that includes both bubble data and current date-time
    bubble_string = "".join([f"{x}_{y}_{r}" for x, y, r in bubble_data]) + current_datetime
    
    # Generate a hashed code
    hashed_code = hashlib.sha256(bubble_string.encode()).hexdigest()[:8]
    return f"{hashed_code} - {current_datetime}"  # Return code with datetime

def detect_bubbles(frame):
    """Detect bubbles in the given frame and return their properties."""
    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply GaussianBlur to reduce noise
    blurred = cv2.GaussianBlur(gray, (11, 11), 0)

    # Apply threshold to simplify the image
    _, thresh = cv2.threshold(blurred, 50, 255, cv2.THRESH_BINARY)

    # Detect edges using Canny Edge Detector
    edges = cv2.Canny(thresh, 30, 150)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bubble_data = []  # To store bubble information

    for contour in contours:
        # Calculate the minimum enclosing circle for each contour
        ((x, y), radius) = cv2.minEnclosingCircle(contour)
        area = cv2.contourArea(contour)

        # Filter out noise
        if radius > 20 and area > 300:  # Adjust thresholds
            bubble_data.append((int(x), int(y), int(radius)))
            # Draw detected bubbles
            cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)

    return frame, bubble_data

def start_detection_for_5_seconds():
    """Start video capture, detect bubbles, and generate codes for only 5 seconds."""
    global generated_codes, code_generation_start_time
    cap = cv2.VideoCapture(0)
    print("Starting 5-second detection... Press 'q' or 'ESC' to stop.")
    start_time = time.time()
    code_generation_start_time = start_time  # Record the start time of code generation

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Unable to capture video.")
            break

        # Detect bubbles
        processed_frame, bubble_data = detect_bubbles(frame)

        # Generate code if at least 3 bubbles are detected
        current_time = time.time()
        if bubble_data and len(bubble_data) >= 3 and (current_time - start_time <= 5):  # Only generate within 5 seconds
            code = generate_code(bubble_data)
            if code not in generated_codes:
                print("Generated Code:", code)
                generated_codes.append(code)

        # Display the processed frame
        cv2.imshow("Lava Lamp Bubble Detector", processed_frame)

        # Break the loop when 'q' or ESC is pressed, or after 5 seconds
        if time.time() - start_time > 5:
            print("5 seconds elapsed. Stopping code generation.")
            break

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # Check for 'q' or ESC key
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
    """Allow user to log in using a generated code within 10 seconds."""
    print("\n--- Login with Code ---")
    if not generated_codes:
        print("No codes available. Please generate codes first.")
        return

    print("You have 10 seconds to input the correct code.")
    start_time = time.time()

    while True:
        entered_code = input("Enter Code: ").strip()

        # Check if the entered code is valid and if the time is within the 10 seconds
        if time.time() - start_time > 10:
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
            start_detection_for_5_seconds()
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
