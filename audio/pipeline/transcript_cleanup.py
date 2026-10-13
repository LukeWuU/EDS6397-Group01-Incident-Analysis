"""Transcript cleanup and quality assessment for ASR output."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


HOLD_PHRASES = (
    "you have reached",
    "please continue to hold",
    "continue to hold",
    "all our representatives",
    "handling another emergency call",
    "currently handling another",
)


@dataclass(frozen=True)
class TranscriptUsability:
    score: float
    use_metadata: bool
    note: str


def repetition_ratio(text: str, n: int = 8) -> float:
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    if len(words) < n * 3:
        return 0.0
    ngrams = [" ".join(words[index : index + n]) for index in range(len(words) - n + 1)]
    if not ngrams:
        return 0.0
    _phrase, count = Counter(ngrams).most_common(1)[0]
    return count / len(ngrams)


def collapse_repetitive_loops(text: str, window_words: int = 12) -> str:
    """Remove repeated hold-message / ASR loop blocks while keeping unique tail content."""
    words = re.findall(r"[A-Za-z0-9']+", text)
    if len(words) < window_words * 3:
        return re.sub(r"\s+", " ", text).strip()

    seen: set[str] = set()
    kept: list[str] = []
    index = 0
    while index < len(words):
        if index + window_words <= len(words):
            chunk = " ".join(words[index : index + window_words]).lower()
            if chunk in seen:
                index += window_words
                continue
            seen.add(chunk)
        kept.append(words[index])
        index += 1

    collapsed = " ".join(kept).strip()
    if not collapsed:
        return re.sub(r"\s+", " ", text).strip()
    return collapsed


def trim_hold_recording_loops(text: str, max_loop_words: int = 90) -> str:
    """Keep one hold-message loop plus any unique caller content after repetitions."""
    lower = text.lower()
    if not any(phrase in lower for phrase in HOLD_PHRASES):
        return collapse_repetitive_loops(text)

    words = re.findall(r"[A-Za-z0-9']+", text)
    if len(words) <= max_loop_words * 2:
        return collapse_repetitive_loops(text)

    head = " ".join(words[:max_loop_words])
    tail = " ".join(words[max_loop_words:])
    tail_clean = collapse_repetitive_loops(tail, window_words=10)

    if tail_clean and repetition_ratio(tail_clean) < 0.2:
        return f"{head} ... {tail_clean}".strip()
    return collapse_repetitive_loops(text)


def clean_asr_transcript(text: str, backend: str = "whisper") -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if backend != "wav2vec2":
        return cleaned
    cleaned = trim_hold_recording_loops(cleaned)
    return collapse_repetitive_loops(cleaned)


def assess_transcript_usability(
    transcript: str,
    quality_score: float,
    backend: str = "whisper",
) -> TranscriptUsability:
    plain = re.sub(r"\bSPK_\d\b", "", transcript, flags=re.IGNORECASE)
    plain = re.sub(r"\b\d+:\d{2}\b", "", plain)
    plain = re.sub(r"\s+", " ", plain).strip()

    word_count = len(re.findall(r"[A-Za-z0-9']+", plain))
    rep = repetition_ratio(plain)
    wav2vec_penalty = 0.12 if backend == "wav2vec2" else 0.0

    score = max(0.0, min(1.0, quality_score - rep * 1.5 - wav2vec_penalty))
    if word_count < 25:
        score = min(score, 0.35)

    if score < 0.2 or rep > 0.22:
        return TranscriptUsability(
            score=score,
            use_metadata=False,
            note=(
                "Transcript quality is very poor (noisy/repetitive ASR). "
                "The summary MUST describe only words present in the transcript. "
                "Do NOT use metadata description or title to invent caller details."
            ),
        )

    if score < 0.45 or rep > 0.12 or backend == "wav2vec2":
        return TranscriptUsability(
            score=score,
            use_metadata=False,
            note=(
                "Transcript may be partially unreliable. "
                "Base the summary on transcript text only; metadata may be used for event_type if supported."
            ),
        )

    return TranscriptUsability(score=score, use_metadata=True, note="")


def is_probably_garbage_transcript(transcript: str, quality_score: float) -> bool:
    usability = assess_transcript_usability(transcript, quality_score, backend="wav2vec2")
    return usability.score < 0.25
