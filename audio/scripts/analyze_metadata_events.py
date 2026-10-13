"""Analyze metadata titles and descriptions to derive event categories."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

METADATA_PATH = Path(__file__).resolve().parents[1] / "dataset" / "911_metadata.csv"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "metadata_event_analysis.txt"


def main() -> None:
    df = pd.read_csv(METADATA_PATH)
    lines: list[str] = []
    lines.append(f"Total rows: {len(df)}")
    lines.append(f"Rows with file_name: {df['file_name'].notna().sum()}")
    lines.append("")

    titled = df[df["title"].notna()].copy()
    lines.append(f"Unique titles: {titled['title'].nunique()}")
    lines.append("")
    lines.append("=== ALL UNIQUE TITLES ===")
    for title in sorted(titled["title"].astype(str).unique(), key=str.lower):
        lines.append(title)

    lines.append("")
    lines.append("=== TITLE KEYWORD FREQUENCY (tokenized) ===")
    words: Counter[str] = Counter()
    for title in titled["title"].astype(str):
        tokens = re.findall(r"[a-zA-Z']+", title.lower())
        words.update(tokens)
    for word, count in words.most_common(80):
        if len(word) > 2:
            lines.append(f"{word}: {count}")

    lines.append("")
    lines.append("=== SAMPLE TITLE + DESCRIPTION (first 30 with file_name) ===")
    sample = df[df["file_name"].notna()][["title", "description", "file_name"]].head(30)
    for _, row in sample.iterrows():
        lines.append(f"FILE: {row['file_name']}")
        lines.append(f"TITLE: {row['title']}")
        desc = str(row.get("description", ""))[:300]
        lines.append(f"DESC: {desc}")
        lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
