"""
document_pipeline.py
EDS 6397 - Multimodal Incident Report Analyzer
Student 2: Document Analyst

Converts police / 1033-program PDF documents into a structured incident CSV.

PIPELINE
  1. Extract text from each PDF, page by page. Typed pages use pdfplumber;
     scanned pages fall back to OCR (pytesseract on a PyMuPDF render).
  2. Segment the multi-agency LESO2 bundle into one record per agency.
  3. Run spaCy NER + rule-based extraction to fill the standardized schema.
  4. Standardize dates to ISO (YYYY-MM-DD) and assign Incident_IDs.
  5. Write document_incidents.csv in the team's seven-column schema.

OUTPUT SCHEMA (team standard):
  Incident_ID, Event_Type, Source_Type, Date_Time, Location,
  Confidence_Score, Summary

SETUP (run once):
  pip install -r requirements.txt
  python -m spacy download en_core_web_sm
  # OCR also needs the Tesseract ENGINE installed on the system:
  #   Ubuntu / Colab : apt-get install -y tesseract-ocr
  #   Windows        : https://github.com/UB-Mannheim/tesseract/wiki

USAGE:
  Put the source PDFs in a ./pdfs folder, then:  python document_pipeline.py
"""

import io
import os
import re
import glob
from collections import Counter

import pdfplumber
import fitz  # PyMuPDF
import pytesseract
import pandas as pd
import spacy
from PIL import Image

# ----------------------------------------------------------------------
# Configuration
# Incident_ID block agreed with the team (1000-wide blocks):
#   Audio 000001+ | Document 001000+ | Image 002000+ | Video 003000+ | Text 004000+
# ----------------------------------------------------------------------
YEAR = 2026
DOC_START = 1000
PDF_DIR = "pdfs"
BUNDLE_FILE = "LESO2.pdf"                          # multi-agency 1033 bundle
LEA_FILE = "List_of_LEA_with_training_plans.pdf"
OUTPUT_CSV = "document_incidents.csv"

# Arkansas agencies inside the LESO2 bundle; each is one incident record.
AGENCY_MARKERS = [
    "Benton County Sheriff", "Benton Police Department", "Bentonville Police Department",
    "Bryant Police Department", "Cabot Police Department", "Craighead County Sheriff",
    "Crawford County Sheriff", "Fort Smith Police Department", "Hot Springs Police Department",
    "Jacksonville Police Department", "Little Rock Police Department", "Union County Sheriff",
]

MONTHS = ("January|February|March|April|May|June|July|August|"
          "September|October|November|December")

nlp = spacy.load("en_core_web_sm")


# ----------------------------------------------------------------------
# 1. Text extraction (typed -> pdfplumber, scanned -> OCR fallback, per page)
# ----------------------------------------------------------------------
def _ocr_page(fitz_page, dpi=300):
    zoom = dpi / 72
    pix = fitz_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img)


def extract_pdf_text(pdf_path, min_chars=20, ocr_dpi=300):
    """Return [(page_number, method, text), ...]; OCR only pages with little text."""
    results = []
    doc = fitz.open(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = (page.extract_text() or "").strip()
            if len(text) >= min_chars:
                results.append((i + 1, "text", text))
            else:
                results.append((i + 1, "ocr", _ocr_page(doc[i], ocr_dpi).strip()))
    doc.close()
    return results


# ----------------------------------------------------------------------
# 2. Segment the bundle into one record per agency
# ----------------------------------------------------------------------
def segment_by_agency(pages):
    """Slice the page list into per-agency chunks. Each agency is searched only
    in pages AFTER the previous one, so cross-references can't steal boundaries."""
    first_page = {}
    search_from = 1
    for marker in AGENCY_MARKERS:
        for num, _method, text in pages:
            if num >= search_from and marker.lower() in text.lower():
                first_page[marker] = num
                search_from = num + 1
                break

    ordered = sorted(first_page.items(), key=lambda kv: kv[1])
    last_page = pages[-1][0]
    records = []
    for i, (marker, start) in enumerate(ordered):
        end = ordered[i + 1][1] - 1 if i + 1 < len(ordered) else last_page
        text = "\n".join(t for (n, _m, t) in pages if start <= n <= end)
        records.append({"agency": marker, "pages": f"{start}-{end}", "text": text})
    return records


# ----------------------------------------------------------------------
# 3. Field-extraction helpers
# ----------------------------------------------------------------------
def classify_event(text):
    t = text.lower()
    scores = {
        "Training Plan": t.count("training"),
        "Policy / Procedure": t.count("policy") + t.count("procedure"),
        "Equipment Acquisition (MRAP/ARV)": (
            t.count("mrap") + t.count("armored") + t.count("ambush")),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other / Administrative"


def text_quality(doc):
    """OCR-confidence proxy: share of clean word-like tokens (0-1)."""
    toks = [t for t in doc if not t.is_space and not t.is_punct]
    return round(len([t for t in toks if t.is_alpha]) / len(toks), 4) if toks else 0.0


def extract_date(raw):
    """Return a date string (month name or slash format), else 'Unknown'.
    Requires a real month name so address ZIP codes are not misread as dates."""
    m = re.search(r"(" + MONTHS + r")\s+\d{1,2},?\s*\d{4}", raw)
    if m:
        return re.sub(r"\s+", " ", m.group())
    m = re.search(r"\d{1,2}/\d{1,2}/\d{2,4}", raw)
    return m.group() if m else "Unknown"


def agency_location(agency):
    """Location from the agency name (more reliable than NER on noisy OCR)."""
    if "County" in agency:
        return re.match(r"(.+? County)", agency).group(1) + ", AR"
    return re.sub(r"\s*Police Department.*$", "", agency).strip() + ", AR"


def officer(doc):
    vals = [e.text.strip() for e in doc.ents
            if e.label_ == "PERSON" and len(e.text.strip()) > 3]
    return Counter(vals).most_common(1)[0][0] if vals else "Unknown"


def subject(raw):
    for line in raw.splitlines():
        s = line.strip()
        if re.match(r"^(RE:|Re:|SUBJECT)", s):
            return re.sub(r"^(RE:|Re:|SUBJECT)\s*", "", s)[:110]
    return next((l.strip()[:110] for l in raw.splitlines() if len(l.strip()) > 25), "")


# ----------------------------------------------------------------------
# 4. Build the structured rows
# ----------------------------------------------------------------------
def build_rows(records, lea_text):
    rows = []
    for i, rec in enumerate(records):
        doc = nlp(rec["text"])
        rows.append({
            "Incident_ID": f"INC-{YEAR}-{DOC_START + i:06d}",
            "Event_Type": classify_event(rec["text"]),
            "Source_Type": "Document",
            "Date_Time": extract_date(rec["text"]),
            "Location": agency_location(rec["agency"]),
            "Confidence_Score": text_quality(doc),
            "Summary": (f"{rec['agency']} (LESO2 p{rec['pages']}). "
                        f"{subject(rec['text'])} | Officer: {officer(doc)}"),
        })

    ldoc = nlp(lea_text)
    rows.append({
        "Incident_ID": f"INC-{YEAR}-{DOC_START + len(records):06d}",
        "Event_Type": "Reference List (Training Plans)",
        "Source_Type": "Document",
        "Date_Time": extract_date(lea_text),
        "Location": "Arkansas (statewide)",
        "Confidence_Score": text_quality(ldoc),
        "Summary": ("List of Local Education Agencies with training plans. "
                    + lea_text[:110].replace("\n", " ")),
    })
    return rows


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    bundle_path = os.path.join(PDF_DIR, BUNDLE_FILE)
    lea_path = os.path.join(PDF_DIR, LEA_FILE)

    print(f"Extracting {BUNDLE_FILE} (scanned pages need OCR, may take minutes)...")
    pages = extract_pdf_text(bundle_path)
    print(f"  {len(pages)} pages extracted.")

    records = segment_by_agency(pages)
    print(f"Segmented into {len(records)} agency records.")

    lea_text = "\n".join(t for (_n, _m, t) in extract_pdf_text(lea_path))

    df = pd.DataFrame(build_rows(records, lea_text))

    # Standardize dates to ISO (YYYY-MM-DD); unparseable values -> 'Unknown'
    df["Date_Time"] = (
        pd.to_datetime(df["Date_Time"], errors="coerce", format="mixed")
          .dt.strftime("%Y-%m-%d")
          .fillna("Unknown")
    )

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(df)} rows -> {OUTPUT_CSV}\n")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
