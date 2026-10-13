"""CSV record assembly and export helpers."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional, Union

import pandas as pd

from pipeline.analyzer import AnalysisResult
from pipeline.extractor import ExtractionResult
from pipeline.llm_analyzer import LLMExtractionResult
from pipeline.transcriber import TranscriptionResult
from pipeline.transcript_cleanup import clean_asr_transcript, repetition_ratio


TRANSCRIBED_SCRIPT_COLUMN = "Transcribed Script"

OUTPUT_COLUMNS = [
    "Incident_ID",
    "Event_Type",
    "Source_Type",
    TRANSCRIBED_SCRIPT_COLUMN,
    "Transcript Summary",
    "Date_Time",
    "Location",
    "Sentiment",
    "Urgency_Score",
    "Confidence_Score",
]


def load_metadata(dataset_dir: Union[str, Path] = "dataset") -> dict[str, dict[str, Any]]:
    """Load optional 911 metadata keyed by audio file name."""
    metadata_path = Path(dataset_dir) / "911_metadata.csv"
    if not metadata_path.exists():
        return {}

    try:
        frame = pd.read_csv(metadata_path)
    except Exception:
        return {}

    if "file_name" not in frame.columns:
        return {}

    frame = frame.dropna(subset=["file_name"])
    metadata: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        file_name = str(row["file_name"]).strip()
        if not file_name:
            continue

        row_data = row.to_dict()
        metadata[file_name.lower()] = row_data
        metadata[Path(file_name).stem.lower()] = row_data
    return metadata


def build_record(
    index: int,
    transcription: TranscriptionResult,
    extraction: ExtractionResult,
    analysis: AnalysisResult,
    llm_result: LLMExtractionResult,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    transcript_excerpt = _transcript_excerpt(transcription)
    if transcription.transcript == "ERROR":
        transcript_summary = "Summary: Transcription failed.\nLocation and Person Name Mention: Unknown\nKeywords: Unknown"
        event_type = "Unknown"
    else:
        transcript_summary = llm_result.transcript_summary_block()
        event_type = llm_result.event_type

    return {
        "Incident_ID": f"INC-2026-{index:06d}",
        "Event_Type": event_type,
        "Source_Type": "Audio",
        TRANSCRIBED_SCRIPT_COLUMN: transcript_excerpt,
        "Transcript Summary": transcript_summary,
        "Date_Time": _date_time_from_metadata(metadata),
        "Location": _metadata_location(metadata),
        "Sentiment": analysis.sentiment,
        "Urgency_Score": analysis.urgency_score,
        "Confidence_Score": _confidence_score(transcription, analysis, llm_result),
    }


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(records, columns=OUTPUT_COLUMNS)


def export_csv(records: list[dict[str, Any]], output_path: Union[str, Path] = "outputs/emergency_analysis_output.csv") -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records_to_dataframe(records).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _metadata_or(metadata: dict[str, Any], field: str, fallback: str) -> str:
    value = metadata.get(field)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _transcript_excerpt(transcription: TranscriptionResult) -> str:
    if transcription.transcript == "ERROR":
        return "Transcription failed for this audio file."

    plain = (transcription.transcript or "").strip()
    quality = getattr(transcription, "transcript_quality_score", 1.0)
    if repetition_ratio(plain) > 0.12 or quality < 0.45:
        cleaned = clean_asr_transcript(plain, backend="wav2vec2")
        if cleaned and len(cleaned) < len(plain) * 0.85:
            plain = cleaned

    return re.sub(r"\s+", " ", plain).strip()


def _safe_location(value: str) -> str:
    text = _normalize_text(value)
    if not text or text.lower() == "unknown":
        return "Unknown"
    if len(text.split()) > 8 or _looks_like_noisy_asr(text):
        return "Unknown"
    return text


def _looks_like_noisy_asr(value: str) -> bool:
    words = re.findall(r"[A-Za-z']+", value)
    if not words:
        return True

    short_word_ratio = sum(1 for word in words if len(word) <= 2) / len(words)
    uppercase_ratio = sum(1 for char in value if char.isupper()) / max(1, sum(1 for char in value if char.isalpha()))
    long_word_ratio = sum(1 for word in words if len(word) >= 18) / len(words)
    repeated_noise = len(re.findall(r"\b([A-Za-z]{1,3})\b(?:\s+\1\b){2,}", value, flags=re.IGNORECASE))
    return short_word_ratio > 0.38 or uppercase_ratio > 0.85 or long_word_ratio > 0.08 or repeated_noise > 2


def _normalize_text(value: str) -> str:
    text = _repair_text_encoding(value)
    text = _plain_ascii_punctuation(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b([A-Z])(?:\s+\1){3,}\b", "", text)
    text = re.sub(r"\b([A-Za-z])\1{3,}\b", r"\1", text)
    return text


def _remove_dangling_metadata_fragments(value: str) -> str:
    patterns = [
        r"\bAlso check this\b.*$",
        r"\bAlso listen to\b.*$",
        r"\bListen to the second\b.*$",
        r"\bClick here\b.*$",
        r"\bMore audio\b.*$",
    ]
    text = value
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    return text


def _repair_text_encoding(value: str) -> str:
    """Repair common UTF-8 text that was decoded as Windows-1252."""
    try:
        repaired = value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value

    if _mojibake_score(repaired) < _mojibake_score(value):
        return repaired
    return value


def _mojibake_score(value: str) -> int:
    markers = ("\\u00e2", "\\u20ac", "\\ufffd", "\\u009d")
    return sum(value.count(marker.encode("utf-8").decode("unicode_escape")) for marker in markers)


def _plain_ascii_punctuation(value: str) -> str:
    translations = {
        0x2018: "'",
        0x2019: "'",
        0x201A: "'",
        0x201B: "'",
        0x201C: '"',
        0x201D: '"',
        0x201E: '"',
        0x201F: '"',
        0x2013: "-",
        0x2014: "-",
        0x2026: "...",
        0x00A0: " ",
    }
    text = value.translate(translations)
    text = text.replace("\u00e2\u20ac\u0153", '"')
    text = text.replace("\u00e2\u20ac\u009c", '"')
    text = text.replace("\u00e2\u20ac\u009d", '"')
    text = text.replace("\u00e2\u20ac\ufffd", '"')
    text = text.replace("\u00e2\u20ac\u2122", "'")
    text = text.replace("\u00e2\u20ac\u02dc", "'")
    text = text.replace("\u00e2\u20ac\u201c", "-")
    text = text.replace("\u00e2\u20ac\u201d", "-")
    return text


def _first_sentences(text: str, max_sentences: int, max_chars: int) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not parts:
        parts = [text]

    excerpt = " ".join(parts[:max_sentences])
    if len(excerpt) <= max_chars:
        return excerpt

    trimmed = excerpt[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{trimmed}."


def _metadata_location(metadata: dict[str, Any]) -> str:
    return _safe_location(_metadata_or(metadata, "state", "Unknown"))


def _date_time_from_metadata(metadata: dict[str, Any]) -> str:
    description_date = _date_from_text(str(metadata.get("description", "")))
    if description_date:
        return description_date

    metadata_date = _date_from_metadata_value(metadata.get("date"))
    if metadata_date:
        return metadata_date

    return "Unknown"


def _date_from_text(text: str) -> str:
    normalized = _plain_ascii_punctuation(_repair_text_encoding(text))
    month_pattern = (
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+"
        r"(\d{4})\b"
    )
    match = re.search(month_pattern, normalized, flags=re.IGNORECASE)
    if not match:
        return ""

    month = _month_number(match.group(1))
    year = int(match.group(2))
    if not month:
        return ""
    return f"{year:04d}-{month:02d}-01 00:00:00"


def _date_from_metadata_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or not str(value).strip():
        return ""

    text = str(value).strip()
    month_year = re.fullmatch(r"(\d{1,2})/(\d{2,4})", text)
    if month_year:
        month = int(month_year.group(1))
        year = _normalize_year(int(month_year.group(2)))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-01 00:00:00"

    parsed = pd.to_datetime(text, errors="coerce")
    if not pd.isna(parsed):
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    if _has_time_component(text):
        return text
    return ""


def _month_number(value: str) -> int:
    key = value.lower().rstrip(".")[:3]
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    return months.get(key, 0)


def _normalize_year(year: int) -> int:
    if year >= 100:
        return year
    return 2000 + year if year < 70 else 1900 + year


def _has_time_component(value: str) -> bool:
    return bool(re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", value))


def _confidence_score(
    transcription: TranscriptionResult,
    analysis: AnalysisResult,
    llm_result: LLMExtractionResult,
) -> float:
    if transcription.transcript == "ERROR":
        return 0.0
    scores = [transcription.confidence_score, analysis.sentiment_confidence, llm_result.confidence]
    return round(sum(scores) / len(scores), 2)
