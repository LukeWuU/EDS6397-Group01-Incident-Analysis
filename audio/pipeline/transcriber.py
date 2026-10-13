"""Speech-to-text transcription using HuggingFace Whisper, faster-whisper, or Wav2Vec2."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np

from pipeline.transcript_cleanup import clean_asr_transcript


SAMPLE_RATE = 16_000

WHISPER_SPEED_TIERS: tuple[str, ...] = (
    "Fast",
    "Moderate",
    "Slow",
    "Large v3 Turbo",
    "Distil Large v3",
)

WHISPER_MODEL_CATALOG: dict[str, dict[str, str]] = {
    "Fast": {"hf": "openai/whisper-tiny", "fw": "tiny"},
    "Moderate": {"hf": "openai/whisper-small", "fw": "small"},
    "Slow": {"hf": "openai/whisper-medium", "fw": "medium"},
    "Large v3 Turbo": {"hf": "openai/whisper-large-v3-turbo", "fw": "large-v3-turbo"},
    "Distil Large v3": {"hf": "distil-whisper/distil-large-v3", "fw": "distil-large-v3"},
}

# Backward-compatible HuggingFace map used by older configs/tests.
WHISPER_MODEL_OPTIONS = {tier: WHISPER_MODEL_CATALOG[tier]["hf"] for tier in ("Fast", "Moderate", "Slow")}

WAV2VEC2_MODEL_OPTIONS = {
    "Fast": "facebook/wav2vec2-large-960h",
    "Moderate": "facebook/wav2vec2-large-960h-lv60-self",
    "Slow": "facebook/wav2vec2-large-960h-lv60-self",
}

WAV2VEC2_CHUNK_SECONDS = {
    "Fast": 10,
    "Moderate": 8,
    "Slow": 6,
}

# Wav2Vec2 CTC models are unstable in FP16; cap manual chunks to avoid OOM on long calls.
WAV2VEC2_MAX_CHUNK_SECONDS = 8


@dataclass
class TranscriptionResult:
    """Result returned for each audio file."""

    call_id: str
    file_name: str
    transcript: str
    formatted_transcript: str
    confidence_score: float
    transcript_quality_score: float
    duration_seconds: float
    source_modified_time: str
    error: Optional[str] = None


def resolve_whisper_model(speed_tier: str, backend: str) -> str:
    tier = speed_tier if speed_tier in WHISPER_MODEL_CATALOG else "Fast"
    key = "fw" if backend == "faster-whisper" else "hf"
    return WHISPER_MODEL_CATALOG[tier][key]


def create_transcriber(
    backend: str,
    speed_tier: str,
    device: str,
    model_name: str | None = None,
    *,
    compute_type: str = "float32",
) -> "AudioTranscriber":
    if backend in {"whisper", "faster-whisper"}:
        resolved_model = model_name or resolve_whisper_model(speed_tier, backend)
    else:
        options = WAV2VEC2_MODEL_OPTIONS
        resolved_model = model_name or options.get(speed_tier, options["Fast"])
    return AudioTranscriber(
        model_name=resolved_model,
        device=device,
        backend=backend,
        speed_tier=speed_tier,
        compute_type=compute_type,
    )


class AudioTranscriber:
    """Whisper, faster-whisper, or Wav2Vec2 transcriber with shared post-processing."""

    def __init__(
        self,
        model_name: str = "openai/whisper-medium",
        device: str = "cpu",
        backend: str = "whisper",
        speed_tier: str = "Fast",
        compute_type: str = "float32",
    ) -> None:
        import torch
        from transformers.utils import logging as transformers_logging

        self.model_name = model_name
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        self.backend = backend
        self.speed_tier = speed_tier
        self.compute_type = self._resolve_compute_type(compute_type, torch)
        self.faster_whisper_model = None
        transformers_logging.set_verbosity_error()

        if backend == "wav2vec2":
            self._init_wav2vec2(torch)
        elif backend == "faster-whisper":
            self._init_faster_whisper()
        else:
            self._init_whisper(torch)

    @staticmethod
    def _resolve_compute_type(compute_type: str, torch) -> str:
        normalized = (compute_type or "float32").lower()
        if normalized not in {"float32", "float16", "int8"}:
            return "float32"
        if normalized == "float16" and not torch.cuda.is_available():
            return "float32"
        return normalized

    def _init_whisper(self, torch) -> None:
        from transformers import pipeline

        pipeline_device = 0 if self.device == "cuda" else -1
        model_kwargs: dict = {}
        if self.device == "cuda" and self.compute_type == "float16":
            model_kwargs["torch_dtype"] = torch.float16
        self.asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=self.model_name,
            device=pipeline_device,
            model_kwargs=model_kwargs,
        )

    def _init_faster_whisper(self) -> None:
        from faster_whisper import WhisperModel

        device = "cuda" if self.device == "cuda" else "cpu"
        compute_type = self.compute_type
        if device == "cpu" and compute_type == "float16":
            compute_type = "int8"

        self.faster_whisper_model = WhisperModel(
            self.model_name,
            device=device,
            compute_type=compute_type,
        )

    def _init_wav2vec2(self, torch) -> None:
        from transformers import pipeline

        pipeline_device = 0 if self.device == "cuda" else -1
        self.wav2vec_chunk_s = min(
            WAV2VEC2_CHUNK_SECONDS.get(self.speed_tier, 10),
            WAV2VEC2_MAX_CHUNK_SECONDS,
        )
        # FP32 only — half precision causes dtype/LayerNorm errors on many GPUs.
        try:
            self.asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=pipeline_device,
                torch_dtype=torch.float32,
            )
        except TypeError:
            self.asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=pipeline_device,
            )

    def transcribe_file(
        self,
        audio_path: Union[str, Path],
        call_id: str,
    ) -> TranscriptionResult:
        """Transcribe an audio file and return a normalized result object."""
        path = Path(audio_path)
        try:
            audio, duration = self._load_audio(path)
            light_preprocess = self.backend == "wav2vec2" and self.speed_tier == "Fast"
            audio = self._preprocess_audio(audio, light=light_preprocess)

            if self.backend == "wav2vec2":
                utterances = self._transcribe_with_wav2vec2(audio)
            elif self.backend == "faster-whisper":
                utterances = self._transcribe_with_faster_whisper(audio)
            else:
                utterances = self._transcribe_with_whisper(audio)

            transcript = " ".join(utterance["text"] for utterance in utterances).strip()
            transcript = clean_asr_transcript(transcript, backend=self.backend)
            if transcript:
                utterances = self._utterances_from_cleaned_transcript(transcript, utterances)
            formatted_transcript = transcript
            audio_quality = self._audio_quality_score(audio)
            transcript_quality = self._transcript_quality_score(transcript)
            return TranscriptionResult(
                call_id=call_id,
                file_name=path.name,
                transcript=transcript or "",
                formatted_transcript=formatted_transcript or transcript,
                confidence_score=round((audio_quality + transcript_quality) / 2, 2),
                transcript_quality_score=transcript_quality,
                duration_seconds=round(duration, 2),
                source_modified_time=self._file_modified_time(path),
            )
        except Exception as exc:  # noqa: BLE001 - failures should not stop batch processing
            return TranscriptionResult(
                call_id=call_id,
                file_name=path.name,
                transcript="ERROR",
                formatted_transcript="ERROR",
                confidence_score=0.0,
                transcript_quality_score=0.0,
                duration_seconds=0.0,
                source_modified_time=self._file_modified_time(path),
                error=str(exc),
            )

    def _utterances_from_cleaned_transcript(
        self,
        transcript: str,
        utterances: list[dict],
    ) -> list[dict]:
        if not utterances:
            return [{"start": 0.0, "text": transcript, "confidence": 0.8}]

        cleaned_parts = [part.strip() for part in transcript.split(" ... ") if part.strip()]
        if len(cleaned_parts) == 1 and len(utterances) == 1:
            return [{**utterances[0], "text": cleaned_parts[0]}]

        if len(cleaned_parts) > 1:
            rebuilt = []
            for index, part in enumerate(cleaned_parts):
                start = utterances[min(index, len(utterances) - 1)]["start"]
                rebuilt.append({"start": start, "text": part, "confidence": 0.8})
            return self._postprocess_utterances(rebuilt)

        return [{**utterances[0], "text": transcript}]

    def _transcribe_with_wav2vec2(self, audio: np.ndarray) -> list[dict]:
        try:
            utterances = self._transcribe_wav2vec2_pipeline(audio)
            if utterances:
                return utterances
        except Exception:
            pass

        return self._transcribe_wav2vec2_manual(audio)

    def _transcribe_wav2vec2_pipeline(self, audio: np.ndarray) -> list[dict]:
        chunk_kwargs = {
            "chunk_length_s": self.wav2vec_chunk_s,
            "stride_length_s": 2,
        }
        audio_input = {"array": audio, "sampling_rate": SAMPLE_RATE}

        try:
            result = self.asr_pipeline(audio_input, return_timestamps=True, **chunk_kwargs)
        except (TypeError, ValueError):
            try:
                result = self.asr_pipeline(audio_input, return_timestamps=True)
            except (TypeError, ValueError):
                try:
                    result = self.asr_pipeline(audio_input, **chunk_kwargs)
                except (TypeError, ValueError):
                    result = self.asr_pipeline(audio_input)

        if not isinstance(result, dict):
            text = self._clean_chunk_text(str(result))
            return [{"start": 0.0, "text": text, "confidence": 0.8}] if text else []

        chunks = result.get("chunks") or []
        utterances: list[dict] = []
        for chunk in chunks:
            text = self._clean_chunk_text(str(chunk.get("text", "")))
            if not text:
                continue
            timestamp = chunk.get("timestamp") or (0.0, 0.0)
            start = float(timestamp[0] or 0.0)
            utterances.append({"start": start, "text": text, "confidence": 0.8})

        if utterances:
            return self._postprocess_utterances(utterances)

        text = self._clean_chunk_text(str(result.get("text", "")))
        return [{"start": 0.0, "text": text, "confidence": 0.8}] if text else []

    def _transcribe_wav2vec2_manual(self, audio: np.ndarray) -> list[dict]:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        processor = Wav2Vec2Processor.from_pretrained(self.model_name)
        model = Wav2Vec2ForCTC.from_pretrained(self.model_name, torch_dtype=torch.float32)
        model.to(self.device)
        model.eval()

        chunk_samples = int(WAV2VEC2_MAX_CHUNK_SECONDS * SAMPLE_RATE)
        utterances: list[dict] = []

        for start in range(0, audio.size, chunk_samples):
            chunk = audio[start : start + chunk_samples]
            if chunk.size < SAMPLE_RATE // 5:
                continue

            inputs = processor(
                chunk,
                sampling_rate=SAMPLE_RATE,
                return_tensors="pt",
                padding=True,
            )
            input_values = inputs.input_values.to(device=self.device, dtype=torch.float32)
            attention_mask = inputs.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(device=self.device, dtype=torch.long)

            with torch.inference_mode():
                logits = model(input_values, attention_mask=attention_mask).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            text = processor.decode(predicted_ids[0], skip_special_tokens=True)
            text = self._clean_chunk_text(text)
            if text:
                utterances.append(
                    {
                        "start": float(start / SAMPLE_RATE),
                        "text": text,
                        "confidence": 0.8,
                    }
                )

        utterances = self._postprocess_utterances(utterances)
        if utterances:
            return utterances

        raise RuntimeError("Wav2Vec2 returned no transcript text.")

    def _transcribe_with_faster_whisper(self, audio: np.ndarray) -> list[dict]:
        if self.faster_whisper_model is None:
            raise RuntimeError("faster-whisper model is not initialized.")

        segments, _info = self.faster_whisper_model.transcribe(
            audio,
            language="en",
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            word_timestamps=False,
        )

        utterances: list[dict] = []
        for segment in segments:
            text = self._clean_chunk_text(segment.text)
            if not text:
                continue
            utterances.append(
                {
                    "start": float(segment.start or 0.0),
                    "text": text,
                    "confidence": 0.85,
                }
            )

        return self._postprocess_utterances(utterances)

    def _transcribe_with_whisper(self, audio: np.ndarray) -> list[dict]:
        result = self._run_whisper(audio)
        chunks = result.get("chunks") or []
        utterances = self._postprocess_utterances(self._utterances_from_whisper_chunks(chunks))
        if utterances:
            return utterances

        text = self._clean_chunk_text(str(result.get("text", "")))
        return [{"start": 0.0, "text": text, "confidence": 0.8}] if text else []

    def _run_whisper(self, audio: np.ndarray) -> dict:
        kwargs = {
            "chunk_length_s": 30,
            "stride_length_s": (5, 5),
            "generate_kwargs": {"language": "english", "task": "transcribe"},
        }
        try:
            return self.asr_pipeline(
                {"array": audio, "sampling_rate": SAMPLE_RATE},
                return_timestamps="word",
                **kwargs,
            )
        except (TypeError, ValueError):
            return self.asr_pipeline(
                {"array": audio, "sampling_rate": SAMPLE_RATE},
                return_timestamps=True,
                **kwargs,
            )

    def _load_audio(self, path: Path) -> tuple[np.ndarray, float]:
        import librosa

        audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
        audio = np.asarray(audio, dtype=np.float32)
        if audio.size == 0:
            raise ValueError("Audio file contains no samples.")
        duration = float(audio.size / SAMPLE_RATE)
        return audio, duration

    def _utterances_from_whisper_chunks(self, chunks: list[dict]) -> list[dict]:
        utterances: list[dict] = []
        current_words: list[str] = []
        current_start = 0.0
        previous_end = 0.0

        for chunk in chunks:
            text = self._clean_chunk_text(str(chunk.get("text", "")))
            if not text:
                continue

            timestamp = chunk.get("timestamp") or (previous_end, previous_end)
            start = float(timestamp[0] or previous_end or 0.0)
            end = float(timestamp[1] or start)
            if end < start:
                end = start

            starts_new_turn = bool(current_words) and (
                start - previous_end > 0.85
                or len(current_words) >= 14
                or current_words[-1].endswith((".", "?", "!"))
                or (start > previous_end and self._looks_like_short_response(text))
            )
            if starts_new_turn:
                utterances.append({"start": current_start, "text": " ".join(current_words).strip(), "confidence": 0.85})
                current_words = []

            if not current_words:
                current_start = start

            current_words.append(text)
            previous_end = end

        if current_words:
            utterances.append({"start": current_start, "text": " ".join(current_words).strip(), "confidence": 0.85})
        return utterances

    def _postprocess_utterances(self, utterances: list[dict]) -> list[dict]:
        deduped = self._dedupe_timestamped_utterances(utterances)
        collapsed = self._collapse_adjacent_same_speaker_text(deduped)
        return self._remove_filler_loops(collapsed)

    @staticmethod
    def _dedupe_timestamped_utterances(utterances: list[dict]) -> list[dict]:
        output: list[dict] = []
        seen: set[tuple[int, str]] = set()
        for utterance in utterances:
            text = AudioTranscriber._normalize_for_dedupe(utterance["text"])
            timestamp_bucket = int(round(float(utterance["start"])))
            key = (timestamp_bucket, text)
            if key in seen:
                continue
            seen.add(key)
            output.append(utterance)
        return output

    @staticmethod
    def _collapse_adjacent_same_speaker_text(utterances: list[dict]) -> list[dict]:
        output: list[dict] = []
        previous_text = ""
        previous_start = -999.0
        for utterance in utterances:
            text = AudioTranscriber._normalize_for_dedupe(utterance["text"])
            start = float(utterance["start"])
            if text == previous_text and start - previous_start < 3.0:
                continue
            output.append(utterance)
            previous_text = text
            previous_start = start
        return output

    @staticmethod
    def _remove_filler_loops(utterances: list[dict]) -> list[dict]:
        output: list[dict] = []
        filler_counts: dict[str, int] = {}
        for utterance in utterances:
            normalized = AudioTranscriber._normalize_for_dedupe(utterance["text"])
            if AudioTranscriber._is_filler_only(normalized):
                filler_counts[normalized] = filler_counts.get(normalized, 0) + 1
                if filler_counts[normalized] > 2:
                    continue
            output.append(utterance)
        return output

    @staticmethod
    def _clean_chunk_text(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _normalize_for_dedupe(text: str) -> str:
        return re.sub(r"[^a-z0-9']+", " ", text.lower()).strip()

    @staticmethod
    def _is_filler_only(normalized_text: str) -> bool:
        fillers = {
            "okay",
            "ok",
            "yes",
            "yeah",
            "no",
            "right",
            "alright",
            "all right",
            "uh huh",
            "mm hmm",
        }
        return normalized_text in fillers

    @staticmethod
    def _looks_like_short_response(text: str) -> bool:
        words = text.split()
        return 0 < len(words) <= 3 and text.endswith((".", "?", "!"))

    @staticmethod
    def _file_modified_time(path: Path) -> str:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            return "Unknown"

    def _preprocess_audio(self, audio: np.ndarray, *, light: bool = False) -> np.ndarray:
        audio = self._remove_dc_offset(audio)
        if light:
            return self._peak_normalize(audio)

        import librosa
        import scipy.signal

        profile = self._audio_profile(audio)
        if profile["needs_filter"]:
            audio = self._voice_band_filter(audio, scipy.signal)
        if profile["needs_denoise"]:
            audio = self._reduce_stationary_noise(audio, librosa)
        if profile["needs_silence_compaction"]:
            audio = self._trim_and_compact_speech(audio, librosa)
        if profile["needs_preemphasis"]:
            audio = librosa.effects.preemphasis(audio)

        audio = self._compress_dynamic_range(audio)
        audio = self._peak_normalize(audio)
        return np.asarray(audio, dtype=np.float32)

    @staticmethod
    def _audio_profile(audio: np.ndarray) -> dict[str, bool]:
        if audio.size == 0:
            return {
                "needs_filter": False,
                "needs_denoise": False,
                "needs_silence_compaction": False,
                "needs_preemphasis": False,
            }

        abs_audio = np.abs(audio)
        peak = float(np.max(abs_audio))
        rms = float(np.sqrt(np.mean(np.square(audio))))
        noise_floor = float(np.percentile(abs_audio, 20))
        snr_proxy = rms / max(noise_floor, 1e-5)
        silence_ratio = float(np.mean(abs_audio < max(noise_floor * 1.5, 0.01)))

        return {
            "needs_filter": True,
            "needs_denoise": snr_proxy < 6.0 or noise_floor > 0.015,
            "needs_silence_compaction": silence_ratio > 0.35,
            "needs_preemphasis": peak < 0.35 or snr_proxy < 8.0,
        }

    @staticmethod
    def _remove_dc_offset(audio: np.ndarray) -> np.ndarray:
        if audio.size == 0:
            return audio
        return audio - float(np.mean(audio))

    @staticmethod
    def _voice_band_filter(audio: np.ndarray, scipy_signal) -> np.ndarray:
        if audio.size < SAMPLE_RATE:
            return audio
        sos = scipy_signal.butter(6, [80, 7600], btype="bandpass", fs=SAMPLE_RATE, output="sos")
        return scipy_signal.sosfiltfilt(sos, audio).astype(np.float32)

    @staticmethod
    def _reduce_stationary_noise(audio: np.ndarray, librosa_module) -> np.ndarray:
        if audio.size < SAMPLE_RATE:
            return audio

        frame_length = 2048
        hop_length = 512
        spectrum = librosa_module.stft(audio, n_fft=frame_length, hop_length=hop_length)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        noise_floor = np.percentile(magnitude, 15, axis=1, keepdims=True)
        cleaned_magnitude = np.maximum(magnitude - noise_floor * 1.4, magnitude * 0.12)
        cleaned = librosa_module.istft(
            cleaned_magnitude * np.exp(1j * phase),
            hop_length=hop_length,
            length=len(audio),
        )
        return np.asarray(cleaned, dtype=np.float32)

    @staticmethod
    def _trim_and_compact_speech(audio: np.ndarray, librosa_module) -> np.ndarray:
        intervals = librosa_module.effects.split(audio, top_db=28)
        if len(intervals) == 0:
            return audio

        padding = int(0.15 * SAMPLE_RATE)
        chunks = []
        for start, end in intervals:
            padded_start = max(0, start - padding)
            padded_end = min(len(audio), end + padding)
            chunk = audio[padded_start:padded_end]
            if chunk.size:
                chunks.append(chunk)
        return np.concatenate(chunks).astype(np.float32) if chunks else audio

    @staticmethod
    def _compress_dynamic_range(audio: np.ndarray) -> np.ndarray:
        if audio.size == 0:
            return audio
        return np.tanh(audio * 1.6).astype(np.float32)

    @staticmethod
    def _peak_normalize(audio: np.ndarray) -> np.ndarray:
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak <= 0:
            return audio
        return (audio / peak * 0.95).astype(np.float32)

    @staticmethod
    def _audio_quality_score(audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        rms = float(np.sqrt(np.mean(np.square(audio))))
        peak = float(np.max(np.abs(audio)))
        clipping_penalty = 0.15 if peak >= 0.99 else 0.0
        score = min(1.0, max(0.0, 0.65 + rms - clipping_penalty))
        return round(score, 2)

    @staticmethod
    def _transcript_quality_score(transcript: str) -> float:
        words = re.findall(r"[A-Za-z']+", transcript)
        if len(words) < 5:
            return 0.1

        short_word_ratio = sum(1 for word in words if len(word) <= 2) / len(words)
        long_word_ratio = sum(1 for word in words if len(word) >= 18) / len(words)
        uppercase_ratio = sum(1 for char in transcript if char.isupper()) / max(
            1, sum(1 for char in transcript if char.isalpha())
        )
        emergency_terms = {
            "911",
            "help",
            "emergency",
            "gun",
            "shot",
            "fire",
            "bleeding",
            "ambulance",
            "police",
            "stabbing",
            "accident",
            "crash",
        }
        emergency_bonus = 0.1 if any(term in transcript.lower() for term in emergency_terms) else 0.0
        score = 1.0 - (short_word_ratio * 0.55) - (long_word_ratio * 0.4) - max(0.0, uppercase_ratio - 0.75)
        return round(min(1.0, max(0.0, score + emergency_bonus)), 2)
