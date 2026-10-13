# National Incident Command Center

Emergency operations dashboard for **EDS6397 Group 01** — final submission build.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Final dashboard with embedded enriched `DATA` object |
| `dataset.csv` | Final integrated dataset (1,252 records, 9 columns) |
| `embed_dataset.py` | Dashboard Enrichment Layer — reads `dataset.csv` and builds JSON |
| `build_command_center.py` | Full rebuild — runs enrichment and writes `index.html` |
| `pipeline.png` | Integration and dashboard workflow diagram |
| `README.md` | This file |

Canonical dataset copy: `../02_Final_Dataset/data/dataset.csv` (same file as local `dataset.csv`).

## Open

Double-click **`index.html`** in any modern browser. Hard refresh with **Ctrl+F5** after rebuilding.

## Rebuild

Full dashboard rebuild:

```bash
python build_command_center.py
```

This reads `dataset.csv`, runs the **Dashboard Enrichment Layer** (`embed_dataset.py`), and writes a new `index.html`.

To refresh embedded data only (preserves existing HTML shell and styles):

```bash
python embed_dataset.py
```

## Integration Pipeline and Dashboard Enrichment Layer

This dashboard uses **two separate layers**:

| Layer | Input / Output | What it does |
|-------|----------------|--------------|
| **Integration Pipeline** | Five modality CSVs → `dataset.csv` | Assigns modality-prefixed `Incident_ID`, UNION merge, N/A handling, and **Severity** from `Confidence_Score × 10` (Low 0–3, Medium 3–7, High 7–10). Produces 9 validated columns and 1,252 rows. |
| **Dashboard Enrichment Layer** | `dataset.csv` → embedded `DATA` in `index.html` | Derives **Urgency**, **Actionable**, **Priority_Rank**, standardized `Event_Type`, KPI metrics, and chart data **without modifying** `dataset.csv`. |

`dataset.csv` does **not** contain Urgency, Actionable, or Priority_Rank. Those fields exist only in the embedded `DATA` object inside `index.html`.

See `pipeline.png` in this folder and **`../02_Final_Dataset/data/Final_Dataset_and_Dashboard_Pipeline.md`** for the complete workflow, classification rules, and field-level mapping.

## Dashboard layout

1. KPI summary cards  
2. Filters: Source Type → **Urgency** → Event Type → Severity → Location  
3. Investigation Table (default 5 rows per page)  
4. Priority Queue + charts (locations, event types, severity donut)

## Live site

[incident-tracker.audreyrah.com](https://incident-tracker.audreyrah.com/)
