"""Object detection using YOLOv8."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from ultralytics import YOLO

from src.config import COCO_MODEL_PATH, FIRE_MODEL_PATH, FIRE_MODEL_URL

logger = logging.getLogger(__name__)

_coco_model: YOLO | None = None
_fire_model: YOLO | None = None

ImageInput = np.ndarray


class ModelError(Exception):
    """Raised when object detection fails."""


def _get_coco_model() -> YOLO:
    global _coco_model
    if _coco_model is None:
        logger.debug("Loading COCO detection model from %s", COCO_MODEL_PATH)
        _coco_model = YOLO(str(COCO_MODEL_PATH))
    return _coco_model


def _download_fire_model(destination: Path) -> None:
    """Download pretrained fire/smoke YOLO weights if they are not cached."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        FIRE_MODEL_URL,
        headers={"User-Agent": "incident-analysis/1.0"},
    )
    logger.info("Downloading fire/smoke detection model to %s", destination)
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        handle.write(response.read())


def _get_fire_model() -> YOLO:
    global _fire_model
    if _fire_model is None:
        if not FIRE_MODEL_PATH.exists():
            _download_fire_model(FIRE_MODEL_PATH)
        logger.debug("Loading fire/smoke detection model from %s", FIRE_MODEL_PATH)
        _fire_model = YOLO(str(FIRE_MODEL_PATH))
    return _fire_model


def _scalar_value(value: Any) -> float | int:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (list, tuple)):
        return value[0]
    return value


def _value_to_float(value: Any) -> float:
    return float(_scalar_value(value))


def _value_to_int(value: Any) -> int:
    return int(_scalar_value(value))


def _best_confidence_by_object(
    detections: list[tuple[str, float]],
) -> dict[str, float]:
    best_confidence: dict[str, float] = {}

    for name, confidence in detections:
        if name not in best_confidence or confidence > best_confidence[name]:
            best_confidence[name] = confidence

    return best_confidence


def normalize_detections(detections: list[tuple[str, float]]) -> list[str]:
    """Remove duplicate object names and sort by highest confidence."""
    return [name for name, _ in detections_with_confidence(detections)]


def detections_with_confidence(
    detections: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    """Return unique objects with their highest confidence, sorted descending."""
    best_confidence = _best_confidence_by_object(detections)
    return sorted(best_confidence.items(), key=lambda item: item[1], reverse=True)


def _normalize_object_name(name: str) -> str:
    return name.strip().lower()


def _extract_detections(results: Any) -> list[tuple[str, float]]:
    detections: list[tuple[str, float]] = []

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            class_id = _value_to_int(box.cls)
            confidence = _value_to_float(box.conf)
            name = _normalize_object_name(result.names[class_id])
            detections.append((name, confidence))

    return detections


def average_detection_confidence(detections: list[tuple[str, float]]) -> float:
    """Return the average confidence across all detections."""
    if not detections:
        return 0.0

    total_confidence = sum(confidence for _, confidence in detections)
    return round(total_confidence / len(detections), 2)


def _run_single_model_inference(
    model: YOLO, image: ImageInput
) -> list[tuple[str, float]]:
    results = model(image, verbose=False)
    return _extract_detections(results)


def _run_inference(image: ImageInput) -> list[tuple[str, float]]:
    """Run COCO and fire/smoke YOLO models and merge detections."""
    detections: list[tuple[str, float]] = []

    try:
        detections.extend(_run_single_model_inference(_get_coco_model(), image))
        detections.extend(_run_single_model_inference(_get_fire_model(), image))
    except Exception as exc:
        raise ModelError("Object detection failed.") from exc

    return detections


def detect_objects(image: ImageInput) -> list[str]:
    """Run object detection on an image and return unique object names."""
    return normalize_detections(_run_inference(image))


def detect_objects_with_confidence(
    image: ImageInput,
) -> tuple[list[tuple[str, float]], float]:
    """Run object detection and return per-object confidences plus row average."""
    detections = _run_inference(image)
    return (
        detections_with_confidence(detections),
        average_detection_confidence(detections),
    )
