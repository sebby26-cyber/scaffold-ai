"""
ai_planning.py — Team-based planning workflow.

Supports running a worker team in planning capacity:
- PM lead (batch cut + merge order)
- Scope assistants (ticket splits + collision detection proposals)
- Reviewers/analyzers (risk and feasibility critique)
- Researcher lane (optional, external references)

Workflow:
1. Draft plan
2. Debate/critique plan (reviewers)
3. Resolve collisions
4. Approve plan
5. Generate execution tickets
6. Launch execution mode
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


PLANNING_ROLES = {
    "pm_lead": {
        "title": "PM Lead",
        "responsibilities": ["batch cut", "merge order", "scope decisions"],
        "allowed_ticket_types": ["review", "research", "docs"],
    },
    "scope_assistant": {
        "title": "Scope Assistant",
        "responsibilities": ["ticket splits", "collision proposals", "anti-bloat"],
        "allowed_ticket_types": ["review", "research"],
    },
    "reviewer": {
        "title": "Reviewer / Analyzer",
        "responsibilities": ["risk critique", "feasibility check", "regression risk"],
        "allowed_ticket_types": ["review"],
    },
    "researcher": {
        "title": "Researcher",
        "responsibilities": ["external refs", "prior art", "technical research"],
        "allowed_ticket_types": ["research"],
    },
}

PLAN_STATUSES = ("draft", "debate", "collisions", "approved", "execution_ready")


def load_plan(project_root: Path) -> dict | None:
    """Load the current plan from .ai/state/plan.yaml."""
    plan_path = project_root / ".ai" / "state" / "plan.yaml"
    if not plan_path.exists() or yaml is None:
        return None
    try:
        return yaml.safe_load(plan_path.read_text()) or None
    except Exception:
        return None


def save_plan(project_root: Path, plan: dict) -> Path:
    """Save plan to .ai/state/plan.yaml."""
    if yaml is None:
        raise ImportError("PyYAML required")
    plan_path = project_root / ".ai" / "state" / "plan.yaml"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(yaml.dump(plan, default_flow_style=False, sort_keys=False))
    return plan_path


def create_draft_plan(
    project_root: Path,
    objective: str,
    ticket_drafts: list[dict] | None = None,
) -> dict:
    """Create a new draft plan.

    Returns the plan dict.
    """
    plan = {
        "plan_id": datetime.now(timezone.utc).strftime("plan_%Y%m%d_%H%M%S"),
        "objective": objective,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "orchestrator",
        "ticket_drafts": ticket_drafts or [],
        "reviewer_feedback": [],
        "collision_report": None,
        "approval": None,
    }
    save_plan(project_root, plan)
    return plan


def add_reviewer_feedback(
    project_root: Path,
    reviewer_id: str,
    feedback: str,
    classification: str = "advisory",
) -> str:
    """Add reviewer feedback to the current plan."""
    plan = load_plan(project_root)
    if not plan:
        return "No active plan found. Create a draft plan first."

    entry = {
        "reviewer_id": reviewer_id,
        "feedback": feedback,
        "classification": classification,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    plan.setdefault("reviewer_feedback", []).append(entry)

    if plan["status"] == "draft":
        plan["status"] = "debate"

    save_plan(project_root, plan)
    return f"Feedback added from {reviewer_id}. Plan status: {plan['status']}"


def resolve_collisions(project_root: Path) -> str:
    """Run collision detection and attach results to plan."""
    from . import ai_collisions, ai_tickets

    plan = load_plan(project_root)
    if not plan:
        return "No active plan found."

    tickets = plan.get("ticket_drafts", [])
    if not tickets:
        return "No ticket drafts in plan to check."

    collisions = ai_collisions.detect_collisions(tickets, project_root)
    report = ai_collisions.format_collision_report(collisions)

    plan["collision_report"] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "collision_count": len(collisions),
        "hard_collisions": len([c for c in collisions if c["severity"] == "hard"]),
        "report": report,
    }
    plan["status"] = "collisions"
    save_plan(project_root, plan)

    return report


def approve_plan(project_root: Path, approved_by: str = "orchestrator") -> str:
    """Approve the plan, transitioning to approved status."""
    plan = load_plan(project_root)
    if not plan:
        return "No active plan found."

    # Check for unresolved hard collisions
    collision_report = plan.get("collision_report", {})
    if collision_report.get("hard_collisions", 0) > 0:
        return (
            "Cannot approve: plan has unresolved hard collisions. "
            "Resolve collisions first."
        )

    plan["status"] = "approved"
    plan["approval"] = {
        "approved_by": approved_by,
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    save_plan(project_root, plan)

    return f"Plan approved by {approved_by}. Ready to generate execution tickets."


def generate_execution_tickets(project_root: Path) -> str:
    """Generate execution tickets from an approved plan.

    Converts ticket_drafts into real ticket files in .ai/tickets/.
    Sets mode to execution.
    """
    from . import ai_tickets, ai_modes

    plan = load_plan(project_root)
    if not plan:
        return "No active plan found."

    if plan.get("status") != "approved":
        return f"Plan must be approved first. Current status: {plan.get('status')}"

    drafts = plan.get("ticket_drafts", [])
    if not drafts:
        return "No ticket drafts in plan."

    created = []
    for draft in drafts:
        # Ensure required fields
        if "ticket_id" not in draft:
            draft["ticket_id"] = f"t_{datetime.now(timezone.utc).strftime('%H%M%S')}_{len(created)}"
        draft.setdefault("status", "ready")
        draft.setdefault("granularity", "L2")
        draft.setdefault("approval_tier", "auto")

        # Classify legacy tickets
        draft = ai_tickets.classify_legacy_ticket(draft)

        path = ai_tickets.save_ticket(project_root, draft)
        created.append(draft["ticket_id"])

    # Update index
    ai_tickets.update_ticket_index(project_root)

    # Update plan status
    plan["status"] = "execution_ready"
    plan["tickets_generated"] = created
    plan["tickets_generated_at"] = datetime.now(timezone.utc).isoformat()
    save_plan(project_root, plan)

    # Switch to execution mode
    ai_modes.set_mode(project_root, "execution")

    lines = [
        f"Generated {len(created)} execution ticket(s):",
    ]
    for tid in created:
        lines.append(f"  - {tid}")
    lines.append("")
    lines.append("Mode switched to: EXECUTION")
    lines.append("Run 'ai tickets validate' to verify, then 'ai spawn-workers'.")

    return "\n".join(lines)


def format_plan_status(project_root: Path) -> str:
    """Format current plan status for display."""
    plan = load_plan(project_root)
    if not plan:
        return "No active plan. Use 'ai plan draft' to create one."

    lines = [
        "=" * 60,
        "  PLANNING STATUS",
        "=" * 60,
        "",
        f"  Plan: {plan.get('plan_id', '?')}",
        f"  Status: {plan.get('status', '?').upper()}",
        f"  Objective: {plan.get('objective', '?')}",
        f"  Created: {plan.get('created_at', '?')}",
        "",
    ]

    drafts = plan.get("ticket_drafts", [])
    lines.append(f"  Ticket Drafts ({len(drafts)}):")
    for d in drafts:
        lines.append(
            f"    - {d.get('ticket_id', '?')} [{d.get('ticket_type', '?')}] "
            f"{d.get('granularity', 'L2')} — {d.get('objective', '?')[:50]}"
        )
    lines.append("")

    feedback = plan.get("reviewer_feedback", [])
    if feedback:
        lines.append(f"  Reviewer Feedback ({len(feedback)}):")
        for f in feedback:
            lines.append(
                f"    [{f.get('classification', '?')}] {f.get('reviewer_id', '?')}: "
                f"{f.get('feedback', '')[:60]}"
            )
        lines.append("")

    collision_report = plan.get("collision_report")
    if collision_report:
        lines.append(f"  Collisions: {collision_report.get('collision_count', 0)} "
                      f"(hard: {collision_report.get('hard_collisions', 0)})")
        lines.append("")

    approval = plan.get("approval")
    if approval:
        lines.append(f"  Approved by: {approval.get('approved_by', '?')} "
                      f"at {approval.get('approved_at', '?')}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def get_planning_team_spec(project_root: Path) -> str:
    """Generate a team spec suitable for planning mode.

    Returns a natural language spec for configure-team.
    """
    return (
        "1 Codex PM lead, "
        "2 Codex scope assistants, "
        "1 Gemini reviewer, "
        "1 Gemini researcher"
    )
