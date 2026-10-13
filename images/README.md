# Incident Analysis Module

Student 3 image analysis: crime-scene photos → structured CSV via YOLO object detection, scene classification, and OCR.

## Installation

Python 3.10+ required.

```bash
pip install -r requirements.txt
```

Install Tesseract OCR (extracts any visible text found in an image):

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`

On first run, YOLOv8 downloads `models/yolov8n.pt` if it is not already present. A pretrained fire/smoke YOLOv8 model is also downloaded automatically to `models/fire_smoke.pt` (D-Fire fine-tune from Hugging Face).

## Dataset

The assignment recommends the [Roboflow Fire Detection](https://universe.roboflow.com/search?q=fire+detection) datasets (1000+ images, YOLOv8 format) for training/evaluation examples.

This prototype uses a practical substitute that does not require committing large image binaries to the repo:

| Component | Source | Role |
| --------- | ------ | ---- |
| General objects (person, car, truck, …) | COCO-pretrained `models/yolov8n.pt` | Traffic / people scene evidence |
| Fire and smoke | [rabahdev/fire-smoke-yolov8n](https://huggingface.co/rabahdev/fire-smoke-yolov8n) on Hugging Face | Fire/smoke detection (D-Fire fine-tune) |
| Input images | Your own files in `input/` | Any crime-scene, accident, fire, or traffic photos |

**To use Roboflow images:** create a free Roboflow account, download a fire-detection dataset in YOLOv8 format, and place test images (`.jpg`, `.png`, etc.) in `input/`. The pipeline runs inference only — no training step is required.

**Sample output:** `output/images_output.csv` shows example rows from a prior run. Re-run the pipeline after adding images to regenerate it.

## Running

From the project root:

```bash
python -m src.main
```

Place images in `input/` (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`). Output is written to `output/images_output.csv` and `output/images_for_integration.csv`. Bad or unsupported files are logged and skipped.

Each run assigns at most **999** image IDs (`IMG-001` through `IMG-999`). Additional images are skipped once that limit is reached.

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `INCIDENT_INPUT_DIR` | `input/` | Input image directory |
| `INCIDENT_OUTPUT_DIR` | `output/` | Output directory |
| `INCIDENT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `WARNING`, etc.) |
| `INCIDENT_COCO_MODEL` | `models/yolov8n.pt` | COCO YOLO weights for people, vehicles, signs |
| `INCIDENT_FIRE_MODEL` | `models/fire_smoke.pt` | Fire/smoke YOLO weights (auto-downloaded) |
| `TESSERACT_CMD` | _(auto-detect)_ | Path to the Tesseract binary if not on `PATH` |

## Output schema

| Column | Description |
| ------ | ----------- |
| `Image_ID` | Modality-prefixed ID (`IMG_001`, `IMG_002`, …) for team integration |
| `Scene_Type` | One of: Fire Scene, Smoke Scene, Traffic Scene, People Scene, Other |
| `Objects_Detected` | Detected object names, e.g. `fire; smoke` |
| `Text_Extracted` | OCR text from the image, or `N/A` |
| `Confidence_Score` | Average of all raw detection confidences (0–1); intended for Student 6 severity mapping |

`Confidence_Score` is the mean across every bounding box returned before deduplication, so integration can derive Low / Medium / High severity from a single row-level signal.

Row order in `images_output.csv` maps to incident numbers in `images_for_integration.csv` (first row → `INC-2026-002000`, second → `INC-2026-002001`, and so on).

## Dependencies

Python: `opencv-python`, `ultralytics`, `pytesseract`, `Pillow`, `numpy` (see `requirements.txt`).

System: Tesseract OCR.
