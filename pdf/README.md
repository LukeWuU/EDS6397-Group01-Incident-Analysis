# Document Modality (Student 2)

Part of the EDS 6397 Multimodal Incident Report Analyzer. This module converts
police / 1033-program PDF documents into a structured incident dataset that
merges with the other four modalities.

## Input data

Two FOIA-released PDFs from MuckRock (Arkansas 1033 Program records):

- `LESO2.pdf` — a 75-page scanned bundle containing twelve separate Arkansas
  law-enforcement agencies' MRAP / ARV acquisition, training, and policy documents.
- `List_of_LEA_with_training_plans.pdf` — a one-page list of Local Education
  Agencies with training plans.

## How it works

1. **Text extraction** (`extract_pdf_text`): reads each page with pdfplumber.
   Pages with little or no embedded text are treated as scans and sent to OCR
   (pytesseract on a PyMuPDF-rendered image). The decision is made per page, so a
   document with both typed and scanned pages still extracts correctly.
2. **Segmentation** (`segment_by_agency`): the 75-page bundle is split into one
   record per agency. Each agency is matched only in pages after the previous one,
   so cross-references between neighboring jurisdictions do not break the boundaries.
3. **Field extraction**: spaCy NER plus rule-based logic fills the schema. Dates
   use month-anchored patterns, location is derived from the agency name, event
   type is keyword-scored, and a text-quality measure serves as the confidence score.
4. **Standardization**: dates are normalized to ISO (YYYY-MM-DD), and Incident_IDs
   are assigned in the team's Document block.

## Output

`document_incidents.csv`, 13 rows, in the team's seven-column schema:

`Incident_ID, Event_Type, Source_Type, Date_Time, Location, Confidence_Score, Summary`

- `Source_Type` is always `Document`.
- `Incident_ID` runs `INC-2026-001000` through `INC-2026-001012` (Document block: 1000+).

## Run it

    pip install -r requirements.txt
    python -m spacy download en_core_web_sm
    # system OCR engine: apt-get install -y tesseract-ocr   (or the Windows Tesseract installer)
    # place the two PDFs in a ./pdfs folder, then:
    python document_pipeline.py

## Known limitations

- OCR of the scanned bundle is imperfect; some extracted text contains noise.
- Segmentation is by detected agency name, so section boundaries are approximate
  and a few unlabeled pages fold into the preceding agency (the Little Rock record
  is oversized for this reason).
- A couple of records have `Date_Time = Unknown` where no clear date was found;
  these are left honest rather than guessed.
- The modality datasets across the project are independent stand-ins, so the final
  integration demonstrates pipeline mechanics and schema compatibility rather than
  genuine cross-source incident correlation, which would emerge only with
  co-located real-world feeds.
