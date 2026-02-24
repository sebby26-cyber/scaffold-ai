"""
ai_compaction.py — Provider-agnostic context compaction protocol.

Implements a skeleton-level compaction/checkpoint protocol that works
regardless of provider CLI:

- Canonical checkpoint artifact schema
- Periodic compaction triggers (time-based, size-based, stall-risk)
- Provider adapter layer for native compaction commands
- Fallback to skeleton-generated checkpoint/handoff summary

Goal: prevent long-context workers from failing silently or wasting tokens,
and make worker replacement/resume deterministic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Canonical checkpoint artifact schema version
CHECKPOINT_SCHEMA_VERSION = "1.0"

# Default compaction trigger thresholds
DEFAULT_COMPACTION_CONFIG = {
    "time_interval_minutes": 15,
    "max_context_tokens_estimate": 80000,
    "stall_risk_minutes": 10,
    "auto_compact": True,
}

# Provider-specific compaction commands (if supported)
PROVIDER_COMPACT_COMMANDS = {
    "claude": "/compact",
    "codex": None,  # No native compaction
    "gemini": None,  # No native compaction
    "cursor": None,  # No native compaction
}


def load_compaction_config(project_root: Path) -> dict:
    """Load compaction config from recovery.yaml or defaults."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "recovery.yaml"
        if path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(path.read_text()) or {}
                return {
                    "time_interval_minutes": data.get(
                        "compaction_interval_minutes",
                        DEFAULT_COMPACTION_CONFIG["time_interval_minutes"],
                    ),
                    "max_context_tokens_estimate": data.get(
                        "max_context_tokens_estimate",
                        DEFAULT_COMPACTION_CONFIG["max_context_tokens_estimate"],
                    ),
                    "stall_risk_minutes": data.get(
                        "stall_no_diff_minutes",
                        DEFAULT_COMPACTION_CONFIG["stall_risk_minutes"],
                    ),
                    "auto_compact": data.get(
                        "auto_compact",
                        DEFAULT_COMPACTION_CONFIG["auto_compact"],
                    ),
                }
            except Exception:
                pass
    return dict(DEFAULT_COMPACTION_CONFIG)


def generate_checkpoint_artifact(
    project_root: Path,
    worker_id: str,
    objective: str = "",
    completed_steps: list[str] | None = None,
    changed_files: list[str] | None = None,
    pending_steps: list[str] | None = None,
    assumptions: list[str] | None = None,
    blockers: list[str] | None = None,
) -> dict:
    """Generate a canonical checkpoint artifact.

    Schema:
    - schema_version
    - worker_id
    - timestamp
    - current_objective
    - completed_steps
    - changed_files
    - pending_steps
    - assumptions
    - blockers
    - resume_command
    """
    from . import ai_recovery, ai_providers

    # Load worker info for resume command
    resume_cmd = ""
    reg_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    if reg_path.exists():
        try:
            registry = json.loads(reg_path.read_text())
            for w in registry.get("workers", []):
                if w.get("worker_id") == worker_id:
                    provider = w.get("provider", "")
                    cli = ai_providers.get_cli_command(provider, project_root)
                    model_arg = ai_providers.get_model_arg(provider, project_root)
                    model = w.get("model", "")
                    prompt_path = w.get("prompt_path", "")
                    parts = [cli, "--prompt", prompt_path]
                    if model_arg and model and model != "default":
                        parts.extend([model_arg, model])
                    resume_cmd = " ".join(parts)
                    break
        except Exception:
            pass

    artifact = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "worker_id": worker_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_objective": objective,
        "completed_steps": completed_steps or [],
        "changed_files": changed_files or [],
        "pending_steps": pending_steps or [],
        "assumptions": assumptions or [],
        "blockers": blockers or [],
        "resume_command": resume_cmd,
    }

    return artifact


def save_checkpoint_artifact(project_root: Path, artifact: dict) -> Path:
    """Save checkpoint artifact to runtime and canonical locations."""
    worker_id = artifact.get("worker_id", "unknown")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Runtime checkpoint
    rt_dir = project_root / ".ai_runtime" / "workers" / "checkpoints" / worker_id
    rt_dir.mkdir(parents=True, exist_ok=True)
    rt_path = rt_dir / f"{ts}_compact.json"
    rt_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))

    # Canonical checkpoint (portable)
    canon_dir = project_root / ".ai" / "workers" / "checkpoints" / worker_id
    canon_dir.mkdir(parents=True, exist_ok=True)
    canon_path = canon_dir / f"{ts}_compact.json"
    canon_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))

    return rt_path


def should_compact(
    project_root: Path,
    worker_id: str,
    elapsed_minutes: float = 0,
    estimated_tokens: int = 0,
) -> tuple[bool, str]:
    """Check if compaction should be triggered.

    Returns (should_compact, reason).
    """
    config = load_compaction_config(project_root)

    # Time-based trigger
    interval = config.get("time_interval_minutes", 15)
    if elapsed_minutes >= interval:
        return True, f"Time interval reached ({elapsed_minutes:.0f} >= {interval} minutes)"

    # Token/size-based trigger
    max_tokens = config.get("max_context_tokens_estimate", 80000)
    if estimated_tokens > 0 and estimated_tokens >= max_tokens:
        return True, f"Token estimate reached ({estimated_tokens} >= {max_tokens})"

    # Stall-risk trigger
    stall_risk = config.get("stall_risk_minutes", 10)
    from . import ai_stall_detect
    stall = ai_stall_detect.check_worker_stall(project_root, worker_id)
    if stall:
        return True, f"Stall risk detected: {stall['stall_type']}"

    return False, "No compaction needed"


def get_provider_compact_command(provider: str) -> str | None:
    """Get native compaction command for a provider, if supported."""
    return PROVIDER_COMPACT_COMMANDS.get(provider.lower())


def generate_handoff_summary(artifact: dict) -> str:
    """Generate a human-readable handoff summary from a checkpoint artifact.

    Used as fallback when provider has no native compaction.
    """
    lines = [
        "# CONTEXT COMPACTION — Handoff Summary",
        "",
        f"Worker: {artifact.get('worker_id', '?')}",
        f"Timestamp: {artifact.get('timestamp', '?')}",
        "",
        "## Current Objective",
        artifact.get("current_objective", "(not set)"),
        "",
    ]

    completed = artifact.get("completed_steps", [])
    if completed:
        lines.append("## Completed Steps")
        for s in completed:
            lines.append(f"- {s}")
        lines.append("")

    changed = artifact.get("changed_files", [])
    if changed:
        lines.append("## Changed Files")
        for f in changed:
            lines.append(f"- {f}")
        lines.append("")

    pending = artifact.get("pending_steps", [])
    if pending:
        lines.append("## Pending Steps")
        for s in pending:
            lines.append(f"- {s}")
        lines.append("")

    assumptions = artifact.get("assumptions", [])
    if assumptions:
        lines.append("## Assumptions")
        for a in assumptions:
            lines.append(f"- {a}")
        lines.append("")

    blockers = artifact.get("blockers", [])
    if blockers:
        lines.append("## Blockers")
        for b in blockers:
            lines.append(f"- {b}")
        lines.append("")

    resume = artifact.get("resume_command", "")
    if resume:
        lines.append("## Resume Command")
        lines.append(f"```\n{resume}\n```")
        lines.append("")

    lines.append("## Instructions")
    lines.append("Continue from the pending steps above.")
    lines.append("Do not repeat completed work.")

    return "\n".join(lines)


def validate_checkpoint_artifact(artifact: dict) -> list[str]:
    """Validate a checkpoint artifact against the schema."""
    errors: list[str] = []
    required = ["schema_version", "worker_id", "timestamp"]
    for field in required:
        if field not in artifact:
            errors.append(f"Missing required field: {field}")

    if artifact.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        errors.append(
            f"Unknown schema version: {artifact.get('schema_version')} "
            f"(expected {CHECKPOINT_SCHEMA_VERSION})"
        )

    for field in ["completed_steps", "changed_files", "pending_steps", "assumptions", "blockers"]:
        val = artifact.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"{field} must be a list, got {type(val).__name__}")

    return errors
