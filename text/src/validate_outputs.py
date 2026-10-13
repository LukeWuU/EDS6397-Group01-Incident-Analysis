"""
Validation script for Part 5 — Text Analyst outputs.

This script checks whether the generated CSV files follow:
1. The Part 5 text-analysis output format
2. The team common integration output format
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "text" / "outputs"

TEXT_OUTPUT_FILE = "part5_text_analysis_output.csv"
INTEGRATION_OUTPUT_FILE = "part5_text_integration_output.csv"

EXPECTED_TEXT_COLUMNS = [
    "Text_ID",
    "Source",
    "Raw_Text",
    "Sentiment",
    "Entities",
    "Topic",
]

EXPECTED_INTEGRATION_COLUMNS = [
    "Incident_ID",
    "Event_Type",
    "Source_Type",
    "Date_Time",
    "Location",
    "Confidence_Score",
    "Summary",
]
INCIDENT_ID_START_NUMBER = 4000


def validate_outputs(output_dir: Path, expected_rows: int | None = 115) -> None:
    text_path = output_dir / TEXT_OUTPUT_FILE
    integration_path = output_dir / INTEGRATION_OUTPUT_FILE

    if not text_path.exists():
        raise FileNotFoundError(f"Missing text analysis output: {text_path}")

    if not integration_path.exists():
        raise FileNotFoundError(f"Missing integration output: {integration_path}")

    text_df = pd.read_csv(text_path)
    integration_df = pd.read_csv(integration_path)

    if list(text_df.columns) != EXPECTED_TEXT_COLUMNS:
        raise AssertionError(
            f"Text output columns do not match.\n"
            f"Expected: {EXPECTED_TEXT_COLUMNS}\n"
            f"Actual:   {text_df.columns.tolist()}"
        )

    if list(integration_df.columns) != EXPECTED_INTEGRATION_COLUMNS:
        raise AssertionError(
            f"Integration output columns do not match.\n"
            f"Expected: {EXPECTED_INTEGRATION_COLUMNS}\n"
            f"Actual:   {integration_df.columns.tolist()}"
        )

    if expected_rows is not None:
        if len(text_df) != expected_rows:
            raise AssertionError(
                f"Text output row count should be {expected_rows}, but got {len(text_df)}."
            )

        if len(integration_df) != expected_rows:
            raise AssertionError(
                f"Integration output row count should be {expected_rows}, but got {len(integration_df)}."
            )

    incident_pattern = re.compile(r"^INC-2026-\d{6}$")
    invalid_incident_ids = [
        incident_id
        for incident_id in integration_df["Incident_ID"].astype(str)
        if not incident_pattern.match(incident_id)
    ]

    if invalid_incident_ids:
        raise AssertionError(f"Invalid Incident_ID values: {invalid_incident_ids[:5]}")
        expected_first_id = f"INC-2026-{INCIDENT_ID_START_NUMBER:06d}"
        actual_first_id = str(integration_df["Incident_ID"].iloc[0])

        if actual_first_id != expected_first_id:
            raise AssertionError(
                f"First Incident_ID should be {expected_first_id}, but got {actual_first_id}."
            )

        if expected_rows is not None:
            expected_last_number = INCIDENT_ID_START_NUMBER + expected_rows - 1
            expected_last_id = f"INC-2026-{expected_last_number:06d}"
            actual_last_id = str(integration_df["Incident_ID"].iloc[-1])

            if actual_last_id != expected_last_id:
                raise AssertionError(
                    f"Last Incident_ID should be {expected_last_id}, but got {actual_last_id}."
                )

    if not (integration_df["Source_Type"] == "Text").all():
        raise AssertionError("All Source_Type values must be 'Text'.")

    if not integration_df["Confidence_Score"].between(0, 1).all():
        raise AssertionError("All Confidence_Score values must be between 0 and 1.")

    required_text_fields = ["Text_ID", "Source", "Raw_Text", "Sentiment", "Entities", "Topic"]
    required_integration_fields = [
        "Incident_ID",
        "Event_Type",
        "Source_Type",
        "Date_Time",
        "Location",
        "Confidence_Score",
        "Summary",
    ]

    if text_df[required_text_fields].isna().any().any():
        raise AssertionError("Text output contains missing values in required fields.")

    if integration_df[required_integration_fields].isna().any().any():
        raise AssertionError("Integration output contains missing values in required fields.")

    print("Part 5 output validation passed.")
    print(f"Text output: {text_df.shape}")
    print(f"Integration output: {integration_df.shape}")
    print("\nTopic counts:")
    print(text_df["Topic"].value_counts())
    print("\nSentiment counts:")
    print(text_df["Sentiment"].value_counts())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Part 5 Text Analyst outputs.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory containing Part 5 output CSV files.",
    )
    parser.add_argument(
        "--expected-rows",
        type=int,
        default=115,
        help="Expected number of output rows. Use 0 to skip row-count check.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    expected_rows = None if args.expected_rows == 0 else args.expected_rows
    validate_outputs(output_dir=args.output_dir, expected_rows=expected_rows)