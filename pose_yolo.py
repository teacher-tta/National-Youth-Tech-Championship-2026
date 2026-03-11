from ultralytics import YOLO
import cv2
import numpy as np
from ugot import ugot
import time

try:
    from IPython.display import display, clear_output, Image
    _HAS_IPYTHON = True
except ImportError:
    _HAS_IPYTHON = False

COCO_KEYPOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

def draw_deadzone_band(
    frame,
    kps,
    up_margin_factor: float,
    down_margin_factor: float,
    min_conf: float = 0.3,
):
    """
    Draw a horizontal 'deadzone' band between the up/down thresholds
    based on shoulder + (optional) hip keypoints.
    """
    h, w, _ = frame.shape

    # Indices for keypoints
    idx = {name: i for i, name in enumerate(COCO_KEYPOINTS)}

    def get_point(name):
        i = idx.get(name, None)
        if i is None:
            return None
        x, y, c = kps[i]
        if c < min_conf:
            return None
        return np.array([x, y], dtype=np.float32)

    ls = get_point("left_shoulder")
    rs = get_point("right_shoulder")
    lh = get_point("left_hip")
    rh = get_point("right_hip")

    # Need at least both shoulders
    if ls is None or rs is None:
        return

    # Torso length (same idea as classify_pose)
    torso_lengths = []
    if lh is not None:
        torso_lengths.append(np.linalg.norm(ls - lh))
    if rh is not None:
        torso_lengths.append(np.linalg.norm(rs - rh))
    if torso_lengths:
        torso = float(np.mean(torso_lengths))
    else:
        torso = float(np.linalg.norm(ls - rs))  # shoulder width fallback

    if torso < 1e-3:
        return

    ls_y, rs_y = ls[1], rs[1]
    up_margin = up_margin_factor * torso
    down_margin = down_margin_factor * torso

    # Vertical bounds of the deadzone, based on both shoulders
    top_y = int(min(ls_y - up_margin, rs_y - up_margin))
    bot_y = int(max(ls_y + down_margin, rs_y + down_margin))

    # Clamp to frame
    top_y = max(0, min(h - 1, top_y))
    bot_y = max(0, min(h - 1, bot_y))
    if bot_y <= top_y:
        return

    # Lightly shaded band
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, top_y), (w, bot_y), (255, 255, 0), -1)  # yellow-ish
    alpha = 0.2
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)

    # Draw top and bottom boundary lines
    cv2.line(frame, (0, top_y), (w, top_y), (0, 255, 255), 2)
    cv2.line(frame, (0, bot_y), (w, bot_y), (0, 255, 255), 2)

    # Optional label
    cv2.putText(
        frame,
        "DEADZONE",
        (10, max(30, top_y - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2,
    )


def classify_pose(
    keypoints,
    up_margin_factor=0.25,
    down_margin_factor=0.25,
    min_conf: float = 0.3,
):
    """
    Classify pose into FORWARD / BACKWARD / LEFT / RIGHT / EXIT / PICKUP / NONE.

    - FORWARD: both hands up
    - BACKWARD: both hands down
    - LEFT: only left hand up
    - RIGHT: only right hand up
    - EXIT: both hands in the vertical deadzone, close together
    - PICKUP: both hands in the vertical deadzone, spread far apart (arms wide)
    """

    def get(name):
        if name not in keypoints:
            return None
        x, y, c = keypoints[name]
        if c < min_conf:
            return None
        return np.array([x, y], dtype=np.float32)

    ls = get("left_shoulder")
    rs = get("right_shoulder")
    lw = get("left_wrist")
    rw = get("right_wrist")
    lh = get("left_hip")
    rh = get("right_hip")

    # Need at least shoulders + wrists
    if not all([ls is not None, rs is not None, lw is not None, rw is not None]):
        return "NONE"

    # ----- Compute a scale (torso length) so thresholds adapt to your size -----
    torso_lengths = []
    if lh is not None:
        torso_lengths.append(np.linalg.norm(ls - lh))
    if rh is not None:
        torso_lengths.append(np.linalg.norm(rs - rh))
    if torso_lengths:
        torso = float(np.mean(torso_lengths))
    else:
        torso = float(np.linalg.norm(ls - rs))  # shoulder width fallback

    if torso < 1e-3:
        return "NONE"

    # y-axis: smaller y = higher in image
    ls_y, rs_y = ls[1], rs[1]
    lw_y, rw_y = lw[1], rw[1]

    # Margins for "up" / "down"
    up_margin = up_margin_factor * torso
    down_margin = down_margin_factor * torso

    # Hand states
    left_up   = lw_y < ls_y - up_margin
    right_up  = rw_y < rs_y - up_margin

    left_down  = lw_y > ls_y + down_margin
    right_down = rw_y > rs_y + down_margin

    # Deadzone: neither up nor down
    left_mid  = not left_up and not left_down
    right_mid = not right_up and not right_down

    # Horizontal distance between wrists
    wrist_dx = abs(lw[0] - rw[0])

    # -------- EXIT POSE (deadzone + close together) --------
    # Hands between up/down thresholds AND close together horizontally
    exit_pose = (
        left_mid and right_mid and
        wrist_dx < 0.4 * torso  # tweak 0.4 if needed
    )
    if exit_pose:
        return "EXIT"

    # -------- PICKUP POSE (deadzone + spread out) --------
    # Arms roughly at shoulder height (deadzone) but far apart horizontally.
    pickup_pose = (
        left_mid and right_mid and
        wrist_dx > 2.5 * torso  # tweak if needed
    )
    if pickup_pose:
        return "PICKUP"

    # -------- Movement poses --------
    # Both up  -> FORWARD
    if left_up and right_up:
        return "FORWARD"
    # Both down -> BACKWARD
    elif left_down and right_down:
        return "BACKWARD"
    # Only left hand up -> LEFT
    elif left_up and not right_up:
        return "LEFT"
    # Only right hand up -> RIGHT
    elif right_up and not left_up:
        return "RIGHT"
    else:
        return "NONE"


def handle_pickup(got):
    if got is None:
        return
    
    got.mechanical_clamp_release()
    time.sleep(0.2)
    got.mechanical_joint_control(0, 45, 45, 500)
    time.sleep(0.5)
    got.mechanical_joint_control(0, 0, -90, 500)
    time.sleep(0.7)
    got.mechanical_clamp_close()
    time.sleep(0.5)
    got.mechanical_joint_control(0, 45, 45, 500)
    time.sleep(0.5)


def run_pose_control(
    forward_speed: int = 30,
    backward_speed: int = 30,
    turn_speed: int = 45,
    camera_index: int = 0,
    model_path: str = "yolov8n-pose.pt",
    up_margin_factor: float = 0.1,
    down_margin_factor: float = 0.1,
    min_conf: float = 0.3,
    enable_robot: bool = True,
    debounce_frames: int = 5,
    got=None,
):
    """
    Windowed version (cv2.imshow). Best for running as a normal script.
    """

    # Only create a robot if we don't already have one
    if enable_robot and got is None:
        got = ugot.UGOT()

    model = YOLO(model_path)
    cap = cv2.VideoCapture(camera_index)

    last_raw_command = "NONE"
    stable_command = "NONE"
    stable_count = 0

    prev_stable_command = "NONE"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)
        raw_command = "NONE"

        if len(results) > 0:
            r = results[0]
            if r.keypoints is not None and len(r.keypoints) > 0:
                kps = r.keypoints[0].data[0].cpu().numpy()

                keypoints_dict = {}
                for i, name in enumerate(COCO_KEYPOINTS):
                    x, y, c = kps[i]
                    keypoints_dict[name] = (float(x), float(y), float(c))

                raw_command = classify_pose(
                    keypoints_dict,
                    up_margin_factor=up_margin_factor,
                    down_margin_factor=down_margin_factor,
                    min_conf=min_conf,
                )

                # --- draw the deadzone band based on shoulders/hips ---
                draw_deadzone_band(
                    frame,
                    kps,
                    up_margin_factor=up_margin_factor,
                    down_margin_factor=down_margin_factor,
                    min_conf=min_conf,
                )

                # draw keypoints
                for x, y, c in kps:
                    if c > min_conf:
                        cv2.circle(frame, (int(x), int(y)), 4, (0, 255, 0), -1)

        # Debounce
        if raw_command == last_raw_command:
            stable_count += 1
        else:
            last_raw_command = raw_command
            stable_count = 1

        if stable_count >= debounce_frames:
            stable_command = raw_command

        cv2.putText(frame, f"CMD: {stable_command}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("YOLO Pose Control", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

        # Exit gesture: stop robot and exit loop
        if stable_command == "EXIT":
            if enable_robot and got is not None:
                got.mecanum_stop()
            break

        # Normal robot control
        if enable_robot and got is not None:
            if stable_command == "FORWARD":
                got.mecanum_move_speed(0, forward_speed)
            elif stable_command == "BACKWARD":
                got.mecanum_move_speed(1, backward_speed)
            elif stable_command == "LEFT":
                got.mecanum_turn_speed(2, turn_speed)
            elif stable_command == "RIGHT":
                got.mecanum_turn_speed(3, turn_speed)
            elif stable_command == "PICKUP":
                # Only trigger once when we *enter* the PICKUP state
                if prev_stable_command != "PICKUP":
                    handle_pickup(got)
            else:
                got.mecanum_stop()

        # Update previous stable command at the end of the loop
        prev_stable_command = stable_command


    cap.release()
    cv2.destroyAllWindows()


def run_pose_control_inline(
    robot_ip: str = '192.168.1.217',
    forward_speed: int = 30,
    backward_speed: int = 30,
    turn_speed: int = 45,
    camera_index: int = 0,
    model_path: str = "yolov8n-pose.pt",
    up_margin_factor: float = 0.1,
    down_margin_factor: float = 0.1,
    min_conf: float = 0.3,
    enable_robot: bool = True,
    debounce_frames: int = 5,
    max_frames: int | None = None,
    got=None,
):
    if not _HAS_IPYTHON:
        raise RuntimeError("run_pose_control_inline requires IPython/Jupyter environment.")

    # Only create/initialize if one isn't provided
    if enable_robot and got is None:
        got = ugot.UGOT()
        got.initialize(robot_ip)

    model = YOLO(model_path)
    cap = cv2.VideoCapture(camera_index)

    last_raw_command = "NONE"
    stable_command = "NONE"
    stable_count = 0
    frame_idx = 0

    prev_stable_command = "NONE"

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = model(frame, verbose=False)
            raw_command = "NONE"

            if len(results) > 0:
                r = results[0]
                if r.keypoints is not None and len(r.keypoints) > 0:
                    kps = r.keypoints[0].data[0].cpu().numpy()

                    keypoints_dict = {}
                    for i, name in enumerate(COCO_KEYPOINTS):
                        x, y, c = kps[i]
                        keypoints_dict[name] = (float(x), float(y), float(c))

                    raw_command = classify_pose(
                        keypoints_dict,
                        up_margin_factor=up_margin_factor,
                        down_margin_factor=down_margin_factor,
                        min_conf=min_conf,
                    )

                    # --- draw the deadzone band ---
                    draw_deadzone_band(
                        frame,
                        kps,
                        up_margin_factor=up_margin_factor,
                        down_margin_factor=down_margin_factor,
                        min_conf=min_conf,
                    )

                    for x, y, c in kps:
                        if c > min_conf:
                            cv2.circle(frame, (int(x), int(y)), 4, (0, 255, 0), -1)

            # Debounce
            if raw_command == last_raw_command:
                stable_count += 1
            else:
                last_raw_command = raw_command
                stable_count = 1

            if stable_count >= debounce_frames:
                stable_command = raw_command

            cv2.putText(frame, f"CMD: {stable_command}", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            _, jpeg = cv2.imencode(".jpg", frame)
            clear_output(wait=True)
            display(Image(data=jpeg.tobytes()))

            # Exit gesture
            if stable_command == "EXIT":
                if enable_robot and got is not None:
                    got.mecanum_stop()
                break

            # Normal robot control
            if enable_robot and got is not None:
                if stable_command == "FORWARD":
                    got.mecanum_move_speed(0, forward_speed)
                elif stable_command == "BACKWARD":
                    got.mecanum_move_speed(1, backward_speed)
                elif stable_command == "LEFT":
                    got.mecanum_turn_speed(2, turn_speed)
                elif stable_command == "RIGHT":
                    got.mecanum_turn_speed(3, turn_speed)
                elif stable_command == "PICKUP":
                    # Only trigger once when we *enter* the PICKUP state
                    if prev_stable_command != "PICKUP":
                        handle_pickup(got)
                else:
                    got.mecanum_stop()

            # Update previous stable command at the end of the loop
            prev_stable_command = stable_command

            frame_idx += 1
            if max_frames is not None and frame_idx >= max_frames:
                break

    finally:
        cap.release()
        if enable_robot and got is not None:
            got.mecanum_stop()