"""Shared CLI command catalog for help rendering and command normalization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CliCommandSpec:
    cli_name: str
    help_spec: str
    help_description: str
    json_description: str
    json_example: str
    aliases: tuple[str, ...] = ()


COMMAND_SPECS: tuple[CliCommandSpec, ...] = (
    CliCommandSpec(
        "init",
        "init",
        "Initialize .ai/ and .ai_runtime/ in the project",
        "Initialize .ai/ and .ai_runtime/ in the project",
        "ai init",
        aliases=("/init",),
    ),
    CliCommandSpec(
        "run",
        "run",
        "Start the interactive orchestrator loop",
        "Start the interactive orchestrator loop",
        "ai run",
    ),
    CliCommandSpec(
        "help",
        "help [--json]",
        "Context-aware help and usage guide",
        "Show this guide",
        "ai help",
        aliases=("/help", "/guide", "guide"),
    ),
    CliCommandSpec(
        "status",
        "status",
        "Generate and print project status report",
        "Project status report",
        "ai status",
        aliases=("/status",),
    ),
    CliCommandSpec(
        "validate",
        "validate [--full|--hygiene]",
        "Validate YAML / full harness / repo hygiene",
        "Validate YAML against schemas",
        "ai validate",
        aliases=("/validate",),
    ),
    CliCommandSpec(
        "export-memory",
        "export-memory [--out PATH]",
        "Export memory pack for portability",
        "Export memory pack",
        "ai export-memory --out pack.zip",
        aliases=("/export-memory",),
    ),
    CliCommandSpec(
        "import-memory",
        "import-memory --in PATH",
        "Import a memory pack",
        "Import a memory pack",
        "ai import-memory --in pack.zip",
        aliases=("/import-memory",),
    ),
    CliCommandSpec(
        "rehydrate-db",
        "rehydrate-db",
        "Rebuild SQLite DB from canonical YAML",
        "Rebuild local DB from YAML",
        "ai rehydrate-db",
        aliases=("/rehydrate-db", "/rehydrate"),
    ),
    CliCommandSpec(
        "git-sync",
        "git-sync",
        "Commit canonical state files to git",
        "Commit canonical state to git",
        "ai git-sync",
        aliases=("/git-sync",),
    ),
    CliCommandSpec(
        "migrate",
        "migrate",
        "Apply new template files (non-destructive)",
        "Apply new template files",
        "ai migrate",
        aliases=("/migrate",),
    ),
    CliCommandSpec(
        "force-sync",
        "force-sync [--git]",
        "Force flush state + checkpoint all workers",
        "Force flush state + checkpoint",
        "ai force-sync",
        aliases=("/force-sync", "/sync"),
    ),
    CliCommandSpec(
        "spawn-workers",
        "spawn-workers",
        "Generate worker prompts and spawn worker bees",
        "Spawn worker bees",
        "ai spawn-workers",
        aliases=("/spawn-workers",),
    ),
    CliCommandSpec(
        "workers-status",
        "workers-status",
        "Show current status of all worker bees",
        "Show worker status",
        "ai workers-status",
        aliases=("/workers-status",),
    ),
    CliCommandSpec(
        "stop-workers",
        "stop-workers",
        "Stop all active worker bees",
        "Stop all workers",
        "ai stop-workers",
        aliases=("/stop-workers",),
    ),
    CliCommandSpec(
        "configure-team",
        "configure-team --spec TEXT",
        "Parse team spec and write to team.yaml",
        "Configure team roles",
        "ai configure-team --spec \"3 Codex devs and 1 Claude designer\"",
        aliases=("/configure-team",),
    ),
    CliCommandSpec(
        "workers-resume",
        "workers-resume",
        "Resume stalled or paused workers",
        "Resume stalled workers",
        "ai workers-resume",
        aliases=("/workers-resume",),
    ),
    CliCommandSpec(
        "workers-pause",
        "workers-pause --worker_id ID",
        "Pause a worker and save checkpoint",
        "Pause a worker",
        "ai workers-pause --worker_id dev-1",
        aliases=("/workers-pause",),
    ),
    CliCommandSpec(
        "workers-restart",
        "workers-restart --worker_id ID",
        "Restart a worker from scratch",
        "Restart a worker",
        "ai workers-restart --worker_id dev-1",
        aliases=("/workers-restart",),
    ),
    CliCommandSpec(
        "checkpoint-workers",
        "checkpoint-workers",
        "Force checkpoint all active workers",
        "Force checkpoint all active workers",
        "ai checkpoint-workers",
        aliases=("/checkpoint-workers",),
    ),
    CliCommandSpec(
        "show-checkpoints",
        "show-checkpoints",
        "Show latest checkpoint per worker",
        "Show latest checkpoint per worker",
        "ai show-checkpoints",
        aliases=("/show-checkpoints",),
    ),
    CliCommandSpec(
        "scope",
        "scope [--text TEXT]",
        "Show or check project scope boundaries",
        "Show/check project scope",
        "ai scope",
        aliases=("/scope",),
    ),
    CliCommandSpec(
        "memory export",
        "memory export [--out PATH]",
        "Export session memory pack (advanced)",
        "Export session memory pack",
        "ai memory export",
        aliases=("/memory-export", "memory-export"),
    ),
    CliCommandSpec(
        "memory import",
        "memory import --in PATH",
        "Import session memory pack (advanced)",
        "Import session memory pack",
        "ai memory import --in pack.zip",
        aliases=("/memory-import", "memory-import"),
    ),
    CliCommandSpec(
        "memory purge",
        "memory purge [--ns NS]",
        "Purge session memory (advanced)",
        "Purge session memory",
        "ai memory purge --ns orchestrator --days 30",
        aliases=("/memory-purge", "memory-purge"),
    ),
)


def cli_help_command_lines() -> list[str]:
    """Return aligned command lines for the CLI help output."""
    width = max(len(spec.help_spec) for spec in COMMAND_SPECS)
    return [
        f"  {spec.help_spec.ljust(width)}  {spec.help_description}"
        for spec in COMMAND_SPECS
    ]


def help_json_commands() -> list[dict[str, str]]:
    """Return help --json command entries from the shared registry."""
    return [
        {
            "name": spec.cli_name,
            "description": spec.json_description,
            "example": spec.json_example,
        }
        for spec in COMMAND_SPECS
    ]


def implemented_cli_command_names() -> set[str]:
    return {spec.cli_name for spec in COMMAND_SPECS}


def cli_example_for_alias(alias: str) -> str | None:
    """Map an intent alias or command id to the actual CLI invocation example."""
    token = (alias or "").strip()
    if not token:
        return None

    for spec in COMMAND_SPECS:
        if token == spec.cli_name or token in spec.aliases:
            return spec.json_example
        if token.startswith("/") and token[1:] == spec.cli_name:
            return spec.json_example

    if token.startswith("/"):
        token = token[1:]
    return f"ai {token}" if token else None
