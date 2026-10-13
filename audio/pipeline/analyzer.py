"""Sentiment classification and urgency scoring."""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.extractor import ExtractionResult
from pipeline.urgency_scorer import build_urgency_focus_text, compute_urgency_score


@dataclass
class AnalysisResult:
    sentiment: str
    urgency_score: float
    sentiment_confidence: float
    urgency_level: str


def _distress_from_scores(scores: dict[str, float]) -> float:
    return max(
        scores.get("fear", 0.0),
        scores.get("anger", 0.0),
        scores.get("sadness", 0.0),
        scores.get("disgust", 0.0),
        scores.get("negative", 0.0),
    )


class SentimentUrgencyAnalyzer:
    """Analyze transcript emotion and compute urgency from transcript + LLM outputs."""

    def __init__(
        self,
        model_name: str = "j-hartmann/emotion-english-distilroberta-base",
        device: str = "cpu",
    ) -> None:
        from transformers import pipeline

        pipeline_device = 0 if device == "cuda" else -1
        self.classifier = pipeline("sentiment-analysis", model=model_name, device=pipeline_device)
        self.model_name = model_name

    def analyze(
        self,
        transcript: str,
        extraction: ExtractionResult,
        *,
        event_type: str = "Unknown",
        llm_summary: str = "",
        llm_keywords: str = "",
    ) -> AnalysisResult:
        if not transcript or transcript == "ERROR":
            return AnalysisResult("Neutral", -1.0, 0.0, "Error")

        focus_text = build_urgency_focus_text(transcript, llm_summary, llm_keywords)
        emotion_scores = self._emotion_scores(focus_text or transcript)
        distressed_confidence = _distress_from_scores(emotion_scores)

        urgency_score, _signals = compute_urgency_score(
            transcript,
            event_type=event_type,
            llm_summary=llm_summary,
            llm_keywords=llm_keywords,
            emotion_distress=distressed_confidence,
        )

        sentiment, sentiment_confidence = self._map_sentiment(emotion_scores, urgency_score)

        return AnalysisResult(
            sentiment=sentiment,
            urgency_score=urgency_score,
            sentiment_confidence=round(sentiment_confidence, 2),
            urgency_level=urgency_level(urgency_score),
        )

    def _emotion_scores(self, text: str) -> dict[str, float]:
        raw_result = self.classifier(text, truncation=True, max_length=512, top_k=None)
        results = raw_result[0] if raw_result and isinstance(raw_result[0], list) else raw_result
        return {str(item["label"]).lower(): float(item["score"]) for item in results}

    @staticmethod
    def _map_sentiment(scores: dict[str, float], urgency_score: float) -> tuple[str, float]:
        if not scores:
            return "Neutral", 0.0

        top_label = max(scores, key=scores.get)
        top_score = scores[top_label]
        label_map = {
            "anger": "Angry",
            "disgust": "Disgusted",
            "fear": "Fearful",
            "joy": "Calm",
            "neutral": "Neutral",
            "sadness": "Sad",
            "surprise": "Surprised",
            "negative": "Distressed",
            "positive": "Calm",
        }

        if urgency_score >= 0.75 and top_label in {"anger", "disgust", "fear", "sadness", "negative"}:
            return "Critical Distress", top_score

        return label_map.get(top_label, top_label.title()), top_score


def urgency_level(score: float) -> str:
    if score < 0:
        return "Error"
    if score <= 0.3:
        return "Low"
    if score <= 0.6:
        return "Moderate"
    if score <= 0.8:
        return "High"
    return "Critical"
