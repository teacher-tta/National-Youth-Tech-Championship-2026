"""
Usage:
    uv run 4_infer_RPi.py --none-class none

infer_pi.py — Run real-time ONNX inference on the Raspberry Pi and stream the
annotated camera feed to a browser (MJPEG via Flask), so you can watch live
predictions without any extra streaming software.

The camera frame is split into three zones -- left, center, right -- and
each zone is classified independently, e.g. "Left: monkey, Center: bear,
Right: cat".

When a zone recognizes something other than the "none" class, its region
and class name are handed off to handle_detection() in robot_control.py,
which blocks until the robot action finishes before this script resumes.

Usage (on the Pi, after scp'ing model.onnx + classes.json into ./models/,
and regions.py + robot_control.py into the script directory):
    python infer_pi.py

Then from your browser, visit:
    http://raspberrypi.local:5000
(or http://<pi-ip-address>:5000 if .local doesn't resolve on your network)

The latest per-zone predictions are also available as JSON at /status, in
case you want another program (or a second Pi) to poll them.
"""

import argparse
import json

import cv2
import numpy as np
import onnxruntime as ort
from flask import Flask, Response, jsonify, render_template_string

from regions import REGION_NAMES, three_square_regions
from robot_control import connect, handle_detection

IMAGE_SIZE = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

app = Flask(__name__)
state = {}  # populated in main() before app.run()
latest = {"results": []}  # updated each frame, read by /status


def softmax(x):
    e = np.exp(x - np.max(x))
    return e / e.sum()


def preprocess(cropped_bgr):
    """Match the resize/normalize steps used in train.py."""
    img = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
    img = img.astype(np.float32) / 255.0
    img = (img - MEAN) / STD
    img = img.transpose(2, 0, 1)  # HWC -> CHW
    return np.expand_dims(img, axis=0).astype(np.float32)


def predict(session, input_name, cropped_bgr):
    tensor = preprocess(cropped_bgr)
    outputs = session.run(None, {input_name: tensor})
    probs = softmax(outputs[0][0])
    idx = int(np.argmax(probs))
    return idx, float(probs[idx])


def predict_regions(session, input_name, class_names, frame, crop_size):
    """
    Run prediction on the left/center/right zones of a BGR frame.
    Returns a list of (name, label, confidence, box) tuples in
    Left, Center, Right order.
    """
    results = []
    for name, crop, box in three_square_regions(frame, crop_size):
        idx, confidence = predict(session, input_name, crop)
        results.append((name, class_names[idx], confidence, box))
    return results


def summarize(results):
    return ", ".join(f"{name}: {label}" for name, label, _confidence, _box in results)


def generate_frames():
    cap = state["cap"]
    session = state["session"]
    input_name = state["input_name"]
    class_names = state["class_names"]
    crop_size = state["crop_size"]
    none_class = state["none_class"]
    last_triggered = state["last_triggered"]

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        results = predict_regions(session, input_name, class_names, frame, crop_size)
        latest["results"] = [
            {"zone": name, "label": label, "confidence": confidence}
            for name, label, confidence, _box in results
        ]

        for name, label, confidence, (x1, y1, x2, y2) in results:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            text = f"{name}: {label} ({confidence:.0%})"
            cv2.putText(frame, text, (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        summary = summarize(results)
        cv2.putText(frame, summary, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

        # Hand off to the robot for any zone whose detection just changed to
        # something other than "none". Triggering only on a *change* (rather
        # than every frame) means an object sitting in view doesn't re-fire
        # the same action dozens of times a second -- it fires once, then
        # again only if the zone's prediction changes to something else.
        #
        # handle_detection() blocks until the robot is done, which pauses
        # this generator (and therefore the video feed) until it returns --
        # control comes back here automatically once the function exits.
        for name, label, confidence, _box in results:
            if label == none_class:
                last_triggered[name] = None
                continue
            if last_triggered[name] != label:
                handle_detection(name, label, confidence)
                last_triggered[name] = label


PAGE = """
<!doctype html>
<html>
<head><title>Live Classification</title></head>
<body style="background:#111; text-align:center; font-family:sans-serif;">
  <h2 style="color:#eee;">Live Classification Feed</h2>
  <img src="/video_feed" style="max-width:95%; border:2px solid #444;">
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                     mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/status")
def status():
    """Latest per-zone predictions as JSON."""
    return jsonify(latest["results"])


def main():
    parser = argparse.ArgumentParser(description="Stream live ONNX inference from the Pi.")
    parser.add_argument("--model", default="models/model.onnx")
    parser.add_argument("--classes", default="models/classes.json")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    parser.add_argument(
        "--crop-size", type=int, default=400,
        help=(
            "Side length in pixels of each left/center/right square zone, "
            "matching capture_images.py (default 400)"
        ),
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--none-class", default="none",
        help=(
            "Class name treated as 'nothing recognized'. A zone predicting "
            "this class never triggers the robot (default: none)"
        ),
    )
    parser.add_argument(
        "--robot-ip", default=None,
        help="IP address of the UGOT robot. If omitted, uses DEFAULT_ROBOT_IP in robot_control.py",
    )
    args = parser.parse_args()

    with open(args.classes) as f:
        class_names = json.load(f)

    if args.none_class not in class_names:
        print(
            f"Warning: --none-class '{args.none_class}' is not one of the "
            f"trained classes {class_names} -- every detection will be "
            "treated as non-none and will trigger the robot."
        )

    session = ort.InferenceSession(args.model, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    if args.robot_ip:
        connect(args.robot_ip)
    else:
        connect()  # uses DEFAULT_ROBOT_IP from robot_control.py

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit(
            f"Could not open camera index {args.camera}. If you're using the official "
            "Pi Camera Module and this fails, OpenCV may not see it directly through "
            "libcamera — see the note in the chat about picamera2 as an alternative."
        )

    state["cap"] = cap
    state["session"] = session
    state["input_name"] = input_name
    state["class_names"] = class_names
    state["crop_size"] = args.crop_size
    state["none_class"] = args.none_class
    state["last_triggered"] = {name: None for name in REGION_NAMES}

    print(f"Classes: {class_names}")
    print(f"Starting server — open http://<pi-ip-or-hostname>:{args.port} in a browser")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()