# Final Dataset and Dashboard Pipeline

**EDS6397 Group 01 — Incident Analysis Project**  
**Integration & Dashboard Lead:** Audrey Rah  
**Submission folder:** `dashboard1_incident_command_cente_timeline`

This document describes the **complete workflow** for the final submission: how five modality CSV files become `dataset.csv` through the **Integration Pipeline**, and how the dashboard is built through the **Dashboard Enrichment Layer**—without modifying `dataset.csv`.

---

## Table of Contents

1. [Two-Layer Architecture](#two-layer-architecture)
2. [Pipeline Diagram](#pipeline-diagram)
3. [Integration Pipeline](#integration-pipeline)
4. [dataset.csv — Final Validated Integrated Dataset](#datasetcsv--final-validated-integrated-dataset)
5. [What dataset.csv Does NOT Contain](#what-datasetcsv-does-not-contain)
6. [Urgency Classification (Dashboard-Derived)](#urgency-classification-dashboard-derived)
7. [Dashboard Enrichment Layer](#dashboard-enrichment-layer)
8. [Building index.html](#building-indexhtml)
9. [Current Dashboard Features](#current-dashboard-features)
10. [Example Record Through Both Layers](#example-record-through-both-layers)
11. [Field Summary Table](#field-summary-table)
12. [Submission Folder Files](#submission-folder-files)

---

## Two-Layer Architecture

This project uses **two separate layers**. They must not be confused:

| Layer | Purpose | Output | Modifies `dataset.csv`? |
|-------|---------|--------|-------------------------|
| **Integration Pipeline** | Merge five modality CSVs into one validated file | `dataset.csv` (9 columns) | **Yes** — this creates the file |
| **Dashboard Enrichment Layer** | Prepare data for the interactive UI | Embedded JSON in `index.html` | **No** — reads CSV only |

**Key point:** `Urgency`, `Actionable`, `Priority_Rank`, and standardized `Event_Type` labels exist **only** in the embedded dashboard data. They are computed automatically during the dashboard build (`embed_dataset.py` → `build_command_center.py`). They are **not** written back to `dataset.csv`.

---

## Pipeline Diagram

```
Five Modality CSVs
  audio.csv · pdf.csv · image.csv · video.csv · text.csv
        │
        ▼
Integration Pipeline
  · Modality-prefixed Incident_ID (AUD-, DOC-, IMG-, VID-, TXT-)
  · pandas.concat UNION merge (1,252 rows)
  · Missing values → N/A
  · Severity from Confidence_Score × 10
  · Schema validation
        │
        ▼
dataset.csv  (9 validated columns)
        │
        ▼
Dashboard Enrichment Layer
  ├── Event Type Standardization
  ├── Urgency Classification
  ├── Actionable Classification
  ├── Priority Rank
  ├── KPI Generation
  ├── Chart Aggregation
  ├── Filter Generation
  └── Investigation Table Data
        │
        ▼
embed_dataset.py  →  build_data()
        │
        ▼
build_command_center.py
        │
        ▼
index.html  (National Incident Command Center)
```

At runtime the browser opens **`index.html` only**. It does **not** load `dataset.csv`. All incident data is embedded at build time.

---

## Integration Pipeline

The Integration Pipeline combines outputs from all five team modalities into one unified, validated CSV.

### Input: Five Modality CSV Files

Each modality pipeline exports a CSV using the shared seven-column schema:

| Column | Description |
|--------|-------------|
| `Incident_ID` | `INC-YYYY-NNNNNN` (reserved range per modality) |
| `Event_Type` | Detected or labeled event category |
| `Source_Type` | Audio, Document, Image, Text, or Video |
| `Date_Time` | Timestamp when available |
| `Location` | Location string when available |
| `Confidence_Score` | Model confidence (0.0–1.0) |
| `Summary` | Incident summary text |

| Integration file | Modality | Rows |
|------------------|----------|-----:|
| `audio.csv` | Audio | 708 |
| `pdf.csv` | Document | 13 |
| `image.csv` | Image | 72 |
| `video.csv` | Video | 344 |
| `text.csv` | Text | 115 |
| **Total** | | **1,252** |

### Step 1 — Modality-Prefixed Incident_ID

Each row receives a prefix on `Incident_ID`. The original ID is preserved in `Original_Incident_ID`.

| Source_Type | Prefix | Example |
|-------------|--------|---------|
| Audio | `AUD-` | `AUD-000001` |
| Document | `DOC-` | `DOC-001000` |
| Image | `IMG-` | `IMG-002000` |
| Video | `VID-` | `VID-003000` |
| Text | `TXT-` | `TXT-004000` |

### Step 2 — UNION Merge

All five DataFrames are stacked with **`pandas.concat`** (UNION). One row per source record; no join on `Incident_ID`.

### Step 3 — Missing Values

Empty or missing fields are filled with the literal text **`N/A`**.

### Step 4 — Severity Classification

`Severity` is derived from `Confidence_Score` and stored in `dataset.csv`:

```
severity_score = Confidence_Score × 10
```

| Severity | Threshold |
|----------|-----------|
| Low | 0 ≤ score < 3 |
| Medium | 3 ≤ score < 7 |
| High | 7 ≤ score ≤ 10 |

**Distribution:** High 609 · Medium 407 · Low 236

### Step 5 — Validation

Before dashboard deployment, the integrated file is validated for:

- All required columns present
- 1,252 unique `Incident_ID` values
- Correct `Source_Type` per modality
- `Confidence_Score` in range 0.0–1.0
- Every row has `Severity` assigned

**Result:** `dataset.csv` in this submission folder (copy of `dashboard/data/dataset.csv`).

---

## dataset.csv — Final Validated Integrated Dataset

`dataset.csv` is the **only** persistent output of the Integration Pipeline. It contains **exactly 9 columns**:

| # | Column | Description |
|---|--------|-------------|
| 1 | `Incident_ID` | Modality-prefixed unique ID |
| 2 | `Event_Type` | Event category as produced by modality pipelines |
| 3 | `Source_Type` | Audio, Document, Image, Text, or Video |
| 4 | `Date_Time` | Timestamp or `N/A` |
| 5 | `Location` | Location string or `N/A` |
| 6 | `Confidence_Score` | Model confidence (0.0–1.0) |
| 7 | `Summary` | Incident summary text |
| 8 | `Severity` | Low / Medium / High (from Integration Step 4) |
| 9 | `Original_Incident_ID` | Pre-prefix ID (e.g. `INC-2026-000001`) |

**Note:** `Event_Type` values in `dataset.csv` reflect the integrated source data. Labels such as `Fire Scene` and `Fire`, or `Missing Child` and `Missing Person`, may appear as separate values. Consolidation of labels happens in the Dashboard Enrichment Layer, not in this file.

---

## What dataset.csv Does NOT Contain

The following fields are **intentionally absent** from `dataset.csv`. They are **not** part of the integration deliverable:

| Field | Why it is not in dataset.csv |
|-------|------------------------------|
| **Urgency** | Derived from `Event_Type` at dashboard build time |
| **Actionable** | Derived from `Event_Type` at dashboard build time |
| **Priority_Rank** | Computed from Urgency + Severity + Confidence at dashboard build time |
| **Standardized Event_Type** | Original labels preserved; standardization applied only during enrichment |

---

## Urgency Classification (Dashboard-Derived)

**Urgency is NOT stored in `dataset.csv`.**

The integrated dataset remains unchanged and contains only the original modality fields plus the integration-derived columns **`Severity`** and **`Original_Incident_ID`**. The nine columns in `dataset.csv` are the single source of truth for integration; no dashboard-only fields are written back to this file.

During the **dashboard build process** (`embed_dataset.py`, invoked by `build_command_center.py`), the data is enriched with additional dashboard-only fields in memory. One of these derived fields is **`Urgency`**, which is generated from the **standardized** `Event_Type`.

### Event type standardization (before Urgency)

Before assigning Urgency, event types are standardized in `embed_dataset.py` so filters, charts, and the priority queue use consistent labels. Examples:

| Original label (case-insensitive) | Standardized label |
|-----------------------------------|-------------------|
| Fire Scene | Fire |
| Missing Child / Missing Children | Missing person |
| Theft / Robbery | Robbery |
| Reference list (training plans) | Training Plan |
| Other | Unknown |

All other `Event_Type` values pass through unchanged unless they match the mapping table in `embed_dataset.py`.

### Operational Urgency rules (after standardization)

Urgency is assigned from the standardized event type (case-insensitive):

**High**

Assault, Bear attack, Bomb threat, Building collapse, Carjacking, Fire, Found body, Home invasion, Kidnapping, Medical emergency, Missing person, Murder, Plane crash, School lockdown, Sex, Shooting, Smoke scene, Stabbing, Suicide, Vehicle chase, Vehicle collision, Vehicle in water.

**Low**

Child custody dispute, No activity detected, Reference List (Training Plans), Student disturbance.

*(After standardization, “Reference list (training plans)” becomes `Training Plan`, which maps to Low via the `training plan` rule in `embed_dataset.py`.)*

**Medium**

All remaining event types.

### Where Urgency lives and how the dashboard uses it

- **This Urgency field exists only inside the dashboard’s embedded data** (`const DATA = { ... }` in `index.html`). It is not a column in `dataset.csv`.
- **It is used for** the Urgency filter, Incident Priority Queue ranking (Urgency → Severity → Confidence), KPI counts, and chart/filter logic when Urgency is selected.
- **It is not written back to `dataset.csv`**, preserving the integrated dataset as the single source of truth for integration deliverables.

**Urgency ≠ Severity:** `Severity` is derived during integration from `Confidence_Score × 10` and is stored in `dataset.csv`. `Urgency` reflects operational time-sensitivity of the event type and is computed only at dashboard build time.

**Implementation:** `embed_dataset.py` — `URGENCY_HIGH`, `URGENCY_LOW`, `derive_urgency()`

---

## Dashboard Enrichment Layer

During the dashboard build, `embed_dataset.py` reads `dataset.csv` and applies transformations **in memory**. The CSV file on disk is **never modified**.

### Processing flow (`build_data()`)

```
For each row in dataset.csv:
  1. clean_text() on all text fields
  2. standardize_event_type() on Event_Type
  3. derive_urgency() from standardized Event_Type
  4. derive Actionable from standardized Event_Type
  5. copy Severity and Confidence_Score from CSV

After all rows:
  6. assign Priority_Rank (global sort)
  7. compute dashboard metrics, filter lists, chart aggregates
```

The enriched result is serialized as `const DATA = { ... }` inside `index.html`.

---

### 1. Event Type Standardization

Applied so filters, charts, and KPIs use consistent labels. **`dataset.csv` is not changed.**

| Original label (case-insensitive) | Standardized label |
|-----------------------------------|-------------------|
| fire scene | Fire |
| missing child | Missing person |
| missing children | Missing person |
| people walking | People Scene |
| theft / robbery | Robbery |
| theft/robbery | Robbery |
| reference list (training plans) | Training Plan |
| reference list (training plan) | Training Plan |
| other | Unknown |
| public safety incident | Public Disturbance *(if Public Disturbance exists elsewhere in the dataset)* |

All other `Event_Type` values pass through unchanged.

---

### 2. Urgency Classification (see also [Urgency Classification (Dashboard-Derived)](#urgency-classification-dashboard-derived))

At build time, `derive_urgency()` assigns **High**, **Medium**, or **Low** from the standardized `Event_Type`. Full rules and rationale are documented in the section above; this step does not modify `dataset.csv`.

---

### 3. Actionable Classification

`Actionable` is `false` when standardized `Event_Type` (case-insensitive) is:

- blank, N/A, Unknown, False alarm, No activity detected, or Person walking / present

All other event types → `Actionable = true`.

Recomputed in the browser at runtime using the same rule for KPIs and queue logic.

---

### 4. Priority Rank Generation

Every record receives `Priority_Rank` (1 = highest) for the Incident Priority Queue.

**Sort order:**
1. Urgency — High → Medium → Low
2. Severity — High → Medium → Low
3. Confidence_Score — highest first

---

### 5. Dashboard Metrics

`embed_dataset.py` computes summary metrics embedded in `DATA.metrics` and `DATA.meta`, including:

- Total records, High severity count, actionable count, priority queue count
- Average confidence, source type list
- Severity rule documentation, actionable rule text

KPI cards in the UI recompute counts from filtered `DATA.records` at runtime.

---

### 6. Filter Generation

Filter dropdown options are built from enriched `DATA.records`:

| Filter | Source field | Notes |
|--------|--------------|-------|
| Source Type | `Source_Type` | Populated at init |
| **Urgency** | `Urgency` | Static options: All, High, Medium, Low |
| Event Type | `Event_Type` (standardized) | **Cascading** — updates when other filters change |
| Severity | `Severity` | From `dataset.csv` |
| Location | `Location` | From `dataset.csv` |

The **Urgency** filter uses the derived `Urgency` field. It does not exist in `dataset.csv`.

---

### 7. Chart Aggregation

Chart data is computed at runtime from filtered records. Charts in the current dashboard:

| Chart | Data basis |
|-------|------------|
| High Priority Incident Locations (Top 10) | High `Severity`, geographic locations only |
| Top Incident Locations | Location frequency; excludes N/A and CCTV |
| High Priority Incident Types | High `Severity` event types |
| Incident Priority Levels (donut) | `Severity` distribution (confidence-based) |

Charts respond to all active filters including Urgency.

---

### 8. Investigation Table Data

The Investigation Table uses enriched `DATA.records` with:

- Default **5 rows per page**
- Sortable columns: Incident ID, Severity, Event Type, Source, Date/Time, Location, Confidence
- Confidence displayed as percentage with progress bar
- Summary with hover tooltip
- Row click cross-links to queue and charts

Table is positioned **directly below the filter toolbar** (top of the main content area, before the Priority Queue and charts).

---

## Building index.html

### Step 1 — `embed_dataset.py`

```bash
python embed_dataset.py
```

Reads `dataset.csv`, runs the Dashboard Enrichment Layer, and can patch `DATA` into an existing `index.html`.

### Step 2 — `build_command_center.py` (recommended full rebuild)

```bash
python build_command_center.py
```

1. Calls `build_data()` from `embed_dataset.py`
2. Embeds `const DATA = { ... };` in the page
3. Writes complete `index.html` with HTML, CSS, JavaScript, and Plotly charts

**Open:** double-click `index.html` · hard refresh **Ctrl+F5** after rebuilding

---

## Current Dashboard Features

Layout order (top to bottom):

1. **Header** — National Incident Command Center, live clock, incident count
2. **KPI row** — Total Incidents, Medium Priority, High Priority, Actionable Queue
3. **Filter toolbar** — Source Type → Urgency → Event Type → Severity → Location
4. **Investigation Table** — paginated, default 5 rows
5. **Priority Queue** (left) + **Charts** (right)

**Cross-linked filtering:** Queue items, chart bars, donut segments, and table rows all update KPIs, charts, queue, and table together.

**Live deployment:** [incident-tracker.audreyrah.com](https://incident-tracker.audreyrah.com/) (may differ from local build until redeployed)

---

## Example Record Through Both Layers

### After Integration Pipeline → `dataset.csv`

| Field | Value |
|-------|-------|
| Incident_ID | `AUD-000002` |
| Event_Type | `Robbery` |
| Source_Type | Audio |
| Confidence_Score | 0.73 |
| Severity | High *(0.73 × 10 = 7.3)* |
| Original_Incident_ID | INC-2026-000002 |

*No Urgency, Actionable, or Priority_Rank columns.*

### After Dashboard Enrichment Layer → embedded in `index.html`

| Field | Value |
|-------|-------|
| Event_Type | Robbery *(unchanged)* |
| Severity | High *(from CSV)* |
| **Urgency** | Medium *(Robbery not in High/Low list)* |
| **Actionable** | true |
| **Priority_Rank** | Assigned by global Urgency → Severity → Confidence sort |

---

## Field Summary Table

| Field | Modality CSV | dataset.csv | index.html (DATA) | Layer |
|-------|:------------:|:-----------:|:-----------------:|-------|
| Incident_ID | ✓ | ✓ | ✓ | Integration |
| Original_Incident_ID | — | ✓ | — | Integration |
| Event_Type (raw) | ✓ | ✓ | — | Integration |
| Event_Type (standardized) | — | — | ✓ | Enrichment |
| Source_Type | ✓ | ✓ | ✓ | Integration |
| Date_Time | ✓ | ✓ | ✓ | Integration |
| Location | ✓ | ✓ | ✓ | Integration |
| Confidence_Score | ✓ | ✓ | ✓ | Integration |
| Summary | ✓ | ✓ | ✓ | Integration |
| Severity | — | ✓ | ✓ | Integration |
| Urgency | — | **—** | ✓ | Enrichment |
| Actionable | — | **—** | ✓ | Enrichment |
| Priority_Rank | — | **—** | ✓ | Enrichment |

---

## Submission Folder Files

```
dashboard1_incident_command_cente_timeline/
├── dataset.csv                              # Integration Pipeline output (9 columns)
├── embed_dataset.py                         # Dashboard Enrichment Layer
├── build_command_center.py                  # Full HTML dashboard builder
├── index.html                               # Final dashboard (open in browser)
├── README.md                                # Quick start
├── pipline.png                              # Pipeline / architecture diagram
└── Final_Dataset_and_Dashboard_Pipeline.md  # This document
```

---

## References

| Document | Location |
|----------|----------|
| Integration steps 1–4 | `../data/dataset _preparation.md` |
| Project report | `../../Project_Report.md` |
| Team schema & ID ranges | `../../README.md` |

---

*Integration Pipeline produces `dataset.csv`. Dashboard Enrichment Layer produces `index.html`. Derived fields (Urgency, Actionable, Priority_Rank, standardized Event_Type) exist only in the embedded dashboard data and are generated automatically during the build.*
