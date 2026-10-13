"""Transform incident CSV rows into the team's merge-ready integration format."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.config import (
    CSV_COLUMNS,
    CSV_FILENAME,
    INTEGRATION_COLUMNS,
    MERGE_READY_FILENAME,
    OUTPUT_DIR,
)
from src.utils import IncidentIdGenerator

logger = logging.getLogger(__name__)

NA = "N/A"
SOURCE_TYPE_IMAGE = "Image"
_MAX_SUMMARY_OCR_LENGTH = 120


def _format_objects_for_summary(objects_detected: str) -> str:
    items = [item.strip() for item in objects_detected.split(";") if item.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _scene_type_label(scene_type: str) -> str:
    if not scene_type:
        return "Scene"
    parts = scene_type.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {' '.join(part.lower() for part in parts[1:])}"


def _ocr_text_for_summary(text_extracted: str) -> str | None:
    cleaned = text_extracted.strip()
    if not cleaned or cleaned == NA:
        return None
    if len(cleaned) > _MAX_SUMMARY_OCR_LENGTH:
        return cleaned[: _MAX_SUMMARY_OCR_LENGTH - 3].rstrip() + "..."
    return cleaned


def build_summary(
    scene_type: str,
    objects_detected: str,
    text_extracted: str,
) -> str:
    """Build a human-readable summary from scene, objects, and OCR text."""
    scene_label = _scene_type_label(scene_type)
    objects_part = _format_objects_for_summary(objects_detected)

    if objects_part:
        summary = f"{scene_label} detected with {objects_part}."
    else:
        summary = f"{scene_label} detected."

    ocr_text = _ocr_text_for_summary(text_extracted)
    if ocr_text:
        summary += f" OCR text: {ocr_text}."

    return summary


def transform_row(row: dict[str, str], sequence_index: int) -> dict[str, str]:
    """Convert one image CSV row into an integration CSV row."""
    scene_type = row.get("Scene_Type", "")
    objects_detected = row.get("Objects_Detected", "")
    text_extracted = row.get("Text_Extracted", NA)
    incident_id_generator = IncidentIdGenerator()

    return {
        "Incident_ID": incident_id_generator.id_for_sequence(sequence_index),
        "Event_Type": scene_type,
        "Source_Type": SOURCE_TYPE_IMAGE,
        "Date_Time": NA,
        "Location": NA,
        "Confidence_Score": row.get("Confidence_Score", ""),
        "Summary": build_summary(scene_type, objects_detected, text_extracted),
    }


def write_merge_ready_image_output(
    input_path: Path,
    output_path: Path,
) -> Path:
    """Read incident rows and write the merge-ready integration CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"No CSV header found in {input_path}")

        missing_columns = set(CSV_COLUMNS) - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Input CSV is missing required columns: {missing}")

        rows = [
            transform_row(row, sequence_index)
            for sequence_index, row in enumerate(reader)
        ]

    with output_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=INTEGRATION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def create_merge_ready_image_output(
    output_dir: Path | None = None,
    *,
    input_filename: str = CSV_FILENAME,
    output_filename: str = MERGE_READY_FILENAME,
) -> Path:
    """Create merge-ready integration output from the incident analysis CSV."""
    output_dir = output_dir or OUTPUT_DIR
    input_path = output_dir / input_filename
    output_path = output_dir / output_filename
    return write_merge_ready_image_output(input_path, output_path)


def main() -> None:
    """CLI entry point for the integration transformation step."""
    from src.config import configure_logging

    configure_logging()
    output_path = create_merge_ready_image_output()
    logger.info("Merge-ready output written to: %s", output_path)


if __name__ == "__main__":
    main()
