"""Keyword and entity extraction for emergency transcripts."""

from __future__ import annotations

import re
from dataclasses import dataclass


URGENCY_PHRASES = [
    "help",
    "hurry",
    "emergency",
    "urgent",
    "please",
    "trapped",
    "can't breathe",
    "cant breathe",
    "cannot breathe",
    "bleeding",
    "unconscious",
    "shots fired",
    "gun",
    "fire",
    "smoke",
    "heart attack",
    "not breathing",
    "won't stop",
    "wont stop",
    "stabbed",
    "shot",
    "shooting",
    "ambulance",
    "baby",
    "labor",
    "contraction",
    "officer down",
    "need backup",
    "dying",
    "cardiac arrest",
    "overdose",
    "hostage",
    "kill him",
    "kill her",
    "murder",
    "pinned",
    "can't move",
    "cant move",
    "explosion",
    "unresponsive",
    "choking",
    "seizure",
    "stroke",
]

STRONG_URGENCY_PHRASES: tuple[tuple[str, float], ...] = (
    ("shots fired", 1.0),
    ("officer down", 1.0),
    ("not breathing", 0.98),
    ("can't breathe", 0.98),
    ("cant breathe", 0.98),
    ("cannot breathe", 0.98),
    ("cardiac arrest", 0.96),
    ("unconscious", 0.92),
    ("unresponsive", 0.92),
    ("bleeding out", 0.95),
    ("severely bleeding", 0.92),
    ("hostage", 0.94),
    ("active shooter", 0.98),
    ("need backup now", 0.95),
    ("dying", 0.90),
    ("explosion", 0.90),
    ("stabbing", 0.92),
    ("someone shot", 0.95),
    ("baby not breathing", 0.98),
    ("having a heart attack", 0.94),
    ("car in the water", 0.93),
    ("pinned in", 0.88),
    ("trapped", 0.85),
)

NEGATION_PATTERNS = (
    "can't breathe",
    "cant breathe",
    "cannot breathe",
    "not breathing",
    "won't wake",
    "wont wake",
    "can't move",
    "cant move",
    "cannot move",
    "unable to breathe",
    "unable to move",
    "losing consciousness",
    "passed out",
)

LOCATION_PATTERN = re.compile(
    r"\b(?:at|near|on|inside|outside|in front of)\s+([A-Z0-9][A-Za-z0-9 .'-]*(?:Street|St|Avenue|Ave|"
    r"Road|Rd|Highway|Hwy|Boulevard|Blvd|Park|School|Hospital|Mall|Bank|Station|Floor|Apartment|Apt)\b)",
    re.IGNORECASE,
)

PROPER_NOUN_LOCATION_PATTERN = re.compile(
    r"\b(?:at|in|near|on)\s+((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}))\b"
)

NOT_PERSON_NAMES = {
    "just", "okay", "ok", "stay", "sir", "ma'am", "maam", "yes", "no", "yeah",
    "step", "wait", "listen", "hello", "huh", "hold", "county", "channel",
    "staff", "mpd", "please", "thanks", "thank", "welcome", "excuse", "sorry",
    "ma", "am", "let", "tell", "turn", "pull", "see", "need", "want", "got",
    "there", "who", "when", "how", "what", "where", "why", "roll", "stop",
    "slow", "fast", "going", "sign", "lights", "light", "one", "two", "three",
    "well", "right", "left", "now", "then", "also", "today", "talk", "talking",
}

COMMON_ENGLISH_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "can", "your", "you", "yours", "my", "mine", "our",
    "we", "they", "them", "their", "it", "its", "this", "that", "these", "those",
    "i", "me", "he", "she", "him", "her", "his", "not", "no", "yes", "just",
    "car", "stop", "pull", "over", "when", "where", "what", "who", "how", "why",
    "going", "want", "need", "know", "tell", "talk", "get", "got", "going", "come",
    "middle", "next", "few", "last", "first", "one", "two", "three", "slow", "fast",
    "sign", "light", "lights", "okay", "stay", "let", "until", "then", "also",
    "today", "right", "left", "well", "if", "so", "because", "about", "into",
    "out", "up", "down", "back", "here", "there", "now", "very", "really",
}


@dataclass
class ExtractionResult:
    event_type: str
    location: str
    locations: list[str]
    names: list[str]
    urgency_phrases: list[str]
    keyword_density_score: float
    negation_boost: float


def extract_entities(transcript: str) -> ExtractionResult:
    """Extract incident, location, person names, and urgency signals."""
    if not transcript or transcript == "ERROR":
        return ExtractionResult("Unknown", "Unknown", [], [], [], 0.0, 0.0)

    tokens, named_entities = _nltk_entities(transcript)
    lower_text = transcript.lower()

    event_type = "Unknown"
    locations = _extract_locations(named_entities, transcript)
    names = _extract_names(named_entities)
    urgency_phrases = [phrase for phrase in URGENCY_PHRASES if phrase in lower_text]

    phrase_score, matched = compute_phrase_urgency(transcript)
    keyword_density = phrase_score
    negation_boost = compute_negation_boost(lower_text)

    return ExtractionResult(
        event_type=event_type,
        location=locations[0] if locations else "Unknown",
        locations=locations,
        names=names,
        urgency_phrases=matched or urgency_phrases,
        keyword_density_score=round(keyword_density, 2),
        negation_boost=negation_boost,
    )


def compute_negation_boost(text: str) -> float:
    lower = (text or "").lower()
    if any(pattern in lower for pattern in NEGATION_PATTERNS):
        return 1.0
    return 0.0


def compute_phrase_urgency(text: str) -> tuple[float, list[str]]:
    """Score urgency from phrase hits (max-hit weighted, not diluted by length)."""
    lower = (text or "").lower()
    if not lower.strip():
        return 0.0, []

    matched: list[str] = []
    score = 0.0
    for phrase, weight in STRONG_URGENCY_PHRASES:
        if phrase in lower:
            matched.append(phrase)
            score = max(score, weight)

    for phrase in URGENCY_PHRASES:
        if phrase in lower and phrase not in matched:
            matched.append(phrase)
            score = max(score, min(0.82, score + 0.12))

    if compute_negation_boost(lower) >= 1.0:
        score = max(score, 0.88)

    return round(min(1.0, score), 2), matched


def _nltk_entities(transcript: str) -> tuple[list[str], list[tuple[str, str]]]:
    import nltk

    _ensure_nltk_data(nltk)
    tokens = nltk.word_tokenize(transcript)
    tagged = nltk.pos_tag(tokens)
    tree = nltk.ne_chunk(tagged)

    entities: list[tuple[str, str]] = []
    for node in tree:
        if hasattr(node, "label"):
            label = node.label()
            text = " ".join(token for token, _ in node)
            entities.append((label, text))
    return tokens, entities


def _ensure_nltk_data(nltk) -> None:
    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("taggers/averaged_perceptron_tagger", "averaged_perceptron_tagger"),
        ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
        ("chunkers/maxent_ne_chunker", "maxent_ne_chunker"),
        ("chunkers/maxent_ne_chunker_tab", "maxent_ne_chunker_tab"),
        ("corpora/words", "words"),
    ]
    for path, package in resources:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(package, quiet=True)


def _extract_locations(named_entities: list[tuple[str, str]], transcript: str) -> list[str]:
    labels = {"GPE", "LOC", "LOCATION", "FACILITY", "FAC"}
    locations = [text for label, text in named_entities if label in labels]
    locations.extend(match.group(1).strip() for match in LOCATION_PATTERN.finditer(transcript))
    locations.extend(
        match.group(1).strip()
        for match in PROPER_NOUN_LOCATION_PATTERN.finditer(transcript)
    )
    return _dedupe(location for location in locations if is_valid_location_mention(location))


def is_valid_location_mention(value: str) -> bool:
    text = re.sub(r"\s+", " ", value.strip())
    if not text or len(text) > 48:
        return False

    words = [word for word in re.findall(r"[A-Za-z0-9'.-]+", text) if word]
    if not words or len(words) > 4:
        return False

    lower_words = [word.lower() for word in words]
    if any(word in COMMON_ENGLISH_WORDS for word in lower_words):
        return False
    if any(word in NOT_PERSON_NAMES for word in lower_words):
        return False

    if re.search(
        r"\b(?:street|st|avenue|ave|road|rd|highway|hwy|boulevard|blvd|station|metro|"
        r"mall|park|hospital|county|city|school|bank|apt|apartment|floor|unifest)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return True

    if len(words) == 1:
        return bool(re.match(r"^[A-Z][a-z]{2,}$", words[0]))

    return all(re.match(r"^[A-Z][a-z]+(?:'[A-Za-z]+)?$", word) for word in words)


def _is_valid_person_name(name: str) -> bool:
    normalized = re.sub(r"\s+", " ", name.strip())
    if not normalized or len(normalized) < 2 or len(normalized) > 24:
        return False

    words = normalized.split()
    if len(words) > 2:
        return False

    lower_words = [word.lower() for word in words]
    if any(word in NOT_PERSON_NAMES for word in lower_words):
        return False
    if any(word in COMMON_ENGLISH_WORDS for word in lower_words):
        return False
    if re.search(
        r"\b(?:street|st|avenue|ave|road|rd|highway|hwy|boulevard|blvd|station|metro|county|channel)\b",
        normalized,
        flags=re.IGNORECASE,
    ):
        return False
    if normalized.isupper() and len(normalized) <= 4:
        return False
    return bool(re.match(r"^[A-Z][a-z]+(?:'[A-Za-z]+)?(?:\s+[A-Z][a-z]+(?:'[A-Za-z]+)?)?$", normalized))


def _extract_names(named_entities: list[tuple[str, str]]) -> list[str]:
    names = (text for label, text in named_entities if label == "PERSON")
    return _dedupe(name for name in names if _is_valid_person_name(name))


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            output.append(normalized)
            seen.add(key)
    return output
