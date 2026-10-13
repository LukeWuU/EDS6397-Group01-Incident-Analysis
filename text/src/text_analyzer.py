"""
Part 5 — Text Analyst
Multimodal Crime / Incident Report Analyzer

This script processes the Kaggle CrimeReport text dataset and generates:
1. A Part 5 text-analysis CSV:
   Text_ID, Source, Raw_Text, Sentiment, Entities, Topic

2. A team-integration CSV using the shared format:
   Incident_ID, Event_Type, Source_Type, Date_Time, Location, Confidence_Score, Summary

Input dataset:
    text/data/CrimeReport (1).txt

The Kaggle file is a JSON Lines .txt file, where each line is one social/news post record.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import TreebankWordTokenizer
from transformers import pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "text" / "data" / "CrimeReport (1).txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "text" / "outputs"

TEXT_OUTPUT_FILENAME = "part5_text_analysis_output.csv"
INTEGRATION_OUTPUT_FILENAME = "part5_text_integration_output.csv"
INCIDENT_ID_START_NUMBER = 4000

ENTITY_LABELS = {"PERSON", "GPE", "LOC", "FAC", "ORG", "DATE"}

TOPIC_LABELS = [
    "Shooting",
    "Theft / Robbery",
    "Assault",
    "Fire",
    "Accident",
    "Drug Crime",
    "Public Disturbance",
    "Police Activity",
    "Legal / Court",
    "Other",
]

TOKENIZER = TreebankWordTokenizer()
STOP_WORDS = set(stopwords.words("english"))

def clean_text(text: object) -> str:
    """
    Clean noisy social/news text while preserving meaning for NLP analysis.
    """
    if pd.isna(text):
        return ""

    text = str(text)
    text = html.unescape(text)
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def tokenize_text(text: str) -> List[str]:
    """
    Tokenize cleaned text and remove common English stopwords.

    This step explicitly satisfies the Part 5 preprocessing requirement:
    remove noise, normalize, and tokenize.
    """
    if not text:
        return []

    tokens = TOKENIZER.tokenize(text.lower())

    filtered_tokens = [
        token
        for token in tokens
        if re.search(r"[a-zA-Z0-9]", token) and token not in STOP_WORDS
    ]

    return filtered_tokens

def clean_source(source: object) -> str:
    """
    Convert Twitter source HTML into a readable platform/source name.
    Example:
        '<a href="...">TweetDeck</a>' -> 'TweetDeck'
        'web' -> 'web'
    """
    if pd.isna(source):
        return "Unknown"

    source_text = html.unescape(str(source)).strip()

    match = re.search(r">([^<>]+)<", source_text)
    if match:
        return match.group(1).strip()

    source_text = re.sub(r"<.*?>", "", source_text).strip()
    return source_text if source_text else "Unknown"


def load_dataset(input_path: Path) -> pd.DataFrame:
    """
    Load the CrimeReport dataset.

    The downloaded Kaggle file is JSON Lines format, even though the assignment
    description says CSV. Therefore, pandas.read_json(..., lines=True) is used.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Please download the Kaggle dataset into text/data first."
        )

    df = pd.read_json(input_path, lines=True)

    required_columns = {"id", "text", "created_at", "source"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    return df


def extract_entities(text: str, nlp_model) -> Tuple[str, List[Dict[str, str]]]:
    """
    Extract people, locations, organizations, facilities, and dates using spaCy NER.
    Returns both a display string and a detailed entity list.
    """
    doc = nlp_model(text)

    entities: List[Dict[str, str]] = []
    seen = set()

    for ent in doc.ents:
        if ent.label_ in ENTITY_LABELS:
            key = (ent.text.strip(), ent.label_)
            if key not in seen:
                seen.add(key)
                entities.append({"text": ent.text.strip(), "label": ent.label_})

    if not entities:
        return "No entities found", []

    entity_string = "; ".join(
        f"{entity['text']} ({entity['label']})" for entity in entities
    )
    return entity_string, entities


def select_location(row: pd.Series, entities: List[Dict[str, str]]) -> str:
    """
    Select the best available location for the integration output.
    Priority:
    1. Twitter place.full_name if available
    2. spaCy location entities
    3. user.location if available
    4. Unknown
    """
    place = row.get("place")
    if isinstance(place, dict):
        full_name = place.get("full_name")
        if full_name:
            return str(full_name)

    location_entities = [
        entity["text"]
        for entity in entities
        if entity["label"] in {"GPE", "LOC", "FAC"}
    ]
    if location_entities:
        return "; ".join(location_entities[:3])

    user = row.get("user")
    if isinstance(user, dict):
        user_location = user.get("location")
        if user_location:
            return str(user_location)

    return "Unknown"


def normalize_sentiment_label(label: str) -> str:
    """
    Normalize HuggingFace sentiment labels to assignment-friendly labels.
    """
    label = label.upper()

    if "NEGATIVE" in label or label == "LABEL_0":
        return "Negative"
    if "POSITIVE" in label or label == "LABEL_2":
        return "Positive"
    return "Neutral"


def analyze_sentiment(text: str, sentiment_pipeline) -> Tuple[str, float]:
    """
    Run HuggingFace sentiment analysis.
    """
    if not text:
        return "Neutral", 0.0

    result = sentiment_pipeline(text[:512])[0]
    sentiment = normalize_sentiment_label(result["label"])
    score = float(result.get("score", 0.0))
    return sentiment, round(score, 4)


def classify_topic(text: str, topic_pipeline) -> Tuple[str, float]:
    """
    Run HuggingFace zero-shot topic classification.
    """
    if not text:
        return "Other", 0.0

    result = topic_pipeline(text[:512], candidate_labels=TOPIC_LABELS)
    label = result["labels"][0]
    score = float(result["scores"][0])
    return label, round(score, 4)


def make_incident_id(index: int) -> str:
    """
    Create the shared team Incident_ID format for Part 5 text records.
    The first Part 5 text incident starts at INC-2026-004000.
    Example: INC-2026-004000
    """
    incident_number = INCIDENT_ID_START_NUMBER + index - 1
    return f"INC-2026-{incident_number:06d}"


def make_text_id(index: int) -> str:
    """
    Create the Part 5 text record ID.
    Example: TXT-000001
    """
    return f"TXT-{index:06d}"


def make_summary(text: str, sentiment: str, entities: str, max_length: int = 260) -> str:
    """
    Create a short human-readable summary for the integration file.
    """
    base = text.strip()
    if len(base) > max_length:
        base = base[: max_length - 3].rstrip() + "..."

    return f"{base} | Sentiment: {sentiment} | Entities: {entities}"


def run_text_analysis(input_path: Path, output_dir: Path, limit: int | None = None) -> None:
    """
    Main pipeline for Part 5 — Text Analyst.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading dataset...")
    df = load_dataset(input_path)

    if limit is not None:
        df = df.head(limit).copy()

    print(f"Loaded {len(df)} text records.")

    print("Loading spaCy NER model...")
    nlp_model = spacy.load("en_core_web_sm")

    print("Loading HuggingFace sentiment model...")
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
    )

    print("Loading HuggingFace zero-shot topic model...")
    topic_pipeline = pipeline(
        "zero-shot-classification",
        model="typeform/distilbert-base-uncased-mnli",
    )

    text_rows = []
    integration_rows = []

    print("Processing records...")
    for output_index, (_, row) in enumerate(df.iterrows(), start=1):
        raw_text = str(row.get("text", ""))
        clean = clean_text(raw_text)
        source = clean_source(row.get("source", "Unknown"))

        tokens = tokenize_text(clean)

        entities_string, entities_detail = extract_entities(clean, nlp_model)
        sentiment, sentiment_score = analyze_sentiment(clean, sentiment_pipeline)
        topic, topic_score = classify_topic(clean, topic_pipeline)

        text_id = make_text_id(output_index)
        incident_id = make_incident_id(output_index)
        location = select_location(row, entities_detail)

        date_time = row.get("created_at")
        if pd.isna(date_time):
            date_time = "Unknown"
        else:
            date_time = str(date_time)

        summary = make_summary(clean, sentiment, entities_string)

        text_rows.append(
            {
                "Text_ID": text_id,
                "Source": source,
                "Raw_Text": raw_text,
                "Sentiment": sentiment,
                "Entities": entities_string,
                "Topic": topic,
            }
        )

        integration_rows.append(
            {
                "Incident_ID": incident_id,
                "Event_Type": topic,
                "Source_Type": "Text",
                "Date_Time": date_time,
                "Location": location,
                "Confidence_Score": topic_score,
                "Summary": summary,
            }
        )

    text_output_df = pd.DataFrame(text_rows)
    integration_output_df = pd.DataFrame(integration_rows)

    text_output_path = output_dir / TEXT_OUTPUT_FILENAME
    integration_output_path = output_dir / INTEGRATION_OUTPUT_FILENAME

    text_output_df.to_csv(text_output_path, index=False, encoding="utf-8-sig")
    integration_output_df.to_csv(
        integration_output_path, index=False, encoding="utf-8-sig"
    )

    print("\nPart 5 text analysis completed successfully.")
    print(f"Text analysis output: {text_output_path}")
    print(f"Integration output: {integration_output_path}")
    print("\nText output preview:")
    print(text_output_df.head())
    print("\nIntegration output preview:")
    print(integration_output_df.head())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Part 5 Text Analyst pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to CrimeReport JSON Lines text file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where output CSV files will be saved.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for quick testing. Example: --limit 10",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_text_analysis(input_path=args.input, output_dir=args.output_dir, limit=args.limit)