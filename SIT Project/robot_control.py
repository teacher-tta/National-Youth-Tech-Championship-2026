"""
robot_control.py — Robot action dispatch.

Called from 4_infer_RPI.py whenever a region's classifier recognizes
something other than the "none" class. Fill in the placeholder functions
below with your actual got.* calls.

This module is intentionally synchronous / blocking: infer_pi.py calls
handle_detection() and waits for it to return before grabbing the next
camera frame. That means only one robot action ever runs at a time, and
the live feed pauses for the duration of the action -- once this function
returns, control passes back to the inference loop automatically.
"""

import time

from ugot import ugot

from line_follow import follow_line

# ---------------------------------------------------------------------------
# Connection -- created once, here at module load, and shared by every
# action function below via the module-level `got` object. connect() does
# the actual handshake and is called exactly once, from 4_infer_RPI.py's
# main(), before the camera loop starts. Do NOT call got.initialize() inside
# an action function or handle_detection() -- that would reconnect on every
# single detection.
# ---------------------------------------------------------------------------

got = ugot.UGOT()

DEFAULT_ROBOT_IP = "192.168.100.245"  # e.g. "192.168.1.42"
_connected = False


def connect(ip_address=DEFAULT_ROBOT_IP):
    """Connect to the robot and load the models it needs. Call this once at
    startup -- every action function below assumes `got` is already
    connected by the time handle_detection() is called."""
    global _connected
    if _connected:
        return
    print(f"[robot] Connecting to UGOT at {ip_address} ...")
    got.initialize(ip_address)
    got.open_camera()  # needed by follow_line()'s got.read_camera_data()
    _connected = True
    print("[robot] Connected.")

# ---------------------------------------------------------------------------
# Map (region, class_name) -> action function. Add one entry per
# region/object combination you want the robot to react to. Region names
# are "Left", "Center", "Right" (see regions.py); class names are whatever
# your data/<class_name>/ folders were named when you captured training
# images.
# ---------------------------------------------------------------------------


def action_left_monkey():
    print("[robot] Left monkey detected -- starting line follow")
    follow_line(got)
    print("[robot] Line follow finished, handing control back to inference loop")


def action_center_monkey():
    print("[robot] TODO: replace with real got.* calls")
    time.sleep(0.5)


def action_right_monkey():
    print("[robot] TODO: replace with real got.* calls")
    time.sleep(0.5)


def action_default(region, label):
    """Fallback used when no specific (region, label) entry is registered
    in ACTIONS below. Replace or delete once you've filled in real actions
    for everything you care about."""
    print(f"[robot] No action registered for {region}: {label} -- add one to ACTIONS")
    time.sleep(0.2)


ACTIONS = {
    ("Left", "monkey"): action_left_monkey,
    ("Center", "monkey"): action_center_monkey,
    ("Right", "monkey"): action_right_monkey,
    # Add more (region, class_name) -> function pairs here.
}


def handle_detection(region, label, confidence=None):
    """
    Entry point called by 4_infer_RPI.py.

    region:      "Left" | "Center" | "Right"
    label:       the recognized class name, e.g. "monkey"
    confidence:  softmax confidence of the prediction (0-1), optional

    Blocks until the robot action finishes, then returns -- at which point
    the inference loop that called this resumes on its own.
    """
    conf_str = f" (confidence={confidence:.0%})" if confidence is not None else ""
    print(f"[robot] Handling detection: {region} -> {label}{conf_str}")

    action = ACTIONS.get((region, label))
    if action is not None:
        action()
    else:
        action_default(region, label)

    print("[robot] Action complete, returning control to inference loop.")


if __name__ == "__main__":
    # Quick manual test without running the full camera pipeline:
    #   python robot_control.py
    # Once the action functions above have real got.* calls in them, this
    # will actually move the robot -- update DEFAULT_ROBOT_IP first.
    connect()
    handle_detection("Left", "monkey", confidence=0.94)