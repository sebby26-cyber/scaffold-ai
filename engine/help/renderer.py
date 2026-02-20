"""
renderer.py — Terminal renderer for HelpGuide.

Produces clean, beginner-friendly terminal output.
All rendering derives from the help model (which is JSON-serializable).
"""

from __future__ import annotations

from .model import HelpGuide


def render_help_terminal(guide: HelpGuide) -> str:
    """Render a HelpGuide as terminal-friendly text."""
    W = 72
    lines: list[str] = []

    # ── Header ──
    lines.append("=" * W)
    lines.append(_center("SCAFFOLD AI — GUIDE", W))
    lines.append("=" * W)
    lines.append(f"  Project:   {guide.project_name}")
    lines.append(f"  Generated: {guide.generated_at}")
    lines.append("")

    # ── Current State ──
    lines.append(_section("Your Project Right Now"))
    s = guide.current_state
    lines.append(f"  Initialized:          {'Yes' if s.initialized else 'No — run ai init'}")
    lines.append(f"  Team configured:      {'Yes' if s.assignments_configured else 'No'}"
                 + (f" ({s.worker_count} worker(s))" if s.assignments_configured else ""))
    lines.append(f"  Tasks tracked:        {s.task_count}")
    lines.append(f"  Session memory:       {'Active' if s.memory_runtime_present else 'Not yet started'}")
    lines.append(f"  Memory pack:          {'Available' if s.memory_pack_available else 'None'}")
    lines.append("")

    # ── Quick Start ──
    lines.append(_section("Quick Start"))
    for i, step in enumerate(guide.quick_start_steps, 1):
        lines.append(f"  {i}. {step}")
    lines.append("")

    # ── Common Prompts ──
    lines.append(_section("What You Can Say"))
    lines.append("  Just talk to the orchestrator in plain language:")
    lines.append("")
    for prompt in guide.common_prompts:
        lines.append(f"    {prompt}")
    lines.append("")

    # ── Commands ──
    if guide.commands:
        lines.append(_section("Commands (for power users)"))
        # Find max name length for alignment
        max_name = max(len(c.name) for c in guide.commands)
        for cmd in guide.commands:
            lines.append(f"  {cmd.name:<{max_name + 2}} {cmd.description}")
        lines.append("")

    # ── Resume ──
    lines.append(_section("Resume on a New Machine"))
    for i, step in enumerate(guide.how_to_resume_on_new_machine, 1):
        lines.append(f"  {i}. {step}")
    lines.append("")

    # ── Files ──
    lines.append(_section("Where Things Live"))
    for loc in guide.where_to_find_files:
        lines.append(f"  {loc.path}")
        lines.append(f"      {loc.description}")
    lines.append("")

    # ── Troubleshooting ──
    lines.append(_section("Troubleshooting"))
    for tip in guide.troubleshooting:
        lines.append(f"  - {tip}")
    lines.append("")

    lines.append("=" * W)

    return "\n".join(lines)


def _center(text: str, width: int) -> str:
    pad = (width - len(text)) // 2
    return " " * pad + text


def _section(title: str) -> str:
    return f"  --- {title} ---"
