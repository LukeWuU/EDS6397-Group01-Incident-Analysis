"""CSV output writer for incident records."""

from __future__ import annotations

import csv
from pathlib import Path

from src.config import CSV_COLUMNS


def write_row(
    path: Path,
    image_id: str,
    scene_type: str,
    objects_detected: str,
    text_extracted: str,
    confidence_score: float,
) -> None:
    """Append one image analysis row to the CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "Image_ID": image_id,
                "Scene_Type": scene_type,
                "Objects_Detected": objects_detected,
                "Text_Extracted": text_extracted,
                "Confidence_Score": confidence_score,
            }
        )
