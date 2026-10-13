"""
detect_motion.py
-----------------
Stage 2 of the video pipeline: frame-difference motion detection.

Compares each sampled frame to the previous sampled frame. If the
difference exceeds a threshold, the frame is flagged as containing
motion -- only flagged frames get passed on to YOLO object detection
(stage 3), which keeps inference fast and avoids running a model on
every single frame, most of which are static background.

Usage (as a module):
    from detect_motion import flag_motion_frames
    flagged = flag_motion_frames(frame_records)
"""

import cv2
import numpy as np


def compute_motion_score(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
    """
    Returns a 0-100+ motion score between two frames using absolute
    pixel difference on grayscale versions. Higher = more motion.
    """
    gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY)

    # Slight blur to reduce noise sensitivity
    gray_a = cv2.GaussianBlur(gray_a, (5, 5), 0)
    gray_b = cv2.GaussianBlur(gray_b, (5, 5), 0)

    diff = cv2.absdiff(gray_a, gray_b)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

    # percentage of pixels that changed significantly
    motion_score = (np.count_nonzero(thresh) / thresh.size) * 100
    return motion_score


def flag_motion_frames(frame_records: list, motion_threshold: float = 1.5) -> list:
    """
    Given a list of frame_records (as produced by extract_frames.py,
    each containing 'frame_path'), compute motion score relative to
    the previous frame and flag whether motion was detected.

    motion_threshold: percentage of changed pixels required to flag
                       motion (tune this if too many/few frames flag).

    Returns the same list of dicts, with two new keys added:
        'motion_score': float
        'motion_detected': bool
    """
    prev_frame = None

    for record in frame_records:
        current_frame = cv2.imread(record["frame_path"])

        if prev_frame is None:
            # first frame has nothing to compare to
            record["motion_score"] = 0.0
            record["motion_detected"] = False
        else:
            score = compute_motion_score(prev_frame, current_frame)
            record["motion_score"] = round(score, 2)
            record["motion_detected"] = score >= motion_threshold

        prev_frame = current_frame

    flagged_count = sum(1 for r in frame_records if r["motion_detected"])
    print(f"[detect_motion] {flagged_count} of {len(frame_records)} frames flagged "
          f"(threshold={motion_threshold}%)")
    return frame_records
