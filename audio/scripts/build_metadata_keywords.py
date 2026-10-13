"""Build metadata-informed keyword lists per event category."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

METADATA_PATH = Path(__file__).resolve().parents[1] / "dataset" / "911_metadata.csv"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "pipeline" / "metadata_event_keywords.json"

# Map metadata title tokens to canonical event types (order = priority for assignment)
CATEGORY_TITLE_HINTS: dict[str, tuple[str, ...]] = {
    "Vehicle chase": ("pursuit", "chase", "chasing", "runaway car", "out-of-control", "stolen patrol", "police car stolen", "car stop", "reckless driver"),
    "Shooting": ("shooting", "shoot-out", "shoot out", "shot", "gunman", "gun range", "officer-involved shooting", "officer shooting", "mass shooting", "school shooting", "workplace shooting"),
    "Murder": ("murder", "homicide", "murders", "killed", "fatal beating", "beheading"),
    "Stabbing": ("stabbing", "stabbed", "knife"),
    "Robbery": ("robbery", "robber", "bank robbery", "hold-up", "holdup"),
    "Burglary": ("burglary", "burglar", "break-in", "break in", "home invasion", "in-progress burglary", "intruder"),
    "Kidnapping": ("kidnap", "kidnapping", "abduction", "hostage", "amber alert"),
    "Fire": ("fire", "arson", "smoke", "burn", "refinery fire", "convent fire"),
    "Explosion": ("explosion", "bomb", "hazmat", "gas main", "natural gas"),
    "Vehicle collision": ("crash", "collision", "accident", "pile-up", "pile up", "wreck", "fender bender", "bus crash", "train", "road rage"),
    "Vehicle in water": ("car in water", "into pond", "swept", "sinking vehicle", "floating car", "drowning in car", "icy pond"),
    "Medical emergency": ("medical", "heart attack", "overdose", "unconscious", "not breathing", "diabetes", "electrocution", "carbon monoxide", "choking", "cpr"),
    "Childbirth": ("baby delivery", "child birth", "childbirth", "labor", "delivery"),
    "Drowning": ("drowning", "pool save", "submerged"),
    "Domestic disturbance": ("domestic", "family stabbing", "parents stabbed", "husband", "wife"),
    "Carjacking": ("carjacking", "car jacking"),
    "Suicide": ("suicidal", "suicide", "kill myself"),
    "Animal attack": ("dog attack", "bear attack", "alligator", "snake", "bee swarm", "coyote", "shark bite"),
    "Plane crash": ("plane crash", "air crash", "helicopter crash", "jet plane"),
    "DUI": ("dui", "drunk driver", "impaired"),
    "False alarm": ("prank", "accidental dialing", "wrong address", "non-emerg", "bad sandwich", "bad chicken"),
}


def categorize_title(title: str) -> list[str]:
    lower = title.lower()
    matched = []
    for category, hints in CATEGORY_TITLE_HINTS.items():
        if any(hint in lower for hint in hints):
            matched.append(category)
    return matched or ["Public safety incident"]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def main() -> None:
    df = pd.read_csv(METADATA_PATH)
    df = df[df["title"].notna()].copy()

    category_titles: dict[str, list[str]] = defaultdict(list)
    category_desc_words: dict[str, Counter[str]] = defaultdict(Counter)

    for _, row in df.iterrows():
        title = str(row["title"])
        desc = str(row.get("description", "") or "")
        categories = categorize_title(title)
        primary = categories[0]
        category_titles[primary].append(title)
        category_desc_words[primary].update(tokenize(desc))

    output: dict[str, dict] = {}
    for category in CATEGORY_TITLE_HINTS:
        words = category_desc_words.get(category, Counter())
        top_words = [w for w, c in words.most_common(40) if len(w) > 3 and w not in {"with", "from", "that", "this", "were", "when", "after", "before", "then", "also", "listen", "read", "more", "about", "call", "called", "dispatcher", "police", "county", "year", "old"}]
        output[category] = {
            "title_count": len(category_titles.get(category, [])),
            "sample_titles": category_titles.get(category, [])[:8],
            "description_keywords": top_words[:25],
        }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    for cat, data in sorted(output.items(), key=lambda x: -x[1]["title_count"]):
        print(f"{cat}: {data['title_count']} titles")


if __name__ == "__main__":
    main()
