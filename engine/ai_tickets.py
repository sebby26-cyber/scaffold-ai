"""
ai_tickets.py — Ticket contract CRUD, validation, policy enforcement.

Tickets live as individual YAML files in .ai/tickets/<ticket_id>.yaml.
A _index.yaml provides fast lookup. This module handles:
- Loading/saving individual tickets and the index
- Schema + required field validation
- Type-based policy enforcement (review, test, docs constraints)
- Post-run violation detection (forbidden file changes, diff budget)
- Granularity levels (L0-L4) and approval tier metadata
"""

from __future__ import annotations

import fnmatch
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


TICKET_TYPES = ("prod", "test", "docs", "review", "research", "ops")
TICKET_STATUSES = ("draft", "ready", "assigned", "in_progress", "review", "done", "blocked")
REQUIRED_FIELDS = ("ticket_id", "role", "ticket_type", "objective", "allowed_files")

GRANULARITY_LEVELS = {
    "L0": "Strategic (milestones/phases)",
    "L1": "Batch (parallel wave plan)",
    "L2": "Worker Ticket (single deliverable)",
    "L3": "Micro-task (small patch/test)",
    "L4": "Integration (merge/test/commit checklist)",
}

APPROVAL_TIERS = {
    "auto": "Auto-approved (read-only, docs formatting, bounded tests)",
    "pm": "PM approval required (prod code, dependency changes)",
    "orchestrator": "Orchestrator approval required (architecture, cross-cutting)",
    "user": "User approval required (core truths, destructive ops, scope expansion)",
}

# File patterns that code-producing tickets should NOT touch
CODE_PATTERNS = ("*.py", "*.rs", "*.go", "*.js", "*.ts", "*.tsx", "*.jsx",
                 "*.java", "*.c", "*.cpp", "*.h", "*.rb", "*.swift", "*.kt")
TEST_PATTERNS = ("*test*", "*spec*", "tests/**", "test/**", "*_test.*", "*_spec.*")
DOCS_PATTERNS = ("*.md", "*.rst", "*.txt", "docs/**", "*.yaml", "*.yml", "*.json",
                 "*.toml", "*.cfg", "*.ini")


def _tickets_dir(project_root: Path) -> Path:
    return project_root / ".ai" / "tickets"


def load_ticket(project_root: Path, ticket_id: str) -> dict | None:
    """Load a single ticket by ID. Returns None if not found."""
    path = _tickets_dir(project_root) / f"{ticket_id}.yaml"
    if not path.exists() or yaml is None:
        return None
    try:
        return yaml.safe_load(path.read_text()) or None
    except Exception:
        return None


def load_all_tickets(project_root: Path) -> list[dict]:
    """Load all ticket YAML files from .ai/tickets/."""
    tdir = _tickets_dir(project_root)
    if not tdir.is_dir() or yaml is None:
        return []
    tickets = []
    for f in sorted(tdir.glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        try:
            data = yaml.safe_load(f.read_text())
            if data and isinstance(data, dict):
                tickets.append(data)
        except Exception:
            continue
    return tickets


def save_ticket(project_root: Path, ticket: dict) -> Path:
    """Save a ticket dict to .ai/tickets/<ticket_id>.yaml. Returns path."""
    if yaml is None:
        raise ImportError("PyYAML required")
    tdir = _tickets_dir(project_root)
    tdir.mkdir(parents=True, exist_ok=True)
    ticket_id = ticket.get("ticket_id", "unknown")
    path = tdir / f"{ticket_id}.yaml"
    path.write_text(yaml.dump(ticket, default_flow_style=False, sort_keys=False))
    return path


def validate_ticket(ticket: dict) -> list[str]:
    """Validate a ticket against required fields and allowed values.

    Returns list of error messages (empty = valid).
    """
    errors: list[str] = []
    if not isinstance(ticket, dict):
        return ["Ticket is not a dict"]

    for field in REQUIRED_FIELDS:
        if field not in ticket:
            errors.append(f"Missing required field: {field}")

    tid = ticket.get("ticket_id", "?")

    if ticket.get("ticket_type") and ticket["ticket_type"] not in TICKET_TYPES:
        errors.append(f"[{tid}] Invalid ticket_type: {ticket['ticket_type']}")

    if ticket.get("status") and ticket["status"] not in TICKET_STATUSES:
        errors.append(f"[{tid}] Invalid status: {ticket['status']}")

    if ticket.get("granularity") and ticket["granularity"] not in GRANULARITY_LEVELS:
        errors.append(f"[{tid}] Invalid granularity: {ticket['granularity']}")

    if ticket.get("approval_tier") and ticket["approval_tier"] not in APPROVAL_TIERS:
        errors.append(f"[{tid}] Invalid approval_tier: {ticket['approval_tier']}")

    allowed = ticket.get("allowed_files")
    if allowed is not None and not isinstance(allowed, list):
        errors.append(f"[{tid}] allowed_files must be a list")

    return errors


def validate_ticket_policy(ticket: dict) -> list[str]:
    """Type-based policy enforcement.

    - review tickets: allowed_files cannot include code patterns
    - test tickets: allowed_files must match test or explicit allow
    - docs tickets: allowed_files must match docs/markdown patterns
    """
    errors: list[str] = []
    tid = ticket.get("ticket_id", "?")
    ttype = ticket.get("ticket_type", "")
    allowed = ticket.get("allowed_files", [])
    if not isinstance(allowed, list):
        return errors

    if ttype == "review":
        for pattern in allowed:
            for code_pat in CODE_PATTERNS:
                if fnmatch.fnmatch(pattern, code_pat) or pattern == code_pat:
                    errors.append(
                        f"[{tid}] review ticket cannot include code pattern: {pattern}"
                    )
                    break

    elif ttype == "test":
        for pattern in allowed:
            is_test = any(fnmatch.fnmatch(pattern.lower(), tp) for tp in TEST_PATTERNS)
            if not is_test and not pattern.startswith("!"):
                # Allow explicit overrides but warn
                pass  # Permissive: test tickets can touch test-adjacent files

    elif ttype == "docs":
        for pattern in allowed:
            is_doc = any(fnmatch.fnmatch(pattern.lower(), dp) for dp in DOCS_PATTERNS)
            if not is_doc:
                errors.append(
                    f"[{tid}] docs ticket has non-docs pattern: {pattern}"
                )

    return errors


def check_post_run_violations(
    project_root: Path,
    ticket_id: str,
    changed_files: list[str],
) -> list[str]:
    """Check if a worker's changed files violate its ticket contract.

    Returns list of violation messages.
    """
    ticket = load_ticket(project_root, ticket_id)
    if not ticket:
        return [f"Ticket {ticket_id} not found"]

    errors: list[str] = []
    allowed = ticket.get("allowed_files", [])
    forbidden = ticket.get("forbidden_files", [])

    for changed in changed_files:
        # Check forbidden
        for fb in forbidden:
            if fnmatch.fnmatch(changed, fb):
                errors.append(f"[{ticket_id}] Forbidden file modified: {changed} (matches {fb})")

        # Check allowed
        if allowed:
            matched = any(fnmatch.fnmatch(changed, a) for a in allowed)
            if not matched:
                errors.append(f"[{ticket_id}] File not in allowed_files: {changed}")

    # Diff budget check
    errors.extend(check_diff_budget(ticket, changed_files))

    return errors


def check_diff_budget(ticket: dict, changed_files: list[str]) -> list[str]:
    """Check if changed files exceed the ticket's max_files_changed budget."""
    errors: list[str] = []
    max_files = ticket.get("max_files_changed")
    if max_files is not None and isinstance(max_files, int):
        if len(changed_files) > max_files:
            tid = ticket.get("ticket_id", "?")
            errors.append(
                f"[{tid}] Diff budget exceeded: {len(changed_files)} files changed "
                f"(max: {max_files})"
            )
    return errors


def get_active_tickets(project_root: Path) -> list[dict]:
    """Return tickets with status in (ready, assigned, in_progress, review)."""
    active_statuses = {"ready", "assigned", "in_progress", "review"}
    return [
        t for t in load_all_tickets(project_root)
        if t.get("status", "draft") in active_statuses
    ]


def update_ticket_index(project_root: Path) -> Path:
    """Regenerate _index.yaml from all ticket files.

    Index format: {tickets: [{ticket_id, status, ticket_type, role, granularity}]}
    """
    if yaml is None:
        raise ImportError("PyYAML required")

    tdir = _tickets_dir(project_root)
    tdir.mkdir(parents=True, exist_ok=True)

    tickets = load_all_tickets(project_root)
    index_entries = []
    for t in tickets:
        index_entries.append({
            "ticket_id": t.get("ticket_id", "?"),
            "status": t.get("status", "draft"),
            "ticket_type": t.get("ticket_type", "?"),
            "role": t.get("role", "?"),
            "granularity": t.get("granularity", "L2"),
            "approval_tier": t.get("approval_tier", "auto"),
        })

    index_data = {"tickets": index_entries}
    index_path = tdir / "_index.yaml"
    index_path.write_text(yaml.dump(index_data, default_flow_style=False, sort_keys=False))
    return index_path


def validate_all_tickets(project_root: Path) -> tuple[int, int, list[str]]:
    """Validate all tickets. Returns (pass_count, fail_count, all_errors)."""
    tickets = load_all_tickets(project_root)
    if not tickets:
        return 0, 0, ["No tickets found in .ai/tickets/"]

    pass_count = 0
    fail_count = 0
    all_errors: list[str] = []

    for t in tickets:
        errs = validate_ticket(t) + validate_ticket_policy(t)

        # Check core truth references if truths exist
        errs.extend(check_core_truth_references(project_root, t))

        if errs:
            fail_count += 1
            all_errors.extend(errs)
        else:
            pass_count += 1

    return pass_count, fail_count, all_errors


def check_core_truth_references(project_root: Path, ticket: dict) -> list[str]:
    """Check that ticket references applicable core truths.

    Returns warnings (not errors) if truths exist but ticket has no references.
    """
    errors: list[str] = []
    truths_path = project_root / ".ai" / "core_truths.yaml"
    if not truths_path.exists() or yaml is None:
        return []

    try:
        truths_data = yaml.safe_load(truths_path.read_text()) or {}
    except Exception:
        return []

    truths = truths_data.get("truths", [])
    if not truths:
        return []

    tid = ticket.get("ticket_id", "?")
    refs = ticket.get("core_truth_refs", [])
    ttype = ticket.get("ticket_type", "")

    # Prod and ops tickets SHOULD reference core truths
    if ttype in ("prod", "ops") and not refs:
        errors.append(
            f"[{tid}] prod/ops ticket has no core_truth_refs "
            f"({len(truths)} truths defined)"
        )

    # Validate referenced truth IDs exist
    truth_ids = {t.get("id") for t in truths if t.get("id")}
    for ref in refs:
        if ref not in truth_ids:
            errors.append(f"[{tid}] Unknown core truth ref: {ref}")

    return errors


def is_ticket_approved(ticket: dict) -> bool:
    """Check if a ticket's approval tier allows execution.

    Auto-approved tickets can run immediately. Others need explicit approval.
    """
    tier = ticket.get("approval_tier", "auto")
    if tier == "auto":
        return True
    return ticket.get("approved", False)


def classify_legacy_ticket(ticket: dict) -> dict:
    """Add missing metadata to legacy tickets with warnings."""
    if "ticket_type" not in ticket:
        ticket["ticket_type"] = "prod"
        ticket.setdefault("_warnings", []).append("legacy_unbounded: missing ticket_type, defaulted to prod")
    if "granularity" not in ticket:
        ticket["granularity"] = "L2"
        ticket.setdefault("_warnings", []).append("legacy_unbounded: missing granularity, defaulted to L2")
    if "approval_tier" not in ticket:
        ticket["approval_tier"] = "pm"
        ticket.setdefault("_warnings", []).append("legacy_unbounded: missing approval_tier, defaulted to pm")
    if "allowed_files" not in ticket:
        ticket["allowed_files"] = ["**"]
        ticket.setdefault("_warnings", []).append("legacy_unbounded: missing allowed_files, defaulted to **")
    return ticket
