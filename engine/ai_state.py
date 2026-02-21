"""
ai_state.py — State load/save and reconciliation.

Loads canonical YAML, computes hashes, reconciles with SQLite cache.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from . import ai_db


def _load_yaml(path: Path) -> dict:
    text = path.read_text()
    if yaml:
        return yaml.safe_load(text) or {}
    raise ImportError("PyYAML is required. Install it: pip install pyyaml")


def _save_yaml(path: Path, data: dict):
    if yaml:
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    else:
        raise ImportError("PyYAML is required. Install it: pip install pyyaml")


def compute_canonical_hash(ai_dir: Path) -> str:
    """Compute a hash of all canonical YAML files to detect changes."""
    state_dir = ai_dir / "state"
    h = hashlib.sha256()
    for name in sorted(["team.yaml", "board.yaml", "approvals.yaml", "commands.yaml", "capabilities.yaml"]):
        fpath = state_dir / name
        if fpath.exists():
            h.update(fpath.read_bytes())
    return h.hexdigest()


def load_canonical(ai_dir: Path) -> dict:
    """Load all canonical YAML state files into a single dict."""
    state_dir = ai_dir / "state"
    return {
        "team": _load_yaml(state_dir / "team.yaml"),
        "board": _load_yaml(state_dir / "board.yaml"),
        "approvals": _load_yaml(state_dir / "approvals.yaml"),
        "commands": _load_yaml(state_dir / "commands.yaml"),
    }


def save_canonical(ai_dir: Path, state: dict):
    """Save state dict back to canonical YAML files."""
    state_dir = ai_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    if "team" in state:
        _save_yaml(state_dir / "team.yaml", state["team"])
    if "board" in state:
        _save_yaml(state_dir / "board.yaml", state["board"])
    if "approvals" in state:
        _save_yaml(state_dir / "approvals.yaml", state["approvals"])
    if "commands" in state:
        _save_yaml(state_dir / "commands.yaml", state["commands"])


def reconcile(ai_dir: Path, runtime_dir: Path) -> bool:
    """Reconcile canonical YAML with SQLite DB.

    Returns True if DB was updated, False if already in sync.
    """
    conn = ai_db.connect_db(runtime_dir)
    current_hash = compute_canonical_hash(ai_dir)
    stored_hash = ai_db.get_snapshot(conn, "canonical_hash")

    if stored_hash == current_hash:
        conn.close()
        return False

    # Canonical changed (or first run) — re-ingest
    state = load_canonical(ai_dir)
    ai_db.ingest_team(conn, state["team"])
    ai_db.ingest_board(conn, state["board"])
    ai_db.ingest_approvals(conn, state["approvals"])

    from datetime import datetime, timezone

    ai_db.set_snapshot(conn, "canonical_hash", current_hash)
    ai_db.set_snapshot(conn, "last_ingested_ts", datetime.now(timezone.utc).isoformat())
    ai_db.add_event(conn, "system", "reconcile", {"hash": current_hash})

    conn.close()
    return True


def _load_capabilities(ai_dir: Path) -> dict:
    """Load capabilities.yaml if present."""
    caps_path = ai_dir / "state" / "capabilities.yaml"
    if caps_path.exists() and yaml is not None:
        try:
            return yaml.safe_load(caps_path.read_text()) or {}
        except Exception:
            pass
    return {}


def render_status(ai_dir: Path, runtime_dir: Path) -> str:
    """Render a terminal-friendly status report and update STATUS.md."""
    state = load_canonical(ai_dir)
    board = state["board"]
    team = state["team"]
    approvals = state["approvals"]

    columns = board.get("columns", [])
    tasks = board.get("tasks", [])

    # Count tasks per column
    counts = {col: 0 for col in columns}
    for task in tasks:
        s = task.get("status", "backlog")
        if s in counts:
            counts[s] += 1

    total = len(tasks)
    done = counts.get("done", 0)
    pct = int((done / total * 100)) if total > 0 else 0

    # Progress bar
    bar_width = 20
    filled = int(bar_width * pct / 100)
    bar = "#" * filled + "." * (bar_width - filled)

    # Active tasks
    active = [t for t in tasks if t.get("status") == "in_progress"]

    # Blockers (tasks blocked by approvals)
    pending_approvals = approvals.get("approval_log", [])
    pending = [a for a in pending_approvals if a.get("status") == "pending"]

    # Group tasks by status
    tasks_by_status = {col: [] for col in columns}
    for task in tasks:
        s = task.get("status", "backlog")
        if s in tasks_by_status:
            tasks_by_status[s].append(task)

    # Determine phase
    if total == 0:
        phase = "Initialization"
    elif done == total:
        phase = "Complete"
    elif any(t.get("status") == "in_progress" for t in tasks):
        phase = "Active Development"
    else:
        phase = "Planning"

    # Build report
    lines = []
    lines.append("=" * 60)
    lines.append("  PROJECT STATUS")
    lines.append("=" * 60)
    lines.append(f"  Phase: {phase}")
    lines.append(f"  Progress: [{bar}] {pct}%  ({done}/{total} tasks done)")
    lines.append("")

    # Summary row
    lines.append("  Summary:")
    max_col_len = max((len(c) for c in columns), default=10)
    max_count = max(counts.values()) if counts else 1
    for col in columns:
        cnt = counts[col]
        bar_len = int(5 * cnt / max_count) if max_count > 0 else 0
        bar_str = "#" * bar_len + "." * (5 - bar_len)
        lines.append(f"    {col:<{max_col_len}}  {bar_str}  {cnt}")
    lines.append("")

    # Detailed task listing per non-empty status (skip done for brevity)
    display_order = [c for c in columns if c != "done"]
    for col in display_order:
        col_tasks = tasks_by_status.get(col, [])
        if not col_tasks:
            continue
        lines.append(f"  {col.upper().replace('_', ' ')} ({len(col_tasks)}):")
        for t in col_tasks:
            owner = t.get("owner_role", "unassigned")
            priority = t.get("priority", "")
            pri_tag = f" [{priority}]" if priority else ""
            lines.append(f"    - {t['id']}: {t['title']}{pri_tag} ({owner})")
        lines.append("")

    # Done tasks (collapsed list)
    done_tasks = tasks_by_status.get("done", [])
    if done_tasks:
        lines.append(f"  DONE ({len(done_tasks)}):")
        for t in done_tasks:
            lines.append(f"    - {t['id']}: {t['title']}")
        lines.append("")

    # Worker Bees
    capabilities = _load_capabilities(ai_dir)
    worker_cfg = capabilities.get("worker_bees", {})
    workers_configured = []
    for role in team.get("roles", []):
        for w in role.get("workers", []):
            workers_configured.append({
                "id": w.get("id", "?"),
                "role": role.get("role_id", "?"),
                "model": w.get("model", "?"),
            })

    lines.append("  Worker Bees:")
    if workers_configured:
        max_workers = worker_cfg.get("max_concurrent_workers", "?")
        lines.append(f"    Configured: {len(workers_configured)} (max concurrent: {max_workers})")
        for w in workers_configured:
            # Find assigned tasks
            assigned = [t for t in tasks if t.get("owner_role") == w["role"] and t.get("status") == "in_progress"]
            task_info = f" — working on: {assigned[0]['id']}" if assigned else " — idle"
            lines.append(f"    - {w['id']} ({w['role']}){task_info}")
    else:
        lines.append("    No worker assignments configured.")
        if worker_cfg.get("supported"):
            lines.append('    Say "Set up worker bees for this project" to configure.')
    lines.append("")

    # Blockers / Approvals
    if pending:
        lines.append("  Pending Approvals:")
        for a in pending:
            lines.append(f"    - {a.get('trigger_id', 'unknown')} on {a.get('task_id', '?')}")
    else:
        lines.append("  Blockers: None")
        lines.append("  Pending Approvals: None")

    # Recent decisions
    decisions_path = ai_dir / "DECISIONS.md"
    if decisions_path.exists():
        lines.append("")
        lines.append("  Recent Decisions: see .ai/DECISIONS.md")

    lines.append("")
    lines.append("=" * 60)

    report = "\n".join(lines)

    # Also write STATUS.md
    _write_status_md(ai_dir, phase, columns, counts, total, done, pct,
                     active, pending, tasks_by_status)

    return report


def _write_status_md(ai_dir, phase, columns, counts, total, done, pct,
                     active, pending, tasks_by_status):
    from datetime import datetime, timezone

    bar_width = 20
    filled = int(bar_width * pct / 100)
    bar_md = "#" * filled + "." * (bar_width - filled)

    lines = ["# Project Status", ""]
    lines.append("> Auto-generated by `ai status`. Do not edit manually.")
    lines.append("")
    lines.append(f"## Phase\n{phase}")
    lines.append("")
    lines.append(f"## Progress\n[{bar_md}] {pct}%  ({done}/{total} tasks done)")
    lines.append("")
    lines.append("## Task Summary")
    lines.append("| Column | Count |")
    lines.append("|--------|-------|")
    for col in columns:
        lines.append(f"| {col} | {counts.get(col, 0)} |")
    lines.append("")

    # Detailed task listing per status
    display_order = [c for c in columns if c != "done"]
    for col in display_order:
        col_tasks = tasks_by_status.get(col, [])
        if not col_tasks:
            continue
        lines.append(f"## {col.replace('_', ' ').title()} ({len(col_tasks)})")
        for t in col_tasks:
            owner = t.get("owner_role", "unassigned")
            priority = t.get("priority", "")
            pri_tag = f" `{priority}`" if priority else ""
            lines.append(f"- **{t['id']}**: {t['title']}{pri_tag} (owner: {owner})")
        lines.append("")

    # Done tasks
    done_tasks = tasks_by_status.get("done", [])
    if done_tasks:
        lines.append(f"## Done ({len(done_tasks)})")
        for t in done_tasks:
            lines.append(f"- ~~{t['id']}~~: {t['title']}")
        lines.append("")

    if pending:
        lines.append("## Pending Approvals")
        for a in pending:
            lines.append(f"- {a.get('trigger_id', 'unknown')} on {a.get('task_id', '?')}")
    else:
        lines.append("## Blockers\nNone")
        lines.append("")
        lines.append("## Pending Approvals\nNone")
    lines.append("")
    lines.append("## Recent Decisions\nSee DECISIONS.md")
    lines.append("")
    lines.append(f"---\n*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")

    # Preserve Legacy Snapshot section if it exists in the current STATUS.md
    status_path = ai_dir / "STATUS.md"
    legacy_section = ""
    if status_path.exists():
        existing = status_path.read_text()
        marker = "## Legacy Status Snapshot"
        idx = existing.find(marker)
        if idx >= 0:
            legacy_section = "\n\n" + existing[idx:]

    (ai_dir / "STATUS.md").write_text("\n".join(lines) + legacy_section + "\n")
