"""
1_webcam.py

This program opens your computer's webcam using OpenCV and displays the live
video feed in a window. The program continuously reads frames from the webcam
and shows them on the screen until you press the 'q' key to quit.
"""

import cv2  # Import the OpenCV library for computer vision and webcam access


def main():
    # Create a VideoCapture object to access the default webcam (index 0)
    cap = cv2.VideoCapture(0)

    # Check if the webcam opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    # Start an infinite loop to continuously capture frames from the webcam
    while True:
        # Read a frame from the webcam
        # ret = True if frame was successfully captured
        # frame = the captured image frame
        ret, frame = cap.read()

        # If the frame was not captured successfully, exit the loop
        if not ret:
            print("Failed to grab frame")
            break

        # Display the captured frame in a window titled "Webcam Feed"
        cv2.imshow("Webcam Feed", frame)

        # Wait 1 millisecond for a key press
        # If the 'q' key is pressed, exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the webcam so other programs can use it
    cap.release()

    # Close all OpenCV windows
    cv2.destroyAllWindows()


# This ensures main() only runs if this file is executed directly
# and not when it is imported as a module
if __name__ == "__main__":
    main()