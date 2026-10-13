# Dataset Preparation

The final integrated dataset (`dataset.csv`) was built from the five modality-specific CSV files (`audio.csv`, `pdf.csv`, `image.csv`, `text.csv`, and `video.csv`) following the professor's integration steps below.

## Integration Steps (1–4)

### Step 1 — Modality-prefixed Incident_ID

Each row received a unique modality prefix while preserving the original ID in `Original_Incident_ID`:

| Source | Prefix | Example |
|--------|--------|---------|
| Audio | `AUD-` | `AUD-000001` |
| Document (PDF) | `DOC-` | `DOC-001000` |
| Image | `IMG-` | `IMG-002000` |
| Video | `VID-` | `VID-003000` |
| Text | `TXT-` | `TXT-004000` |

### Step 2 — UNION merge

All five standardized DataFrames were combined with `pandas.concat` (UNION). One row per source record; no join on `Incident_ID` because modalities do not share incidents.

**Result:** 1,252 total rows (708 Audio + 13 Document + 72 Image + 115 Text + 344 Video).

### Step 3 — Missing values

Fields with no data for a given modality were filled with the literal text **`N/A`**. Image records missing `Date_Time` and `Location` (72 rows each) were updated accordingly.

### Step 4 — Severity classification

A derived **`Severity`** column was added using each row's `Confidence_Score`:

**Formula:** `severity_score = Confidence_Score × 10` (scale 0–10)

| Severity | Threshold (severity_score) |
|----------|----------------------------|
| **Low** | 0 ≤ score < 3 |
| **Medium** | 3 ≤ score < 7 |
| **High** | 7 ≤ score ≤ 10 |

**Distribution in `dataset.csv`:**

| Severity | Count |
|----------|------:|
| High | 609 |
| Medium | 407 |
| Low | 236 |

---

## Final Schema

| Column | Description |
|--------|-------------|
| `Incident_ID` | Modality-prefixed unique ID |
| `Event_Type` | Detected or labeled event category |
| `Source_Type` | Audio, Document, Image, Text, or Video |
| `Date_Time` | Timestamp or `N/A` |
| `Location` | Location string or `N/A` |
| `Confidence_Score` | Model confidence (0.0–1.0) |
| `Summary` | Incident summary text |
| `Severity` | Low / Medium / High (derived in Step 4) |
| `Original_Incident_ID` | Pre-prefix ID (e.g. `INC-2026-000001`) |

## Validation

Before and after integration, each dataset was reviewed for required columns, unique Incident_ID values, correct Source_Type, missing values, data types, and schema consistency. A final check confirmed no duplicate `Incident_ID` values, consistent schema across all 1,252 records, and correct severity assignment for every row.

All figures, dashboards, and statistics in this repository were generated from this validated integrated dataset.
