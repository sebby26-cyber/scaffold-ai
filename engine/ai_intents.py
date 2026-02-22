"""
ai_intents.py — Universal natural language intent router.

Resolution order:
1. Exact alias match (from intents.yaml aliases) -> confidence 1.0
2. Keyword match (from intents.yaml keywords) -> confidence 0.7-0.9
3. Token overlap similarity (against examples) -> confidence 0.3-0.6
4. None if no match above threshold

This sits between user input and command dispatch.
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_intents(project_root: Path) -> list[dict]:
    """Load intents.yaml from canonical state."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "intents.yaml"
        if path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(path.read_text()) or {}
                return data.get("intents", [])
            except Exception:
                pass
    return []


def resolve_intent(text: str, project_root: Path) -> tuple[str, float, str] | None:
    """Resolve user text to (handler_name, confidence, intent_id).

    Returns None if no match above threshold.
    """
    intents = load_intents(project_root)
    if not intents:
        return None

    normalized = _normalize(text)

    # 1. Exact alias match
    result = _exact_alias_match(normalized, intents)
    if result:
        handler, intent_id = result
        return (handler, 1.0, intent_id)

    # 2. Keyword match
    result_kw = _keyword_match(normalized, intents)
    if result_kw:
        return result_kw

    # 3. Token similarity against examples
    result_sim = _similarity_match(normalized, intents)
    if result_sim:
        return result_sim

    return None


def get_intent_examples(project_root: Path, intent_id: str) -> list[str]:
    """Return example phrases for a given intent."""
    intents = load_intents(project_root)
    for intent in intents:
        if intent.get("id") == intent_id:
            return intent.get("examples", [])
    return []


def get_intents_by_category(project_root: Path) -> dict[str, list[dict]]:
    """Group all intents by category. Used by help builder."""
    intents = load_intents(project_root)
    groups: dict[str, list[dict]] = {}
    for intent in intents:
        cat = intent.get("category", "other")
        groups.setdefault(cat, []).append(intent)
    return groups


def _normalize(text: str) -> str:
    """Normalize input: lowercase, strip punctuation except slashes."""
    text = text.strip().lower()
    # Keep /command intact but strip trailing punctuation
    text = re.sub(r'[?!.,;:]+$', '', text)
    return text


def _exact_alias_match(text: str, intents: list[dict]) -> tuple[str, str] | None:
    """Check if text exactly matches any intent alias."""
    for intent in intents:
        for alias in intent.get("aliases", []):
            if text == alias.lower():
                return (intent["handler"], intent["id"])
    return None


def _keyword_match(text: str, intents: list[dict]) -> tuple[str, float, str] | None:
    """Score text against intent keywords. Returns best match above threshold."""
    tokens = set(re.findall(r'\w+', text))

    best: tuple[str, float, str] | None = None
    best_score = 0.0

    for intent in intents:
        keywords = intent.get("keywords", [])
        if not keywords:
            continue

        matched = 0
        for kw in keywords:
            kw_tokens = set(re.findall(r'\w+', kw.lower()))
            if kw_tokens.issubset(tokens):
                matched += 1

        if matched == 0:
            continue

        # Score: ratio of matched keywords, scaled to 0.7-0.9 range
        ratio = matched / len(keywords)
        score = 0.7 + (ratio * 0.2)

        if score > best_score:
            best_score = score
            best = (intent["handler"], score, intent["id"])

    if best and best_score >= 0.7:
        return best
    return None


def _similarity_match(text: str, intents: list[dict]) -> tuple[str, float, str] | None:
    """Token overlap against intent examples. Returns best match above threshold."""
    text_tokens = set(re.findall(r'\w+', text.lower()))
    if not text_tokens:
        return None

    best: tuple[str, float, str] | None = None
    best_score = 0.0

    for intent in intents:
        examples = intent.get("examples", [])
        if not examples:
            continue

        max_overlap = 0.0
        for example in examples:
            ex_tokens = set(re.findall(r'\w+', example.lower()))
            if not ex_tokens:
                continue
            overlap = len(text_tokens & ex_tokens) / max(len(text_tokens), len(ex_tokens))
            if overlap > max_overlap:
                max_overlap = overlap

        # Scale to 0.3-0.6 range
        score = 0.3 + (max_overlap * 0.3)

        if score > best_score:
            best_score = score
            best = (intent["handler"], score, intent["id"])

    if best and best_score >= 0.4:
        return best
    return None
