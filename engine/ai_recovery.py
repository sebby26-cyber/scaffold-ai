"""
ai_recovery.py — Worker hang/token-limit recovery.

Handles:
- Heartbeat updates and stall detection
- Checkpoint writes to .ai_runtime/workers/checkpoints/<worker_id>/
- Resume prompt generation from last checkpoint
- Worker restart orchestration
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_recovery_config(project_root: Path) -> dict:
    """Load recovery.yaml from canonical state."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "recovery.yaml"
        if path.exists() and yaml is not None:
            try:
                return yaml.safe_load(path.read_text()) or {}
            except Exception:
                pass
    return {
        "stall_timeout_seconds": 120,
        "max_retries": 3,
        "checkpoint_enabled": True,
    }


def _load_registry(project_root: Path) -> tuple[dict, Path]:
    """Load worker registry. Returns (registry_dict, registry_path)."""
    registry_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    if not registry_path.exists():
        return {}, registry_path
    try:
        return json.loads(registry_path.read_text()), registry_path
    except Exception:
        return {}, registry_path


def _save_registry(registry: dict, registry_path: Path) -> None:
    """Write registry back to disk."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))


def update_heartbeat(project_root: Path, worker_id: str) -> None:
    """Update last_heartbeat_at in registry.json for a worker."""
    registry, path = _load_registry(project_root)
    if not registry:
        return
    now = datetime.now(timezone.utc).isoformat()
    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            w["last_heartbeat_at"] = now
            break
    _save_registry(registry, path)


def detect_stalled_workers(project_root: Path) -> list[dict]:
    """Compare last_heartbeat_at against stall_timeout. Return list of stalled worker dicts."""
    config = load_recovery_config(project_root)
    timeout = config.get("stall_timeout_seconds", 120)

    registry, _ = _load_registry(project_root)
    if not registry:
        return []

    now = datetime.now(timezone.utc)
    stalled = []

    for w in registry.get("workers", []):
        status = w.get("status", "")
        if status in ("stopped", "paused", "completed"):
            continue

        heartbeat = w.get("last_heartbeat_at")
        if not heartbeat:
            # No heartbeat yet — check spawn time
            heartbeat = registry.get("spawned_at")
        if not heartbeat:
            continue

        try:
            last = datetime.fromisoformat(heartbeat)
            elapsed = (now - last).total_seconds()
            if elapsed > timeout:
                stalled.append(w)
        except (ValueError, TypeError):
            continue

    return stalled


def write_checkpoint(project_root: Path, worker_id: str, checkpoint_data: dict | None = None) -> str:
    """Write checkpoint to .ai_runtime/workers/checkpoints/<worker_id>/<timestamp>.json.

    Returns checkpoint_id.
    """
    now = datetime.now(timezone.utc)
    checkpoint_id = now.strftime("%Y%m%d_%H%M%S")

    cp_dir = project_root / ".ai_runtime" / "workers" / "checkpoints" / worker_id
    cp_dir.mkdir(parents=True, exist_ok=True)

    data = checkpoint_data or {}
    data.setdefault("checkpoint_id", checkpoint_id)
    data.setdefault("worker_id", worker_id)
    data.setdefault("timestamp", now.isoformat())

    # Pull current worker info from registry
    registry, reg_path = _load_registry(project_root)
    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            data.setdefault("role", w.get("role", ""))
            data.setdefault("provider", w.get("provider", ""))
            data.setdefault("model", w.get("model", ""))
            data.setdefault("prompt_path", w.get("prompt_path", ""))
            # Update registry with checkpoint ref
            w["last_checkpoint_id"] = checkpoint_id
            _save_registry(registry, reg_path)
            break

    cp_path = cp_dir / f"{checkpoint_id}.json"
    cp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    return checkpoint_id


def load_latest_checkpoint(project_root: Path, worker_id: str) -> dict | None:
    """Load the most recent checkpoint for a worker. Returns None if no checkpoint."""
    cp_dir = project_root / ".ai_runtime" / "workers" / "checkpoints" / worker_id
    if not cp_dir.is_dir():
        return None

    files = sorted(cp_dir.glob("*.json"), reverse=True)
    if not files:
        return None

    try:
        return json.loads(files[0].read_text())
    except Exception:
        return None


def build_resume_prompt(project_root: Path, worker_id: str) -> str:
    """Read latest checkpoint + original prompt, build a resume prompt with context."""
    checkpoint = load_latest_checkpoint(project_root, worker_id)

    # Load original prompt
    original_prompt = ""
    if checkpoint and checkpoint.get("prompt_path"):
        prompt_path = Path(checkpoint["prompt_path"])
        if prompt_path.exists():
            original_prompt = prompt_path.read_text()

    lines = ["# RESUME SESSION\n"]
    lines.append("You are resuming a previous work session that was interrupted.\n")

    if checkpoint:
        lines.append(f"## Previous State")
        lines.append(f"- Worker: {checkpoint.get('worker_id', '?')}")
        lines.append(f"- Role: {checkpoint.get('role', '?')}")
        lines.append(f"- Last checkpoint: {checkpoint.get('timestamp', '?')}")
        if checkpoint.get("progress_summary"):
            lines.append(f"- Progress: {checkpoint['progress_summary']}")
        if checkpoint.get("next_steps"):
            lines.append(f"- Next steps: {checkpoint['next_steps']}")
        lines.append("")

    if original_prompt:
        lines.append("## Original Role Prompt")
        lines.append(original_prompt)
        lines.append("")

    lines.append("## Instructions")
    lines.append("Continue from where the previous session left off.")
    lines.append("Do not repeat already-completed work.")

    return "\n".join(lines)


def resume_worker(project_root: Path, worker_id: str) -> str:
    """Full resume flow: load checkpoint -> build resume prompt -> update registry.

    Returns formatted instructions for the user to run.
    """
    from . import ai_providers

    config = load_recovery_config(project_root)
    max_retries = config.get("max_retries", 3)

    registry, reg_path = _load_registry(project_root)
    if not registry:
        return "No worker registry found. Spawn workers first."

    worker = None
    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            worker = w
            break

    if not worker:
        return f"Worker '{worker_id}' not found in registry."

    retries = worker.get("retry_count", 0)
    if retries >= max_retries:
        return (
            f"Worker '{worker_id}' has exceeded max retries ({max_retries}).\n"
            "Manual intervention required. Check the checkpoint data and restart manually."
        )

    # Write checkpoint before resume
    if config.get("checkpoint_enabled", True):
        write_checkpoint(project_root, worker_id, {
            "progress_summary": "Interrupted — resuming",
        })

    # Build resume prompt
    resume_prompt = build_resume_prompt(project_root, worker_id)

    # Write resume prompt to runtime
    prompts_dir = project_root / ".ai_runtime" / "workers" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    resume_path = prompts_dir / f"{worker_id}_resume.md"
    resume_path.write_text(resume_prompt)

    # Get CLI command
    provider = worker.get("provider", "")
    cli = ai_providers.get_cli_command(provider, project_root)
    model_arg = ai_providers.get_model_arg(provider, project_root)
    model = worker.get("model", "")

    cmd_parts = [cli, "--prompt", str(resume_path)]
    if model_arg and model and model != "default":
        cmd_parts.extend([model_arg, model])
    cmd = " ".join(cmd_parts)

    # Update registry
    worker["status"] = "resuming"
    worker["retry_count"] = retries + 1
    _save_registry(registry, reg_path)

    return (
        f"Resuming worker '{worker_id}' (attempt {retries + 1}/{max_retries}):\n"
        f"  Resume prompt: {resume_path}\n"
        f"  Run: {cmd}\n"
    )


def pause_worker(project_root: Path, worker_id: str) -> str:
    """Mark worker as paused in registry, write checkpoint."""
    config = load_recovery_config(project_root)

    registry, reg_path = _load_registry(project_root)
    if not registry:
        return "No worker registry found."

    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            w["status"] = "paused"
            _save_registry(registry, reg_path)
            if config.get("checkpoint_enabled", True):
                cp_id = write_checkpoint(project_root, worker_id, {
                    "progress_summary": "Paused by user",
                })
                return f"Worker '{worker_id}' paused. Checkpoint: {cp_id}"
            return f"Worker '{worker_id}' paused."

    return f"Worker '{worker_id}' not found in registry."


def restart_worker(project_root: Path, worker_id: str) -> str:
    """Full restart: checkpoint -> reset retries -> fresh spawn instructions."""
    from . import ai_providers

    config = load_recovery_config(project_root)

    registry, reg_path = _load_registry(project_root)
    if not registry:
        return "No worker registry found."

    worker = None
    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            worker = w
            break

    if not worker:
        return f"Worker '{worker_id}' not found in registry."

    # Checkpoint before restart
    if config.get("checkpoint_enabled", True):
        write_checkpoint(project_root, worker_id, {
            "progress_summary": "Restarted by user",
        })

    # Reset retry count
    worker["status"] = "ready"
    worker["retry_count"] = 0
    _save_registry(registry, reg_path)

    # Get CLI command
    provider = worker.get("provider", "")
    cli = ai_providers.get_cli_command(provider, project_root)
    model_arg = ai_providers.get_model_arg(provider, project_root)
    model = worker.get("model", "")
    prompt_path = worker.get("prompt_path", "")

    cmd_parts = [cli, "--prompt", prompt_path]
    if model_arg and model and model != "default":
        cmd_parts.extend([model_arg, model])
    cmd = " ".join(cmd_parts)

    return (
        f"Worker '{worker_id}' restarted (retries reset).\n"
        f"  Run: {cmd}\n"
    )
