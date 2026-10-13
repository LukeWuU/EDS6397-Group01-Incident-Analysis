"""LLM-based event classification and transcript summarization via HuggingFace."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from pipeline.event_rules import (
    ALLOWED_EVENT_TYPES,
    CLASSIFICATION_GUIDANCE,
    build_llm_classification_context,
    enrich_location_mention,
    event_keywords,
    metadata_location_hint,
    reconcile_event_type,
)
from pipeline.transcript_cleanup import TranscriptUsability, assess_transcript_usability, clean_asr_transcript

# Apache 2.0, no HuggingFace token required. ~3 GB RAM / ~1.5 GB VRAM in FP16.
LLM_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_TRANSCRIPT_CHARS = 4500
MAX_PROMPT_TOKENS = 2048
MAX_NEW_TOKENS = 384

ALLOWED_EVENT_TYPES_TEXT = ", ".join(f'"{item}"' for item in ALLOWED_EVENT_TYPES)

SYSTEM_PROMPT = f"""You are an expert 911 emergency call analyst.
You receive a speech-to-text transcript (possibly noisy), optional reference metadata, and rule-based classification hints.

Analyze the conversation and respond with ONLY a single JSON object (no markdown, no extra text) using exactly these keys:
- "event_type": MUST be exactly one of: {ALLOWED_EVENT_TYPES_TEXT}
- "summary": 2-4 sentences describing the exchange between dispatcher and caller; do NOT mention transcript quality or ASR errors
- "location_and_person_mention": comma-separated locations and real person names from the transcript; include metadata state only if spoken location is missing; otherwise "Unknown"
- "keywords": 3-8 comma-separated emergency keywords that match the chosen event_type (no contradictory labels)

{CLASSIFICATION_GUIDANCE}

Output consistency rules:
- event_type, summary, and keywords must describe the SAME incident.
- Do not use "Traffic violation" as event_type.
- Do not include filler words (Okay, Just, Sir) as person names.
- Do not include sentence fragments as locations.
- If unclear, use "Unknown" for location/person fields and "Public safety incident" for event_type only when no specific type fits.
- The summary MUST match the Transcript section. Never copy metadata description into the summary unless the same facts appear in the transcript."""

RETRY_SYSTEM_PROMPT = f"""Return ONLY one valid JSON object with keys:
"event_type", "summary", "location_and_person_mention", "keywords".
event_type must be one of: {ALLOWED_EVENT_TYPES_TEXT}.
No markdown, no explanation, no text before or after the JSON."""


@dataclass
class LLMExtractionResult:
    event_type: str
    summary: str
    location_and_person_mention: str
    keywords: str
    confidence: float
    error: Optional[str] = None

    def transcript_summary_block(self) -> str:
        return (
            f"Summary: {self.summary}\n"
            f"Location and Person Name Mention: {self.location_and_person_mention}\n"
            f"Keywords: {self.keywords}"
        )

    @classmethod
    def failure(cls, message: str) -> "LLMExtractionResult":
        return cls(
            event_type="Unknown",
            summary="LLM analysis unavailable.",
            location_and_person_mention="Unknown",
            keywords="Unknown",
            confidence=0.0,
            error=message,
        )


class TranscriptLLMAnalyzer:
    """Summarize Whisper transcripts and classify events with Qwen2.5-1.5B-Instruct."""

    def __init__(self, model_name: str = LLM_MODEL, device: str = "cpu") -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
        )
        self.model.to(self.device)
        self.model.eval()

    def analyze_transcript(
        self,
        formatted_transcript: str,
        plain_transcript: str,
        metadata: Optional[dict[str, Any]] = None,
        *,
        transcript_quality: float = 1.0,
        asr_backend: str = "whisper",
    ) -> LLMExtractionResult:
        source = (plain_transcript or formatted_transcript or "").strip()
        if not source or source == "ERROR":
            return LLMExtractionResult.failure("Empty or failed transcript.")

        source = clean_asr_transcript(source[:MAX_TRANSCRIPT_CHARS], backend=asr_backend)
        usability = assess_transcript_usability(source, transcript_quality, backend=asr_backend)
        prompt_metadata = metadata if usability.use_metadata else _state_only_metadata(metadata)
        context = build_llm_classification_context(source, prompt_metadata)

        user_prompt = self._build_user_prompt(source, metadata, context, usability)

        decoded = self._generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        result = self._parse_response(decoded, source, metadata, context, usability)
        if result.error is None:
            return result

        retry_prompt = (
            f"{user_prompt}\n\n"
            "Your previous answer was invalid. Return ONLY valid JSON with the four required keys."
        )
        decoded_retry = self._generate_json(
            system_prompt=RETRY_SYSTEM_PROMPT,
            user_prompt=retry_prompt,
        )
        retry_result = self._parse_response(decoded_retry, source, metadata, context, usability)
        if retry_result.error is None:
            return retry_result

        return self._complete_from_partial_or_rules(
            decoded=decoded_retry or decoded,
            transcript=source,
            metadata=metadata,
            context=context,
            usability=usability,
        )

    def _generate_json(self, system_prompt: str, user_prompt: str) -> str:
        import torch

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_PROMPT_TOKENS,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated = output_ids[0, inputs["input_ids"].shape[-1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()

    def _build_user_prompt(
        self,
        transcript: str,
        metadata: Optional[dict[str, Any]],
        context: dict[str, object],
        usability: TranscriptUsability,
    ) -> str:
        sections = ["Transcript:", transcript]

        if usability.note:
            sections.extend(["", "Transcript quality note:", usability.note])

        prompt_metadata = metadata if usability.use_metadata else _state_only_metadata(metadata)
        meta_block = self._format_metadata_block(prompt_metadata, include_description=usability.use_metadata)
        if meta_block:
            sections.extend(
                [
                    "",
                    "Reference metadata (event_type hint only; do not copy into summary unless transcript confirms):",
                    meta_block,
                ]
            )

        hint_lines = context.get("hint_lines") or []
        if hint_lines:
            sections.extend(["", "Rule-based hints:", *hint_lines])

        suggested_type = context.get("suggested_type")
        suggested_score = context.get("suggested_score", 0)
        if suggested_type and suggested_type != "Unknown" and suggested_score:
            sections.append(
                f"Suggested event_type if transcript agrees: {suggested_type} (confidence {suggested_score})"
            )

        return "\n".join(sections)

    @staticmethod
    def _format_metadata_block(
        metadata: Optional[dict[str, Any]],
        *,
        include_description: bool = True,
    ) -> str:
        if not metadata:
            return ""

        lines = []
        field_specs = [
            ("title", "Incident title"),
            ("state", "State"),
            ("date", "Date"),
        ]
        if include_description:
            field_specs.insert(1, ("description", "Description"))

        for field, label in field_specs:
            value = metadata.get(field)
            if value is None or (isinstance(value, float) and str(value) == "nan"):
                continue
            text = str(value).strip()
            if not text:
                continue
            if field == "description":
                text = text[:400]
            lines.append(f"- {label}: {text}")
        return "\n".join(lines)

    def _parse_response(
        self,
        text: str,
        transcript: str,
        metadata: Optional[dict[str, Any]],
        context: dict[str, object],
        usability: TranscriptUsability,
    ) -> LLMExtractionResult:
        payload = self._extract_json(text)
        if not payload:
            return LLMExtractionResult.failure("Could not parse LLM JSON.")

        summary = str(payload.get("summary", "")).strip()
        if not summary or summary.lower() == "unknown":
            return LLMExtractionResult.failure("LLM JSON missing summary.")

        raw_event_type = str(payload.get("event_type", "Unknown")).strip() or "Unknown"
        reconcile_metadata = metadata if usability.use_metadata else _state_only_metadata(metadata)
        event_type, confidence = reconcile_event_type(raw_event_type, transcript, reconcile_metadata)
        confidence = min(confidence, max(0.45, usability.score))

        if not usability.use_metadata and _summary_copied_from_metadata(summary, transcript, metadata):
            summary = self._summary_from_transcript(transcript, event_type, usability)
            confidence = min(confidence, usability.score)

        location = str(
            payload.get("location_and_person_mention")
            or payload.get("location_and_person_name_mention")
            or payload.get("location_mention")
            or "Unknown"
        ).strip() or "Unknown"
        location = enrich_location_mention(location, reconcile_metadata)

        keywords = self._normalize_keywords(
            str(payload.get("keywords", "Unknown")).strip() or "Unknown",
            event_type,
            context,
        )

        return LLMExtractionResult(
            event_type=event_type,
            summary=summary,
            location_and_person_mention=location,
            keywords=keywords,
            confidence=confidence,
        )

    def _complete_from_partial_or_rules(
        self,
        decoded: str,
        transcript: str,
        metadata: Optional[dict[str, Any]],
        context: dict[str, object],
        usability: TranscriptUsability,
    ) -> LLMExtractionResult:
        partial = self._extract_json_loose(decoded)
        suggested = str(partial.get("event_type") or context.get("suggested_type") or "Unknown")
        reconcile_metadata = metadata if usability.use_metadata else _state_only_metadata(metadata)
        event_type, confidence = reconcile_event_type(suggested, transcript, reconcile_metadata)
        confidence = min(confidence, max(0.45, usability.score))

        summary = str(partial.get("summary", "")).strip()
        if not summary:
            summary = self._summary_from_transcript(transcript, event_type, usability)

        location = str(partial.get("location_and_person_mention", "")).strip()
        location = enrich_location_mention(
            location or metadata_location_hint(reconcile_metadata),
            reconcile_metadata,
        )

        keywords = self._normalize_keywords(
            str(partial.get("keywords", "")).strip() or "Unknown",
            event_type,
            context,
        )

        return LLMExtractionResult(
            event_type=event_type,
            summary=summary,
            location_and_person_mention=location,
            keywords=keywords,
            confidence=max(confidence - 0.05, 0.55),
        )

    @staticmethod
    def _summary_from_transcript(
        transcript: str,
        event_type: str,
        usability: TranscriptUsability,
    ) -> str:
        plain = re.sub(r"\bSPK_\d\b", "", transcript, flags=re.IGNORECASE)
        plain = re.sub(r"\b\d+:\d{2}\b", "", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        excerpt = plain[:420].strip()
        if not excerpt:
            return "The transcript did not contain enough clear speech to summarize."

        if any(phrase in excerpt.lower() for phrase in ("continue to hold", "you have reached", "handling another emergency call")):
            return (
                "The recording is dominated by a repeated hold or automated emergency message. "
                f"Later speech in the transcript includes: {excerpt[-220:].strip()}"
            )

        if usability.score < 0.35:
            return f"The call transcript is partially unclear, but includes: {excerpt}"

        return f"The dispatcher and caller discuss a {event_type.lower()} incident. {excerpt[:320]}"

    @staticmethod
    def _normalize_keywords(keywords: str, event_type: str, context: dict[str, object]) -> str:
        parts = [part.strip() for part in keywords.split(",") if part.strip()]
        cleaned: list[str] = []
        banned = {"traffic violation", "transcript quality", "asr error", "unknown"}

        for part in parts:
            lower = part.lower()
            if lower in banned:
                continue
            if event_type == "Vehicle chase" and lower in {"traffic violation", "officers"}:
                continue
            cleaned.append(part)

        if not cleaned:
            rule_terms = context.get("rule_terms") or []
            cleaned = list(rule_terms[:5])

        if not cleaned:
            cleaned = list(event_keywords(event_type)[:5])

        if not cleaned:
            return "Unknown"

        return ", ".join(dict.fromkeys(cleaned))

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        for candidate in TranscriptLLMAnalyzer._json_candidates(text):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return {}

    @staticmethod
    def _json_candidates(text: str) -> list[str]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        candidates = [TranscriptLLMAnalyzer._repair_json(cleaned)]
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            candidates.append(TranscriptLLMAnalyzer._repair_json(match.group(0)))
        return candidates

    @staticmethod
    def _repair_json(text: str) -> str:
        text = text.strip()
        text = text.replace(""", '"').replace(""", '"').replace("'", "'")
        text = re.sub(r",\s*([}\]])", r"\1", text)
        text = re.sub(r"'([^']*)'\s*:", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        return text

    @staticmethod
    def _extract_json_loose(text: str) -> dict[str, str]:
        fields = ("event_type", "summary", "location_and_person_mention", "keywords")
        payload: dict[str, str] = {}
        for field in fields:
            match = re.search(
                rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"\\])*)"',
                text,
                flags=re.DOTALL,
            )
            if match:
                value = match.group(1).replace('\\"', '"').replace("\\n", " ")
                payload[field] = value
        return payload


_SUMMARY_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "was", "were",
    "are", "not", "but", "you", "your", "they", "their", "about", "into", "call", "incident",
}


def _summary_copied_from_metadata(
    summary: str,
    transcript: str,
    metadata: Optional[dict[str, Any]],
) -> bool:
    if not metadata:
        return False

    plain_transcript = re.sub(r"\s+", " ", transcript.lower())
    summary_lower = summary.lower()

    for field in ("title", "description"):
        value = str(metadata.get(field, "") or "").strip()
        if not value:
            continue

        keywords = [
            word
            for word in re.findall(r"[a-z]{4,}", value.lower())
            if word not in _SUMMARY_STOPWORDS
        ]
        if len(keywords) < 2:
            continue

        transcript_hits = sum(1 for word in keywords if word in plain_transcript)
        summary_hits = sum(1 for word in keywords if word in summary_lower)
        if summary_hits >= 2 and transcript_hits < max(1, len(keywords) // 3):
            return True

    return False


def _state_only_metadata(metadata: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not metadata:
        return None
    state = metadata.get("state")
    if state is None or (isinstance(state, float) and str(state) == "nan"):
        return {}
    text = str(state).strip()
    return {"state": text} if text else {}
