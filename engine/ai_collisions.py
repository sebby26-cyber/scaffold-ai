"""
ai_collisions.py — File ownership matrix and collision detection.

Prevents multiple workers from editing the same files by comparing
allowed_files globs across active tickets before spawning.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


def build_ownership_matrix(tickets: list[dict]) -> dict[str, list[str]]:
    """Build {glob_pattern: [ticket_ids]} from allowed_files across tickets."""
    matrix: dict[str, list[str]] = {}
    for t in tickets:
        tid = t.get("ticket_id", "?")
        for pattern in t.get("allowed_files", []):
            matrix.setdefault(pattern, []).append(tid)
    return matrix


def detect_collisions(tickets: list[dict], project_root: Path) -> list[dict]:
    """Compare glob expansions across tickets using fnmatch.

    Returns [{file_pattern, conflicting_tickets, severity}].
    Severity: "hard" if both are prod tickets, "soft" if test/docs overlap.
    """
    collisions: list[dict] = []
    if len(tickets) < 2:
        return collisions

    # Build per-ticket expanded patterns
    ticket_patterns: list[tuple[str, list[str], str]] = []
    for t in tickets:
        tid = t.get("ticket_id", "?")
        ttype = t.get("ticket_type", "prod")
        patterns = t.get("allowed_files", [])
        ticket_patterns.append((tid, patterns, ttype))

    # Compare each pair
    seen: set[tuple[str, str]] = set()
    for i in range(len(ticket_patterns)):
        tid_a, pats_a, type_a = ticket_patterns[i]
        for j in range(i + 1, len(ticket_patterns)):
            tid_b, pats_b, type_b = ticket_patterns[j]
            pair_key = (min(tid_a, tid_b), max(tid_a, tid_b))
            if pair_key in seen:
                continue

            overlaps = _find_overlapping_patterns(pats_a, pats_b)
            if overlaps:
                seen.add(pair_key)
                severity = "hard" if type_a == "prod" and type_b == "prod" else "soft"
                for overlap in overlaps:
                    collisions.append({
                        "file_pattern": overlap,
                        "conflicting_tickets": [tid_a, tid_b],
                        "severity": severity,
                    })

    return collisions


def _find_overlapping_patterns(pats_a: list[str], pats_b: list[str]) -> list[str]:
    """Find patterns from two lists that could match the same files."""
    overlaps: list[str] = []
    for pa in pats_a:
        for pb in pats_b:
            if _patterns_overlap(pa, pb):
                overlaps.append(f"{pa} <-> {pb}")
    return overlaps


def _patterns_overlap(pa: str, pb: str) -> bool:
    """Heuristic: two glob patterns overlap if one matches the other or share prefix."""
    # Direct match
    if pa == pb:
        return True
    # One is a wildcard superset of the other
    if fnmatch.fnmatch(pa, pb) or fnmatch.fnmatch(pb, pa):
        return True
    # Both are directory wildcards with overlapping prefixes
    # e.g., "src/**" and "src/utils/**"
    pa_base = pa.split("*")[0].rstrip("/")
    pb_base = pb.split("*")[0].rstrip("/")
    if pa_base and pb_base:
        if pa_base.startswith(pb_base) or pb_base.startswith(pa_base):
            return True
    return False


def format_collision_report(collisions: list[dict]) -> str:
    """Human-readable collision report."""
    if not collisions:
        return "No file collisions detected."

    lines = [f"FILE COLLISIONS DETECTED ({len(collisions)}):\n"]
    for c in collisions:
        severity = c["severity"].upper()
        tickets = " vs ".join(c["conflicting_tickets"])
        lines.append(f"  [{severity}] {tickets}")
        lines.append(f"         Pattern: {c['file_pattern']}")
        if c["severity"] == "hard":
            lines.append("         Action: Split files or merge tickets before spawning")
        else:
            lines.append("         Action: Review overlap — may be acceptable for test/docs")
        lines.append("")

    return "\n".join(lines)


def precheck_collisions(project_root: Path) -> tuple[bool, str]:
    """Full pre-launch check: load active tickets, detect collisions, format.

    Returns (has_collisions, formatted_report).
    """
    from . import ai_tickets

    tickets = ai_tickets.get_active_tickets(project_root)
    if not tickets:
        return False, "No active tickets to check."

    collisions = detect_collisions(tickets, project_root)
    hard = [c for c in collisions if c["severity"] == "hard"]

    report = format_collision_report(collisions)
    return len(hard) > 0, report
