"""
ai_compat.py — Compatibility checker and skeleton version lock.

Verifies that all advertised capabilities have matching engine handlers.
Used by bootstrap step 2 to gate readiness on compatibility.
Also manages skeleton_lock.yaml for safe update detection.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def load_advertised_capabilities(project_root: Path) -> list[dict]:
    """Load capabilities_advertised.yaml from canonical state or templates."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "capabilities_advertised.yaml"
        if path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(path.read_text()) or {}
                return data.get("capabilities", [])
            except Exception:
                pass
    return []


def get_engine_handlers() -> set[str]:
    """Return the set of handler names implemented in the engine."""
    from . import ai_run
    return set(ai_run.HANDLERS.keys())


def check_capabilities(project_root: Path) -> dict:
    """Check advertised capabilities against engine handlers.

    Returns:
        {
            "status": "PASS" | "FAIL",
            "advertised_count": int,
            "implemented_count": int,
            "missing": [{"id": ..., "handler": ..., "aliases": [...]}],
            "extra": [str],  # handlers with no advertised capability
        }
    """
    advertised = load_advertised_capabilities(project_root)
    handlers = get_engine_handlers()

    missing = []
    matched = set()

    for cap in advertised:
        handler_name = cap.get("handler", "")
        if handler_name in handlers:
            matched.add(handler_name)
        else:
            missing.append({
                "id": cap.get("id", "?"),
                "handler": handler_name,
                "aliases": cap.get("aliases", []),
            })

    extra = sorted(handlers - matched)

    return {
        "status": "PASS" if not missing else "FAIL",
        "advertised_count": len(advertised),
        "implemented_count": len(matched),
        "missing": missing,
        "extra": extra,
    }


def format_capabilities_report(result: dict) -> str:
    """Format a human-readable capabilities check report."""
    lines = []
    status = result["status"]
    lines.append(f"Capabilities check: {status}")
    lines.append(
        f"  Advertised: {result['advertised_count']}  "
        f"Implemented: {result['implemented_count']}"
    )

    if result["missing"]:
        lines.append("")
        lines.append("  MISSING capabilities (advertised but no handler):")
        for m in result["missing"]:
            aliases = ", ".join(m["aliases"][:3])
            lines.append(f"    - {m['id']} (handler: {m['handler']})")
            lines.append(f"      Human says: {aliases}")
        lines.append("")
        lines.append("  To fix:")
        lines.append("    A) Upgrade skeleton engine (git submodule update)")
        lines.append("    B) Run 'ai migrate' to apply new templates")
        lines.append("    C) Remove unsupported features from capabilities_advertised.yaml")

    return "\n".join(lines)


# ── Skeleton Version Lock ──


def load_skeleton_lock(project_root: Path) -> dict:
    """Load skeleton_lock.yaml from canonical state."""
    lock_path = project_root / ".ai" / "state" / "skeleton_lock.yaml"
    if lock_path.exists() and yaml is not None:
        try:
            return yaml.safe_load(lock_path.read_text()) or {}
        except Exception:
            pass
    return {}


def write_skeleton_lock(project_root: Path, skeleton_dir: Path) -> dict:
    """Write/update skeleton_lock.yaml with current skeleton version info."""
    from . import ai_git

    version = ai_git.get_skeleton_version(skeleton_dir)
    head = _get_skeleton_head(skeleton_dir)

    lock = {
        "skeleton_version": version,
        "skeleton_commit": head,
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "capabilities_version": "1.0",
    }

    lock_path = project_root / ".ai" / "state" / "skeleton_lock.yaml"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if yaml is not None:
        lock_path.write_text(
            yaml.dump(lock, default_flow_style=False, sort_keys=False)
        )

    return lock


def check_skeleton_update(project_root: Path, skeleton_dir: Path) -> dict:
    """Check if skeleton has been updated since last lock.

    Returns:
        {
            "changed": bool,
            "locked_version": str,
            "locked_commit": str,
            "current_version": str,
            "current_commit": str,
        }
    """
    from . import ai_git

    lock = load_skeleton_lock(project_root)
    current_version = ai_git.get_skeleton_version(skeleton_dir)
    current_commit = _get_skeleton_head(skeleton_dir)

    locked_commit = lock.get("skeleton_commit", "")
    locked_version = lock.get("skeleton_version", "")

    changed = bool(
        locked_commit and current_commit != locked_commit
    )

    return {
        "changed": changed,
        "locked_version": locked_version,
        "locked_commit": locked_commit,
        "current_version": current_version,
        "current_commit": current_commit,
    }


def format_update_report(update: dict) -> str:
    """Format skeleton update check as human-readable text."""
    if not update["changed"]:
        return (
            f"Skeleton version: {update['current_version']} "
            f"(commit: {update['current_commit'][:8]}) — no change since lock."
        )

    return (
        f"SKELETON UPDATED since last lock!\n"
        f"  Locked:  {update['locked_version']} ({update['locked_commit'][:8]})\n"
        f"  Current: {update['current_version']} ({update['current_commit'][:8]})\n"
        f"\n"
        f"  Actions required:\n"
        f"    1. Run 'ai validate --full' to check compatibility\n"
        f"    2. Run 'ai migrate' to apply new templates\n"
        f"    3. Review CAPABILITY_MATRIX.md for changes\n"
        f"  Do NOT proceed without validating."
    )


def run_bootstrap_gate(project_root: Path, skeleton_dir: Path) -> tuple[bool, str]:
    """Run the full bootstrap compatibility gate.

    Returns (ready, message).
    """
    lines = []

    # 1. Capabilities check
    cap_result = check_capabilities(project_root)
    lines.append(format_capabilities_report(cap_result))

    # 2. Skeleton update check
    update = check_skeleton_update(project_root, skeleton_dir)
    lines.append("")
    lines.append(format_update_report(update))

    # 3. If skeleton changed, re-validate
    if update["changed"]:
        lines.append("")
        lines.append("Re-running capabilities check after skeleton update...")
        cap_result = check_capabilities(project_root)
        lines.append(format_capabilities_report(cap_result))

    ready = cap_result["status"] == "PASS"

    if ready:
        # Update lock to current
        write_skeleton_lock(project_root, skeleton_dir)
        lines.append("")
        lines.append("Bootstrap gate: READY")
        lines.append('Type "help" to see what\'s available.')
    else:
        lines.append("")
        lines.append("Bootstrap gate: NOT READY")
        lines.append(
            "Fix missing capabilities before proceeding. "
            "Help and README will not advertise unsupported features."
        )

    return ready, "\n".join(lines)


def _get_skeleton_head(skeleton_dir: Path) -> str:
    """Return the current HEAD commit of the skeleton."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(skeleton_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def get_available_capabilities(project_root: Path) -> list[dict]:
    """Return only capabilities that are actually implemented.

    Used by help/guide to filter out missing features.
    """
    advertised = load_advertised_capabilities(project_root)
    handlers = get_engine_handlers()
    return [cap for cap in advertised if cap.get("handler", "") in handlers]
