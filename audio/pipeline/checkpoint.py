"""Resume-friendly checkpoint storage for large batch runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from pipeline.transcriber import TranscriptionResult


BATCH_DIR = Path("outputs/.batch")
TRANSCRIPT_CACHE = BATCH_DIR / "transcripts.jsonl"
RESULTS_CACHE = BATCH_DIR / "results.jsonl"


def _ensure_batch_dir() -> None:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)


def load_completed_files() -> set[str]:
    completed: set[str] = set()
    if not RESULTS_CACHE.exists():
        return completed

    for line in RESULTS_CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        file_name = str(payload.get("file_name", "")).strip()
        if file_name:
            completed.add(file_name.lower())
    return completed


def load_cached_transcripts(
    asr_backend: Optional[str] = None,
    asr_model: Optional[str] = None,
    asr_compute_type: Optional[str] = None,
) -> dict[str, dict[str, Any]]:
    cached: dict[str, dict[str, Any]] = {}
    if not TRANSCRIPT_CACHE.exists():
        return cached

    for line in TRANSCRIPT_CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if asr_backend and payload.get("asr_backend") != asr_backend:
            continue
        if asr_model and payload.get("asr_model") != asr_model:
            continue
        if asr_compute_type and payload.get("asr_compute_type") != asr_compute_type:
            continue
        file_name = str(payload.get("file_name", "")).strip().lower()
        if file_name:
            cached[file_name] = payload
    return cached


def append_transcript_cache(
    file_name: str,
    call_id: str,
    transcription: TranscriptionResult,
    metadata: dict[str, Any],
    *,
    asr_backend: str = "",
    asr_model: str = "",
    asr_compute_type: str = "float32",
) -> None:
    _ensure_batch_dir()
    payload = {
        "file_name": file_name,
        "call_id": call_id,
        "transcription": transcription_to_dict(transcription),
        "metadata": metadata,
        "asr_backend": asr_backend,
        "asr_model": asr_model,
        "asr_compute_type": asr_compute_type,
    }
    with TRANSCRIPT_CACHE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_result_record(record: dict[str, Any], file_name: str) -> None:
    _ensure_batch_dir()
    payload = {"file_name": file_name, "record": record}
    with RESULTS_CACHE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_result_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not RESULTS_CACHE.exists():
        return records

    for line in RESULTS_CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        record = payload.get("record")
        if isinstance(record, dict):
            records.append(record)
    return records


def transcription_to_dict(transcription: TranscriptionResult) -> dict[str, Any]:
    return asdict(transcription)


def transcription_from_dict(payload: dict[str, Any]) -> TranscriptionResult:
    return TranscriptionResult(**payload)


def clear_checkpoint() -> None:
    for path in (TRANSCRIPT_CACHE, RESULTS_CACHE):
        if path.exists():
            path.unlink()
