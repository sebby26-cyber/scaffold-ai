"""
ai_persistence.py — Continuous state persistence.

Handles auto-flush on state-changing events and force-sync combining
flush + checkpoint + optional git-sync.
"""

from __future__ import annotations

import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


_last_flush_ts: float = 0.0


def load_persistence_config(project_root: Path) -> dict:
    """Load persistence.yaml from canonical state."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "persistence.yaml"
        if path.exists() and yaml is not None:
            try:
                return yaml.safe_load(path.read_text()) or {}
            except Exception:
                pass
    return {
        "auto_flush": {
            "on_task_transition": True,
            "on_decision_recorded": True,
            "on_worker_status_change": True,
            "debounce_seconds": 5,
        },
        "force_sync_includes_git": False,
    }


_EVENT_TO_CONFIG_KEY = {
    "task_transition": "on_task_transition",
    "decision_recorded": "on_decision_recorded",
    "worker_status_change": "on_worker_status_change",
}


def should_flush(event_type: str, project_root: Path) -> bool:
    """Check if an event type should trigger auto-flush, respecting debounce."""
    global _last_flush_ts

    config = load_persistence_config(project_root)
    auto = config.get("auto_flush", {})

    config_key = _EVENT_TO_CONFIG_KEY.get(event_type)
    if config_key and not auto.get(config_key, True):
        return False

    debounce = auto.get("debounce_seconds", 5)
    now = time.time()
    if now - _last_flush_ts < debounce:
        return False

    return True


def auto_flush(project_root: Path, event_type: str) -> bool:
    """If should_flush, reconcile canonical state + write STATUS.md. Returns True if flushed."""
    global _last_flush_ts

    if not should_flush(event_type, project_root):
        return False

    from . import ai_state

    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

    try:
        ai_state.reconcile(ai_dir, runtime_dir)
        # Re-render STATUS.md
        ai_state.render_status(ai_dir, runtime_dir)
        _last_flush_ts = time.time()
        return True
    except Exception:
        return False


def force_sync(project_root: Path, git_sync: bool = False) -> str:
    """Force flush + checkpoint all workers + optional git-sync.

    Returns formatted status message.
    """
    from . import ai_state, ai_recovery

    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"
    results = []

    # 1. Reconcile state
    try:
        updated = ai_state.reconcile(ai_dir, runtime_dir)
        results.append(f"State reconciled: {'updated' if updated else 'already in sync'}")
    except Exception as e:
        results.append(f"State reconcile failed: {e}")

    # 2. Re-render STATUS.md
    try:
        ai_state.render_status(ai_dir, runtime_dir)
        results.append("STATUS.md updated.")
    except Exception as e:
        results.append(f"STATUS.md render failed: {e}")

    # 3. Checkpoint all active workers
    registry_path = runtime_dir / "workers" / "registry.json"
    if registry_path.exists():
        import json
        try:
            registry = json.loads(registry_path.read_text())
            checkpointed = 0
            for w in registry.get("workers", []):
                if w.get("status") in ("ready", "running", "resuming"):
                    ai_recovery.write_checkpoint(project_root, w["worker_id"], {
                        "progress_summary": "Force sync checkpoint",
                    })
                    checkpointed += 1
            if checkpointed:
                results.append(f"Checkpointed {checkpointed} active worker(s).")
        except Exception as e:
            results.append(f"Worker checkpoint failed: {e}")

    # 4. Optional git-sync
    if git_sync:
        from . import ai_git
        try:
            ok, msg = ai_git.git_sync(project_root, message="Force sync")
            results.append(f"Git sync: {msg}")
        except Exception as e:
            results.append(f"Git sync failed: {e}")
    else:
        results.append("Git sync: skipped (opt-in via force_sync_includes_git in persistence.yaml)")

    return "\n".join(results)
