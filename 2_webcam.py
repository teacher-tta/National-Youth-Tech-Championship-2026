"""
2_webcam.py

This program opens the computer's webcam and displays the live video feed.
In addition to showing the webcam image, it shows you how to draw a rectangle 
on the frame and overlay text. 
"""

import cv2  # Import OpenCV library for webcam capture and drawing functions


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

        # Draw a rectangle on the frame
        # Parameters: (image, top-left corner, bottom-right corner, color, thickness)
        cv2.rectangle(frame, (50, 50), (300, 200), (0, 255, 0), 2)

        # Add text to the frame
        # Parameters: (image, text, position, font, font scale, color, thickness)
        cv2.putText(
            frame,
            "Hello OpenCV",
            (60, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            2
        )

        # Display the modified frame in a window
        cv2.imshow("Webcam Feed", frame)

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