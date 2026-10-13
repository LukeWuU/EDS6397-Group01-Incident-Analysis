"""Metadata-informed rule-based emergency event detection for Whisper transcripts.

Event categories and keywords are derived from the 911_metadata.csv catalog
(538 unique incident titles across 706 audio files). Rules match spoken
phrases in ASR output — metadata is used only to build the rule set, not
to classify individual calls at runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EventRule:
    event_type: str
    priority: int
    strong_phrases: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    min_keyword_score: int = 1
    support_phrases: tuple[str, ...] = ()
    min_support_score: int = 0


# Priority: lower number = evaluated first (more specific before generic).
EVENT_RULES: tuple[EventRule, ...] = (
    EventRule(
        event_type="False alarm",
        priority=10,
        strong_phrases=(
            "prank call",
            "wrong address",
            "accidental dial",
            "pocket dial",
            "not an emergency",
            "bad sandwich",
            "bad chicken",
        ),
        keywords=("prank", "wrong number", "wrong address", "accidental"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Vehicle chase",
        priority=20,
        strong_phrases=(
            "chasing me",
            "they're chasing",
            "they are chasing",
            "police chase",
            "being pursued",
            "pursued by police",
            "high speed pursuit",
            "high-speed pursuit",
        ),
        support_phrases=(
            "pull over",
            "police car",
            "behind you",
            "how fast are you",
            "slow down",
            "stop your car",
            "lights and sirens",
            "lights are on",
            "running from",
            "steering wheel",
            "pursuit",
            "chased",
            "chase",
        ),
        min_support_score=3,
        keywords=("pursuit", "chased", "fleeing", "runaway car", "reckless driver"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Vehicle in water",
        priority=30,
        strong_phrases=(
            "car in the water",
            "car in water",
            "into the pond",
            "into a pond",
            "sinking vehicle",
            "submerged in water",
            "car swept",
            "floating car",
        ),
        keywords=("pond", "creek", "river", "sinking", "submerged", "water", "drowning in car"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Childbirth",
        priority=40,
        strong_phrases=(
            "having a baby",
            "delivering a baby",
            "baby is coming",
            "baby's coming",
            "in labor",
            "going into labor",
        ),
        keywords=("baby delivery", "childbirth", "contractions", "contraction", "deliver", "labor", "giving birth"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Explosion",
        priority=50,
        strong_phrases=("bomb went off", "gas explosion", "natural gas explosion", "train derailment"),
        keywords=("explosion", "exploded", "bomb", "hazmat", "gas leak", "gas main", "detonation"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Shooting",
        priority=60,
        strong_phrases=(
            "shots fired",
            "shot him",
            "shot her",
            "shot me",
            "someone shot",
            "active shooter",
            "shoot-out",
            "shoot out",
            "gunman",
            "opened fire",
        ),
        keywords=("shooting", "shot", "gunshot", "gun fire", "bullet", "rifle", "pistol", "handgun"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Stabbing",
        priority=70,
        strong_phrases=(
            "been stabbed",
            "got stabbed",
            "was stabbed",
            "knife attack",
            "stabbed me",
            "stabbed him",
            "stabbed her",
        ),
        keywords=("stabbing", "stabbed", "knife wound", "knifed", "with a knife"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Murder",
        priority=80,
        strong_phrases=(
            "been murdered",
            "was murdered",
            "someone killed",
            "killed him",
            "killed her",
            "killed my",
            "dead body",
            "found dead",
            "homicide",
        ),
        keywords=("murder", "murdered", "homicide", "killed", "fatal", "beheaded"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Kidnapping",
        priority=90,
        strong_phrases=(
            "been kidnapped",
            "was kidnapped",
            "taken hostage",
            "held hostage",
            "hostage situation",
            "child abduction",
            "amber alert",
        ),
        keywords=("kidnap", "kidnapping", "abduction", "abducted", "hostage", "snatched"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Carjacking",
        priority=100,
        strong_phrases=("carjacking", "car jacking", "stole my car", "took my car at gunpoint"),
        keywords=("carjacking", "car jacking", "stolen car", "took the car"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Robbery",
        priority=110,
        strong_phrases=(
            "being robbed",
            "getting robbed",
            "bank robbery",
            "armed robbery",
            "robbery in progress",
            "hold up",
            "hold-up",
        ),
        keywords=("robbery", "robbed", "robber", "robbers", "mugging", "stick up"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Burglary",
        priority=120,
        strong_phrases=(
            "breaking in",
            "break in",
            "break-in",
            "burglary in progress",
            "someone in my house",
            "intruder in",
            "home invasion",
        ),
        keywords=("burglary", "burglar", "intruder", "breaking in", "broke in", "broke into"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Fire",
        priority=130,
        strong_phrases=(
            "house on fire",
            "building on fire",
            "trapped in fire",
            "smoke everywhere",
            "flames everywhere",
        ),
        keywords=("fire", "smoke", "burning", "flames", "arson", "smoke inhalation", "trapped"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Plane crash",
        priority=140,
        strong_phrases=("plane crash", "plane went down", "aircraft crash", "helicopter crash"),
        keywords=("plane crash", "air crash", "helicopter", "aircraft", "jet crash", "midair"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Vehicle collision",
        priority=150,
        strong_phrases=(
            "car accident",
            "traffic accident",
            "vehicle accident",
            "head on collision",
            "rear ended",
            "fender bender",
            "ran over",
            "hit pedestrians",
            "pile up",
            "pile-up",
        ),
        keywords=("crash", "crashed", "collision", "accident", "wreck", "hit a car", "hit by car"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Medical emergency",
        priority=160,
        strong_phrases=(
            "not breathing",
            "can't breathe",
            "cannot breathe",
            "heart attack",
            "having a heart attack",
            "unconscious",
            "passed out",
            "overdose",
            "overdosed",
            "need an ambulance",
            "need ambulance",
        ),
        keywords=(
            "medical",
            "ambulance",
            "cpr",
            "choking",
            "seizure",
            "stroke",
            "diabetic",
            "allergic reaction",
            "bleeding",
            "unresponsive",
            "carbon monoxide",
        ),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Drowning",
        priority=170,
        strong_phrases=("drowning", "drowned", "going under water", "submerged in pool"),
        keywords=("drowning", "drowned", "pool", "lake", "river rescue"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Domestic disturbance",
        priority=180,
        strong_phrases=("domestic dispute", "domestic violence", "fight with my husband", "fight with my wife"),
        keywords=("domestic", "husband and wife", "boyfriend", "girlfriend fight", "family fight"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Suicide",
        priority=190,
        strong_phrases=(
            "kill myself",
            "killing myself",
            "want to die",
            "suicidal",
            "going to hurt myself",
        ),
        keywords=("suicide", "suicidal", "self harm", "end my life"),
        min_keyword_score=1,
    ),
    EventRule(
        event_type="Animal attack",
        priority=200,
        strong_phrases=("dog attack", "bear attack", "alligator", "shark bite", "bitten by"),
        keywords=("dog bite", "animal attack", "bear", "snake bite", "coyote", "bee swarm"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="DUI",
        priority=210,
        strong_phrases=("drunk driver", "impaired driver", "dui suspect"),
        keywords=("dui", "drunk", "intoxicated", "swerving", "wrong way driver"),
        min_keyword_score=2,
    ),
    EventRule(
        event_type="Public safety incident",
        priority=900,
        keywords=("emergency", "help", "police", "danger", "threat", "suspicious", "urgent", "911"),
        min_keyword_score=2,
    ),
)

EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    rule.event_type: rule.keywords for rule in EVENT_RULES if rule.keywords
}

ALLOWED_EVENT_TYPES: tuple[str, ...] = tuple(
    dict.fromkeys(rule.event_type for rule in sorted(EVENT_RULES, key=lambda item: item.priority))
)

EVENT_TYPE_ALIASES: dict[str, str] = {
    "traffic violation": "Public safety incident",
    "traffic stop": "Public safety incident",
    "police pursuit": "Vehicle chase",
    "car chase": "Vehicle chase",
    "high speed pursuit": "Vehicle chase",
    "high-speed pursuit": "Vehicle chase",
    "pursuit": "Vehicle chase",
    "car accident": "Vehicle collision",
    "traffic accident": "Vehicle collision",
    "auto accident": "Vehicle collision",
    "gunfire": "Shooting",
    "active shooter": "Shooting",
    "heart attack": "Medical emergency",
    "ambulance needed": "Medical emergency",
    "domestic violence": "Domestic disturbance",
    "domestic dispute": "Domestic disturbance",
    "hostage": "Kidnapping",
    "abduction": "Kidnapping",
    "prank": "False alarm",
    "prank call": "False alarm",
}

METADATA_TITLE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpursuit\b", re.I), "Vehicle chase"),
    (re.compile(r"\bhigh[- ]speed (?:pursuit|chase)\b", re.I), "Vehicle chase"),
    (re.compile(r"\bvehicle chase\b", re.I), "Vehicle chase"),
    (re.compile(r"\bshoot(?:ing)?[- ]?out\b", re.I), "Shooting"),
    (re.compile(r"\bofficer shooting\b", re.I), "Shooting"),
    (re.compile(r"\bbank robbery\b", re.I), "Robbery"),
    (re.compile(r"\brobbery\b", re.I), "Robbery"),
    (re.compile(r"\bburglary\b", re.I), "Burglary"),
    (re.compile(r"\bkidnapp(?:ing|ed)\b", re.I), "Kidnapping"),
    (re.compile(r"\bdomestic\b", re.I), "Domestic disturbance"),
    (re.compile(r"\bdui\b", re.I), "DUI"),
    (re.compile(r"\bdrunk driver\b", re.I), "DUI"),
    (re.compile(r"\bchildbirth\b|\bbaby delivery\b|\bin labor\b", re.I), "Childbirth"),
    (re.compile(r"\bplane crash\b|\bair crash\b", re.I), "Plane crash"),
    (re.compile(r"\bexplosion\b|\bbomb\b", re.I), "Explosion"),
    (re.compile(r"\bfalse alarm\b|\bprank\b", re.I), "False alarm"),
    (re.compile(r"\bcarjacking\b", re.I), "Carjacking"),
    (re.compile(r"\bstabbing\b|\bstabbed\b", re.I), "Stabbing"),
    (re.compile(r"\bmurder\b|\bhomicide\b", re.I), "Murder"),
    (re.compile(r"\bdrowning\b", re.I), "Drowning"),
    (re.compile(r"\bfire\b|\barson\b", re.I), "Fire"),
    (re.compile(r"\bcollision\b|\bcar accident\b|\bcrash\b", re.I), "Vehicle collision"),
    (re.compile(r"\bmedical\b|\bambulance\b|\bheart attack\b", re.I), "Medical emergency"),
    (re.compile(r"\bsuicid", re.I), "Suicide"),
    (re.compile(r"\banimal attack\b|\bdog bite\b", re.I), "Animal attack"),
    (re.compile(r"\bvehicle in water\b|\bcar in (?:the )?water\b", re.I), "Vehicle in water"),
)

CLASSIFICATION_GUIDANCE = """CLASSIFICATION RULES (follow strictly):
- Use ONLY one event_type from the allowed list below.
- "Vehicle chase": police or officers are actively pursuing a fleeing vehicle; caller reports being chased, won't pull over, high speed, lights/sirens, pursuit in progress. A routine traffic stop or minor infraction WITHOUT pursuit is NOT a chase.
- "Traffic violation" is NOT a valid label — use "Public safety incident" for minor non-emergency complaints, or "Vehicle chase" when pursuit language appears.
- "Vehicle collision": a crash, wreck, hit, rear-ended, or accident — not an ongoing pursuit.
- "Shooting": shots fired, gunman, someone shot — not merely "officers" or "police" without gunfire.
- "Medical emergency": breathing problems, heart attack, unconscious, overdose, need ambulance.
- "False alarm": prank call, pocket dial, wrong address, not a real emergency.
- Match keywords in the summary to the chosen event_type (do not mention unrelated categories in keywords).
- When metadata incident title/description suggests an event type AND the transcript supports it, use that type.
- Prefer specific types over "Public safety incident" or "Unknown" when evidence exists."""


def normalize_transcript(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = text.replace("'", "'").replace(""", '"').replace(""", '"')
    return text


def detect_event_type(transcript: str) -> tuple[str, int, list[str]]:
    """Return (event_type, confidence_score, matched_terms) from transcript text."""
    lower_text = normalize_transcript(transcript)
    if not lower_text or lower_text == "error":
        return "Unknown", 0, []

    for rule in sorted(EVENT_RULES, key=lambda item: item.priority):
        matched_strong = [phrase for phrase in rule.strong_phrases if phrase in lower_text]
        if matched_strong:
            return rule.event_type, 5, matched_strong

        if rule.support_phrases and rule.min_support_score:
            matched_support = [phrase for phrase in rule.support_phrases if phrase in lower_text]
            if len(matched_support) >= rule.min_support_score:
                return rule.event_type, len(matched_support) + 2, matched_support

        matched_keywords = [keyword for keyword in rule.keywords if keyword in lower_text]
        if len(matched_keywords) >= rule.min_keyword_score:
            return rule.event_type, len(matched_keywords), matched_keywords

    return "Unknown", 0, []


def is_vehicle_chase(transcript: str) -> bool:
    event_type, score, _ = detect_event_type(transcript)
    return event_type == "Vehicle chase" and score > 0


def event_keywords(event_type: str) -> tuple[str, ...]:
    return EVENT_KEYWORDS.get(event_type, ())


def normalize_event_type(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", (label or "").strip())
    if not cleaned:
        return "Unknown"

    lower = cleaned.lower()
    if lower in EVENT_TYPE_ALIASES:
        return EVENT_TYPE_ALIASES[lower]

    for canonical in ALLOWED_EVENT_TYPES:
        if lower == canonical.lower():
            return canonical

    for canonical in ALLOWED_EVENT_TYPES:
        if canonical.lower() in lower or lower in canonical.lower():
            return canonical

    return cleaned.title()


def _metadata_text(metadata: dict) -> str:
    parts = []
    for field in ("title", "description", "state"):
        value = metadata.get(field)
        if value is None or (isinstance(value, float) and str(value) == "nan"):
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def infer_event_type_from_metadata(metadata: dict | None) -> tuple[str, int, list[str]]:
    """Return (event_type, confidence_score, matched_terms) from 911 metadata."""
    if not metadata:
        return "Unknown", 0, []

    title = str(metadata.get("title", "") or "").strip()
    for pattern, event_type in METADATA_TITLE_PATTERNS:
        if title and pattern.search(title):
            return event_type, 5, [title]

    combined = _metadata_text(metadata)
    if not combined:
        return "Unknown", 0, []

    return detect_event_type(combined)


def build_llm_classification_context(
    transcript: str,
    metadata: dict | None = None,
) -> dict[str, object]:
    """Build rule- and metadata-based hints for the LLM prompt."""
    rule_type, rule_score, rule_terms = detect_event_type(transcript)
    meta_type, meta_score, meta_terms = infer_event_type_from_metadata(metadata)

    hints: list[str] = []
    if rule_score > 0:
        hints.append(
            f"Transcript rule match: {rule_type} (score {rule_score}, terms: {', '.join(rule_terms[:5])})"
        )
    if meta_score > 0:
        hints.append(
            f"Metadata rule match: {meta_type} (score {meta_score}, terms: {', '.join(meta_terms[:5])})"
        )

    suggested = rule_type if rule_score >= meta_score else meta_type
    suggested_score = max(rule_score, meta_score)
    if suggested == "Unknown":
        if meta_score > 0:
            suggested, suggested_score = meta_type, meta_score
        elif rule_score > 0:
            suggested, suggested_score = rule_type, rule_score

    return {
        "rule_type": rule_type,
        "rule_score": rule_score,
        "rule_terms": rule_terms,
        "meta_type": meta_type,
        "meta_score": meta_score,
        "meta_terms": meta_terms,
        "suggested_type": suggested,
        "suggested_score": suggested_score,
        "hint_lines": hints,
    }


def reconcile_event_type(
    llm_event: str,
    transcript: str,
    metadata: dict | None = None,
) -> tuple[str, float]:
    """Combine LLM output with transcript rules and metadata for a consistent label."""
    normalized_llm = normalize_event_type(llm_event)
    rule_type, rule_score, _ = detect_event_type(transcript)
    meta_type, meta_score, _ = infer_event_type_from_metadata(metadata)

    weak_llm_labels = {
        "Unknown",
        "Public safety incident",
        "Traffic violation",
        "Traffic Violation",
    }

    if rule_score >= 5:
        if normalized_llm in weak_llm_labels or _types_conflict(normalized_llm, rule_type):
            return rule_type, 0.93

    if meta_score >= 5:
        if normalized_llm in weak_llm_labels or _types_conflict(normalized_llm, meta_type):
            return meta_type, 0.91

    if rule_type == "Vehicle chase" and rule_score >= 4:
        if normalized_llm in weak_llm_labels or normalized_llm in {
            "Vehicle collision",
            "DUI",
            "Public safety incident",
        }:
            return rule_type, 0.9

    if meta_type == "Vehicle chase" and meta_score >= 4 and rule_score >= 3:
        if normalized_llm in weak_llm_labels or normalized_llm == "Vehicle collision":
            return "Vehicle chase", 0.89

    if normalized_llm in weak_llm_labels and rule_score >= 3:
        return rule_type, 0.85

    if normalized_llm in weak_llm_labels and meta_score >= 3:
        return meta_type, 0.83

    return normalized_llm, 0.85


def _types_conflict(predicted: str, reference: str) -> bool:
    if predicted == reference:
        return False
    chase_family = {"Vehicle chase", "Public safety incident", "Traffic violation", "DUI"}
    collision_family = {"Vehicle collision", "Vehicle chase"}
    if reference == "Vehicle chase" and predicted in chase_family - {"Vehicle chase"}:
        return True
    if reference == "Vehicle collision" and predicted in collision_family - {"Vehicle collision"}:
        return True
    return predicted in {"Unknown", "Public safety incident", "Traffic violation"}


def metadata_location_hint(metadata: dict | None) -> str:
    if not metadata:
        return ""
    state = metadata.get("state")
    if state is None or (isinstance(state, float) and str(state) == "nan"):
        return ""
    text = str(state).strip()
    return text if text else ""


def enrich_location_mention(location: str, metadata: dict | None = None) -> str:
    cleaned = re.sub(r"\s+", " ", (location or "").strip())
    if cleaned and cleaned.lower() != "unknown":
        return cleaned

    hint = metadata_location_hint(metadata)
    return hint if hint else "Unknown"
