from dataclasses import dataclass

import cv2
import numpy as np
from ugot import ugot

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROBOT_IP = "192.168.100.245"
SHOW_DEBUG = True 

DIR_LEFT = 2
DIR_RIGHT = 3


@dataclass
class Config:
    # Speed
    max_speed: float = 35  # speed on straights (steering near 0)
    min_speed: float = 20  # speed floor on sharp turns
    steering_at_min_speed: float = 15  # |steering| at which speed bottoms out at min_speed

    # PD steering
    kp: float = 0.5
    kd: float = 0.2

    # Smoothing / anti-jerk
    error_deadband: float = 10  # px; errors smaller than this are treated as 0
    smoothing_alpha: float = 0.3  # EMA weight for new readings (0-1, lower = smoother)
    max_steering_delta: float = 20  # max change in steering allowed per frame
    max_speed_delta: float = 4  # max change in speed allowed per frame
    max_steering: float = 70  # hard ceiling on |steering| sent to hardware,
    # applied after smoothing/rate-limiting (rate-limiting alone doesn't cap
    # the value it converges to)

    # Lost-line handling
    lost_line_threshold: int = 5  # frames with no line before triggering search

    # End-of-course stop marker (an orange strip of tape laid across the line)
    # min fraction of the *whole* frame area the orange blob must cover to
    # trigger a stop -- tune against the fill_frac values follow_line()
    # prints when a marker is in view
    stop_color_min_area_frac: float = 0.02
    # min (blob area / bounding-box area); keeps a scattered handful of
    # orange pixels from being mistaken for one solid marker
    stop_color_min_extent: float = 0.5
    # HSV bounds for "orange" (OpenCV's hue range is 0-179, not 0-359).
    # These are a starting point -- lighting varies, so watch the "Mask"
    # debug window and narrow/widen the range until only the marker shows
    # up white.
    stop_color_lower_hsv: tuple = (5, 150, 100)
    stop_color_upper_hsv: tuple = (25, 255, 255)


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------


def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def detect_stop_color(
    frame,
    lower_hsv=(5, 150, 100),
    upper_hsv=(25, 255, 255),
    min_area_frac=0.02,
    min_extent=0.5,
):
    """
    Look for a solid patch of a specific color anywhere in `frame` --
    default range is orange, for a strip of tape laid across the line as a
    stop marker.

    lower_hsv / upper_hsv: (H, S, V) tuples in OpenCV's ranges
    (H: 0-179, S/V: 0-255) defining the color to look for.
    min_area_frac: minimum blob area, as a fraction of the whole frame
    area, to count as a detection.
    min_extent: minimum (blob area / bounding-box area) -- keeps a
    scattered handful of matching pixels from being mistaken for one
    solid marker.
    """
    height, width = frame.shape[:2]
    frame_area = height * width

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower_hsv), np.array(upper_hsv))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False, None, mask

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    if area < frame_area * min_area_frac:
        return False, None, mask

    x, y, w, h = cv2.boundingRect(largest)
    bbox_area = w * h
    extent = area / bbox_area if bbox_area > 0 else 0.0
    if extent < min_extent:
        return False, None, mask

    return True, (x, y, w, h), mask


def find_centroid_in_strip(mask_strip, min_area=80):
    """Find centroid of largest white blob in a single strip mask."""
    contours, _ = cv2.findContours(
        mask_strip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < min_area:
        return None

    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return (cx, cy)


def get_line_position_multistrip(
    frame, blurred, threshold=100, num_strips=3, scan_height_frac=0.4, scan_width_frac=0.75
):
    height, width = frame.shape[:2]

    # Black line on a grey/white background: the line is the *darker*
    # pixels, so use an inverted threshold -- anything darker than
    # `threshold` becomes white (255) in the mask, everything lighter
    # (the background) becomes black (0). This is the opposite of a
    # bright-line-on-dark-background setup, which would use THRESH_BINARY.
    _, mask = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY_INV)

    # Restrict to a centered vertical band of the given width fraction
    scan_w = int(width * scan_width_frac)
    scan_left = (width - scan_w) // 2
    scan_right = scan_left + scan_w

    # Zero out everything outside the width band so it's excluded from
    # contour detection in every strip
    width_mask = np.zeros_like(mask)
    width_mask[:, scan_left:scan_right] = mask[:, scan_left:scan_right]
    mask = width_mask

    scan_top = int(height * (1 - scan_height_frac))
    scan_zone_height = height - scan_top
    strip_h = scan_zone_height // num_strips

    overlay = frame.copy()
    cv2.line(overlay, (width // 2, 0), (width // 2, height), (0, 255, 255), 1)
    # Draw width band boundaries for visualization
    cv2.line(overlay, (scan_left, 0), (scan_left, height), (255, 0, 255), 1)
    cv2.line(overlay, (scan_right, 0), (scan_right, height), (255, 0, 255), 1)

    results = []  # closest strip (bottom) first
    for i in range(num_strips):
        # i=0 is the strip closest to the bottom (closest to robot)
        strip_bottom = height - i * strip_h
        strip_top = height - (i + 1) * strip_h
        strip_top = max(strip_top, scan_top)

        strip_mask = mask[strip_top:strip_bottom, :]
        centroid = find_centroid_in_strip(strip_mask)

        cv2.rectangle(overlay, (0, strip_top), (width, strip_bottom), (255, 0, 0), 1)

        if centroid is not None:
            cx, cy_local = centroid
            cy_global = strip_top + cy_local
            weight = num_strips - i  # closer strips weighted more heavily
            results.append((cx, cy_global, weight))
            cv2.circle(overlay, (cx, cy_global), 6, (0, 0, 255), -1)
            cv2.putText(
                overlay,
                str(i),
                (cx + 10, cy_global),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

    return results, mask, overlay


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------


def turn(got, steering, forward_speed):
    if steering < 0:
        got.mecanum_move_turn(0, int(forward_speed), DIR_LEFT, int(-steering))
    else:
        got.mecanum_move_turn(0, int(forward_speed), DIR_RIGHT, int(steering))

    print(f"[turn] steering={steering:.1f}, forward_speed={forward_speed}")


def stop(got):
    got.mecanum_stop()
    print("[stop]")


def search_for_line():
    # TODO: replace with your actual search/recovery behavior
    print("[search_for_line] line lost, searching...")


# ---------------------------------------------------------------------------
# Control math
# ---------------------------------------------------------------------------


def compute_steering_error(results, frame_width):
    if not results:
        return None, None

    center_x = frame_width // 2

    # Weighted average error across all strips (overall position)
    total_weight = sum(w for _, _, w in results)
    weighted_error = sum((cx - center_x) * w for cx, _, w in results) / total_weight

    # Curvature signal: compare nearest strip vs farthest strip found
    near_cx = results[0][0]
    far_cx = results[-1][0]
    curvature = far_cx - near_cx  # positive = line curving right ahead

    return weighted_error, curvature


def pd_steering(error, curvature, kp, kd):
    return kp * error + kd * curvature


def speed_for_steering(steering, max_speed, min_speed, steering_at_min_speed):
    turn_fraction = min(abs(steering) / steering_at_min_speed, 1.0)
    return max_speed - turn_fraction * (max_speed - min_speed)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def connect_robot(ip=ROBOT_IP):
    got = ugot.UGOT()
    got.initialize(ip)
    got.open_camera()
    return got


def follow_line(got, cfg=None):
    """
    Run the PD line-following loop on an already-connected `got` object.

    Meant to be called from other modules (e.g. robot_control.py) that have
    already done got.initialize() / got.open_camera() -- this function does
    NOT connect to the robot or open the camera itself, so an existing
    connection can be reused instead of opening a second one.

    Blocks until one of:
      - the orange stop marker is detected, or
      - 'q' is pressed in the debug window (only checked while SHOW_DEBUG
        is True -- see the note near the bottom of this function), or
      - a camera frame fails to grab.
    The robot is stopped (got.mecanum_stop()) before returning in every
    case above, then control passes back to the caller.
    """
    if cfg is None:
        cfg = Config()

    lost_line_count = 0
    smoothed_steering = 0.0
    smoothed_speed = float(cfg.max_speed)

    while True:
        frame = got.read_camera_data()
        if not frame:
            print("Failed to grab frame")
            break

        nparr = np.frombuffer(frame, np.uint8)
        data = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if data is None:
            print("Failed to decode frame")
            continue

        blurred = preprocess_frame(data)

        results, mask, overlay = get_line_position_multistrip(data, blurred)

        marker_found, marker_bbox, marker_mask = detect_stop_color(
            data,
            lower_hsv=cfg.stop_color_lower_hsv,
            upper_hsv=cfg.stop_color_upper_hsv,
            min_area_frac=cfg.stop_color_min_area_frac,
            min_extent=cfg.stop_color_min_extent,
        )
        if marker_found:
            x, y, w, h = marker_bbox
            frame_area = data.shape[0] * data.shape[1]
            fill_frac = (w * h) / frame_area
            print(
                f"[stop_marker] orange marker detected at x={x}, y={y}, w={w}, h={h} "
                f"(~{fill_frac * 100:.1f}% of frame) -- stopping."
            )
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), 3)
            stop(got)
            got.transform_move_speed_times(0, 20, 20, 1)
            stop(got)  # make sure the nudge above doesn't leave us drifting
            if SHOW_DEBUG:
                cv2.imshow("Webcam Feed", overlay)
                cv2.imshow("Mask", marker_mask)
                cv2.waitKey(1)
            break

        error, curvature = compute_steering_error(results, data.shape[1])

        if error is not None:
            lost_line_count = 0

            # Ignore small errors so the robot doesn't hunt/wobble around center
            if abs(error) < cfg.error_deadband:
                error = 0.0

            raw_steering = pd_steering(error, curvature, kp=cfg.kp, kd=cfg.kd)
            raw_speed = speed_for_steering(
                raw_steering,
                cfg.max_speed,
                cfg.min_speed,
                cfg.steering_at_min_speed,
            )

            # Low-pass filter (EMA) to smooth out frame-to-frame vision noise
            target_steering = (
                cfg.smoothing_alpha * raw_steering
                + (1 - cfg.smoothing_alpha) * smoothed_steering
            )
            target_speed = (
                cfg.smoothing_alpha * raw_speed
                + (1 - cfg.smoothing_alpha) * smoothed_speed
            )

            # Rate-limit how much steering/speed can change in a single frame
            steering_delta = max(
                -cfg.max_steering_delta,
                min(cfg.max_steering_delta, target_steering - smoothed_steering),
            )
            speed_delta = max(
                -cfg.max_speed_delta,
                min(cfg.max_speed_delta, target_speed - smoothed_speed),
            )
            smoothed_steering += steering_delta
            smoothed_speed += speed_delta

            # Rate-limiting only bounds how fast steering changes, not the
            # value it settles at -- clamp explicitly before it's sent to
            # the hardware call.
            smoothed_steering = max(
                -cfg.max_steering, min(cfg.max_steering, smoothed_steering)
            )

            print(
                f"error={error:.1f}, curvature={curvature:.1f}, "
                f"raw_steering={raw_steering:.1f}, steering={smoothed_steering:.1f}, "
                f"speed={smoothed_speed:.1f}, strips_found={len(results)}"
            )

            # Single continuous motion command per frame (turn() carries both
            # forward speed and steering, so a separate move_forward() call
            # is unnecessary and was causing conflicting commands each frame).
            turn(got, smoothed_steering, smoothed_speed)
        else:
            lost_line_count += 1
            print(f"Line not found in any strip ({lost_line_count} frames)")

            if lost_line_count >= cfg.lost_line_threshold:
                stop(got)
                search_for_line()
                smoothed_steering = 0.0
                smoothed_speed = float(cfg.max_speed)

        if SHOW_DEBUG:
            cv2.imshow("Webcam Feed", overlay)
            cv2.imshow("Mask", mask)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                stop(got)
                break

    if SHOW_DEBUG:
        cv2.destroyAllWindows()


def main():
    got = connect_robot()
    follow_line(got)


if __name__ == "__main__":
    main()