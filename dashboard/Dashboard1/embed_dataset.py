"""Embed final dataset.csv into index.html."""
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

_here = Path(__file__).resolve().parent
_sub_csv = _here.parent / "02_Final_Dataset" / "data" / "dataset.csv"
_local_csv = _here / "dataset.csv"
CSV_PATH = _local_csv if _local_csv.exists() else _sub_csv
HTML_PATH = Path(__file__).resolve().parent / "index.html"

EVENT_TYPE_MAP = {
    "fire scene": "Fire",
    "missing child": "Missing person",
    "missing children": "Missing person",
    "people walking": "People Scene",
    "theft / robbery": "Robbery",
    "theft/robbery": "Robbery",
    "reference list (training plans)": "Training Plan",
    "reference list (training plan)": "Training Plan",
    "other": "Unknown",
}

URGENCY_HIGH = {
    "assault", "bear attack", "bomb threat", "building collapse", "carjacking",
    "fire", "found body", "home invasion", "kidnapping", "medical emergency",
    "missing person", "murder", "plane crash", "school lockdown", "school lock-down",
    "sex", "shooting", "smoke scene", "stabbing", "suicide", "vehicle chase",
    "vehicle collision", "vehicle in water",
}
URGENCY_LOW = {
    "child custody dispute", "no activity detected",
    "reference list (training plans)", "reference list (training plan)",
    "student disturbance", "training plan",
}

# Actionable is NOT stored in dataset.csv.
# It is derived at embed time from Event_Type for Priority_Rank metadata only.
# Dashboard KPIs recompute Actionable at runtime using the same rule (see index.html).
ACTIONABLE_RULE = (
    "Actionable = false when Event_Type (case-insensitive) is one of: "
    "blank, N/A, Unknown, False alarm, No activity detected, Person walking / present; "
    "otherwise Actionable = true."
)
NON_ACTIONABLE = {
    "",
    "n/a",
    "unknown",
    "false alarm",
    "no activity detected",
    "person walking / present",
    "person walking/present",
}


def clean_text(v):
    if v is None:
        return "N/A"
    return str(v).replace("\u200b", "").strip() or "N/A"


def standardize_event_type(evt, dataset_event_types):
    """Normalize Event_Type labels before KPIs, charts, filters, and queue."""
    key = evt.strip().lower()
    if key in EVENT_TYPE_MAP:
        return EVENT_TYPE_MAP[key]
    if key == "public safety incident" and any(
        e.strip().lower() == "public disturbance" for e in dataset_event_types
    ):
        return "Public Disturbance"
    return evt


def derive_urgency(evt):
    key = evt.strip().lower()
    if key in URGENCY_HIGH:
        return "High"
    if key in URGENCY_LOW:
        return "Low"
    return "Medium"


def parseable_datetime(value):
    v = clean_text(value)
    if v == "N/A":
        return False
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            datetime.strptime(v, fmt)
            return True
        except ValueError:
            pass
    return bool(re.match(r"^\d{1,2}:\d{2}:\d{2}$", v))


def build_data():
    raw_rows = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            raw_rows.append(row)

    dataset_event_types = [clean_text(r["Event_Type"]) for r in raw_rows]
    rows = []
    for row in raw_rows:
        conf = float(row["Confidence_Score"])
        sev = clean_text(row["Severity"])
        evt = standardize_event_type(clean_text(row["Event_Type"]), dataset_event_types)
        rows.append({
            "Incident_ID": clean_text(row["Incident_ID"]),
            "Event_Type": evt,
            "Source_Type": clean_text(row["Source_Type"]),
            "Date_Time": clean_text(row["Date_Time"]),
            "Location": clean_text(row["Location"]),
            "Confidence_Score": conf,
            "Summary": clean_text(row["Summary"]),
            "Severity": sev,
            "Urgency": derive_urgency(evt),
            "Actionable": evt.lower() not in NON_ACTIONABLE,
        })

    urgency_rank = {"High": 0, "Medium": 1, "Low": 2}
    sev_rank = {"High": 0, "Medium": 1, "Low": 2}
    for i, r in enumerate(
        sorted(
            rows,
            key=lambda x: (
                urgency_rank.get(x["Urgency"], 9),
                sev_rank.get(x["Severity"], 9),
                -x["Confidence_Score"],
            ),
        ),
        1,
    ):
        r["Priority_Rank"] = i

    timeline_included = sum(1 for r in rows if parseable_datetime(r["Date_Time"]))
    high = sum(1 for r in rows if r["Severity"] == "High")
    actionable = sum(1 for r in rows if r["Actionable"])
    priority = sum(1 for r in rows if r["Actionable"] and r["Severity"] in ("High", "Medium"))
    avg_conf = sum(r["Confidence_Score"] for r in rows) / len(rows)

    sources = sorted({r["Source_Type"] for r in rows})
    events = sorted({r["Event_Type"] for r in rows})
    locations = sorted({r["Location"] for r in rows})

    evt_counts = Counter(r["Event_Type"] for r in rows)
    src_counts = Counter(r["Source_Type"] for r in rows)
    loc_counts = Counter(
        r["Location"] for r in rows if r["Actionable"] and r["Severity"] in ("High", "Medium")
    )
    high_evt = Counter(r["Event_Type"] for r in rows if r["Severity"] == "High").most_common(1)
    top_loc = loc_counts.most_common(1)
    top_src = src_counts.most_common(1)

    return {
        "records": rows,
        "metrics": {
            "total": len(rows),
            "critical": 0,
            "high": high,
            "priority_queue": priority,
            "actionable": actionable,
            "avg_confidence": avg_conf,
            "source_types": sources,
        },
        "meta": {
            "total_records": len(rows),
            "timeline_included": timeline_included,
            "timeline_excluded": len(rows) - timeline_included,
            "severity_rule": "Severity = Confidence_Score x 10. Low (0-3), Medium (3-7), High (7-10). From final integrated dataset.csv.",
            "critical_event_types": [],
            "actionable_rule": ACTIONABLE_RULE,
        },
        "charts": {
            "event_types": [{"label": k, "count": v} for k, v in evt_counts.most_common(10)],
            "sources": [{"label": k, "count": v} for k, v in src_counts.most_common()],
            "hotspots": [{"label": k, "count": v} for k, v in loc_counts.most_common(10)],
            "timeline": [],
        },
        "decisions": [
            {
                "label": "High Severity Count",
                "value": f"{high} records with Severity = High",
                "detail": "From dataset.csv (score 7-10)",
                "tone": "high",
            },
            {
                "label": "Priority Record Count",
                "value": f"{priority} Actionable records with Severity High or Medium",
                "detail": f"{actionable} records marked Actionable in dataset",
                "tone": "high",
            },
            {
                "label": "Top Location (by count)",
                "value": f"{top_loc[0][0]} - {top_loc[0][1]} Actionable High/Medium records" if top_loc else "N/A",
                "detail": "Based on text Location field only (not GPS coordinates)",
                "tone": "warn",
            },
            {
                "label": "Top High Severity Event Type",
                "value": f"{high_evt[0][0]} - {high_evt[0][1]} High records" if high_evt else "N/A",
                "detail": "Most frequent Event_Type where Severity = High",
                "tone": "info",
            },
            {
                "label": "Top Source Type (by count)",
                "value": f"{top_src[0][0]} - {top_src[0][1]} records" if top_src else "N/A",
                "detail": "Highest record count by Source_Type in dataset",
                "tone": "info",
            },
        ],
        "filters": {
            "sources": sources,
            "events": events,
            "severities": ["High", "Medium", "Low"],
            "locations": locations,
        },
        "severity_colors": {
            "Critical": "#E53935",
            "High": "#E53935",
            "Medium": "#F9A825",
            "Low": "#43A047",
            "Unknown": "#64748B",
        },
        "source_colors": {
            "Audio": "#22D3EE",
            "Document": "#A78BFA",
            "Image": "#FB923C",
            "Text": "#34D399",
            "Video": "#F472B6",
        },
    }


def main():
    data = build_data()
    html = HTML_PATH.read_text(encoding="utf-8")
    new_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    json.loads(new_json)

    start_marker = "    const DATA = "
    end_marker = ";\n    const SEV_COLORS"
    start = html.index(start_marker) + len(start_marker)
    end = html.index(end_marker, start)
    HTML_PATH.write_text(html[:start] + new_json + html[end:], encoding="utf-8")

    print(f"embedded {len(data['records'])} records into {HTML_PATH.name}")
    print(f"first id: {data['records'][0]['Incident_ID']}")
    print(f"severities: {dict(Counter(r['Severity'] for r in data['records']))}")


if __name__ == "__main__":
    main()
