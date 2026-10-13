"""Shared utility helpers."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from src.config import (
    IMAGE_ID_END,
    IMAGE_ID_PREFIX,
    IMAGE_ID_START,
    INCIDENT_ID_END,
    INCIDENT_ID_PREFIX,
    INCIDENT_ID_START,
    INCIDENT_ID_YEAR,
    SUPPORTED_IMAGE_EXTENSIONS,
)


class ImageLoadError(Exception):
    """Raised when an image cannot be loaded."""


COLOR_CONVERSIONS = {
    "gray": cv2.COLOR_BGR2GRAY,
    "rgb": cv2.COLOR_BGR2RGB,
}


class ImageIdExhaustedError(Exception):
    """Raised when no more image IDs are available."""


class ImageIdGenerator:
    """Generate sequential modality-prefixed image IDs within the configured range."""

    def __init__(self) -> None:
        self._next_number = IMAGE_ID_START

    def next_id(self) -> str:
        """Return the next image ID and advance the counter."""
        if self._next_number > IMAGE_ID_END:
            raise ImageIdExhaustedError(
                f"No image IDs remain. Maximum ID is "
                f"{IMAGE_ID_PREFIX}{IMAGE_ID_END:03d}."
            )

        image_id = f"{IMAGE_ID_PREFIX}{self._next_number:03d}"
        self._next_number += 1
        return image_id


class IncidentIdGenerator:
    """Generate sequential incident IDs from image processing order."""

    def __init__(self) -> None:
        self._next_number = INCIDENT_ID_START

    def next_id(self) -> str:
        """Return the next incident ID and advance the counter."""
        if self._next_number > INCIDENT_ID_END:
            raise ImageIdExhaustedError(
                f"No incident IDs remain. Maximum ID is "
                f"{INCIDENT_ID_PREFIX}{INCIDENT_ID_YEAR}-"
                f"{INCIDENT_ID_END:06d}."
            )

        incident_id = (
            f"{INCIDENT_ID_PREFIX}{INCIDENT_ID_YEAR}-{self._next_number:06d}"
        )
        self._next_number += 1
        return incident_id

    def id_for_sequence(self, sequence_index: int) -> str:
        """Return the incident ID for a zero-based row index in image order."""
        incident_number = INCIDENT_ID_START + sequence_index
        if incident_number > INCIDENT_ID_END:
            raise ImageIdExhaustedError(
                f"No incident IDs remain. Maximum ID is "
                f"{INCIDENT_ID_PREFIX}{INCIDENT_ID_YEAR}-"
                f"{INCIDENT_ID_END:06d}."
            )
        return (
            f"{INCIDENT_ID_PREFIX}{INCIDENT_ID_YEAR}-{incident_number:06d}"
        )


def is_supported_image(path: Path) -> bool:
    """Return True if the file extension is a supported image format."""
    return path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def _folder_entry_order_key(path: Path) -> tuple[float, str]:
    """Sort key that preserves the order files appear in a folder."""
    return (path.stat().st_mtime, path.name.lower())


def list_image_files(directory: Path) -> list[Path]:
    """Return supported image files in a directory, in folder order."""
    return [path for path in list_input_files(directory) if is_supported_image(path)]


def list_input_files(directory: Path) -> list[Path]:
    """Return all regular files in a directory, in folder order."""
    if not directory.is_dir():
        return []

    return sorted(
        (path for path in directory.iterdir() if path.is_file()),
        key=_folder_entry_order_key,
    )


def load_image(path: Path | str) -> Image.Image:
    """Load a supported image file and return a PIL Image."""
    image_path = Path(path)
    _validate_image_path(image_path)

    try:
        with Image.open(image_path) as image:
            return image.copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageLoadError(
            f"Could not load image '{image_path.name}': "
            "the file may be corrupted or invalid."
        ) from exc


def _validate_image_path(image_path: Path) -> None:
    if not image_path.exists():
        raise ImageLoadError(f"Image file not found: {image_path}")

    if not image_path.is_file():
        raise ImageLoadError(f"Path is not a file: {image_path}")

    if not is_supported_image(image_path):
        supported = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
        raise ImageLoadError(
            f"Unsupported image format '{image_path.suffix}'. "
            f"Supported formats: {supported}"
        )


def is_valid_opencv_image(image: np.ndarray) -> bool:
    """Return True if the array is a non-empty OpenCV-compatible image."""
    return isinstance(image, np.ndarray) and image.size > 0 and image.ndim in (2, 3)


def load_image_cv(path: Path | str) -> np.ndarray:
    """Load a supported image file with OpenCV and return a BGR image."""
    image_path = Path(path)
    _validate_image_path(image_path)

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None or not is_valid_opencv_image(image):
        raise ImageLoadError(
            f"Could not load image '{image_path.name}': "
            "the file may be corrupted or invalid."
        )

    return image


def process_image(
    image: np.ndarray | Path | str,
    *,
    resize: tuple[int, int] | None = None,
    denoise: bool = False,
    color_conversion: str | None = None,
) -> np.ndarray:
    """Prepare an image for AI models using optional OpenCV processing."""
    if isinstance(image, (str, Path)):
        processed = load_image_cv(image)
    else:
        processed = image.copy()

    if resize is not None:
        width, height = resize
        processed = cv2.resize(processed, (width, height))

    if denoise:
        if processed.ndim == 3:
            processed = cv2.fastNlMeansDenoisingColored(processed, None, 10, 10, 7, 21)
        else:
            processed = cv2.fastNlMeansDenoising(processed, None, 10, 7, 21)

    if color_conversion is not None:
        conversion = COLOR_CONVERSIONS.get(color_conversion.lower())
        if conversion is None:
            supported = ", ".join(sorted(COLOR_CONVERSIONS))
            raise ImageLoadError(
                f"Unsupported color conversion '{color_conversion}'. "
                f"Supported conversions: {supported}"
            )
        processed = cv2.cvtColor(processed, conversion)

    if not is_valid_opencv_image(processed):
        raise ImageLoadError("Processing did not produce a valid OpenCV image.")

    return processed
