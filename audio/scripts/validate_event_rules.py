"""Validate metadata-informed event rules against catalog titles."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.event_rules import detect_event_type

METADATA_PATH = Path(__file__).resolve().parents[1] / "dataset" / "911_metadata.csv"

TITLE_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "Vehicle chase": ("pursuit", "chase", "chasing", "runaway car", "out-of-control", "stolen patrol", "police car stolen", "car stop", "reckless driver"),
    "Shooting": ("shooting", "shoot-out", "shoot out", "shot", "gunman", "officer-involved shooting", "officer shooting", "mass shooting", "school shooting"),
    "Murder": ("murder", "homicide", "murders", "killed", "fatal beating", "beheading"),
    "Stabbing": ("stabbing", "stabbed", "knife"),
    "Robbery": ("robbery", "robber", "bank robbery"),
    "Burglary": ("burglary", "burglar", "home invasion", "intruder"),
    "Kidnapping": ("kidnap", "kidnapping", "abduction", "hostage", "amber alert"),
    "Fire": ("fire", "arson"),
    "Explosion": ("explosion", "bomb", "hazmat", "gas main"),
    "Vehicle collision": ("crash", "collision", "accident", "pile-up", "wreck", "fender bender", "bus crash", "train accident", "plane crash"),
    "Vehicle in water": ("car in water", "into pond", "swept", "sinking vehicle", "floating car", "drowning in car"),
    "Medical emergency": ("medical", "heart attack", "overdose", "unconscious", "not breathing", "cpr", "choking", "carbon monoxide"),
    "Childbirth": ("baby delivery", "child birth", "childbirth", "delivery"),
    "Drowning": ("drowning", "pool save"),
    "Domestic disturbance": ("domestic", "family stabbing", "husband", "wife"),
    "Carjacking": ("carjacking", "car jacking"),
    "Suicide": ("suicidal", "suicide"),
    "Animal attack": ("dog attack", "bear attack", "alligator", "snake", "shark bite"),
    "DUI": ("dui", "drunk driver"),
    "False alarm": ("prank", "accidental dialing", "wrong address", "non-emerg", "bad sandwich"),
}


def expected_category(title: str) -> str:
    lower = title.lower()
    for category, hints in TITLE_CATEGORY_HINTS.items():
        if any(hint in lower for hint in hints):
            return category
    return "Public safety incident"


def synthetic_transcript(title: str, description: str) -> str:
    return f"{title}. {description}".lower()


def main() -> None:
    df = pd.read_csv(METADATA_PATH)
    df = df[df["title"].notna() & df["file_name"].notna()].copy()

    matches = 0
    mismatches: list[tuple[str, str, str, str]] = []
    by_expected: Counter[str] = Counter()

    for _, row in df.iterrows():
        title = str(row["title"])
        description = str(row.get("description", "") or "")
        expected = expected_category(title)
        by_expected[expected] += 1
        transcript = synthetic_transcript(title, description)
        detected, score, terms = detect_event_type(transcript)
        if detected == expected or (expected == "Vehicle collision" and detected == "Plane crash" and "plane" in title.lower()):
            matches += 1
        else:
            mismatches.append((row["file_name"], title, expected, detected))

    total = len(df)
    print(f"Metadata rows with audio: {total}")
    print(f"Title-hint alignment with rules: {matches}/{total} ({matches/total:.1%})")
    print()
    print("Expected category counts:")
    for cat, count in by_expected.most_common(15):
        print(f"  {cat}: {count}")
    print()
    print("Sample mismatches:")
    for item in mismatches[:20]:
        print(f"  {item[0]} | title={item[1]!r} | expected={item[2]} | detected={item[3]}")


if __name__ == "__main__":
    main()
