"""
face_recog_module.py

Usage in a notebook:

    import face_recog_module as frm

    # ROBOT CAMERA VERSION
    # assume you already have `got` set up in the notebook
    fr_robot = frm.FaceRecognition(got, known_dir="known")

    for labels in fr_robot.run_recognition(
        min_confidence=50,
        stop_on_name="jensen", # stop when "jensen" is detected
    ):
        pass # loop ends automatically when "jensen" is seen


    # WEBCAM VERSION
    fr_cam = frm.WebcamFaceRecognition(known_dir="known", camera_index=0)

    for labels in fr_cam.run_recognition(
        min_confidence=50,
        stop_on_name="jensen",   # stop when "jensen" is detected
    ):
        pass  # interrupt the cell OR it ends when "jensen" is seen
"""

import cv2
import face_recognition
import numpy as np
import os
import math
from IPython.display import display, Image, clear_output


def face_confidence(face_distance, face_match_threshold=0.6):
    """
    Convert a face distance (from face_recognition.face_distance) into a
    human-readable confidence percentage string.
    """
    rng = (1.0 - face_match_threshold)
    linear_val = (1.0 - face_distance) / (rng * 2.0)

    if face_distance > face_match_threshold:
        return f"{round(linear_val * 100, 2)}%"
    else:
        value = (linear_val + ((1.0 - linear_val)
                 * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
        return f"{round(value, 2)}%"


class FaceRecognition:
    def __init__(
        self,
        got,
        known_dir="known",
        match_threshold=0.6,
        target_name="jensen",
        target_confidence=80.0,
    ):
        """
        Parameters
        ----------
        got : object
            An object providing at least:
                - open_camera()
                - read_camera_data()
                - mecanum_move_speed(direction, speed)
                - mecanum_stop()
        known_dir : str
            Directory containing known face images.
        match_threshold : float
            Distance threshold for face match (lower = stricter).
        target_name : str
            Name to trigger robot movement on.
        target_confidence : float
            Confidence percentage threshold to trigger movement.
        """
        self.got = got
        self.known_dir = known_dir
        self.match_threshold = match_threshold
        self.target_name = target_name
        self.target_confidence = target_confidence

        self.known_face_encodings = []
        self.known_face_names = []
        self.face_locations = []
        self.face_names = []
        self.process_current_frame = True

        self.encode_faces()

    def encode_faces(self):
        """
        Load and encode each image under `self.known_dir`,
        storing the filename (without extension) as the name.
        """
        if not os.path.isdir(self.known_dir):
            raise FileNotFoundError(f"Known faces directory not found: {self.known_dir}")

        for image in os.listdir(self.known_dir):
            if image.lower().endswith((".jpg", ".png", ".jpeg")):
                name = os.path.splitext(image)[0]
                path = os.path.join(self.known_dir, image)

                img = face_recognition.load_image_file(path)
                enc = face_recognition.face_encodings(img)

                if enc:
                    self.known_face_encodings.append(enc[0])
                    self.known_face_names.append(name)

        print("Loaded faces for:", self.known_face_names)

    def run_recognition(
        self,
        open_camera=True,
        display_output=True,
        min_confidence=0,
        stop_on_name=None,
    ):
        """
        Main loop: yields detected face labels for each displayed frame
        using the robot camera.

        Faces below min_confidence are completely ignored:
        - No label
        - No box drawn
        - Not returned in yielded results

        If stop_on_name is provided and a matching known face is detected
        (based on the raw name, not including confidence), the loop exits.
        """
        if open_camera:
            self.got.open_camera()

        while True:
            frame_data = self.got.read_camera_data()
            if not frame_data:
                break

            # Decode & mirror
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frame = cv2.flip(frame, 1)

            detected_labels = []

            # Run detection on alternate frames
            if self.process_current_frame and self.known_face_encodings:
                small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                locations = face_recognition.face_locations(rgb_small)
                encodings = face_recognition.face_encodings(rgb_small, locations)

                output_labels = []
                output_locations = []

                for loc, face_encoding in zip(locations, encodings):
                    distances = face_recognition.face_distance(
                        self.known_face_encodings, face_encoding
                    )

                    if len(distances) == 0:
                        continue  # ignore because no known faces exist

                    idx = np.argmin(distances)
                    best_dist = distances[idx]
                    match = best_dist <= self.match_threshold

                    name = self.known_face_names[idx] if match else "Unknown"
                    conf_str = face_confidence(best_dist, self.match_threshold)

                    # EARLY EXIT when a specific known face is detected
                    # (ignores confidence threshold, only requires a "match")
                    if stop_on_name and match and name == stop_on_name:
                        # Stop robot, clean up windows, and end generator
                        try:
                            self.got.mecanum_stop()
                        except Exception:
                            pass
                        cv2.destroyAllWindows()
                        return

                    try:
                        conf_val = float(conf_str.strip("%"))
                    except ValueError:
                        conf_val = 0.0

                    # Ignore faces below confidence threshold
                    if conf_val < min_confidence:
                        continue

                    # Robot logic for approaching the target
                    if name == self.target_name and conf_val > self.target_confidence:
                        self.got.mecanum_move_speed(1, 25)

                    label = f"{name} ({conf_str})"

                    output_labels.append(label)
                    output_locations.append(loc)

                # Save final filtered results
                self.face_names = output_labels
                self.face_locations = output_locations

                detected_labels = output_labels

                # Stop robot if nothing detectable
                if not output_labels:
                    self.got.mecanum_stop()

            # Toggle frame skip
            self.process_current_frame = not self.process_current_frame

            # Draw only high-confidence results (already filtered)
            for (top, right, bottom, left), label in zip(
                self.face_locations, self.face_names
            ):
                top, right, bottom, left = [v * 4 for v in (top, right, bottom, left)]
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(
                    frame,
                    (left, bottom - 35),
                    (right, bottom),
                    (0, 0, 255),
                    cv2.FILLED,
                )
                cv2.putText(
                    frame,
                    label,
                    (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.8,
                    (255, 255, 255),
                    1,
                )

            if display_output:
                _, jpeg = cv2.imencode(".jpg", frame)
                clear_output(wait=True)
                display(Image(data=jpeg.tobytes()))

            # Reuse last detections if this frame was skipped
            if not detected_labels:
                detected_labels = list(self.face_names)

            yield detected_labels

        cv2.destroyAllWindows()


class WebcamFaceRecognition(FaceRecognition):
    """
    A version of FaceRecognition that uses the local webcam via OpenCV
    instead of the robot's camera.

    Same inline display behavior, and still yields a list of labels per frame.
    Robot movement logic is removed.

    The known faces / encodings logic is reused from FaceRecognition.
    """

    def __init__(
        self,
        known_dir="known",
        match_threshold=0.6,
        camera_index=0,
    ):
        # Reuse parent's face-encoding logic; got is not used here
        super().__init__(
            got=None,
            known_dir=known_dir,
            match_threshold=match_threshold,
            target_name="",        # unused for webcam
            target_confidence=0.0, # unused for webcam
        )
        self.camera_index = camera_index

    def run_recognition(
        self,
        display_output=True,
        min_confidence=0,
        stop_on_name=None,
    ):
        """
        Main loop: yields detected face labels for each displayed frame
        using the local webcam.

        Faces below min_confidence are completely ignored:
        - No label
        - No box drawn
        - Not returned in yielded results

        If stop_on_name is provided and a matching known face is detected
        (based on the raw name, not including confidence), the loop exits.

        Stop manually with a KeyboardInterrupt in the notebook if desired.
        """
        cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Could not open webcam at index {self.camera_index}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Mirror image to act like a selfie cam
                frame = cv2.flip(frame, 1)

                detected_labels = []

                # Run detection on alternate frames
                if self.process_current_frame and self.known_face_encodings:
                    small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                    locations = face_recognition.face_locations(rgb_small)
                    encodings = face_recognition.face_encodings(rgb_small, locations)

                    output_labels = []
                    output_locations = []

                    for loc, face_encoding in zip(locations, encodings):
                        distances = face_recognition.face_distance(
                            self.known_face_encodings, face_encoding
                        )

                        if len(distances) == 0:
                            continue  # no known faces

                        idx = np.argmin(distances)
                        best_dist = distances[idx]
                        match = best_dist <= self.match_threshold

                        name = self.known_face_names[idx] if match else "Unknown"
                        conf_str = face_confidence(best_dist, self.match_threshold)

                        # EARLY EXIT when a specific known face is detected
                        # (ignores confidence threshold, only requires a "match")
                        if stop_on_name and match and name == stop_on_name:
                            # Let finally block handle cap/destroyAllWindows
                            return

                        try:
                            conf_val = float(conf_str.strip("%"))
                        except ValueError:
                            conf_val = 0.0

                        # Ignore faces below confidence threshold
                        if conf_val < min_confidence:
                            continue

                        label = f"{name} ({conf_str})"
                        output_labels.append(label)
                        output_locations.append(loc)

                    # Save final filtered results
                    self.face_names = output_labels
                    self.face_locations = output_locations

                    detected_labels = output_labels

                # Toggle frame skip
                self.process_current_frame = not self.process_current_frame

                # Draw only high-confidence results (already filtered)
                for (top, right, bottom, left), label in zip(
                    self.face_locations, self.face_names
                ):
                    top, right, bottom, left = [v * 4 for v in (top, right, bottom, left)]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.rectangle(
                        frame,
                        (left, bottom - 35),
                        (right, bottom),
                        (0, 0, 255),
                        cv2.FILLED,
                    )
                    cv2.putText(
                        frame,
                        label,
                        (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.8,
                        (255, 255, 255),
                        1,
                    )

                if display_output:
                    _, jpeg = cv2.imencode(".jpg", frame)
                    clear_output(wait=True)
                    display(Image(data=jpeg.tobytes()))

                # Reuse last detections if this frame was skipped
                if not detected_labels:
                    detected_labels = list(self.face_names)

                yield detected_labels

        finally:
            cap.release()
            cv2.destroyAllWindows()
