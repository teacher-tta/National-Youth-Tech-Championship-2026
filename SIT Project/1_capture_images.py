"""
Usage:
    uv run capture_images.py --classes object_a object_b none

Controls:
    1, 2, 3, ...  Capture a photo for the corresponding class
    q             Quit

Captures a single square photo per key press, from the center of the frame.
At inference time the camera frame is split into three side-by-side zones
(left / center / right) and each zone is classified independently, so by
default the capture crop size is set to roughly one third of the camera's
frame width -- matching the size of each inference zone. Pass --crop-size
to override.

Images are saved to data/<class_name>/<class_name>_<NNNN>.jpg
Can run it again later to add more photos. Numbering picks up where left off.
"""

import argparse
import os

import cv2

from regions import center_square_crop


def main():
    parser = argparse.ArgumentParser(
        description="Capture labeled training images from webcam."
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        required=True,
        help="Class names, e.g. --classes object_a object_b none",
    )
    parser.add_argument(
        "--data-dir", default="data", help="Root directory to save images into"
    )
    parser.add_argument(
        "--camera", type=int, default=0, help="Camera index (default 0)"
    )
    parser.add_argument(
        "--crop-size",
        type=int,
        default=None,
        help=(
            "Side length in pixels of the square to capture. Defaults to "
            "roughly one third of the camera frame width, matching the "
            "size of each left/center/right zone used at inference."
        ),
    )
    args = parser.parse_args()

    if len(args.classes) > 9:
        raise SystemExit("This tool supports up to 9 classes (keys 1-9).")

    # Create output folders and figure out where numbering should resume from
    counters = {}
    for cls in args.classes:
        cls_dir = os.path.join(args.data_dir, cls)
        os.makedirs(cls_dir, exist_ok=True)
        existing = [f for f in os.listdir(cls_dir) if f.lower().endswith(".jpg")]
        counters[cls] = len(existing)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera index {args.camera}")

    crop_size = args.crop_size
    if crop_size is None:
        ok, probe_frame = cap.read()
        if not ok:
            raise SystemExit("Could not read a frame from the camera to size the crop.")
        crop_size = probe_frame.shape[1] // 3
        print(
            f"No --crop-size given; using {crop_size}px "
            f"(about a third of the {probe_frame.shape[1]}px-wide frame)."
        )

    key_map = {str(i + 1): cls for i, cls in enumerate(args.classes)}
    legend = "  ".join(f"[{k}] {v}" for k, v in key_map.items())
    print("Controls:", legend, "  [q] quit")

    window_name = "Capture - " + legend
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Failed to read frame from camera.")
            break

        cropped, (x1, y1, x2, y2) = center_square_crop(frame, crop_size)

        display = frame.copy()
        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.imshow(window_name, display)

        key = cv2.waitKey(1) & 0xFF
        key_char = chr(key) if key != 255 else ""

        if key_char == "q":
            break
        elif key_char in key_map:
            cls = key_map[key_char]
            counters[cls] += 1
            filename = f"{cls}_{counters[cls]:04d}.jpg"
            filepath = os.path.join(args.data_dir, cls, filename)
            cv2.imwrite(filepath, cropped)
            print(f"Saved {filepath}  (class '{cls}' total: {counters[cls]})")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
