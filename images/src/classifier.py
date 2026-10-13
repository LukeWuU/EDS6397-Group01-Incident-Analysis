"""Scene classification and decision matrix."""

from __future__ import annotations

import numpy as np

FIRE_OBJECTS = frozenset({"fire", "flame"})
SMOKE_OBJECTS = frozenset({"smoke"})
TRAFFIC_OBJECTS = frozenset(
    {
        "bicycle",
        "bus",
        "car",
        "motorcycle",
        "traffic light",
        "truck",
    }
)
PEOPLE_OBJECTS = frozenset({"person"})

SCENE_OBJECT_MAP = {
    "Fire Scene": FIRE_OBJECTS,
    "Smoke Scene": SMOKE_OBJECTS,
    "Traffic Scene": TRAFFIC_OBJECTS,
    "People Scene": PEOPLE_OBJECTS,
}

SCENE_PRIORITY = tuple(SCENE_OBJECT_MAP.keys())


def _normalize_objects(objects: list[str]) -> set[str]:
    return {name.strip().lower() for name in objects if name.strip()}


def _matching_scenes(objects: list[str]) -> list[str]:
    """Return scene types that match at least one detected object."""
    normalized = _normalize_objects(objects)
    if not normalized:
        return []

    return [
        scene for scene, keywords in SCENE_OBJECT_MAP.items() if normalized & keywords
    ]


def resolve_scene(matches: list[str]) -> str:
    """Pick the highest-priority scene when multiple categories match."""
    if not matches:
        return "Other"

    match_set = set(matches)
    for scene in SCENE_PRIORITY:
        if scene in match_set:
            return scene

    return "Other"


def classify_scene(objects: list[str]) -> str:
    """Classify the scene based on detected objects.

    Returns exactly one allowed scene type. When multiple categories match,
    the decision matrix picks Fire > Smoke > Traffic > People > Other.
    """
    return resolve_scene(_matching_scenes(objects))


def classify_image(image: np.ndarray) -> str:
    """Classify an image by detecting objects and mapping them to a scene type."""
    from src.detector import detect_objects

    return classify_scene(detect_objects(image))
