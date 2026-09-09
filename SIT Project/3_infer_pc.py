"""
Usage:
    uv run 3_infer_pc.py --webcam

Move the models folder over to the Pi with

scp -r models ugot001@TTARaspberryPi[#].local:~/Desktop/[FOLDER NAME]
"""

import argparse
import json

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from regions import REGION_NAMES, three_square_regions
from robot_control import connect, handle_detection

IMAGE_SIZE = 224

transform = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def predict(model, device, class_names, pil_image):
    tensor = transform(pil_image).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.nn.functional.softmax(outputs, dim=1)[0]
        idx = probs.argmax().item()
    return class_names[idx], probs[idx].item()


def predict_regions(model, device, class_names, frame_rgb, crop_size):
    """
    Run prediction on the left/center/right zones of an RGB frame (numpy array).
    Returns a list of (name, label, confidence, box) tuples in
    Left, Center, Right order.
    """
    results = []
    for name, crop, box in three_square_regions(frame_rgb, crop_size):
        pil_crop = Image.fromarray(crop)
        label, confidence = predict(model, device, class_names, pil_crop)
        results.append((name, label, confidence, box))
    return results


def summarize(results):
    return ", ".join(f"{name}: {label}" for name, label, _confidence, _box in results)


def main():
    parser = argparse.ArgumentParser(
        description="Run inference with the trained model on Mac."
    )
    parser.add_argument("--model", default="models/model.pt")
    parser.add_argument("--classes", default="models/classes.json")
    parser.add_argument("--image", help="Path to a single image to classify")
    parser.add_argument(
        "--webcam", action="store_true", help="Run live classification from webcam"
    )
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument(
        "--crop-size",
        type=int,
        default=400,
        help=(
            "Side length in pixels of each left/center/right square zone, "
            "matching capture_images.py (default 400)"
        ),
    )
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

    device = get_device()
    print(f"Using device: {device}")
    model = torch.jit.load(args.model, map_location=device)
    model.eval()

    if args.image:
        img = Image.open(args.image).convert("RGB")
        frame_rgb = np.array(img)
        results = predict_regions(model, device, class_names, frame_rgb, args.crop_size)
        print(f"Prediction: {summarize(results)}")
        for name, label, confidence, _box in results:
            print(f"  {name}: {label}  (confidence: {confidence:.2%})")
        return

    if args.webcam:
        if args.robot_ip:
            connect(args.robot_ip)
        else:
            connect()  # uses DEFAULT_ROBOT_IP from robot_control.py

        last_triggered = {name: None for name in REGION_NAMES}

        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            raise SystemExit(f"Could not open camera index {args.camera}")
        print("Press 'q' to quit.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = predict_regions(model, device, class_names, frame_rgb, args.crop_size)

            display = frame.copy()
            for name, label, confidence, (x1, y1, x2, y2) in results:
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                text = f"{name}: {label} ({confidence:.0%})"
                cv2.putText(
                    display, text, (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                )

            summary = summarize(results)
            cv2.putText(
                display, summary, (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 2,
            )
            cv2.imshow("Live classification - press q to quit", display)

            # Hand off to the robot for any zone whose detection just changed to
            # something other than "none". Triggering only on a *change* (rather
            # than every frame) means an object sitting in view doesn't re-fire
            # the same action dozens of times a second -- it fires once, then
            # again only if the zone's prediction changes to something else.
            #
            # handle_detection() blocks until the robot is done, which pauses
            # this loop (and therefore the preview window) until it returns --
            # control comes back here automatically once the function exits.
            for name, label, confidence, _box in results:
                if label == args.none_class:
                    last_triggered[name] = None
                    continue
                if last_triggered[name] != label:
                    handle_detection(name, label, confidence)
                    last_triggered[name] = label

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        return

    parser.error("Specify either --image or --webcam")


if __name__ == "__main__":
    main()