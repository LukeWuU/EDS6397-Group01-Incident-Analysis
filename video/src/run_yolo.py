"""
run_yolo.py
-----------
Stage 3 of the video pipeline: run YOLO object detection on frames
that were flagged as containing motion (from detect_motion.py).

Uses the pretrained YOLO nano model (no training required, per
assignment spec). Produces per-frame object lists + confidence scores.

Event labeling: YOLO gives us object classes (person, etc.) but not
activity labels like "fighting" or "collapsing". For this prototype,
we apply a simple heuristic on top of YOLO's person-detection boxes:

    - 0 persons detected         -> "No activity detected"
    - 1 person, normal aspect    -> "Person walking / present"
    - 1 person, wide/flat box    -> "Possible person down / collapse"
      (a standing person's box is taller than it is wide; a person on
      the ground produces a box that is wider than it is tall)
    - 2+ persons, close together -> "Possible altercation / crowd"
    - 3+ persons                 -> "Crowd gathering"

This heuristic is documented here and in the README so it's clear in
the report that full activity-recognition modeling was out of scope,
per the assignment ("training an anomaly model is not required").

Usage (as a module):
    from run_yolo import run_detection_on_frames
    results = run_detection_on_frames(flagged_frame_records, model_path="yolo26n.pt")
"""

from ultralytics import YOLO


def compute_iou(box_a: tuple, box_b: tuple) -> float:
    """
    Intersection-over-Union between two (x1, y1, x2, y2) boxes.
    Returns a value from 0 (no overlap) to 1 (identical boxes).
    """
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_width = max(0, inter_x2 - inter_x1)
    inter_height = max(0, inter_y2 - inter_y1)
    inter_area = inter_width * inter_height

    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def deduplicate_boxes(boxes: list, iou_threshold: float = 0.5) -> list:
    """
    Removes duplicate/overlapping boxes for the same person.

    YOLO at low confidence thresholds can emit multiple overlapping boxes
    around a single real person (especially on noisy, low-res CCTV
    footage). This collapses any boxes whose IoU exceeds iou_threshold
    into a single box, keeping only the highest-confidence one of each
    overlapping group.

    boxes: list of (x1, y1, x2, y2, confidence) tuples
    Returns: list of (x1, y1, x2, y2, confidence) tuples, deduplicated
    """
    if not boxes:
        return []

    # process highest-confidence boxes first
    sorted_boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    kept = []

    for box in sorted_boxes:
        is_duplicate = False
        for kept_box in kept:
            if compute_iou(box[:4], kept_box[:4]) > iou_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(box)

    return kept


def classify_event(person_boxes: list, frame_height: int = None) -> str:
    """
    Apply the heuristic event-labeling rules described above.
    person_boxes: list of (x1, y1, x2, y2) tuples for detected persons.
    frame_height: height of the source frame in pixels, used to check
                  whether a box's vertical center sits in the lower
                  half of the frame (a stronger collapse signal than
                  box shape alone).
    """
    n = len(person_boxes)

    if n == 0:
        return "No activity detected"

    if n == 1:
        x1, y1, x2, y2 = person_boxes[0]
        width = x2 - x1
        height = y2 - y1
        box_is_wide = width > height

        box_in_lower_half = True  # default True if we don't know frame_height
        if frame_height:
            box_vertical_center = (y1 + y2) / 2
            box_in_lower_half = box_vertical_center > (frame_height / 2)

        # require BOTH signals (wide box AND lower-half position) to
        # call it a collapse -- reduces false positives from a normal
        # walking person whose box is momentarily wide near frame edges
        if box_is_wide and box_in_lower_half:
            return "Possible person down / collapse"
        return "Person walking / present"

    if n == 2:
        return "Possible altercation / two-person interaction"

    return "Crowd gathering"


def run_detection_on_frames(frame_records: list, model_path: str = "yolo26n.pt",
                             confidence_threshold: float = 0.4) -> list:
    """
    Runs YOLO only on frames where motion_detected == True.
    Adds the following keys to each motion-flagged record:
        'objects_detected': str   (comma-separated object list, e.g. "1 person")
        'event_detected': str     (heuristic label, see classify_event)
        'confidence': float       (max confidence among detections in that frame)

    Frames with motion_detected == False are skipped (not sent to YOLO)
    and are not included in the returned list -- only flagged frames
    become rows in the final CSV.
    """
    model = YOLO(model_path)

    flagged = [r for r in frame_records if r.get("motion_detected")]
    results_out = []

    for record in flagged:
        results = model(record["frame_path"], verbose=False)
        result = results[0]

        frame_height = result.orig_shape[0]  # (height, width) of the original frame

        raw_person_boxes = []  # (x1, y1, x2, y2, confidence) before dedup
        other_object_counts = {}
        max_confidence = 0.0

        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])

            if conf < confidence_threshold:
                continue

            max_confidence = max(max_confidence, conf)

            if cls_name == "person":
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                raw_person_boxes.append((x1, y1, x2, y2, conf))
            else:
                other_object_counts[cls_name] = other_object_counts.get(cls_name, 0) + 1

        # collapse overlapping/duplicate person detections (common at low
        # confidence thresholds on noisy CCTV footage) into distinct people
        deduped_person_boxes = deduplicate_boxes(raw_person_boxes, iou_threshold=0.5)
        person_boxes = [b[:4] for b in deduped_person_boxes]

        # build "Objects_Detected" string, e.g. "2 person, 1 backpack"
        object_counts = dict(other_object_counts)
        if person_boxes:
            object_counts["person"] = len(person_boxes)
        objects_str = ", ".join(f"{count} {name}" for name, count in object_counts.items())
        if not objects_str:
            objects_str = "none"

        event_label = classify_event(person_boxes, frame_height=frame_height)

        record["objects_detected"] = objects_str
        record["event_detected"] = event_label
        record["confidence"] = round(max_confidence, 2)

        results_out.append(record)

    print(f"[run_yolo] ran detection on {len(results_out)} motion-flagged frames")
    return results_out
