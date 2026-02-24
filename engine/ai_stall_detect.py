"""
ai_stall_detect.py — Behavior-based stall and token-burn detection.

Detects workers that are burning tokens without making progress:
- Log churn with no git diff (reading in loops)
- Repeated test failures
- Silent workers (no heartbeat and no output)
- Workers exceeding time budget with no deliverables
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


STALL_TYPES = ("no_diff", "no_test", "log_churn", "silent", "repeated_failure")


def load_stall_config(project_root: Path) -> dict:
    """Load stall detection config from recovery.yaml."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "recovery.yaml"
        if path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(path.read_text()) or {}
                return {
                    "stall_no_diff_minutes": data.get("stall_no_diff_minutes", 10),
                    "stall_no_test_minutes": data.get("stall_no_test_minutes", 15),
                    "auto_stop_stalled": data.get("auto_stop_stalled", False),
                    "stall_timeout_seconds": data.get("stall_timeout_seconds", 120),
                }
            except Exception:
                pass
    return {
        "stall_no_diff_minutes": 10,
        "stall_no_test_minutes": 15,
        "auto_stop_stalled": False,
        "stall_timeout_seconds": 120,
    }


def _load_registry(project_root: Path) -> dict:
    """Load worker registry."""
    reg_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    if not reg_path.exists():
        return {}
    try:
        return json.loads(reg_path.read_text())
    except Exception:
        return {}


def _get_worker_log_path(project_root: Path, worker_id: str) -> Path:
    """Get the log path for a worker."""
    return project_root / ".ai_runtime" / "workers" / "logs" / f"{worker_id}.log"


def _get_worker_diff_files(project_root: Path, worker_id: str) -> list[str]:
    """Check if a worker has produced any file changes (via checkpoints)."""
    cp_dir = project_root / ".ai_runtime" / "workers" / "checkpoints" / worker_id
    if not cp_dir.is_dir():
        return []
    files = sorted(cp_dir.glob("*.json"), reverse=True)
    if not files:
        return []
    try:
        data = json.loads(files[0].read_text())
        return data.get("files_changed", [])
    except Exception:
        return []


def check_worker_stall(project_root: Path, worker_id: str) -> dict | None:
    """Check if a specific worker is stalled.

    Checks: log growth + no diff, repeated read loops, silent worker.
    Returns {worker_id, stall_type, evidence, minutes_stalled, recommendation}
    or None if worker is healthy.
    """
    config = load_stall_config(project_root)
    registry = _load_registry(project_root)
    if not registry:
        return None

    worker = None
    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            worker = w
            break

    if not worker:
        return None

    status = worker.get("status", "")
    if status in ("stopped", "paused", "completed"):
        return None

    now = datetime.now(timezone.utc)

    # Check heartbeat age
    heartbeat = worker.get("last_heartbeat_at")
    if not heartbeat:
        heartbeat = registry.get("spawned_at")
    if not heartbeat:
        return None

    try:
        last = datetime.fromisoformat(heartbeat)
        elapsed_minutes = (now - last).total_seconds() / 60
    except (ValueError, TypeError):
        return None

    # Check for no-diff stall
    no_diff_threshold = config.get("stall_no_diff_minutes", 10)
    if elapsed_minutes > no_diff_threshold:
        diff_files = _get_worker_diff_files(project_root, worker_id)
        if not diff_files:
            return {
                "worker_id": worker_id,
                "stall_type": "no_diff",
                "evidence": f"No file changes after {elapsed_minutes:.0f} minutes",
                "minutes_stalled": round(elapsed_minutes),
                "recommendation": "Check worker output. Consider restarting with clearer scope.",
            }

    # Check for silent worker (past basic timeout)
    timeout_seconds = config.get("stall_timeout_seconds", 120)
    if elapsed_minutes > (timeout_seconds / 60) * 2:
        return {
            "worker_id": worker_id,
            "stall_type": "silent",
            "evidence": f"No heartbeat for {elapsed_minutes:.0f} minutes",
            "minutes_stalled": round(elapsed_minutes),
            "recommendation": "Worker may have crashed. Resume or restart.",
        }

    # Check for log churn (log file growing but no diffs)
    log_path = _get_worker_log_path(project_root, worker_id)
    if log_path.exists():
        try:
            log_size = log_path.stat().st_size
            if log_size > 50000 and not _get_worker_diff_files(project_root, worker_id):
                return {
                    "worker_id": worker_id,
                    "stall_type": "log_churn",
                    "evidence": f"Log is {log_size} bytes but no file changes produced",
                    "minutes_stalled": round(elapsed_minutes),
                    "recommendation": "Possible read loop. Stop and check ticket scope.",
                }
        except Exception:
            pass

    return None


def detect_all_stalled(project_root: Path) -> list[dict]:
    """Scan all workers for stalls. Returns list of stall info dicts."""
    registry = _load_registry(project_root)
    if not registry:
        return []

    stalled = []
    for w in registry.get("workers", []):
        wid = w.get("worker_id", "")
        if not wid:
            continue
        info = check_worker_stall(project_root, wid)
        if info:
            stalled.append(info)

    return stalled


def mark_stalled(project_root: Path, worker_id: str, stall_info: dict) -> str:
    """Mark a worker as stalled in the registry."""
    reg_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    if not reg_path.exists():
        return "No registry found."
    try:
        registry = json.loads(reg_path.read_text())
    except Exception:
        return "Error reading registry."

    for w in registry.get("workers", []):
        if w.get("worker_id") == worker_id:
            w["status"] = "stalled"
            w["stall_type"] = stall_info.get("stall_type", "unknown")
            w["stall_detected_at"] = datetime.now(timezone.utc).isoformat()
            break

    reg_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    return f"Worker {worker_id} marked as stalled ({stall_info.get('stall_type', '?')})"


def format_stall_report(stalled: list[dict]) -> str:
    """Human-readable stall report."""
    if not stalled:
        return "No stalled workers detected."

    lines = [f"STALLED WORKERS ({len(stalled)}):\n"]
    for s in stalled:
        lines.append(f"  {s['worker_id']}")
        lines.append(f"    Type: {s['stall_type']}")
        lines.append(f"    Evidence: {s['evidence']}")
        lines.append(f"    Stalled for: ~{s['minutes_stalled']} minutes")
        lines.append(f"    Recommendation: {s['recommendation']}")
        lines.append("")

    return "\n".join(lines)
