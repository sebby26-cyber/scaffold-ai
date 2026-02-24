"""
ai_batch.py — Post-batch canonical sync gate and checklist.

Handles:
- Detecting integrated vs pending worker slices
- Running acceptance commands from completed tickets
- Updating board.yaml task statuses
- Detecting unsynced canonical files
- Generating ready-to-commit checklists
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Canonical paths that must be up to date after a batch
CANONICAL_PATHS = [
    ".ai/state/team.yaml",
    ".ai/state/board.yaml",
    ".ai/state/approvals.yaml",
    ".ai/state/commands.yaml",
    ".ai/STATUS.md",
    ".ai/DECISIONS.md",
    ".ai/METADATA.yaml",
    ".ai/workers/roster.yaml",
]


def batch_close(project_root: Path, dry_run: bool = True) -> str:
    """Post-batch canonical sync gate.

    Checklist:
    1. Detect integrated vs pending worker slices
    2. Run acceptance_commands from completed tickets
    3. Update board.yaml task statuses
    4. Regenerate STATUS.md
    5. Prompt for DECISIONS.md update if arch changes detected
    6. Run validate
    7. Report unsynced canonical files
    8. Output ready-to-commit checklist
    """
    results: dict[str, dict] = {}

    # Step 1: Detect worker slice status
    step1 = _check_worker_slices(project_root)
    results["worker_slices"] = step1

    # Step 2: Run acceptance commands
    step2 = _run_acceptance_commands(project_root, dry_run=dry_run)
    results["acceptance"] = step2

    # Step 3: Update board statuses
    step3 = _update_board_statuses(project_root, dry_run=dry_run)
    results["board_update"] = step3

    # Step 4: Regenerate STATUS.md
    step4 = _regenerate_status(project_root, dry_run=dry_run)
    results["status_md"] = step4

    # Step 5: Check for architecture changes
    step5 = _check_arch_changes(project_root)
    results["arch_changes"] = step5

    # Step 6: Run validation
    step6 = _run_validation(project_root)
    results["validation"] = step6

    # Step 7: Detect unsynced files
    unsynced = detect_unsynced_files(project_root)
    results["unsynced"] = {"files": unsynced, "passed": len(unsynced) == 0}

    # Step 8: Generate checklist
    return generate_commit_checklist(project_root, results, dry_run=dry_run)


def _check_worker_slices(project_root: Path) -> dict:
    """Check which workers have completed vs are still pending."""
    reg_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    if not reg_path.exists():
        return {"passed": True, "detail": "No worker registry (no workers spawned)"}

    try:
        registry = json.loads(reg_path.read_text())
    except Exception:
        return {"passed": False, "detail": "Error reading worker registry"}

    workers = registry.get("workers", [])
    completed = [w for w in workers if w.get("status") in ("completed", "stopped")]
    pending = [w for w in workers if w.get("status") not in ("completed", "stopped")]

    return {
        "passed": len(pending) == 0,
        "detail": f"{len(completed)} completed, {len(pending)} pending",
        "completed": [w.get("worker_id") for w in completed],
        "pending": [w.get("worker_id") for w in pending],
    }


def _run_acceptance_commands(project_root: Path, dry_run: bool = True) -> dict:
    """Run acceptance_commands from completed tickets."""
    from . import ai_tickets

    tickets = ai_tickets.load_all_tickets(project_root)
    done_tickets = [t for t in tickets if t.get("status") in ("done", "review")]

    if not done_tickets:
        return {"passed": True, "detail": "No completed tickets with acceptance commands"}

    results = []
    all_pass = True

    for t in done_tickets:
        cmds = t.get("acceptance_commands", [])
        if not cmds:
            continue

        tid = t.get("ticket_id", "?")
        for cmd in cmds:
            if dry_run:
                results.append(f"[DRY RUN] Would run: {cmd} (ticket: {tid})")
            else:
                try:
                    proc = subprocess.run(
                        cmd, shell=True,
                        cwd=str(project_root),
                        capture_output=True, text=True,
                        timeout=60,
                    )
                    if proc.returncode == 0:
                        results.append(f"PASS: {cmd} (ticket: {tid})")
                    else:
                        all_pass = False
                        results.append(f"FAIL: {cmd} (ticket: {tid}): {proc.stderr[:200]}")
                except Exception as e:
                    all_pass = False
                    results.append(f"ERROR: {cmd} (ticket: {tid}): {e}")

    return {"passed": all_pass, "detail": "\n".join(results) if results else "No acceptance commands"}


def _update_board_statuses(project_root: Path, dry_run: bool = True) -> dict:
    """Update board.yaml task statuses based on ticket completion."""
    if yaml is None:
        return {"passed": True, "detail": "YAML not available"}

    board_path = project_root / ".ai" / "state" / "board.yaml"
    if not board_path.exists():
        return {"passed": True, "detail": "No board.yaml"}

    from . import ai_tickets
    tickets = ai_tickets.load_all_tickets(project_root)
    done_ids = {t.get("ticket_id") for t in tickets if t.get("status") == "done"}

    if not done_ids:
        return {"passed": True, "detail": "No done tickets to sync"}

    try:
        board = yaml.safe_load(board_path.read_text()) or {}
    except Exception:
        return {"passed": False, "detail": "Error reading board.yaml"}

    updated = 0
    for task in board.get("tasks", []):
        if task.get("id") in done_ids and task.get("status") != "done":
            if not dry_run:
                task["status"] = "done"
            updated += 1

    if not dry_run and updated > 0:
        board_path.write_text(yaml.dump(board, default_flow_style=False, sort_keys=False))

    prefix = "[DRY RUN] Would update" if dry_run else "Updated"
    return {"passed": True, "detail": f"{prefix} {updated} board task(s)"}


def _regenerate_status(project_root: Path, dry_run: bool = True) -> dict:
    """Regenerate STATUS.md from current state."""
    if dry_run:
        return {"passed": True, "detail": "[DRY RUN] Would regenerate STATUS.md"}
    try:
        from . import ai_state
        ai_dir = project_root / ".ai"
        runtime_dir = project_root / ".ai_runtime"
        ai_state.reconcile(ai_dir, runtime_dir)
        ai_state.render_status(ai_dir, runtime_dir)
        return {"passed": True, "detail": "STATUS.md regenerated"}
    except Exception as e:
        return {"passed": False, "detail": f"Failed to regenerate STATUS.md: {e}"}


def _check_arch_changes(project_root: Path) -> dict:
    """Check git diff for architecture-level changes that need DECISIONS.md update."""
    arch_patterns = [
        ".ai/state/team.yaml",
        ".ai/core/",
        "*.proto",
        "go.mod",
        "Cargo.toml",
        "package.json",
    ]
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"passed": True, "detail": "Could not check git diff"}

        changed = result.stdout.strip().splitlines()
        arch_files = [f for f in changed if any(f.startswith(p.rstrip("*")) or f.endswith(p.lstrip("*")) for p in arch_patterns)]

        if arch_files:
            return {
                "passed": True,
                "detail": f"Architecture changes detected: {', '.join(arch_files)}. "
                          "Consider updating DECISIONS.md.",
                "needs_decisions_update": True,
            }
        return {"passed": True, "detail": "No architecture changes detected"}
    except Exception:
        return {"passed": True, "detail": "Could not check arch changes"}


def _run_validation(project_root: Path) -> dict:
    """Run schema validation."""
    try:
        from . import ai_validate
        from .ai_run import find_schemas_dir
        ai_dir = project_root / ".ai"
        schemas_dir = find_schemas_dir()
        results = ai_validate.validate_all(ai_dir, schemas_dir, project_root=project_root)
        errors = {k: v for k, v in results.items() if v}
        if errors:
            detail = "; ".join(f"{k}: {len(v)} error(s)" for k, v in errors.items())
            return {"passed": False, "detail": f"Validation errors: {detail}"}
        return {"passed": True, "detail": "All validations passed"}
    except Exception as e:
        return {"passed": False, "detail": f"Validation failed: {e}"}


def detect_unsynced_files(project_root: Path) -> list[str]:
    """Compare git status against canonical paths. Return unsynced files."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []

        unsynced = []
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            # Parse porcelain format: XY <file>
            file_path = line[3:].strip()
            for canon in CANONICAL_PATHS:
                if file_path.startswith(canon.rstrip("/")) or file_path == canon:
                    unsynced.append(file_path)
                    break

        return unsynced
    except Exception:
        return []


def generate_commit_checklist(
    project_root: Path,
    results: dict,
    dry_run: bool = True,
) -> str:
    """Formatted checklist with pass/fail per step."""
    mode = "DRY RUN" if dry_run else "BATCH CLOSE"
    lines = [
        f"{'=' * 60}",
        f"  {mode} — Post-Batch Sync Checklist",
        f"{'=' * 60}",
        "",
    ]

    steps = [
        ("1. Worker slices", "worker_slices"),
        ("2. Acceptance commands", "acceptance"),
        ("3. Board status sync", "board_update"),
        ("4. STATUS.md regeneration", "status_md"),
        ("5. Architecture changes", "arch_changes"),
        ("6. Schema validation", "validation"),
        ("7. Canonical file sync", "unsynced"),
    ]

    all_pass = True
    for label, key in steps:
        step = results.get(key, {})
        passed = step.get("passed", True)
        icon = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        detail = step.get("detail", "")
        lines.append(f"  [{icon}] {label}")
        if detail:
            for d in detail.split("\n"):
                lines.append(f"         {d}")
        lines.append("")

    # Unsynced files detail
    unsynced = results.get("unsynced", {}).get("files", [])
    if unsynced:
        lines.append("  Unsynced canonical files:")
        for f in unsynced:
            lines.append(f"    - {f}")
        lines.append("")

    lines.append(f"{'=' * 60}")
    verdict = "READY TO COMMIT" if all_pass else "ACTION REQUIRED"
    lines.append(f"  {verdict}")
    lines.append(f"{'=' * 60}")

    if dry_run:
        lines.append("")
        lines.append("  This was a dry run. Run 'ai batch-close --execute' to apply changes.")

    return "\n".join(lines)
