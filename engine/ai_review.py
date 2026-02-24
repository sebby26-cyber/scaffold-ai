"""
ai_review.py — Reviewer input staging, bundle generation, output classification.

Handles:
- Staging worker outputs for review (diffs, summaries, artifacts)
- Generating review manifests with batch metadata
- Classifying reviewer comments (advisory, actionable, speculative)
- Determining if reviewer output is safe to commit
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Keywords for classifying reviewer output
ACTIONABLE_KEYWORDS = (
    "must fix", "bug:", "required:", "blocker:", "critical:",
    "security:", "breaks", "will fail", "regression",
    "missing test", "null reference", "undefined",
)
ADVISORY_KEYWORDS = (
    "consider", "suggest", "recommend", "could improve",
    "nice to have", "optional", "minor:", "nit:",
    "future:", "TODO:", "note:",
)
SPECULATIVE_KEYWORDS = (
    "rewrite", "maybe", "what if", "hypothetically",
    "in theory", "might want to", "possibly",
    "could potentially", "it depends",
)


def stage_review_inputs(project_root: Path, batch_id: str | None = None) -> str:
    """Create review staging bundle from completed worker outputs.

    Creates .ai_runtime/review_staging/<batch_id>/
    Bundle: manifest.yaml + per-ticket diffs/summaries/artifacts.
    Returns formatted summary.
    """
    from . import ai_tickets

    if batch_id is None:
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    staging_dir = project_root / ".ai_runtime" / "review_staging" / batch_id
    staging_dir.mkdir(parents=True, exist_ok=True)

    tickets = ai_tickets.load_all_tickets(project_root)
    review_tickets = [t for t in tickets if t.get("status") in ("review", "done")]

    if not review_tickets:
        return "No tickets in review/done status to stage."

    manifest = generate_review_manifest(project_root, batch_id, review_tickets)

    # Write manifest
    if yaml is not None:
        manifest_path = staging_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest, default_flow_style=False, sort_keys=False))

    # Stage per-ticket artifacts
    for t in review_tickets:
        tid = t.get("ticket_id", "unknown")
        ticket_dir = staging_dir / tid
        ticket_dir.mkdir(exist_ok=True)

        # Write ticket summary
        summary = {
            "ticket_id": tid,
            "ticket_type": t.get("ticket_type", "?"),
            "objective": t.get("objective", "?"),
            "allowed_files": t.get("allowed_files", []),
            "status": t.get("status", "?"),
            "role": t.get("role", "?"),
        }
        (ticket_dir / "summary.yaml").write_text(
            yaml.dump(summary, default_flow_style=False, sort_keys=False)
            if yaml else json.dumps(summary, indent=2)
        )

        # Copy worker checkpoint if available
        cp_dir = project_root / ".ai_runtime" / "workers" / "checkpoints" / tid
        if cp_dir.is_dir():
            cps = sorted(cp_dir.glob("*.json"), reverse=True)
            if cps:
                import shutil
                shutil.copy2(str(cps[0]), str(ticket_dir / "checkpoint.json"))

    lines = [
        f"Review staging created: {staging_dir}",
        f"Batch: {batch_id}",
        f"Tickets staged: {len(review_tickets)}",
    ]
    for t in review_tickets:
        lines.append(f"  - {t.get('ticket_id', '?')} ({t.get('ticket_type', '?')})")

    return "\n".join(lines)


def generate_review_manifest(
    project_root: Path,
    batch_id: str,
    tickets: list[dict],
) -> dict:
    """Generate review manifest with batch metadata."""
    return {
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket_ids": [t.get("ticket_id", "?") for t in tickets],
        "ticket_count": len(tickets),
        "commit_base": _get_git_ref(project_root, "HEAD~1"),
        "commit_head": _get_git_ref(project_root, "HEAD"),
    }


def _get_git_ref(project_root: Path, ref: str) -> str:
    """Get a git ref safely."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", ref],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def classify_reviewer_output(comment: str) -> str:
    """Classify a reviewer comment by keyword heuristics.

    Returns: "actionable" | "advisory" | "speculative"
    """
    lower = comment.lower()

    # Check actionable first (highest priority)
    for kw in ACTIONABLE_KEYWORDS:
        if kw in lower:
            return "actionable"

    # Check speculative (catch before advisory)
    for kw in SPECULATIVE_KEYWORDS:
        if kw in lower:
            return "speculative"

    # Check advisory
    for kw in ADVISORY_KEYWORDS:
        if kw in lower:
            return "advisory"

    # Default to advisory for unclassified
    return "advisory"


def is_safe_to_commit(classification: str) -> bool:
    """Determine if a reviewer output classification is safe to commit.

    Speculative comments should NOT be committed as-is.
    """
    return classification != "speculative"
