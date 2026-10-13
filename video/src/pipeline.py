"""
pipeline.py
-----------
Runs the full video analysis pipeline end-to-end:
    1. extract_frames  -> pull frames from each clip at 1 fps
    2. detect_motion    -> flag frames with meaningful motion
    3. run_yolo          -> run YOLO object detection on flagged frames only
    4. build_csv          -> write final structured CSV with Incident_IDs

Usage:
    python pipeline.py

Edit the VIDEO_FILES list below to add more clips as you scale up
from 1 clip to 3-5 clips.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from extract_frames import extract_frames
from detect_motion import flag_motion_frames
from run_yolo import run_detection_on_frames
from build_csv import write_incident_csv

# ---- CONFIG ----------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../video/
DATA_DIR = os.path.join(BASE_DIR, "data")
FRAMES_DIR = os.path.join(BASE_DIR, "frames")
OUTPUT_CSV = os.path.join(BASE_DIR, "output", "video_incidents.csv")

# Clips to process — 9 total across normal, fight, rest, meeting, and abandoned object scenarios
VIDEO_FILES = [
    "Walk1.mpg",
    "Rest_FallOnFloor.mpg",
    "Fight_OneManDown.mpg",
    "Meet_Crowd.mpg",
    "LeftBag.mpg",
    "Fight_Chase.mpg",
    "Rest_SlumpOnFloor.mpg",
    "Meet_WalkTogether1.mpg",
    "LeftBag_PickedUp.mpg",
]

SAMPLE_FPS = 2.0           # frames sampled per second of video (raised from 1.0
                            # so we don't skip past brief events like a fall)
MOTION_THRESHOLD = 0.5     # % of pixels changed to flag motion (lowered from 1.5
                            # -- CAVIAR clips have subtle frame-to-frame motion)
YOLO_MODEL = "yolo26n.pt"  # pretrained nano model, auto-downloads on first run
CONFIDENCE_THRESHOLD = 0.25  # lowered from 0.4 -- low-res CCTV footage produces
                              # lower-confidence detections than typical photos
# ------------------------------------------------------------------------


def main():
    all_results = []

    for video_filename in VIDEO_FILES:
        video_path = os.path.join(DATA_DIR, video_filename)
        if not os.path.exists(video_path):
            print(f"[pipeline] SKIPPING missing file: {video_path}")
            continue

        clip_name = os.path.splitext(video_filename)[0]
        clip_frames_dir = os.path.join(FRAMES_DIR, clip_name)

        print(f"\n=== Processing {video_filename} ===")

        # Stage 1: extract frames
        frame_records = extract_frames(video_path, clip_frames_dir, sample_fps=SAMPLE_FPS)

        # Stage 2: flag motion
        frame_records = flag_motion_frames(frame_records, motion_threshold=MOTION_THRESHOLD)

        # Stage 3: run YOLO on flagged frames only
        detection_results = run_detection_on_frames(
            frame_records, model_path=YOLO_MODEL, confidence_threshold=CONFIDENCE_THRESHOLD
        )

        all_results.extend(detection_results)

    # Stage 4: build final CSV (single file across all clips, continuous Incident_ID sequence)
    if all_results:
        write_incident_csv(all_results, OUTPUT_CSV)
    else:
        print("[pipeline] No motion-flagged frames across any clip — nothing to write."
              " Try lowering MOTION_THRESHOLD.")


if __name__ == "__main__":
    main()