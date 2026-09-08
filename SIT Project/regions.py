"""
Shared frame-cropping helpers.

Keeping this logic in one place guarantees that the square crop used when
capturing training photos (1_capture_images.py) is the same size as the
crops used at inference time (3_infer_pc.py, 4_infer_RPI.py) -- so the model
sees consistent framing whether it's learning or predicting.

If you copy the Pi inference script over to a Raspberry Pi, copy this file
alongside it (4_infer_RPI.py imports it).
"""

REGION_NAMES = ("Left", "Center", "Right")


def center_square_crop(frame, size):
    """Crop a single `size` x `size` square from the center of `frame`."""
    h, w = frame.shape[:2]
    size = min(size, h, w)
    cx, cy = w // 2, h // 2
    half = size // 2
    x1, y1 = cx - half, cy - half
    x2, y2 = x1 + size, y1 + size
    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)


def three_square_regions(frame, size):
    """
    Split `frame` into three equal-width zones (left / center / right) and
    return a vertically-centered `size` x `size` square crop from each.

    Works on any array with a `.shape` of (H, W, ...) -- OpenCV BGR frames,
    RGB numpy arrays, doesn't matter, since only spatial slicing is used.

    Returns a list of (name, crop, (x1, y1, x2, y2)) tuples, in
    Left, Center, Right order.
    """
    h, w = frame.shape[:2]
    size = min(size, h, w // 3)
    half = size // 2
    cy = h // 2
    centers_x = (w // 6, w // 2, (5 * w) // 6)

    regions = []
    for name, cx in zip(REGION_NAMES, centers_x):
        x1, y1 = cx - half, cy - half
        x2, y2 = x1 + size, y1 + size
        crop = frame[y1:y2, x1:x2]
        regions.append((name, crop, (x1, y1, x2, y2)))
    return regions
