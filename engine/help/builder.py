"""
builder.py — Help builder. Inspects project state to generate context-aware help.

Accepts an optional adapter dict for project-specific overrides.
Falls back to inspecting the filesystem directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .model import HelpCommand, HelpCurrentState, HelpFileLocation, HelpGuide

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def generate_help(project_root: Path, adapter: dict | None = None) -> HelpGuide:
    """Build a HelpGuide from project state inspection.

    Args:
        project_root: Path to the project root.
        adapter: Optional dict with project-specific overrides:
            - project_name: str
            - extra_commands: list[dict] (name, description, example)
            - extra_prompts: list[str]
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    adapter = adapter or {}

    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

    # --- Detect current state ---
    state = _detect_state(ai_dir, runtime_dir)

    # --- Project name ---
    project_name = adapter.get("project_name") or _detect_project_name(ai_dir)

    # --- Quick start steps (context-aware) ---
    quick_start = _build_quick_start(state, ai_dir)

    # --- Common prompts ---
    prompts = [
        '"Give me a status report."',
        '"What is everyone working on?"',
        '"What\'s next?"',
        '"Break this into tasks and assign the team."',
        '"Approve this and continue."',
        '"Save memory so I can continue on another machine."',
        '"Help" or "Guide me"',
    ]
    if adapter.get("extra_prompts"):
        prompts.extend(adapter["extra_prompts"])

    # --- Commands ---
    commands = _build_commands(ai_dir)
    if adapter.get("extra_commands"):
        for cmd in adapter["extra_commands"]:
            commands.append(HelpCommand(
                name=cmd.get("name", ""),
                description=cmd.get("description", ""),
                example=cmd.get("example", ""),
            ))

    # --- Resume steps ---
    resume = [
        "Clone the project repo and initialize submodules.",
        'Run "ai init --non-interactive" to rebuild local runtime from committed state.',
        "Drop a memory pack into .ai_runtime/import_inbox/ for richer continuity (optional).",
        'Run "ai run" — the system auto-imports the pack on startup.',
        "The orchestrator knows current phase, tasks, and decisions from .ai/ state.",
    ]

    # --- Troubleshooting ---
    troubleshooting = [
        'Status shows no tasks: run "ai rehydrate-db" then "ai status".',
        'Database out of sync: run "ai rehydrate-db" to rebuild from canonical YAML.',
        '"ai" command not found: run via full path (python vendor/scaffold-ai/engine/ai).',
        'YAML validation errors: run "ai validate" and fix reported issues.',
        ".ai_runtime/ accidentally committed: git rm -r --cached .ai_runtime/ and update .gitignore.",
    ]

    # --- File locations ---
    file_locations = [
        HelpFileLocation(".ai/state/", "Canonical project state (team, board, approvals) — committed to git"),
        HelpFileLocation(".ai/STATUS.md", "Auto-generated project status snapshot"),
        HelpFileLocation(".ai/DECISIONS.md", "Append-only decision log"),
        HelpFileLocation(".ai/METADATA.yaml", "Project ID and skeleton version"),
        HelpFileLocation(".ai_runtime/", "Local cache — never committed, fully rebuildable"),
        HelpFileLocation(".ai_runtime/session/memory.db", "Session memory database"),
        HelpFileLocation(".ai_runtime/import_inbox/", "Drop memory packs here for auto-import"),
        HelpFileLocation(".ai_runtime/memory_packs/", "Auto-exported memory packs on exit"),
    ]

    return HelpGuide(
        generated_at=now,
        project_name=project_name,
        current_state=state,
        quick_start_steps=quick_start,
        common_prompts=prompts,
        commands=commands,
        how_to_resume_on_new_machine=resume,
        troubleshooting=troubleshooting,
        where_to_find_files=file_locations,
    )


def _detect_state(ai_dir: Path, runtime_dir: Path) -> HelpCurrentState:
    """Inspect the filesystem to detect current project state."""
    state = HelpCurrentState()

    # Initialized?
    state.initialized = ai_dir.is_dir() and (ai_dir / "state" / "team.yaml").exists()

    # Assignments configured?
    if state.initialized and yaml is not None:
        try:
            team = yaml.safe_load((ai_dir / "state" / "team.yaml").read_text()) or {}
            workers = []
            for role in team.get("roles", []):
                workers.extend(role.get("workers", []))
            state.worker_count = len(workers)
            state.assignments_configured = state.worker_count > 0
        except Exception:
            pass

    # Task count
    if state.initialized and yaml is not None:
        try:
            board = yaml.safe_load((ai_dir / "state" / "board.yaml").read_text()) or {}
            state.task_count = len(board.get("tasks", []))
        except Exception:
            pass

    # Runtime present?
    state.memory_runtime_present = (runtime_dir / "session" / "memory.db").exists()

    # Memory pack available?
    packs_dir = runtime_dir / "memory_packs"
    inbox_dir = runtime_dir / "import_inbox"
    state.memory_pack_available = (
        (packs_dir.is_dir() and any(packs_dir.iterdir()))
        or (inbox_dir.is_dir() and any(
            p for p in inbox_dir.iterdir()
            if p.name != "processed" and not p.name.startswith(".")
        ))
    )

    return state


def _detect_project_name(ai_dir: Path) -> str:
    """Try to read project name from METADATA.yaml."""
    meta_path = ai_dir / "METADATA.yaml"
    if meta_path.exists() and yaml is not None:
        try:
            meta = yaml.safe_load(meta_path.read_text()) or {}
            name = meta.get("project_name") or meta.get("project_id", "")
            if name and name != "PLACEHOLDER":
                return name
        except Exception:
            pass
    return "This Project"


def _build_quick_start(state: HelpCurrentState, ai_dir: Path) -> list[str]:
    """Build context-aware quick start steps."""
    if not state.initialized:
        return [
            'Run "ai init" to set up the project.',
            "The system will walk you through team setup and approval rules.",
            'After setup, say "status" to see the project dashboard.',
        ]

    steps = []

    if not state.assignments_configured:
        steps.append("Configure your team: tell the orchestrator what roles and workers you need.")

    if state.task_count == 0:
        steps.append("Add tasks: describe your project goals and the orchestrator will create a task board.")
    else:
        steps.append(f'Say "status" to see {state.task_count} tracked task(s) and current progress.')

    steps.append('Say "what\'s next?" to see prioritized upcoming work.')

    if not state.memory_runtime_present:
        steps.append('Run "ai run" to start the orchestrator with automatic session persistence.')
    else:
        steps.append("Session memory is active. All turns are persisted automatically.")

    return steps


def _build_commands(ai_dir: Path) -> list[HelpCommand]:
    """Build command list from commands.yaml if available."""
    commands_path = ai_dir / "state" / "commands.yaml"

    # Always include core commands
    core = [
        HelpCommand("help", "Show this guide", "ai help"),
        HelpCommand("status", "Project status report", "ai status"),
        HelpCommand("validate", "Validate YAML against schemas", "ai validate"),
        HelpCommand("git-sync", "Commit canonical state to git", "ai git-sync"),
        HelpCommand("export-memory", "Export memory pack", "ai export-memory --out pack.zip"),
        HelpCommand("import-memory", "Import a memory pack", "ai import-memory --in pack.zip"),
        HelpCommand("rehydrate-db", "Rebuild local DB from YAML", "ai rehydrate-db"),
        HelpCommand("migrate", "Apply new template files", "ai migrate"),
    ]

    # Add session memory commands
    core.extend([
        HelpCommand("memory export", "Export session memory pack", "ai memory export"),
        HelpCommand("memory import", "Import session memory pack", "ai memory import --in pack.zip"),
        HelpCommand("memory purge", "Purge session memory", "ai memory purge --ns orchestrator --days 30"),
    ])

    return core
