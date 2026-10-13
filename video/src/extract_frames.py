"""
extract_frames.py
------------------
Stage 1 of the video pipeline: extract frames from a video clip at a
fixed interval (default: 1 frame per second) and record each frame's
timestamp in HH:MM:SS format.

Timestamp format (documented for the group / Student 6):
    HH:MM:SS  (zero-padded, e.g. 00:00:12)

Frame ID format:
    FRM_<video_basename>_<sequence number, 4 digits>
    e.g. FRM_Walk1_0001

Usage:
    python extract_frames.py <video_path> <output_dir> [--fps 1]
"""

import cv2
import os
import argparse


def format_timestamp(seconds: float) -> str:
    """Convert seconds (float) into HH:MM:SS string."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_frames(video_path: str, output_dir: str, sample_fps: float = 1.0):
    """
    Extract frames from video_path at sample_fps frames per second.
    Saves frames as .jpg into output_dir.

    Returns a list of dicts: [{frame_id, frame_path, timestamp, video_name}, ...]
    """
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS)
    if not native_fps or native_fps <= 0:
        native_fps = 25.0  # CAVIAR clips are commonly ~25fps; fallback default

    # how many native frames to skip between each sampled frame
    frame_interval = max(int(round(native_fps / sample_fps)), 1)

    frame_records = []
    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            saved_count += 1
            frame_id = f"FRM_{video_name}_{saved_count:04d}"
            timestamp_seconds = frame_count / native_fps
            timestamp_str = format_timestamp(timestamp_seconds)

            frame_filename = f"{frame_id}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame)

            frame_records.append({
                "frame_id": frame_id,
                "frame_path": frame_path,
                "timestamp": timestamp_str,
                "video_name": video_name,
            })

        frame_count += 1

    cap.release()
    print(f"[extract_frames] {video_name}: extracted {saved_count} frames "
          f"(native fps={native_fps:.1f}, sample interval={frame_interval} frames)")
    return frame_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from a video at a fixed sample rate.")
    parser.add_argument("video_path", help="Path to the input video file (.mpg, .mp4, etc.)")
    parser.add_argument("output_dir", help="Directory to save extracted frames")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames to sample per second (default: 1.0)")
    args = parser.parse_args()

    records = extract_frames(args.video_path, args.output_dir, args.fps)
    print(f"Done. {len(records)} frames saved to {args.output_dir}")
