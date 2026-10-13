"""Extract date/time from image EXIF and input-folder file metadata."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image

NA = "N/A"
DATETIME_OUTPUT_FORMAT = "%Y-%m-%d %H:%M:%S"
_EXIF_DATETIME_TAG_IDS = (36867, 36868, 306)


def _format_datetime(value: datetime) -> str:
    return value.strftime(DATETIME_OUTPUT_FORMAT)


def _parse_exif_datetime(value: str) -> datetime | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _exif_datetime(image_path: Path) -> datetime | None:
    try:
        with Image.open(image_path) as image:
            exif = image.getexif()
            if not exif:
                return None

            for tag_id in _EXIF_DATETIME_TAG_IDS:
                raw_value = exif.get(tag_id)
                if not raw_value:
                    continue
                parsed = _parse_exif_datetime(str(raw_value))
                if parsed is not None:
                    return parsed
    except OSError:
        return None

    return None


def _folder_datetime(image_path: Path) -> datetime | None:
    try:
        stat = image_path.stat()
    except OSError:
        return None

    timestamp = getattr(stat, "st_birthtime", stat.st_mtime)
    return datetime.fromtimestamp(timestamp)


def extract_image_datetime(image_path: Path) -> str:
    """Return a timestamp from image metadata or folder file metadata."""
    exif_timestamp = _exif_datetime(image_path)
    if exif_timestamp is not None:
        return _format_datetime(exif_timestamp)

    folder_timestamp = _folder_datetime(image_path)
    if folder_timestamp is not None:
        return _format_datetime(folder_timestamp)

    return NA
