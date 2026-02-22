"""
ai_scope.py — Strict scope guardrails.

Reads project.yaml to determine in_scope/out_of_scope rules.
Called before intent execution to warn/block out-of-scope requests.
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_scope(project_root: Path) -> dict:
    """Load project.yaml scope definitions."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "project.yaml"
        if path.exists() and yaml is not None:
            try:
                return yaml.safe_load(path.read_text()) or {}
            except Exception:
                pass
    return {
        "project": {"name": "Unknown", "description": ""},
        "scope": {
            "in_scope": [],
            "out_of_scope": [],
            "enforcement": "off",
        },
    }


def check_scope(text: str, project_root: Path) -> dict:
    """Check if user intent is in scope.

    Returns {in_scope: bool, reason: str, enforcement: str}.

    Logic:
    - If text matches a known intent (from intents.yaml), it is in scope.
    - If text references items from out_of_scope list, flag it.
    - If enforcement is 'off', always returns in_scope=True.
    """
    data = load_scope(project_root)
    scope = data.get("scope", {})
    enforcement = scope.get("enforcement", "off")

    if enforcement == "off":
        return {"in_scope": True, "reason": "Scope enforcement disabled.", "enforcement": "off"}

    # Check if text matches a known intent
    from . import ai_intents
    intent_result = ai_intents.resolve_intent(text, project_root)
    if intent_result and intent_result[1] >= 0.5:
        return {"in_scope": True, "reason": f"Matches known intent: {intent_result[2]}", "enforcement": enforcement}

    # Check against out_of_scope keywords
    text_lower = text.lower()
    for out_item in scope.get("out_of_scope", []):
        # Extract key phrases from the out_of_scope description
        out_tokens = set(re.findall(r'\w+', out_item.lower()))
        text_tokens = set(re.findall(r'\w+', text_lower))
        overlap = len(out_tokens & text_tokens)
        if overlap >= 2 and overlap / len(out_tokens) >= 0.4:
            return {
                "in_scope": False,
                "reason": f"Matches out-of-scope rule: \"{out_item}\"",
                "enforcement": enforcement,
            }

    # Default: in scope if no out-of-scope match
    return {"in_scope": True, "reason": "No out-of-scope rules matched.", "enforcement": enforcement}


def scope_gate(text: str, project_root: Path) -> str | None:
    """Pre-execution scope gate.

    Returns None if allowed, warning/error string if flagged.
    """
    result = check_scope(text, project_root)

    if result["in_scope"]:
        return None

    enforcement = result["enforcement"]
    reason = result["reason"]

    if enforcement == "block":
        return (
            f"Blocked: This request appears outside project scope.\n"
            f"Reason: {reason}\n"
            "Use \"/scope\" to view boundaries, or expand scope with "
            "\"Add this to project scope\"."
        )

    if enforcement == "warn":
        return (
            f"Note: This request may be outside project scope.\n"
            f"Reason: {reason}\n"
            "Proceeding anyway. Use \"/scope\" to review boundaries."
        )

    return None


def format_scope(project_root: Path) -> str:
    """Return formatted scope display."""
    data = load_scope(project_root)
    project = data.get("project", {})
    scope = data.get("scope", {})

    lines = [f"Project: {project.get('name', 'Unknown')}"]
    if project.get("description"):
        lines.append(f"  {project['description']}")
    lines.append("")

    lines.append(f"Enforcement: {scope.get('enforcement', 'off')}")
    lines.append("")

    in_scope = scope.get("in_scope", [])
    if in_scope:
        lines.append("In Scope:")
        for item in in_scope:
            lines.append(f"  + {item}")
        lines.append("")

    out_of_scope = scope.get("out_of_scope", [])
    if out_of_scope:
        lines.append("Out of Scope:")
        for item in out_of_scope:
            lines.append(f"  - {item}")
        lines.append("")

    return "\n".join(lines)
