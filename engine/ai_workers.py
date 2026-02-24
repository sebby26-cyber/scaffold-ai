"""
ai_workers.py — Worker bee spawning, lifecycle, and team spec parsing.

Handles:
- Parsing natural language team specs into structured config
- Writing team config to .ai/state/team.yaml
- Generating per-worker prompt files from templates
- Spawning workers (writing registry + CLI instructions)
- Worker status and stop operations

All writes go to parent project (.ai/ or .ai_runtime/). Never writes to submodule.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Provider registry is now loaded from providers.yaml via ai_providers module.
# See engine/ai_providers.py for the extensible provider registry.

# ── Role keyword → role_id mapping ──

# Ordered longest-first so "test engineer" matches before "engineer"
ROLE_KEYWORDS = [
    ("test engineer", "tester"),
    ("code reviewer", "reviewer"),
    ("project manager", "pm"),
    ("content writer", "content_writer"),
    ("developer", "developer"),
    ("reviewer", "reviewer"),
    ("designer", "designer"),
    ("researcher", "researcher"),
    ("frontend", "developer"),
    ("backend", "developer"),
    ("engineer", "developer"),
    ("tester", "tester"),
    ("coder", "developer"),
    ("dev", "developer"),
    ("ui", "designer"),
    ("ux", "designer"),
    ("research", "researcher"),
    ("analyst", "researcher"),
    ("pm", "pm"),
    ("manager", "pm"),
    ("test", "tester"),
    ("qa", "tester"),
    ("sre", "sre"),
    ("devops", "devops"),
    ("ops", "devops"),
    ("writer", "content_writer"),
    ("content", "content_writer"),
]

ROLE_TITLES = {
    "developer": "Developer",
    "reviewer": "Code Reviewer",
    "designer": "Designer",
    "researcher": "Researcher",
    "pm": "Project Manager",
    "tester": "Test Engineer",
    "sre": "SRE",
    "devops": "DevOps Engineer",
    "content_writer": "Content Writer",
}

ROLE_DEPARTMENTS = {
    "developer": "engineering",
    "reviewer": "engineering",
    "designer": "design",
    "researcher": "research",
    "pm": "management",
    "tester": "engineering",
    "sre": "operations",
    "devops": "operations",
    "content_writer": "marketing",
}


def _get_default_model(provider_name: str, project_root: Path) -> str:
    """Get default model for a provider via the provider registry."""
    from . import ai_providers
    return ai_providers.get_default_model(provider_name, project_root)


def parse_team_spec(text: str, project_root: Path | None = None) -> list[dict]:
    """Parse natural language team spec into structured role definitions.

    Examples:
        "3 Codex devs and 1 Claude designer"
        "2 Codex backend devs, 1 Codex test engineer, 1 Claude UI designer"
        "Use Codex for coding, Claude for design"

    Returns list of role dicts ready for team.yaml.
    """
    from . import ai_providers

    # Build dynamic provider name list from registry
    alias_map = ai_providers.build_provider_alias_map(project_root) if project_root else {}
    if alias_map:
        all_names = "|".join(re.escape(k) for k in sorted(alias_map.keys(), key=len, reverse=True))
    else:
        all_names = "codex|claude|anthropic|openai|cursor|gemini|google"

    roles: list[dict] = []

    # Pattern: <count> <provider> <role_words>
    # e.g. "3 Codex backend devs", "1 Gemini analyst"
    pattern = re.compile(
        rf"(\d+)\s+"                       # count
        rf"({all_names})\s+"               # provider (dynamic from registry)
        r"([\w\s/&]+?)(?:,|and\b|$)",      # role words
        re.IGNORECASE,
    )

    matches = pattern.findall(text)

    if not matches:
        # Try "Use <provider> for <role>" pattern
        use_pattern = re.compile(
            rf"({all_names})\s+for\s+([\w\s]+?)(?:,|and\b|$)",
            re.IGNORECASE,
        )
        use_matches = use_pattern.findall(text)
        for provider, role_words in use_matches:
            matches.append(("1", provider, role_words))

    for count_str, provider, role_words in matches:
        count = int(count_str)
        provider_lower = provider.lower()

        # Canonicalize provider via alias map
        canonical_provider = alias_map.get(provider_lower, provider_lower) if alias_map else provider_lower

        # Resolve role (check longest keywords first)
        role_words_clean = role_words.strip().rstrip("s").lower()
        role_id = None
        for keyword, rid in ROLE_KEYWORDS:
            if keyword in role_words_clean:
                role_id = rid
                break
        if not role_id:
            role_id = role_words_clean.replace(" ", "_")

        title = ROLE_TITLES.get(role_id, role_id.replace("_", " ").title())
        department = ROLE_DEPARTMENTS.get(role_id, "engineering")

        # Resolve model from provider registry
        model = _get_default_model(canonical_provider, project_root) if project_root else "default"

        workers = []
        for i in range(1, count + 1):
            workers.append({
                "id": f"{role_id}-{i}",
                "provider": canonical_provider,
                "model": model,
            })

        roles.append({
            "role_id": role_id,
            "title": title,
            "department": department,
            "reports_to": "orchestrator",
            "authority": "read",
            "workers": workers,
        })

    return roles


def apply_team_spec(project_root: Path, roles: list[dict]) -> str:
    """Write parsed team spec to .ai/state/team.yaml.

    Returns confirmation message.
    """
    if not yaml:
        return "Error: PyYAML is required."
    if not roles:
        return "Error: No roles parsed from team spec."

    team_data = {
        "orchestrator": {
            "role_id": "orchestrator",
            "title": "Orchestrator",
            "authority": "write",
        },
        "roles": roles,
    }

    team_path = project_root / ".ai" / "state" / "team.yaml"
    team_path.parent.mkdir(parents=True, exist_ok=True)
    team_path.write_text(yaml.dump(team_data, default_flow_style=False, sort_keys=False))

    total_workers = sum(len(r.get("workers", [])) for r in roles)
    return (
        f"Team configured: {len(roles)} role(s), {total_workers} worker(s).\n"
        f"Written to: {team_path}\n"
        'Say "Spawn worker bees" to activate them.'
    )


def generate_worker_prompts(project_root: Path) -> list[dict]:
    """Generate per-worker prompt files from role_base.md template.

    Reads team.yaml, renders prompts to .ai_runtime/workers/prompts/.
    Returns list of {worker_id, prompt_path, role, provider, model}.
    """
    if not yaml:
        return []

    team_path = project_root / ".ai" / "state" / "team.yaml"
    if not team_path.exists():
        return []

    team = yaml.safe_load(team_path.read_text()) or {}

    # Load prompt template
    template_text = _load_prompt_template(project_root)

    prompts_dir = project_root / ".ai_runtime" / "workers" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for role in team.get("roles", []):
        role_id = role.get("role_id", "unknown")
        for worker in role.get("workers", []):
            worker_id = worker.get("id", f"{role_id}-?")

            # Render template
            prompt = template_text
            prompt = prompt.replace("{{role_title}}", role.get("title", role_id))
            prompt = prompt.replace("{{role_id}}", role_id)
            prompt = prompt.replace("{{department}}", role.get("department", ""))
            prompt = prompt.replace("{{authority}}", role.get("authority", "read"))
            prompt = prompt.replace("{{authority_description}}", "read files and produce output artifacts")
            prompt = prompt.replace("{{reports_to}}", role.get("reports_to", "orchestrator"))
            prompt = prompt.replace("{{task_description}}", "(Awaiting task assignment from orchestrator)")

            # Add provider/model header
            header = (
                f"# Worker: {worker_id}\n"
                f"# Provider: {worker.get('provider', '?')}\n"
                f"# Model: {worker.get('model', '?')}\n\n"
            )

            prompt_path = prompts_dir / f"{worker_id}.md"
            prompt_path.write_text(header + prompt)

            results.append({
                "worker_id": worker_id,
                "prompt_path": str(prompt_path),
                "role": role_id,
                "provider": worker.get("provider", "?"),
                "model": worker.get("model", "?"),
            })

    return results


def _load_prompt_template(project_root: Path) -> str:
    """Load the role_base.md template, checking project then skeleton."""
    # Check project-level override
    project_template = project_root / ".ai" / "prompts" / "role_templates" / "role_base.md"
    if project_template.exists():
        return project_template.read_text()

    # Check skeleton templates
    from . import ai_init
    skeleton_dir = ai_init.find_skeleton_dir()
    skeleton_template = skeleton_dir / "templates" / ".ai" / "prompts" / "role_templates" / "role_base.md"
    if skeleton_template.exists():
        return skeleton_template.read_text()

    # Minimal fallback
    return (
        "# Worker: {{role_title}} ({{role_id}})\n\n"
        "Department: {{department}}\n"
        "Authority: {{authority}}\n"
        "Reports to: {{reports_to}}\n\n"
        "## Task\n{{task_description}}\n"
    )


def spawn_workers(project_root: Path, force: bool = False) -> str:
    """Spawn worker bees: generate prompts + write registry + print CLI instructions.

    Runs collision precheck before spawning unless --force is set.
    Returns formatted output with per-worker spawn instructions.
    """
    # Collision precheck
    if not force:
        try:
            from . import ai_collisions
            has_collisions, report = ai_collisions.precheck_collisions(project_root)
            if has_collisions:
                return (
                    "SPAWN ABORTED — Hard file collisions detected:\n\n"
                    + report
                    + "\nResolve collisions or use --force to override."
                )
        except Exception:
            pass  # Don't block spawn on precheck failures

    workers = generate_worker_prompts(project_root)
    if not workers:
        return (
            "No workers to spawn. Configure your team first.\n"
            'Say "Set up a team: 3 Codex devs + 1 Claude designer" to configure.'
        )

    # Write registry
    registry = {
        "spawned_at": datetime.now(timezone.utc).isoformat(),
        "workers": [],
    }

    lines = [f"Spawning {len(workers)} worker(s):\n"]

    from . import ai_providers

    for w in workers:
        cli = ai_providers.get_cli_command(w["provider"], project_root)
        model_arg = ai_providers.get_model_arg(w["provider"], project_root)
        prompt_path = w["prompt_path"]

        # Build CLI command with optional model flag
        cmd_parts = [cli, "--prompt", prompt_path]
        if model_arg and w["model"] and w["model"] != "default":
            cmd_parts.extend([model_arg, w["model"]])
        run_cmd = " ".join(cmd_parts)

        entry = {
            "worker_id": w["worker_id"],
            "role": w["role"],
            "provider": w["provider"],
            "model": w["model"],
            "prompt_path": prompt_path,
            "cli": cli,
            "status": "ready",
            "last_heartbeat_at": None,
            "last_output_at": None,
            "last_checkpoint_id": None,
            "retry_count": 0,
        }
        registry["workers"].append(entry)

        lines.append(f"  {w['worker_id']} ({w['role']})")
        lines.append(f"    Provider: {w['provider']} | Model: {w['model']}")
        lines.append(f"    Prompt:   {prompt_path}")
        lines.append(f"    Run:      {run_cmd}")
        lines.append("")

    # Write registry
    registry_dir = project_root / ".ai_runtime" / "workers"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_path = registry_dir / "registry.json"
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))

    # Write canonical state (portable, committed to git)
    from . import ai_worker_state
    ai_worker_state.write_roster(project_root, registry["workers"])
    for w in workers:
        ai_worker_state.write_summary(project_root, w["worker_id"], {
            "role": w["role"],
            "provider": w["provider"],
            "model": w["model"],
            "status": "ready",
        })

    lines.append(f"Registry written to: {registry_path}")
    lines.append("Canonical state written to: .ai/workers/")
    lines.append("\nRun the commands above in separate terminals to start each worker.")

    return "\n".join(lines)


def get_worker_status(project_root: Path, show_stalled: bool = False) -> str:
    """Read worker registry and return formatted status.

    Falls back to canonical roster if runtime registry is missing.
    If show_stalled is True, appends stall detection results.
    """
    registry_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    workers = []
    spawned_at = "?"

    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text())
            workers = registry.get("workers", [])
            spawned_at = registry.get("spawned_at", "?")
        except Exception:
            pass

    # Fall back to canonical roster if no runtime registry
    if not workers:
        from . import ai_worker_state
        roster = ai_worker_state.load_roster(project_root)
        if roster:
            workers = roster
            spawned_at = "(from canonical roster)"
        else:
            return "No workers spawned yet. Say \"Spawn worker bees\" to start."

    W = 60
    sep = "\u2500" * W
    lines = [f"\u250c{sep}\u2510"]
    lines.append(_wbox(f"WORKER BEES  ({len(workers)})", W))
    lines.append(f"\u2514{sep}\u2518")
    lines.append(f"  Spawned: {spawned_at}")
    lines.append("")

    for w in workers:
        wid = w.get("worker_id", w.get("id", "?"))
        status = w.get("status", "?")
        provider = w.get("provider", "?")
        model = w.get("model", "?")

        # Status badge
        if status == "active":
            badge = "\u25cf"  # ●
        elif status == "ready":
            badge = "\u25cb"  # ○
        elif status == "stopped":
            badge = "\u25a0"  # ■
        else:
            badge = "\u25a1"  # □

        lines.append(f"  {badge}  {wid:<28} {w.get('role', '?')}")
        lines.append(f"     {provider}/{model}   status: {status}")

        if w.get("last_heartbeat_at"):
            lines.append(f"     heartbeat: {w['last_heartbeat_at']}")
        if w.get("last_checkpoint_id"):
            lines.append(f"     checkpoint: {w['last_checkpoint_id']}")
        if w.get("retry_count", 0) > 0:
            lines.append(f"     retries: {w['retry_count']}")
        lines.append("")

    # Legend
    lines.append("  \u25cf active   \u25cb ready   \u25a0 stopped   \u25a1 other")

    # Stall detection (if requested)
    if show_stalled:
        try:
            from . import ai_stall_detect
            stalled = ai_stall_detect.detect_all_stalled(project_root)
            if stalled:
                lines.append("")
                lines.append(ai_stall_detect.format_stall_report(stalled))
            else:
                lines.append("\n  No stalled workers detected.")
        except Exception:
            pass

    return "\n".join(lines)


def _wbox(text: str, width: int) -> str:
    """Center text inside box borders."""
    pad = (width - len(text)) // 2
    return f"\u2502{' ' * pad}{text}{' ' * (width - pad - len(text))}\u2502"


def stop_workers(project_root: Path) -> str:
    """Mark all workers as stopped in the registry."""
    registry_path = project_root / ".ai_runtime" / "workers" / "registry.json"
    if not registry_path.exists():
        return "No workers to stop."

    try:
        registry = json.loads(registry_path.read_text())
    except Exception:
        return "Error reading worker registry."

    count = 0
    for w in registry.get("workers", []):
        if w.get("status") != "stopped":
            w["status"] = "stopped"
            count += 1

    registry["stopped_at"] = datetime.now(timezone.utc).isoformat()
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))

    return f"Stopped {count} worker(s). Registry updated."
