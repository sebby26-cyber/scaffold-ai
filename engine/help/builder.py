"""
builder.py — Help builder. Inspects project state to generate context-aware help.

Accepts an optional adapter dict for project-specific overrides.
Falls back to inspecting the filesystem directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..cli_commands import cli_example_for_alias, help_json_commands
from .model import (
    HelpCategory,
    HelpCommand,
    HelpCurrentState,
    HelpFileLocation,
    HelpGuide,
    HelpIntent,
)

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
            - extra_categories: list[dict] (name, icon, intents)
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

    # --- Prompt categories (human-first, intent-mapped) ---
    capabilities = _load_capabilities(ai_dir)
    categories = _build_prompt_categories(capabilities, ai_dir)
    if adapter.get("extra_categories"):
        for cat in adapter["extra_categories"]:
            categories.append(HelpCategory(
                name=cat.get("name", ""),
                icon=cat.get("icon", ""),
                intents=[
                    HelpIntent(
                        prompt=i.get("prompt", ""),
                        command=i.get("command", ""),
                        description=i.get("description", ""),
                    )
                    for i in cat.get("intents", [])
                ],
            ))

    # --- Commands (advanced / power user) ---
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
        "If I'm unsure about a capability, I consult the system layer (skeleton submodule) rather than guessing.",
    ]

    # --- File locations ---
    file_locations = [
        HelpFileLocation(".ai/state/", "Canonical project state (team, board, approvals) — committed to git"),
        HelpFileLocation(".ai/state/providers.yaml", "Provider registry (CLI tools, models, aliases)"),
        HelpFileLocation(".ai/state/intents.yaml", "Intent registry (natural language routing)"),
        HelpFileLocation(".ai/state/project.yaml", "Project scope definition (guardrails)"),
        HelpFileLocation(".ai/state/recovery.yaml", "Worker recovery configuration"),
        HelpFileLocation(".ai/state/persistence.yaml", "Auto-flush and sync configuration"),
        HelpFileLocation(".ai/STATUS.md", "Auto-generated project status snapshot"),
        HelpFileLocation(".ai/DECISIONS.md", "Append-only decision log"),
        HelpFileLocation(".ai/METADATA.yaml", "Project ID and skeleton version"),
        HelpFileLocation(".ai_runtime/", "Local cache — never committed, fully rebuildable"),
        HelpFileLocation(".ai_runtime/session/memory.db", "Session memory database"),
        HelpFileLocation(".ai_runtime/import_inbox/", "Drop memory packs here for auto-import"),
        HelpFileLocation(".ai_runtime/memory_packs/", "Auto-exported memory packs on exit"),
        HelpFileLocation(".ai_runtime/workers/checkpoints/", "Worker checkpoint data (auto-recovery)"),
        HelpFileLocation(".ai/workers/", "Canonical worker state — roster, checkpoints, summaries (committed)"),
        HelpFileLocation(".ai/workers/roster.yaml", "Worker roster (portable across machines)"),
        HelpFileLocation(".ai/workers/checkpoints/", "Portable worker checkpoints (Markdown, human-readable)"),
        HelpFileLocation(".ai/workers/summaries/", "Per-worker state summaries"),
    ]

    return HelpGuide(
        generated_at=now,
        project_name=project_name,
        current_state=state,
        quick_start_steps=quick_start,
        prompt_categories=categories,
        commands=commands,
        how_to_resume_on_new_machine=resume,
        troubleshooting=troubleshooting,
        where_to_find_files=file_locations,
    )


def _load_capabilities(ai_dir: Path) -> dict:
    """Load capabilities.yaml from canonical state."""
    caps_path = ai_dir / "state" / "capabilities.yaml"
    if caps_path.exists() and yaml is not None:
        try:
            return yaml.safe_load(caps_path.read_text()) or {}
        except Exception:
            pass
    return {}


def _build_prompt_categories(capabilities: dict | None = None, ai_dir: Path | None = None) -> list[HelpCategory]:
    """Build human-first intent categories with deterministic command mappings.

    If intents.yaml exists, builds categories from it (grouped by category field).
    Otherwise falls back to hardcoded categories.
    """
    # Try to build from intents.yaml
    if ai_dir:
        intents_path = ai_dir / "state" / "intents.yaml"
        if intents_path.exists() and yaml is not None:
            try:
                result = _build_categories_from_intents(intents_path, capabilities)
                if result:
                    return result
            except Exception:
                pass  # Fall through to hardcoded

    capabilities = capabilities or {}

    categories = [
        HelpCategory(
            name="Getting Started",
            icon="\U0001f680",  # rocket
            intents=[
                HelpIntent("Start or initialize the project", "ai init"),
                HelpIntent("Resume where we left off", "ai run"),
            ],
        ),
        HelpCategory(
            name="Project Visibility",
            icon="\U0001f4ca",  # chart
            intents=[
                HelpIntent("Show me the current status", "ai status"),
                HelpIntent("What's been completed and what's next?", "ai status"),
                HelpIntent("Are there any blockers?", "ai status"),
            ],
        ),
        HelpCategory(
            name="Parallel Work (Worker Bees)",
            icon="\U0001f41d",  # bee
            intents=[
                HelpIntent(
                    "Set up a team: 3 Codex devs + 1 Claude designer + 1 Gemini analyst",
                    "ai configure-team",
                    description="Parses your spec, writes team.yaml with provider/model per role",
                ),
                HelpIntent("Spawn worker bees", "ai spawn-workers"),
                HelpIntent("Show me what each worker is doing", "ai workers-status"),
                HelpIntent("Checkpoint all workers", "ai checkpoint-workers",
                           description="Save worker progress to portable state"),
                HelpIntent("Show me each worker's last checkpoint", "ai show-checkpoints"),
                HelpIntent("Stop all workers", "ai stop-workers"),
            ],
        ),
        HelpCategory(
            name="Worker Recovery",
            icon="\U0001f6e0",  # wrench
            intents=[
                HelpIntent("Resume stalled workers", "ai workers-resume"),
                HelpIntent("Restart the stuck worker", "ai workers-restart"),
            ],
        ),
        HelpCategory(
            name="State Persistence",
            icon="\U0001f4be",  # floppy
            intents=[
                HelpIntent("Save everything now", "ai force-sync",
                           description="Flush state + checkpoint workers"),
                HelpIntent("Update project state", "ai force-sync"),
            ],
        ),
        HelpCategory(
            name="Memory & Continuity",
            icon="\U0001f9e0",  # brain
            intents=[
                HelpIntent("Save current progress", "ai export-memory"),
                HelpIntent("Export project memory", "ai memory export"),
                HelpIntent("Restore previous session", "ai import-memory"),
            ],
        ),
        HelpCategory(
            name="System Actions",
            icon="\u2699\ufe0f",  # gear
            intents=[
                HelpIntent("Validate the project", "ai validate"),
                HelpIntent("Sync project state", "ai git-sync"),
                HelpIntent("Check if everything is working", "ai validate"),
            ],
        ),
        HelpCategory(
            name="Scope Guardrails",
            icon="\U0001f6e1",  # shield
            intents=[
                HelpIntent("What's in scope for this project?", "ai scope"),
                HelpIntent("Add this to project scope", "ai scope"),
            ],
        ),
    ]

    return categories


# Category metadata for intents.yaml grouping
_CATEGORY_META = {
    "getting_started": ("Getting Started", "\U0001f680"),
    "visibility": ("Project Visibility", "\U0001f4ca"),
    "workers": ("Parallel Work (Worker Bees)", "\U0001f41d"),
    "recovery": ("Worker Recovery", "\U0001f6e0"),
    "persistence": ("State Persistence", "\U0001f4be"),
    "memory": ("Memory & Continuity", "\U0001f9e0"),
    "system": ("System Actions", "\u2699\ufe0f"),
    "guardrails": ("Scope Guardrails", "\U0001f6e1"),
}

# Display order for categories
_CATEGORY_ORDER = [
    "getting_started", "visibility", "workers", "recovery",
    "persistence", "memory", "system", "guardrails",
]


def _build_categories_from_intents(intents_path: Path, capabilities: dict | None) -> list[HelpCategory]:
    """Build HelpCategories from intents.yaml, grouping by category field."""
    data = yaml.safe_load(intents_path.read_text()) or {}
    intents = data.get("intents", [])
    if not intents:
        return []

    # Group by category
    groups: dict[str, list] = {}
    for intent in intents:
        cat = intent.get("category", "other")
        groups.setdefault(cat, []).append(intent)

    categories = []
    # Process in defined order, then any remaining
    ordered_cats = [c for c in _CATEGORY_ORDER if c in groups]
    remaining = [c for c in groups if c not in _CATEGORY_ORDER]

    for cat_id in ordered_cats + remaining:
        cat_intents = groups[cat_id]
        name, icon = _CATEGORY_META.get(cat_id, (cat_id.replace("_", " ").title(), ""))

        help_intents = []
        for i in cat_intents:
            examples = i.get("examples", [])
            prompt = examples[0] if examples else i.get("id", "")
            aliases = i.get("aliases", [])
            command = (cli_example_for_alias(aliases[0]) or "") if aliases else ""
            # Use remaining examples as description
            desc = ", ".join(f'"{e}"' for e in examples[1:3]) if len(examples) > 1 else ""
            help_intents.append(HelpIntent(prompt=prompt, command=command, description=desc))

        categories.append(HelpCategory(name=name, icon=icon, intents=help_intents))

    return categories


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
            'Say "Start or initialize the project" (or run ai init).',
            "The system will walk you through team setup and approval rules.",
            'After setup, say "Show me the current status" to see the project dashboard.',
        ]

    steps = []

    if not state.assignments_configured:
        steps.append("Configure your team: tell the orchestrator what roles and workers you need.")

    if state.task_count == 0:
        steps.append("Add tasks: describe your project goals and the orchestrator will create a task board.")
    else:
        steps.append(f'Say "Show me the current status" to see {state.task_count} tracked task(s) and progress.')

    steps.append('Say "What\'s next?" to see prioritized upcoming work.')

    if not state.memory_runtime_present:
        steps.append('Say "Resume where we left off" to start the orchestrator with automatic persistence.')
    else:
        steps.append("Session memory is active. All turns are persisted automatically.")

    return steps


def _build_commands(ai_dir: Path) -> list[HelpCommand]:
    """Build command list from the shared CLI command registry."""
    del ai_dir  # Commands are sourced from the CLI registry, not YAML.
    return [
        HelpCommand(item["name"], item["description"], item["example"])
        for item in help_json_commands()
    ]
