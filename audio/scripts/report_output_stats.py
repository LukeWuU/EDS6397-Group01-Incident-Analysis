"""Print summary statistics from emergency_analysis_output.csv."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "outputs" / "emergency_analysis_output.csv"


def main() -> int:
    if not CSV.exists():
        print(f"Missing: {CSV}")
        return 1

    df = pd.read_csv(CSV)
    print(f"rows={len(df)}")
    print(f"unique_incident_ids={df['Incident_ID'].nunique()}")
    print(f"event_types={df['Event_Type'].nunique()}")
    print("\n-- event_type top 15 --")
    print(df["Event_Type"].value_counts().head(15).to_string())
    print("\n-- sentiment --")
    print(df["Sentiment"].value_counts().to_string())
    for col in ("Urgency_Score", "Confidence_Score"):
        s = df[col]
        print(
            f"\n{col}: mean={s.mean():.3f} median={s.median():.3f} "
            f"min={s.min():.3f} max={s.max():.3f} std={s.std():.3f}"
        )
    bins = [0, 0.3, 0.6, 0.8, 1.01]
    labels = ["Low", "Moderate", "High", "Critical"]
    df["urgency_bucket"] = pd.cut(df["Urgency_Score"], bins=bins, labels=labels, include_lowest=True)
    print("\n-- urgency buckets --")
    print(df["urgency_bucket"].value_counts().sort_index().to_string())
    print("\n-- confidence buckets --")
    for lo, hi, name in [(0, 0.4, "0.0-0.4"), (0.4, 0.6, "0.4-0.6"), (0.6, 0.8, "0.6-0.8"), (0.8, 1.01, "0.8-1.0")]:
        n = ((df["Confidence_Score"] >= lo) & (df["Confidence_Score"] < hi)).sum()
        print(f"{name}: {n}")
    print(f"\nlocation_known={(df['Location'] != 'Unknown').sum()}")
    print(f"location_unknown={(df['Location'] == 'Unknown').sum()}")
    print("\n-- top states --")
    print(df["Location"].value_counts().head(10).to_string())
    lens = df["Transcribed Script"].astype(str).str.len()
    print(f"\ntranscript_chars mean={lens.mean():.0f} median={lens.median():.0f} max={lens.max()}")
    err = df["Transcribed Script"].astype(str).str.contains("failed|ERROR", case=False, na=False).sum()
    print(f"transcription_errors={err}")
    print(f"date_time_known={(df['Date_Time'] != 'Unknown').sum()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
