"""
3_webcam.py

This program opens the computer's webcam and detects red-colored objects in
the video feed. The frame is converted from BGR color space to HSV so that
red colors can be detected more reliably. A mask is created to isolate red
regions, and if red pixels are detected, a bounding rectangle is drawn around
the detected red area.
"""

import cv2  # Import OpenCV library for webcam capture and drawing functions
import numpy as np  # Import NumPy for numerical operations and array handling


def main():
    # Create a VideoCapture object to access the default webcam (index 0)
    cap = cv2.VideoCapture(0)

    # Check if the webcam opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    # Start a loop to continuously capture frames from the webcam
    while True:
        # Read a frame from the webcam
        # ret = True if frame captured successfully
        # frame = the image frame captured from the webcam
        ret, frame = cap.read()

        # If the frame could not be captured, exit the loop
        if not ret:
            print("Failed to grab frame")
            break

        # Convert the frame from BGR color space to HSV color space
        # HSV makes it easier to detect specific colors
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define the lower and upper HSV bounds for detecting red
        lower_red = np.array([0, 120, 70])
        upper_red = np.array([10, 255, 255])

        # Create a mask that keeps only the red colors within the range
        mask = cv2.inRange(hsv, lower_red, upper_red)

        # Find the coordinates of all pixels where the mask is active
        ys, xs = np.where(mask > 0)

        # If red pixels are found, draw a bounding rectangle around them
        if len(xs) > 0 and len(ys) > 0:
            x_min, x_max = xs.min(), xs.max()
            y_min, y_max = ys.min(), ys.max()

            # Draw the rectangle on the original frame
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        # Display the webcam frame with any detected bounding box
        cv2.imshow("Red Object Detection", frame)

        # Wait 1 ms for a key press
        # If the 'q' key is pressed, exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the webcam when the program ends
    cap.release()

    # Close all OpenCV windows
    cv2.destroyAllWindows()


# Run the main function only if this script is executed directly
if __name__ == "__main__":
    main()