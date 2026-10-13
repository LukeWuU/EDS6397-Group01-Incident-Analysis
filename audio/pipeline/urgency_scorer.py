"""Robust urgency scoring from transcript, LLM summary, and LLM event type."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.event_rules import detect_event_type, normalize_event_type
from pipeline.extractor import URGENCY_PHRASES, compute_negation_boost, compute_phrase_urgency


# Baseline severity by LLM event type (life-safety oriented, 0.0–1.0).
EVENT_TYPE_URGENCY: dict[str, float] = {
    "Medical emergency": 0.93,
    "Childbirth": 0.90,
    "Shooting": 0.95,
    "Stabbing": 0.94,
    "Murder": 0.96,
    "Kidnapping": 0.92,
    "Explosion": 0.94,
    "Vehicle in water": 0.93,
    "Drowning": 0.92,
    "Plane crash": 0.95,
    "Fire": 0.82,
    "Domestic disturbance": 0.72,
    "Suicide": 0.88,
    "Robbery": 0.78,
    "Carjacking": 0.80,
    "Burglary": 0.62,
    "Vehicle chase": 0.76,
    "Vehicle collision": 0.68,
    "Animal attack": 0.70,
    "DUI": 0.55,
    "Public safety incident": 0.48,
    "False alarm": 0.12,
    "Unknown": 0.40,
}

CRITICAL_EVENT_TYPES = frozenset(
    {
        "Medical emergency",
        "Childbirth",
        "Shooting",
        "Stabbing",
        "Murder",
        "Kidnapping",
        "Explosion",
        "Vehicle in water",
        "Drowning",
        "Plane crash",
    }
)

LOW_URGENCY_EVENT_TYPES = frozenset({"False alarm"})


@dataclass(frozen=True)
class UrgencySignals:
    event_baseline: float
    transcript_signal: float
    summary_signal: float
    keyword_signal: float
    negation_boost: float
    emotion_signal: float
    matched_phrases: tuple[str, ...]


def build_urgency_focus_text(transcript: str, llm_summary: str, llm_keywords: str = "") -> str:
    """Pick text for emotion scoring: summary first, then urgent transcript windows."""
    summary = _clean_summary(llm_summary)
    if summary:
        parts = [summary]
    else:
        parts = []

    parts.extend(_urgency_windows(transcript))
    if llm_keywords and llm_keywords.lower() != "unknown":
        parts.append(llm_keywords.replace(",", " "))

    combined = " ".join(part.strip() for part in parts if part.strip())
    if combined:
        return combined[:1800]
    return (transcript or "")[:1800]


def compute_urgency_score(
    transcript: str,
    *,
    event_type: str = "Unknown",
    llm_summary: str = "",
    llm_keywords: str = "",
    emotion_distress: float = 0.0,
) -> tuple[float, UrgencySignals]:
    """Return clipped urgency score and component signals."""
    normalized_event = normalize_event_type(event_type)
    event_baseline = EVENT_TYPE_URGENCY.get(normalized_event, EVENT_TYPE_URGENCY["Unknown"])

    summary_text = _clean_summary(llm_summary)
    transcript_signal, transcript_phrases = compute_phrase_urgency(transcript)
    summary_signal, summary_phrases = compute_phrase_urgency(summary_text)
    keyword_signal, keyword_phrases = compute_phrase_urgency(llm_keywords.replace(",", " "))

    combined_text = " ".join(filter(None, [transcript, summary_text, llm_keywords.replace(",", " ")]))
    negation_boost = compute_negation_boost(combined_text)

    _, rule_score, _ = detect_event_type(combined_text)
    rule_signal = min(1.0, rule_score / 5.0)

    text_signal = max(transcript_signal, summary_signal, keyword_signal, rule_signal)

    score = (
        0.30 * event_baseline
        + 0.22 * transcript_signal
        + 0.18 * summary_signal
        + 0.10 * keyword_signal
        + 0.10 * emotion_distress
        + 0.10 * negation_boost
    )

    if text_signal >= 0.55 and event_baseline >= 0.70:
        score = max(score, 0.72)
    if normalized_event in CRITICAL_EVENT_TYPES:
        score = max(score, event_baseline * 0.80, text_signal * 0.65)
    if negation_boost >= 1.0 and event_baseline >= 0.55:
        score = max(score, 0.75)
    if normalized_event in LOW_URGENCY_EVENT_TYPES:
        score = min(score, 0.35)

    score = round(max(0.0, min(1.0, score)), 2)
    matched = tuple(dict.fromkeys([*transcript_phrases, *summary_phrases, *keyword_phrases]))
    signals = UrgencySignals(
        event_baseline=round(event_baseline, 2),
        transcript_signal=round(transcript_signal, 2),
        summary_signal=round(summary_signal, 2),
        keyword_signal=round(keyword_signal, 2),
        negation_boost=round(negation_boost, 2),
        emotion_signal=round(emotion_distress, 2),
        matched_phrases=matched,
    )
    return score, signals


def _clean_summary(summary: str) -> str:
    text = re.sub(r"(?i)^summary:\s*", "", (summary or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _urgency_windows(transcript: str, max_windows: int = 4, window_chars: int = 280) -> list[str]:
    """Extract transcript slices around urgency language and the call tail."""
    if not transcript:
        return []

    lower = transcript.lower()
    windows: list[str] = []
    seen: set[str] = set()

    def add_window(start: int) -> None:
        start = max(0, start - 80)
        end = min(len(transcript), start + window_chars)
        snippet = re.sub(r"\s+", " ", transcript[start:end]).strip()
        key = snippet.lower()
        if snippet and key not in seen:
            windows.append(snippet)
            seen.add(key)

    for phrase in sorted(URGENCY_PHRASES, key=len, reverse=True):
        index = lower.find(phrase)
        if index >= 0:
            add_window(index)
        if len(windows) >= max_windows:
            return windows

    tail = transcript[-window_chars:].strip()
    if tail:
        add_window(max(0, len(transcript) - window_chars))

    return windows[:max_windows]
