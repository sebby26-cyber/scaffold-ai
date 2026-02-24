"""
ai_modes.py — Plan Mode vs Execution Mode orchestration.

Implements explicit orchestration modes with different behavior and constraints:

Plan Mode:
- Produces plans, not code changes (by default)
- Outputs: task DAG, batch plan, file ownership matrix, worker assignments,
  acceptance gates, rollback plan, dependency map
- No tracked file code changes unless explicitly allowed
- Workers for planning/research/review only

Execution Mode:
- Executes approved worker tickets and integrates results
- Enforces allowed/forbidden files
- Enforces acceptance commands
- Classifies and stops stalled workers
- Supports partial harvest/discard of worker diffs
- Requires post-batch canonical sync checklist
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


MODES = ("plan", "execution")

# In plan mode, only these ticket types may be assigned to workers
PLAN_MODE_ALLOWED_TYPES = ("review", "research", "docs")

# In execution mode, all types are allowed but need approval checks
EXECUTION_MODE_REQUIRES_APPROVAL = ("prod", "ops")


def get_current_mode(project_root: Path) -> str:
    """Read current orchestration mode from .ai/state/mode.yaml.

    Defaults to 'plan' if not set.
    """
    mode_path = project_root / ".ai" / "state" / "mode.yaml"
    if not mode_path.exists() or yaml is None:
        return "plan"
    try:
        data = yaml.safe_load(mode_path.read_text()) or {}
        mode = data.get("mode", "plan")
        return mode if mode in MODES else "plan"
    except Exception:
        return "plan"


def set_mode(project_root: Path, mode: str) -> str:
    """Set the orchestration mode. Returns confirmation message."""
    if mode not in MODES:
        return f"Invalid mode: {mode}. Must be one of: {', '.join(MODES)}"

    if yaml is None:
        return "Error: PyYAML required"

    mode_path = project_root / ".ai" / "state" / "mode.yaml"
    mode_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "mode": mode,
        "set_at": datetime.now(timezone.utc).isoformat(),
        "set_by": "orchestrator",
    }
    mode_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    return f"Mode set to: {mode.upper()}"


def validate_mode_constraints(project_root: Path, ticket: dict) -> list[str]:
    """Validate that a ticket respects the current mode constraints.

    In plan mode: only review/research/docs tickets allowed for workers.
    In execution mode: prod/ops tickets require approval.
    """
    errors: list[str] = []
    mode = get_current_mode(project_root)
    ttype = ticket.get("ticket_type", "prod")
    tid = ticket.get("ticket_id", "?")

    if mode == "plan":
        if ttype not in PLAN_MODE_ALLOWED_TYPES:
            errors.append(
                f"[{tid}] ticket_type '{ttype}' not allowed in plan mode. "
                f"Allowed: {', '.join(PLAN_MODE_ALLOWED_TYPES)}"
            )
        # Check no code file patterns in allowed_files
        code_exts = {".py", ".rs", ".go", ".js", ".ts", ".tsx", ".jsx",
                     ".java", ".c", ".cpp", ".h", ".rb", ".swift", ".kt"}
        for pattern in ticket.get("allowed_files", []):
            for ext in code_exts:
                if pattern.endswith(ext) or f"*{ext}" in pattern:
                    if not ticket.get("plan_mode_code_override", False):
                        errors.append(
                            f"[{tid}] Code pattern '{pattern}' not allowed in plan mode "
                            f"(set plan_mode_code_override: true to override)"
                        )
                        break

    elif mode == "execution":
        if ttype in EXECUTION_MODE_REQUIRES_APPROVAL:
            from . import ai_tickets
            if not ai_tickets.is_ticket_approved(ticket):
                errors.append(
                    f"[{tid}] {ttype} ticket requires approval in execution mode"
                )

    return errors


def generate_plan_outputs(project_root: Path) -> dict:
    """Generate plan mode outputs: task DAG, batch plan, file ownership matrix.

    Returns dict with all plan artifacts.
    """
    from . import ai_tickets, ai_collisions

    tickets = ai_tickets.load_all_tickets(project_root)

    # Task DAG (dependency graph)
    dag = _build_task_dag(tickets)

    # Batch plan (parallel lanes)
    batch_plan = _build_batch_plan(tickets, dag)

    # File ownership matrix
    ownership = ai_collisions.build_ownership_matrix(tickets)

    # Worker assignments
    assignments = _build_worker_assignments(tickets)

    # Acceptance gates
    gates = _build_acceptance_gates(tickets)

    # Rollback plan
    rollback = _build_rollback_plan(tickets)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "plan",
        "task_dag": dag,
        "batch_plan": batch_plan,
        "file_ownership_matrix": ownership,
        "worker_assignments": assignments,
        "acceptance_gates": gates,
        "rollback_plan": rollback,
        "ticket_count": len(tickets),
    }


def _build_task_dag(tickets: list[dict]) -> dict:
    """Build a dependency DAG from ticket depends_on fields."""
    nodes = {}
    for t in tickets:
        tid = t.get("ticket_id", "?")
        nodes[tid] = {
            "ticket_type": t.get("ticket_type", "?"),
            "granularity": t.get("granularity", "L2"),
            "depends_on": t.get("depends_on", []),
            "blocks": [],
        }
    # Build reverse edges
    for tid, node in nodes.items():
        for dep in node["depends_on"]:
            if dep in nodes:
                nodes[dep]["blocks"].append(tid)
    return nodes


def _build_batch_plan(tickets: list[dict], dag: dict) -> list[list[str]]:
    """Build parallel batch lanes using topological ordering.

    Returns list of waves, each wave is a list of ticket IDs that can run in parallel.
    """
    remaining = set(dag.keys())
    completed: set[str] = set()
    waves: list[list[str]] = []

    while remaining:
        # Find tickets with all dependencies satisfied
        wave = []
        for tid in list(remaining):
            deps = dag[tid]["depends_on"]
            if all(d in completed or d not in dag for d in deps):
                wave.append(tid)

        if not wave:
            # Circular dependency or unresolvable — dump remaining
            waves.append(list(remaining))
            break

        waves.append(sorted(wave))
        for tid in wave:
            remaining.discard(tid)
            completed.add(tid)

    return waves


def _build_worker_assignments(tickets: list[dict]) -> dict[str, list[str]]:
    """Map roles to ticket IDs."""
    assignments: dict[str, list[str]] = {}
    for t in tickets:
        role = t.get("role", "unassigned")
        assignments.setdefault(role, []).append(t.get("ticket_id", "?"))
    return assignments


def _build_acceptance_gates(tickets: list[dict]) -> list[dict]:
    """Extract acceptance gates from tickets."""
    gates = []
    for t in tickets:
        cmds = t.get("acceptance_commands", [])
        if cmds:
            gates.append({
                "ticket_id": t.get("ticket_id", "?"),
                "commands": cmds,
                "approval_tier": t.get("approval_tier", "auto"),
            })
    return gates


def _build_rollback_plan(tickets: list[dict]) -> list[dict]:
    """Build rollback plan: for each ticket, describe how to undo."""
    plan = []
    for t in tickets:
        tid = t.get("ticket_id", "?")
        plan.append({
            "ticket_id": tid,
            "allowed_files": t.get("allowed_files", []),
            "rollback": f"git checkout HEAD -- {' '.join(t.get('allowed_files', []))}",
        })
    return plan


def format_plan_output(plan: dict) -> str:
    """Format plan outputs for terminal display."""
    lines = [
        "=" * 60,
        "  PLAN MODE — Generated Artifacts",
        "=" * 60,
        "",
    ]

    # Task DAG
    dag = plan.get("task_dag", {})
    lines.append(f"  Task DAG ({len(dag)} tickets):")
    for tid, node in dag.items():
        deps = ", ".join(node["depends_on"]) if node["depends_on"] else "none"
        lines.append(f"    {tid} [{node['granularity']}] depends: {deps}")
    lines.append("")

    # Batch Plan
    waves = plan.get("batch_plan", [])
    lines.append(f"  Batch Plan ({len(waves)} wave(s)):")
    for i, wave in enumerate(waves):
        lines.append(f"    Wave {i + 1}: {', '.join(wave)}")
    lines.append("")

    # File Ownership
    ownership = plan.get("file_ownership_matrix", {})
    lines.append(f"  File Ownership Matrix ({len(ownership)} patterns):")
    for pattern, tids in ownership.items():
        lines.append(f"    {pattern}: {', '.join(tids)}")
    lines.append("")

    # Worker Assignments
    assignments = plan.get("worker_assignments", {})
    lines.append(f"  Worker Assignments ({len(assignments)} roles):")
    for role, tids in assignments.items():
        lines.append(f"    {role}: {', '.join(tids)}")
    lines.append("")

    # Acceptance Gates
    gates = plan.get("acceptance_gates", [])
    if gates:
        lines.append(f"  Acceptance Gates ({len(gates)}):")
        for g in gates:
            lines.append(f"    {g['ticket_id']} [{g['approval_tier']}]: {len(g['commands'])} command(s)")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
