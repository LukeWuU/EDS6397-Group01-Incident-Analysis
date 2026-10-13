"""OCR for extracting any visible text from an image."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError

from src.config import TESSERACT_CMD

logger = logging.getLogger(__name__)

OCR_SKIPPED = "N/A"
TESSERACT_CONFIG = "--psm 3"
_TESSERACT_LOCATIONS = (
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
)
_tesseract_warning_logged = False

ImageInput = np.ndarray | Image.Image


def _to_pil_image(image: ImageInput) -> Image.Image:
    if isinstance(image, Image.Image):
        return image

    if isinstance(image, np.ndarray):
        if image.ndim == 3:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb = image
        return Image.fromarray(rgb)

    raise TypeError("Image must be a PIL Image or OpenCV numpy array.")


def _resolve_tesseract_command() -> str | None:
    if TESSERACT_CMD:
        command = Path(TESSERACT_CMD)
        if command.is_file():
            return str(command)

    found = shutil.which("tesseract")
    if found:
        return found

    for candidate in _TESSERACT_LOCATIONS:
        if Path(candidate).is_file():
            return candidate

    return None


def check_tesseract_available() -> bool:
    """Return True when the Tesseract binary is available for OCR."""
    global _tesseract_warning_logged

    command = _resolve_tesseract_command()
    if command is None:
        if not _tesseract_warning_logged:
            logger.warning(
                "Tesseract OCR is not installed or not on PATH. "
                "Text_Extracted will be N/A until it is installed "
                "(macOS: brew install tesseract)."
            )
            _tesseract_warning_logged = True
        return False

    pytesseract.pytesseract.tesseract_cmd = command
    return True


def _read_text_from_image(image: Image.Image) -> str:
    """Run Tesseract and return any text found in the image."""
    return pytesseract.image_to_string(image, config=TESSERACT_CONFIG).strip()


def extract_text(image: ImageInput) -> str:
    """Extract any visible text from an image, or return N/A when none is found."""
    if not check_tesseract_available():
        return OCR_SKIPPED

    try:
        text = _read_text_from_image(_to_pil_image(image))
    except TesseractNotFoundError:
        check_tesseract_available()
        return OCR_SKIPPED
    except TypeError:
        return OCR_SKIPPED
    except Exception as exc:
        logger.warning("OCR failed: %s", exc)
        return OCR_SKIPPED

    return text if text else OCR_SKIPPED
