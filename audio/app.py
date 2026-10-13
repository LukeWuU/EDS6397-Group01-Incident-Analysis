"""Streamlit UI for Audio Analyst."""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st
import torch

from pipeline.analyzer import SentimentUrgencyAnalyzer
from pipeline.checkpoint import (
    append_result_record,
    append_transcript_cache,
    clear_checkpoint,
    load_cached_transcripts,
    load_completed_files,
    load_result_records,
    transcription_from_dict,
)
from pipeline.exporter import (
    TRANSCRIBED_SCRIPT_COLUMN,
    build_record,
    export_csv,
    load_metadata,
    records_to_dataframe,
)
from pipeline.extractor import extract_entities
from pipeline.llm_analyzer import LLM_MODEL, LLMExtractionResult, TranscriptLLMAnalyzer
from pipeline.memory_utils import clear_gpu_memory
from pipeline.transcriber import (
    WHISPER_MODEL_CATALOG,
    WHISPER_SPEED_TIERS,
    WAV2VEC2_MODEL_OPTIONS,
    AudioTranscriber,
    create_transcriber,
    resolve_whisper_model,
)


APP_TITLE = "Audio Analyst"
DATASET_DIR = Path("dataset")
PROJECT_ROOT = Path(__file__).resolve().parent
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}
SENTIMENT_MODEL = "j-hartmann/emotion-english-distilroberta-base"
LARGE_BATCH_THRESHOLD = 50
MAX_DETAIL_EXPANDERS = 12
AVG_CALL_MINUTES = 3.0


def _configure_hf_cache() -> None:
    """Use a local writable HF cache unless user overrides it."""
    if not os.environ.get("HF_HOME"):
        os.environ["HF_HOME"] = str(PROJECT_ROOT / "hf_cache")

    hf_home = Path(os.environ["HF_HOME"])
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_home / "transformers"))

    for cache_path in (
        hf_home,
        Path(os.environ["HUGGINGFACE_HUB_CACHE"]),
        Path(os.environ["TRANSFORMERS_CACHE"]),
    ):
        cache_path.mkdir(parents=True, exist_ok=True)


_configure_hf_cache()

# Real-time factor: transcribe_seconds / audio_seconds (lower = faster). Rough GPU/CPU estimates.
ASR_RTF: dict[tuple[str, str, str], float] = {
    ("whisper", "Fast", "cuda"): 0.22,
    ("whisper", "Moderate", "cuda"): 0.38,
    ("whisper", "Slow", "cuda"): 0.68,
    ("whisper", "Large v3 Turbo", "cuda"): 0.55,
    ("whisper", "Distil Large v3", "cuda"): 0.42,
    ("whisper", "Fast", "cpu"): 1.4,
    ("whisper", "Moderate", "cpu"): 2.2,
    ("whisper", "Slow", "cpu"): 4.0,
    ("whisper", "Large v3 Turbo", "cpu"): 6.0,
    ("whisper", "Distil Large v3", "cpu"): 4.5,
    ("faster-whisper", "Fast", "cuda"): 0.10,
    ("faster-whisper", "Moderate", "cuda"): 0.16,
    ("faster-whisper", "Slow", "cuda"): 0.28,
    ("faster-whisper", "Large v3 Turbo", "cuda"): 0.22,
    ("faster-whisper", "Distil Large v3", "cuda"): 0.18,
    ("faster-whisper", "Fast", "cpu"): 0.55,
    ("faster-whisper", "Moderate", "cpu"): 0.85,
    ("faster-whisper", "Slow", "cpu"): 1.4,
    ("faster-whisper", "Large v3 Turbo", "cpu"): 1.2,
    ("faster-whisper", "Distil Large v3", "cpu"): 0.95,
    ("wav2vec2", "Fast", "cuda"): 0.14,
    ("wav2vec2", "Moderate", "cuda"): 0.18,
    ("wav2vec2", "Slow", "cuda"): 0.18,
    ("wav2vec2", "Fast", "cpu"): 0.35,
    ("wav2vec2", "Moderate", "cpu"): 0.45,
    ("wav2vec2", "Slow", "cpu"): 0.45,
}
LLM_SECONDS_PER_FILE = 40.0


@dataclass(frozen=True)
class ASRConfig:
    backend: str
    speed: str
    model_name: str
    device: str
    compute_type: str = "float32"

    @property
    def label(self) -> str:
        if self.backend == "wav2vec2":
            engine = "Wav2Vec2 960h"
        elif self.backend == "faster-whisper":
            engine = "faster-whisper"
        else:
            engine = "HuggingFace Whisper"
        precision = f", {self.compute_type.upper()}" if self.backend != "wav2vec2" else ""
        return f"{engine} ({self.speed}, {self.device.upper()}{precision})"

STAGE_LABELS = {
    "transcribe": "Transcribing audio",
    "analyze": "Analyzing sentiment",
    "llm": "Running LLM analysis",
    "finalize": "Finalizing output",
}

STAGE_WEIGHTS = {
    "transcribe": 0.55,
    "analyze": 0.10,
    "llm": 0.30,
    "finalize": 0.05,
}


class BatchProgressTracker:
    """Time-aware progress across transcription, LLM, and other per-file stages."""

    def __init__(self, total_files: int, progress_bar, status) -> None:
        self.total_files = max(total_files, 1)
        self.progress_bar = progress_bar
        self.status = status
        self.start_time = time.perf_counter()
        self._stage_order = ("transcribe", "analyze", "llm", "finalize")

    def update(self, file_index: int, stage: str, file_name: str, *, stage_complete: bool = False) -> None:
        stage_offset = self._stage_offset(stage)
        stage_weight = STAGE_WEIGHTS.get(stage, 0.0)
        fraction_within_file = stage_offset + (stage_weight if stage_complete else 0.0)
        overall = min((file_index + fraction_within_file) / self.total_files, 1.0)
        self.progress_bar.progress(overall)

        elapsed = time.perf_counter() - self.start_time
        elapsed_text = _format_duration(elapsed)
        if overall > 0.02:
            estimated_total = elapsed / overall
            remaining_text = _format_duration(max(0.0, estimated_total - elapsed))
            time_text = f"{elapsed_text} elapsed · ~{remaining_text} remaining"
        else:
            time_text = f"{elapsed_text} elapsed · estimating total time..."

        stage_label = STAGE_LABELS.get(stage, stage.title())
        self.status.write(
            f"{stage_label}: `{file_name}` "
            f"(file {file_index + 1}/{self.total_files}) · {time_text}"
        )

    def complete(self, message: str) -> None:
        self.progress_bar.progress(1.0)
        elapsed_text = _format_duration(time.perf_counter() - self.start_time)
        self.status.write(f"{message} · {elapsed_text} total processing time")

    def _stage_offset(self, stage: str) -> float:
        offset = 0.0
        for name in self._stage_order:
            if name == stage:
                break
            offset += STAGE_WEIGHTS.get(name, 0.0)
        return offset


def _format_duration(seconds: float) -> str:
    total_seconds = int(round(seconds))
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, secs = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


st.set_page_config(page_title=APP_TITLE, page_icon="AA", layout="wide")


@st.cache_resource(show_spinner=False)
def get_transcriber(
    backend: str,
    speed: str,
    device: str,
    model_name: str,
    compute_type: str,
) -> AudioTranscriber:
    return create_transcriber(
        backend=backend,
        speed_tier=speed,
        device=device,
        model_name=model_name,
        compute_type=compute_type,
    )


@st.cache_resource(show_spinner=False)
def get_analyzer(device: str) -> SentimentUrgencyAnalyzer:
    return SentimentUrgencyAnalyzer(model_name=SENTIMENT_MODEL, device=device)


@st.cache_resource(show_spinner="Loading Qwen2.5-1.5B-Instruct for event detection and summaries...")
def get_llm_analyzer(device: str) -> TranscriptLLMAnalyzer:
    return TranscriptLLMAnalyzer(model_name=LLM_MODEL, device=device)


def main() -> None:
    st.title("Audio Analyst: Emergency Audio Intelligence")
    st.caption("Convert emergency calls and witness statements into structured response intelligence.")

    device = _device_selector()
    asr_config = _asr_selector(device)

    uploaded_files = st.file_uploader(
        "Upload emergency audio files",
        type=["wav", "mp3", "flac", "ogg"],
        accept_multiple_files=True,
    )
    include_dataset = st.checkbox("Also process audio files from dataset/", value=True)
    _sidebar(device, asr_config)

    audio_paths = _dataset_audio_files() if include_dataset else []
    if audio_paths:
        st.info(f"Found {len(audio_paths)} supported file(s) in `{DATASET_DIR}/`.")

    total_files = len(audio_paths) + len(uploaded_files or [])
    large_batch, resume = _batch_options(total_files, asr_config)

    if st.button("Process Files", type="primary"):
        if not uploaded_files and not audio_paths:
            st.warning("Upload audio files or add supported audio files to the dataset folder.")
            return
        _process_files(uploaded_files, audio_paths, device, asr_config, large_batch, resume)

    _about_section()


def _device_selector() -> str:
    cuda_available = torch.cuda.is_available() and torch.cuda.device_count() > 0
    if cuda_available:
        st.success(f"CUDA available: {torch.cuda.get_device_name(0)}")
        selected_device = st.radio("Render audio using", ["GPU (CUDA)", "CPU"], horizontal=True)
        return "cuda" if selected_device == "GPU (CUDA)" else "cpu"

    st.warning("CUDA GPU was not detected by PyTorch. CPU processing will be used.")
    st.caption(
        f"PyTorch: {torch.__version__}; torch.version.cuda: {torch.version.cuda}; "
        f"device_count: {torch.cuda.device_count()}"
    )
    st.button("Render audio using CPU", disabled=True)
    return "cpu"


def _asr_selector(global_device: str) -> ASRConfig:
    cuda_available = torch.cuda.is_available() and torch.cuda.device_count() > 0

    engine_label = st.radio(
        "Speech-to-text engine",
        ["faster-whisper", "HuggingFace Whisper", "Wav2Vec2 960h"],
        horizontal=True,
        help="faster-whisper is usually 2–4× faster than HuggingFace Whisper on GPU.",
    )
    if engine_label == "Wav2Vec2 960h":
        backend = "wav2vec2"
    elif engine_label == "faster-whisper":
        backend = "faster-whisper"
    else:
        backend = "whisper"

    speed = st.selectbox(
        "Whisper model / speed tier" if backend != "wav2vec2" else "Transcription speed",
        list(WHISPER_SPEED_TIERS if backend != "wav2vec2" else ("Fast", "Moderate", "Slow")),
        index=1 if backend != "wav2vec2" else 0,
    )

    if backend == "wav2vec2":
        model_name = WAV2VEC2_MODEL_OPTIONS[speed]
        compute_type = "float32"
        st.caption(
            f"Model: `{model_name}` · Fast/Moderate = large-960h · Slow = large-960h-lv60-self"
        )
        st.warning(
            "Wav2Vec2 is faster but often produces noisy transcripts on 911 phone/hold audio. "
            "Use Whisper for readable Transcribed Script."
        )
        use_cuda = st.toggle(
            "Use CUDA for Wav2Vec2",
            value=cuda_available and global_device == "cuda",
            disabled=not cuda_available,
            help="Toggle GPU vs CPU for Wav2Vec2 only. The LLM still uses the main GPU/CPU setting above.",
        )
        asr_device = "cuda" if use_cuda and cuda_available else "cpu"
    else:
        model_name = resolve_whisper_model(speed, backend)
        catalog_entry = WHISPER_MODEL_CATALOG.get(speed, WHISPER_MODEL_CATALOG["Fast"])
        st.caption(
            f"Model: `{model_name}` · HF=`{catalog_entry['hf']}` · faster-whisper=`{catalog_entry['fw']}`"
        )
        asr_device = global_device
        use_fp16 = st.toggle(
            "Use float16 precision (CUDA)",
            value=cuda_available and global_device == "cuda",
            disabled=not cuda_available,
            help="Half precision speeds up Whisper on GPU and reduces VRAM. Falls back to float32 on CPU.",
        )
        compute_type = "float16" if use_fp16 and cuda_available else "float32"
        if backend == "faster-whisper":
            st.info(
                "**faster-whisper** with **Distil Large v3** or **Large v3 Turbo** is the recommended "
                "fast + accurate setup for large batches on a 6 GB GPU."
            )
        elif speed == "Distil Large v3":
            st.info("Distil Large v3: near large-model accuracy with lower VRAM and faster inference.")
        elif speed == "Large v3 Turbo":
            st.caption("Large v3 Turbo: highest Whisper accuracy tier; use float16 + large batch mode on 6 GB GPUs.")

    return ASRConfig(
        backend=backend,
        speed=speed,
        model_name=model_name,
        device=asr_device,
        compute_type=compute_type,
    )


def _batch_options(total_files: int, asr_config: ASRConfig) -> tuple[bool, bool]:
    st.subheader("Batch options")
    default_large_batch = total_files >= LARGE_BATCH_THRESHOLD
    col1, col2, col3 = st.columns(3)
    with col1:
        large_batch = st.checkbox(
            "Large batch mode",
            value=default_large_batch,
            help="Runs transcription first, frees GPU memory, then runs LLM analysis. Recommended for 50+ files on 6 GB GPUs.",
        )
    with col2:
        resume = st.checkbox(
            "Resume from checkpoint",
            value=True,
            help="Skip files already saved in outputs/.batch/results.jsonl.",
        )
    with col3:
        if st.button("Clear checkpoint"):
            clear_checkpoint()
            st.success("Checkpoint cleared.")

    if total_files >= LARGE_BATCH_THRESHOLD:
        _render_batch_time_estimate(total_files, asr_config, large_batch)

    return large_batch, resume


def _render_batch_time_estimate(total_files: int, asr_config: ASRConfig, large_batch: bool) -> None:
    device_key = asr_config.device if asr_config.device in {"cuda", "cpu"} else "cpu"
    rtf = ASR_RTF.get((asr_config.backend, asr_config.speed, device_key), 0.5)
    audio_seconds = total_files * AVG_CALL_MINUTES * 60
    transcribe_seconds = audio_seconds * rtf
    llm_seconds = total_files * LLM_SECONDS_PER_FILE
    overhead = total_files * 8.0
    total_seconds = transcribe_seconds + llm_seconds + overhead

    st.caption(
        f"Rough estimate for **{total_files} files** (~{AVG_CALL_MINUTES:.0f} min/call avg): "
        f"transcribe ~{_format_duration(transcribe_seconds)}, "
        f"LLM ~{_format_duration(llm_seconds)}, "
        f"**total ~{_format_duration(total_seconds)}** "
        f"({asr_config.label}{', large batch' if large_batch else ''}). "
        "Actual time varies by call length and GPU load."
    )

    if asr_config.backend == "wav2vec2" and total_files >= LARGE_BATCH_THRESHOLD:
        fw_rtf = ASR_RTF.get(("faster-whisper", "Distil Large v3", device_key), 0.18)
        fw_transcribe = audio_seconds * fw_rtf
        fw_total = fw_transcribe + llm_seconds + overhead
        st.warning(
            "Wav2Vec2 is faster but often unreadable on 911 phone/hold audio. "
            f"For reliable transcripts, try **faster-whisper · Distil Large v3 · float16** "
            f"(~{_format_duration(fw_total)} total on {device_key.upper()}) with checkpoint resume."
        )


def _resolve_devices(use_gpu: bool, asr_config: ASRConfig) -> dict[str, str]:
    return {
        "whisper": asr_config.device,
        "llm": "cuda" if use_gpu else "cpu",
        "sentiment": "cpu",
    }


def _sidebar(device: str, asr_config: ASRConfig) -> None:
    with st.sidebar:
        st.header("Model Info")
        st.write(f"Speech-to-text: `{asr_config.label}`")
        st.write(f"ASR model ID: `{asr_config.model_name}`")
        st.write(f"ASR precision: `{asr_config.compute_type}`")
        st.write(f"LLM analysis: `{LLM_MODEL}`")
        st.write(f"Sentiment: `{SENTIMENT_MODEL}` (CPU in GPU mode)")
        st.write(f"Device: `{device}`")
        st.write(f"CUDA available: `{torch.cuda.is_available()}`")
        st.write(f"CUDA build: `{torch.version.cuda}`")
        st.write(f"Dataset path: `{DATASET_DIR.resolve()}`")


def _dataset_audio_files() -> list[Path]:
    if not DATASET_DIR.exists():
        return []
    return sorted(
        path for path in DATASET_DIR.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _process_files(
    uploaded_files,
    dataset_paths: list[Path],
    device: str,
    asr_config: ASRConfig,
    large_batch: bool,
    resume: bool,
) -> None:
    metadata = load_metadata(DATASET_DIR)
    progress = st.progress(0.0)
    status = st.empty()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_paths = _save_uploads(uploaded_files, Path(temp_dir))
        all_paths = [*dataset_paths, *temp_paths]
        if not resume:
            clear_checkpoint()
        devices = _resolve_devices(device == "cuda", asr_config)

        if large_batch:
            records, details = _process_large_batch(
                all_paths,
                metadata,
                asr_config,
                devices,
                progress,
                status,
                resume=resume,
            )
        else:
            records, details = _process_single_pass(
                all_paths,
                metadata,
                asr_config,
                devices,
                progress,
                status,
                resume=resume,
            )

    output_path = export_csv(records)
    dataframe = records_to_dataframe(records)
    status.success(f"Processed {len(records)} file(s). CSV written to `{output_path}`.")
    _render_results(dataframe, details, large_batch=len(all_paths) >= LARGE_BATCH_THRESHOLD)


def _pending_paths(all_paths: list[Path], resume: bool) -> list[Path]:
    if not resume:
        return all_paths
    completed = load_completed_files()
    if not completed:
        return all_paths
    pending = [path for path in all_paths if path.name.lower() not in completed]
    if len(pending) < len(all_paths):
        st.info(f"Resuming batch: {len(all_paths) - len(pending)} file(s) already completed, {len(pending)} remaining.")
    return pending


def _process_single_pass(
    all_paths: list[Path],
    metadata: dict,
    asr_config: ASRConfig,
    devices: dict[str, str],
    progress,
    status,
    *,
    resume: bool,
) -> tuple[list[dict], list[tuple]]:
    pending_paths = _pending_paths(all_paths, resume)
    records = load_result_records() if resume else []
    details: list[tuple] = []
    tracker = BatchProgressTracker(len(pending_paths) or 1, progress, status)

    transcriber = get_transcriber(
        asr_config.backend,
        asr_config.speed,
        devices["whisper"],
        asr_config.model_name,
        asr_config.compute_type,
    )
    analyzer = get_analyzer(devices["sentiment"])
    llm_analyzer = get_llm_analyzer(devices["llm"])

    for idx, audio_path in enumerate(pending_paths):
        record, detail = _process_one_file(
            idx,
            audio_path,
            metadata,
            transcriber,
            analyzer,
            llm_analyzer,
            tracker,
        )
        records.append(record)
        details.append(detail)
        append_result_record(record, audio_path.name)
        clear_gpu_memory()

    tracker.complete("Batch complete")
    return records, details


def _process_large_batch(
    all_paths: list[Path],
    metadata: dict,
    asr_config: ASRConfig,
    devices: dict[str, str],
    progress,
    status,
    *,
    resume: bool,
) -> tuple[list[dict], list[tuple]]:
    pending_paths = _pending_paths(all_paths, resume)
    records = load_result_records() if resume else []
    details: list[tuple] = []
    tracker = BatchProgressTracker(len(pending_paths) or 1, progress, status)
    transcript_cache = load_cached_transcripts(
        asr_config.backend,
        asr_config.model_name,
        asr_config.compute_type,
    )

    pending_transcription = [
        path for path in pending_paths if path.name.lower() not in transcript_cache
    ]
    path_index = {path.name.lower(): index for index, path in enumerate(pending_paths)}

    if pending_transcription:
        status.write(f"Phase 1/2: Transcribing audio ({asr_config.label}) ...")
        transcriber = get_transcriber(
            asr_config.backend,
            asr_config.speed,
            devices["whisper"],
            asr_config.model_name,
            asr_config.compute_type,
        )
        for audio_path in pending_transcription:
            file_index = path_index[audio_path.name.lower()]
            call_id = f"C{file_index + len(records) + 1:03d}"
            metadata_row = metadata.get(audio_path.name.lower()) or metadata.get(audio_path.stem.lower(), {})

            tracker.update(file_index, "transcribe", audio_path.name)
            transcription = transcriber.transcribe_file(audio_path, call_id)
            tracker.update(file_index, "transcribe", audio_path.name, stage_complete=True)

            append_transcript_cache(
                audio_path.name,
                call_id,
                transcription,
                metadata_row,
                asr_backend=asr_config.backend,
                asr_model=asr_config.model_name,
                asr_compute_type=asr_config.compute_type,
            )
            clear_gpu_memory()

        get_transcriber.clear()
        clear_gpu_memory()

    transcript_cache = load_cached_transcripts(
        asr_config.backend,
        asr_config.model_name,
        asr_config.compute_type,
    )

    status.write("Phase 2/2: LLM + sentiment analysis ...")
    analyzer = get_analyzer(devices["sentiment"])
    llm_analyzer = get_llm_analyzer(devices["llm"])

    for idx, audio_path in enumerate(pending_paths):
        cache_entry = transcript_cache.get(audio_path.name.lower())
        if not cache_entry:
            continue

        call_id = cache_entry["call_id"]
        metadata_row = cache_entry.get("metadata") or {}
        transcription = cache_entry["transcription"]
        if isinstance(transcription, dict):
            transcription = transcription_from_dict(transcription)

        record, detail = _analyze_cached_transcript(
            idx,
            audio_path.name,
            call_id,
            transcription,
            metadata_row,
            analyzer,
            llm_analyzer,
            tracker,
            asr_backend=asr_config.backend,
        )
        records.append(record)
        details.append(detail)
        append_result_record(record, audio_path.name)
        clear_gpu_memory()

    get_llm_analyzer.clear()
    clear_gpu_memory()
    tracker.complete("Large batch complete")
    return records, details


def _process_one_file(
    file_index: int,
    audio_path: Path,
    metadata: dict,
    transcriber: AudioTranscriber,
    analyzer: SentimentUrgencyAnalyzer,
    llm_analyzer: TranscriptLLMAnalyzer,
    tracker: BatchProgressTracker,
) -> tuple[dict, tuple]:
    call_id = f"C{file_index + 1:03d}"
    metadata_row = metadata.get(audio_path.name.lower()) or metadata.get(audio_path.stem.lower(), {})

    tracker.update(file_index, "transcribe", audio_path.name)
    transcription = transcriber.transcribe_file(audio_path, call_id)
    tracker.update(file_index, "transcribe", audio_path.name, stage_complete=True)

    return _analyze_cached_transcript(
        file_index,
        audio_path.name,
        call_id,
        transcription,
        metadata_row,
        analyzer,
        llm_analyzer,
        tracker,
        record_index=file_index + 1,
        asr_backend=getattr(transcriber, "backend", "whisper"),
    )


def _analyze_cached_transcript(
    file_index: int,
    file_name: str,
    call_id: str,
    transcription,
    metadata_row: dict,
    analyzer: SentimentUrgencyAnalyzer,
    llm_analyzer: TranscriptLLMAnalyzer,
    tracker: BatchProgressTracker,
    *,
    record_index: int | None = None,
    asr_backend: str = "whisper",
) -> tuple[dict, tuple]:
    tracker.update(file_index, "analyze", file_name)
    extraction = extract_entities(transcription.transcript)
    tracker.update(file_index, "analyze", file_name, stage_complete=True)

    tracker.update(file_index, "llm", file_name)
    if transcription.transcript == "ERROR":
        llm_result = LLMExtractionResult.failure("Transcription failed.")
        analysis = analyzer.analyze(transcription.transcript, extraction)
    else:
        llm_result = llm_analyzer.analyze_transcript(
            transcription.transcript,
            transcription.transcript,
            metadata=metadata_row,
            transcript_quality=getattr(transcription, "transcript_quality_score", 1.0),
            asr_backend=asr_backend,
        )
        analysis = analyzer.analyze(
            transcription.transcript,
            extraction,
            event_type=llm_result.event_type,
            llm_summary=llm_result.summary,
            llm_keywords=llm_result.keywords,
        )
    tracker.update(file_index, "llm", file_name, stage_complete=True)

    tracker.update(file_index, "finalize", file_name)
    record = build_record(
        record_index or file_index + 1,
        transcription,
        extraction,
        analysis,
        llm_result,
        metadata_row,
    )
    tracker.update(file_index, "finalize", file_name, stage_complete=True)
    detail = (call_id, file_name, transcription, extraction, analysis, llm_result, record)
    return record, detail


def _save_uploads(uploaded_files, temp_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for uploaded_file in uploaded_files or []:
        path = temp_dir / uploaded_file.name
        path.write_bytes(uploaded_file.getbuffer())
        paths.append(path)
    return paths


def _render_results(dataframe: pd.DataFrame, details: list[tuple], *, large_batch: bool) -> None:
    st.subheader("Results")
    st.dataframe(
        dataframe.style.format({"Urgency_Score": "{:.2f}", "Confidence_Score": "{:.2f}"}),
        use_container_width=True,
    )

    csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="emergency_analysis_output.csv",
        mime="text/csv",
    )

    if large_batch:
        st.caption(
            f"Large batch mode: showing the first {MAX_DETAIL_EXPANDERS} call details only. "
            "Use the CSV download for the full output."
        )
        details = details[:MAX_DETAIL_EXPANDERS]

    st.subheader("Per-Call Details")
    for call_id, file_name, transcription, extraction, analysis, llm_result, record in details:
        with st.expander(f"{call_id} - {file_name}"):
            if transcription.error:
                st.error(f"Transcription error: {transcription.error}")
            if llm_result.error:
                st.warning(f"LLM analysis note: {llm_result.error}")
            st.write("Transcribed Script")
            st.text_area(
                "Speech-to-Text Transcript",
                value=record[TRANSCRIBED_SCRIPT_COLUMN],
                height=260,
                key=f"formatted-transcript-{call_id}-{file_name}",
            )
            st.text_area(
                "Transcript Summary",
                value=record["Transcript Summary"],
                height=160,
                key=f"transcript-summary-{call_id}-{file_name}",
            )
            st.write(f"Detected event (LLM + rules): `{record['Event_Type']}`")
            st.write(f"NLTK location hint: `{extraction.location}`")
            st.write(f"Urgency phrases: `{', '.join(extraction.urgency_phrases) or 'None'}`")
            st.bar_chart(pd.DataFrame({"Score": [max(analysis.urgency_score, 0.0)]}, index=["Urgency"]))


def _about_section() -> None:
    with st.expander("About the Analysis"):
        st.markdown(
            """
            **Sentiment labels**

            - `Fearful`: fear or panic indicators.
            - `Angry`: anger or confrontation indicators.
            - `Sad`: sadness or grief indicators.
            - `Surprised`: shock or sudden unexpected event indicators.
            - `Calm`: positive or composed language.
            - `Neutral`: low-emotion or ambiguous language.
            - `Critical Distress`: high urgency plus a negative emotion signal.

            **Analysis pipeline**

            1. **faster-whisper**, **HuggingFace Whisper**, or **Wav2Vec2 960h** transcribes the audio.
            2. **Qwen2.5-1.5B-Instruct** classifies the event and writes the transcript summary.
            3. A DistilRoBERTa emotion model scores sentiment and urgency on CPU during GPU runs.

            **Large batch tips (750 files, 6 GB GPU)**

            - **Fastest recommended:** `faster-whisper` + **Distil Large v3** + **float16** on GPU.
            - **Best accuracy:** Whisper-family **Large v3 Turbo** or HuggingFace Whisper **Slow** when runtime is less important.
            - **Best balance:** `faster-whisper` + **Large v3 Turbo** or **Distil Large v3** on **GPU**.
            - Enable **Large batch mode** to unload the ASR model before loading the LLM.
            - Enable **Resume from checkpoint** so you can stop and continue across sessions (`outputs/.batch/`).
            - **Avoid Wav2Vec2 for final CSV** on 911 phone/hold audio — it is faster but transcripts are often unusable.
            - Run overnight; if interrupted, leave **Resume** on and click **Process Files** again.

            **Urgency formula**

            `urgency_score` combines transcript, LLM summary, and LLM event type:

            - **30%** event-type baseline (e.g. Shooting, Medical emergency)
            - **22%** transcript phrase urgency (strong hits like “shots fired”, not diluted by length)
            - **18%** LLM summary phrase urgency
            - **10%** LLM keyword urgency
            - **10%** emotional distress (on summary + urgent transcript windows)
            - **10%** high-risk negation (“not breathing”, “can’t move”)

            Critical event types receive a floor so long procedural transcripts do not hide life-threatening calls.
            """
        )


if __name__ == "__main__":
    main()
