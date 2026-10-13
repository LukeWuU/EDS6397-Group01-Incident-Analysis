"""
build_csv.py
------------
Stage 4 of the video pipeline: take YOLO detection results and write
the final structured CSV for the Video modality.

Incident_ID scheme (per group agreement):
    INC-2026-003000 through INC-2026-003999
    Student 4 (Video) owns this entire block exclusively.
    IDs increment by 1 per detected-event row, starting at 003000.

Output columns (aligned with group shared schema):
    Incident_ID, Event_Type, Source_Type, Date_Time, Location,
    Confidence_Score, Summary

Column mapping from video-specific fields:
    Incident_ID    <- generated (INC-2026-003XXX)
    Event_Type     <- event_detected  (e.g. "Person walking / present")
    Source_Type    <- hardcoded "Video"
    Date_Time      <- timestamp (clip-relative HH:MM:SS; no real date available)
    Location       <- derived from frame_id clip name (e.g. "CCTV - Walk1")
    Confidence_Score <- confidence (0-1 float)
    Summary        <- auto-generated sentence from event + objects + confidence

Usage (as a module):
    from build_csv import write_incident_csv
    write_incident_csv(results, "output/video_incidents.csv")
"""

import pandas as pd
import os

ID_PREFIX = "INC-2026-"
ID_START = 3000


def extract_clip_name(frame_id: str) -> str:
    """
    Derives the clip name from a Frame_ID string.
    e.g. "FRM_Walk1_0004" -> "CCTV - Walk1"
         "FRM_Fight_OneManDown_0012" -> "CCTV - Fight_OneManDown"
    """
    # Frame_ID format: FRM_<clipname>_<4digits>
    # Strip leading "FRM_" and trailing "_NNNN"
    parts = frame_id.split("_")
    # first part is "FRM", last part is the 4-digit sequence number
    clip_parts = parts[1:-1]
    clip_name = "_".join(clip_parts)
    return f"CCTV - {clip_name}"


def build_summary(event: str, objects: str, confidence: float) -> str:
    """
    Generates a human-readable summary sentence for the Summary column.
    e.g. "Event detected: Person walking / present. Objects: 1 person. Confidence: 0.67."
    """
    if confidence == 0.0 or objects == "none":
        return f"Motion detected in frame. No objects identified above confidence threshold."
    return (f"Event detected: {event}. "
            f"Objects: {objects}. "
            f"Confidence: {confidence}.")


def write_incident_csv(results: list, output_path: str, start_id: int = ID_START):
    """
    results: list of dicts with keys frame_id, timestamp, event_detected,
             objects_detected, confidence (as produced by run_yolo.py)
    output_path: where to write the CSV
    start_id: starting number for the Incident_ID sequence (default 3000)
    """
    rows = []
    current_id = start_id

    for record in results:
        incident_id = f"{ID_PREFIX}{current_id:06d}"

        event = record["event_detected"]
        objects = record["objects_detected"]
        confidence = record["confidence"]
        frame_id = record["frame_id"]
        timestamp = record["timestamp"]

        rows.append({
            "Incident_ID":      incident_id,
            "Event_Type":       event,
            "Source_Type":      "Video",
            "Date_Time":        timestamp,
            "Location":         extract_clip_name(frame_id),
            "Confidence_Score": confidence,
            "Summary":          build_summary(event, objects, confidence),
        })
        current_id += 1

    if current_id - 1 > start_id + 999:
        print("[build_csv] WARNING: exceeded the reserved ID block "
              f"({ID_PREFIX}{start_id:06d}-{ID_PREFIX}{start_id+999:06d}). "
              "Check with the group before merging.")

    df = pd.DataFrame(rows, columns=[
        "Incident_ID", "Event_Type", "Source_Type", "Date_Time",
        "Location", "Confidence_Score", "Summary"
    ])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"[build_csv] wrote {len(df)} rows to {output_path}")
    print(f"[build_csv] Incident_ID range used: {rows[0]['Incident_ID'] if rows else 'N/A'} "
          f"to {rows[-1]['Incident_ID'] if rows else 'N/A'}")
    return df