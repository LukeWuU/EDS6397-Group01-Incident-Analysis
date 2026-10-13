"""Application configuration."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_LEVEL = os.getenv("INCIDENT_LOG_LEVEL", "INFO")
IMAGES_DIR = Path(os.getenv("INCIDENT_INPUT_DIR", PROJECT_ROOT / "input"))
OUTPUT_DIR = Path(os.getenv("INCIDENT_OUTPUT_DIR", PROJECT_ROOT / "output"))
CSV_FILENAME = "images_output.csv"

MODELS_DIR = PROJECT_ROOT / "models"
COCO_MODEL_PATH = Path(os.getenv("INCIDENT_COCO_MODEL", MODELS_DIR / "yolov8n.pt"))
FIRE_MODEL_PATH = Path(os.getenv("INCIDENT_FIRE_MODEL", MODELS_DIR / "fire_smoke.pt"))
FIRE_MODEL_URL = os.getenv(
    "INCIDENT_FIRE_MODEL_URL",
    "https://huggingface.co/rabahdev/fire-smoke-yolov8n/resolve/main/best.pt",
)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")

IMAGE_ID_PREFIX = "IMG_"
IMAGE_ID_START = 1
IMAGE_ID_END = 999

INCIDENT_ID_PREFIX = "INC-"
INCIDENT_ID_YEAR = 2026
INCIDENT_ID_START = 2000
INCIDENT_ID_END = 2999

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

SCENE_TYPES = (
    "Fire Scene",
    "Smoke Scene",
    "Traffic Scene",
    "People Scene",
    "Other",
)

CSV_COLUMNS = (
    "Image_ID",
    "Scene_Type",
    "Objects_Detected",
    "Text_Extracted",
    "Confidence_Score",
)

MERGE_READY_FILENAME = "images_for_integration.csv"

INTEGRATION_COLUMNS = (
    "Incident_ID",
    "Event_Type",
    "Source_Type",
    "Date_Time",
    "Location",
    "Confidence_Score",
    "Summary",
)


def configure_logging() -> None:
    """Configure application-wide logging to stdout."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
