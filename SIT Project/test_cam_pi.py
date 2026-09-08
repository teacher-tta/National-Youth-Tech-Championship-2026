"""
Camera test script

From your PC browser, visit:
    http://raspberrypi.local:5000
(or http://<pi-ip-address>:5000 if .local doesn't resolve on your network)

By default this scans camera indices 0-4 and streams every one that opens
successfully, each in its own tile, labeled with its index. If you already
know which index the camera is on, pass --cameras to skip the scan.
"""

import argparse

import cv2
from flask import Flask, Response, render_template_string

app = Flask(__name__)
state = {}  # populated in main() before app.run()


def probe_camera(idx):
    """Try to open camera idx and read one frame. Returns the opened
    VideoCapture on success (caller is responsible for releasing it),
    or None on failure."""
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        cap.release()
        return None
    ok, frame = cap.read()
    if not ok:
        cap.release()
        return None
    h, w = frame.shape[:2]
    print(f"  camera {idx}: OK ({w}x{h})")
    return cap


def discover_cameras(max_index):
    """Scan indices 0..max_index-1 and return {idx: VideoCapture} for every
    camera that opens and returns a frame."""
    print(f"Scanning camera indices 0-{max_index - 1}...")
    caps = {}
    for idx in range(max_index):
        cap = probe_camera(idx)
        if cap is not None:
            caps[idx] = cap
    return caps


def open_specific_cameras(indices):
    caps = {}
    for idx in indices:
        cap = probe_camera(idx)
        if cap is not None:
            caps[idx] = cap
        else:
            print(f"  camera {idx}: FAILED to open or read a frame")
    return caps


def generate_frames(idx):
    cap = state["caps"][idx]
    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        cv2.putText(frame, f"camera {idx}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")


PAGE = """
<!doctype html>
<html>
<head><title>Camera Test</title></head>
<body style="background:#111; text-align:center; font-family:sans-serif;">
  <h2 style="color:#eee;">Camera Test — {{ n }} camera(s) found</h2>
  <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:16px;">
    {% for idx in indices %}
      <div>
        <p style="color:#aaa;">Camera {{ idx }}</p>
        <img src="/video_feed/{{ idx }}" style="max-width:45vw; border:2px solid #444;">
      </div>
    {% endfor %}
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, indices=sorted(state["caps"].keys()),
                                   n=len(state["caps"]))


@app.route("/video_feed/<int:idx>")
def video_feed(idx):
    return Response(generate_frames(idx),
                     mimetype="multipart/x-mixed-replace; boundary=frame")


def main():
    parser = argparse.ArgumentParser(description="Test that Pi camera(s) are working, no inference.")
    parser.add_argument("--cameras", default=None,
                         help="Comma-separated camera indices to open, e.g. '0' or '0,1'. "
                              "If omitted, auto-scans indices 0..--scan-range.")
    parser.add_argument("--scan-range", type=int, default=5,
                         help="How many indices (0..N-1) to probe when --cameras isn't given (default 5).")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    if args.cameras:
        indices = [int(x.strip()) for x in args.cameras.split(",")]
        caps = open_specific_cameras(indices)
    else:
        caps = discover_cameras(args.scan_range)

    if not caps:
        raise SystemExit(
            "No cameras opened successfully. If you're using the official Pi Camera "
            "Module, OpenCV may not see it directly through libcamera. See the note "
            "about picamera2 as an alternative. Otherwise check `ls /dev/video*` and "
            "try passing --cameras with the index that shows up."
        )

    state["caps"] = caps

    print(f"\n{len(caps)} camera(s) working: {sorted(caps.keys())}")
    print(f"Starting server — open http://<pi-ip-or-hostname>:{args.port} in a browser")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()