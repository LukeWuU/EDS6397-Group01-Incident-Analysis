# Video Analyst Module (Student 4)

Processes CCTV/surveillance video clips and outputs a structured CSV of
detected events for integration into the team's unified incident dataset.

## Pipeline

1. **extract_frames.py** — samples 1 frame/second from each clip, records timestamp
2. **detect_motion.py** — frame-differencing; flags frames with >0.5% pixel change
3. **run_yolo.py** — runs YOLO (yolo26n.pt, pretrained, no training) only on flagged frames
4. **build_csv.py** — assembles final CSV with Incident_IDs

Run the whole thing with:
```
python src/pipeline.py
```

## Conventions

- **Timestamp format:** `HH:MM:SS` (zero-padded), relative to start of each clip
- **Frame_ID format:** `FRM_<clip_name>_<4-digit sequence>` e.g. `FRM_Walk1_0001`
- **Incident_ID block:** `INC-2026-003000` through `INC-2026-003999` — reserved
  exclusively for the Video modality (Student 4). IDs increment by 1 per
  detected-event row.

## Event labeling approach

YOLO detects object classes (e.g. `person`) but does not classify activities
like "fighting" or "collapsing". Per the assignment ("training an anomaly
model is not required"), this module uses a simple heuristic on top of
YOLO's person bounding boxes instead of a trained activity-recognition model:

| Condition | Event_Detected label |
|---|---|
| 0 persons detected | No activity detected |
| 1 person, box taller than wide, OR box in upper half of frame | Person walking / present |
| 1 person, box wider than tall AND box centered in lower half of frame | Possible person down / collapse |
| 2 persons detected | Possible altercation / two-person interaction |
| 3+ persons detected | Crowd gathering |

(Collapse requires both signals together -- box shape alone produced false
positives on a normal walking person whose box was momentarily wide near
frame edges, so vertical position was added as a second check.)

This is a documented heuristic, not a trained classifier — noted here and in
the project report as the scope boundary for this prototype.

## Output

Final CSV: `output/video_incidents.csv`

Columns: `Incident_ID, Timestamp, Frame_ID, Event_Detected, Objects, Confidence`

## Data

Source clips from the CAVIAR CCTV dataset. The `data/` folder is gitignored
(raw video clips are large binary files and shouldn't live in git) — download
clips from the shared Google Drive folder and place them in `video/data/`
before running the pipeline.

**Google Drive (CAVIAR clips used):** https://drive.google.com/drive/folders/1lRUQ8HRqhQMVs03axHX2eIXomwbO3rxV?usp=sharing

Original dataset: http://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/

Clips used in this prototype (9 total):
- `Walk1.mpg` — single person walking (baseline / normal activity)
- `Rest_FallOnFloor.mpg` — person collapsing (anomaly: person down)
- `Fight_OneManDown.mpg` — fight scenario (anomaly: altercation + person down)
- `Meet_Crowd.mpg` — people gathering (anomaly: crowd)
- `LeftBag.mpg` — person leaving bag unattended (abandoned object scenario)
- `Fight_Chase.mpg` — chase scenario (anomaly: high-motion altercation)
- `Rest_SlumpOnFloor.mpg` — person slumping to floor (anomaly: person down variant)
- `Meet_WalkTogether1.mpg` — two people walking together (multi-person normal activity)
- `LeftBag_PickedUp.mpg` — bag retrieved after being left (abandoned object resolution)
