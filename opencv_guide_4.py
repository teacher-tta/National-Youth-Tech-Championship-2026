"""
4_webcam.py

This program opens the computer's webcam and detects red-colored objects in
the video feed using contour detection. The frame is converted from BGR to
HSV color space so red colors can be detected more reliably. A mask isolates
red regions, and contours are used to find the shapes of these regions.
Small contours are ignored using a minimum area threshold to reduce noise.
A bounding rectangle is drawn around valid red objects.
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

        # Find contours in the mask
        # Contours represent the outlines of detected regions
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Loop through each detected contour
        for contour in contours:
            # Calculate the area of the contour
            area = cv2.contourArea(contour)

            # Ignore small contours to reduce noise in detection
            if area > 500:
                # Get the bounding rectangle for the contour
                x, y, w, h = cv2.boundingRect(contour)

                # Draw the rectangle around the detected red object
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Display the webcam frame with any detected bounding box
        cv2.imshow("Red Object Detection with Contours", frame)

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