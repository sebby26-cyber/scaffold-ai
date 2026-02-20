"""
ai_run.py — Orchestrator loop runner and command dispatcher.

Routes CLI commands to their handlers. Also provides the `ai run` loop
with automatic session memory persistence, auto-import on startup,
and auto-export on graceful exit.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import ai_db, ai_git, ai_init, ai_memory, ai_state, ai_validate


def _load_adapter_data(project_root: Path) -> dict | None:
    """Try to load the project's report_adapter.

    Looks for report_adapter.py in the project root.
    Returns adapter_data dict or None if not available.
    """
    adapter_path = project_root / "report_adapter.py"
    if not adapter_path.exists():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("report_adapter", str(adapter_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.build_adapter_data(project_root)
    except Exception:
        return None


def find_schemas_dir() -> Path:
    """Find the schemas directory in the skeleton repo."""
    return ai_init.find_skeleton_dir() / "schemas"


# ── Command Handlers ──


def handle_status(project_root: Path, **kwargs) -> str:
    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"
    ai_state.reconcile(ai_dir, runtime_dir)

    # Use new reporting pipeline if adapter is available
    adapter_data = _load_adapter_data(project_root)
    if adapter_data is not None:
        from .reporting import generate_report, render_terminal, render_json
        from .reporting.status_md import write_status_md

        report = generate_report(adapter_data)
        write_status_md(report, ai_dir)

        if kwargs.get("json"):
            return render_json(report)
        return render_terminal(report)

    # Fallback to legacy render
    return ai_state.render_status(ai_dir, runtime_dir)


def handle_export_memory(project_root: Path, out: str | None = None, **kwargs) -> str:
    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"
    skeleton_dir = ai_init.find_skeleton_dir()
    version = ai_git.get_skeleton_version(skeleton_dir)
    path = ai_memory.export_memory(ai_dir, runtime_dir, version, out)
    return f"Memory pack exported to: {path}"


def handle_import_memory(project_root: Path, in_path: str = "", **kwargs) -> str:
    if not in_path:
        return "Error: --in <path> is required for import-memory."
    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"
    return ai_memory.import_memory(ai_dir, runtime_dir, in_path)


def handle_rehydrate_db(project_root: Path, **kwargs) -> str:
    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

    # Delete existing DB and rebuild
    db_path = ai_db.get_db_path(runtime_dir)
    if db_path.exists():
        db_path.unlink()

    ai_db.create_db(runtime_dir)
    updated = ai_state.reconcile(ai_dir, runtime_dir)
    return "Database rehydrated from canonical YAML state."


def handle_validate(project_root: Path, **kwargs) -> str:
    ai_dir = project_root / ".ai"
    schemas_dir = find_schemas_dir()
    results = ai_validate.validate_all(ai_dir, schemas_dir)

    lines = []
    all_valid = True
    for filename, errors in results.items():
        if errors:
            all_valid = False
            lines.append(f"  FAIL  {filename}")
            for err in errors:
                lines.append(f"        {err}")
        else:
            lines.append(f"  OK    {filename}")

    header = "Validation: ALL PASSED" if all_valid else "Validation: ERRORS FOUND"
    return header + "\n" + "\n".join(lines)


def handle_migrate(project_root: Path, **kwargs) -> str:
    """Non-destructive template migration."""
    skeleton_dir = ai_init.find_skeleton_dir()
    ai_dir = project_root / ".ai"

    ai_init.copy_templates(skeleton_dir, project_root)
    meta = ai_init.stamp_metadata(project_root, skeleton_dir)

    lines = [
        "Migration complete (non-destructive).",
        f"  Skeleton version: {meta.get('skeleton_version', 'unknown')}",
        "  New template files added (if any were missing).",
        "  Existing files were NOT overwritten.",
        "  Run 'ai validate' to check schema compliance.",
    ]
    return "\n".join(lines)


def handle_session_memory_export(
    project_root: Path,
    out: str | None = None,
    namespaces: str | None = None,
    **kwargs,
) -> str:
    """Export session memory pack."""
    from .memory_core.api import SessionMemory

    mem = SessionMemory(project_root)
    try:
        ns_list = namespaces.split(",") if namespaces else None
        out_path = out or str(project_root / ".ai_runtime" / "session" / "memory_export")
        result_path = mem.export_pack(out_path, ns_list)
        return f"Session memory exported to: {result_path}"
    finally:
        mem.close()


def handle_session_memory_import(
    project_root: Path,
    in_path: str = "",
    **kwargs,
) -> str:
    """Import session memory pack."""
    if not in_path:
        return "Error: --in <path> is required."

    from .memory_core.api import SessionMemory

    mem = SessionMemory(project_root)
    try:
        counts = mem.import_pack(in_path)
        parts = [f"{k}: {v}" for k, v in counts.items() if v > 0]
        return f"Session memory imported. {', '.join(parts)}."
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    finally:
        mem.close()


def handle_session_memory_purge(
    project_root: Path,
    namespace: str | None = None,
    days: str | None = None,
    **kwargs,
) -> str:
    """Purge session memory."""
    from .memory_core.api import SessionMemory

    mem = SessionMemory(project_root)
    try:
        days_int = int(days) if days else None
        counts = mem.purge(namespace=namespace, older_than_days=days_int)
        parts = [f"{k}: {v}" for k, v in counts.items()]
        return f"Session memory purged. {', '.join(parts)}."
    finally:
        mem.close()


def handle_help(project_root: Path, **kwargs) -> str:
    """Generate context-aware help/guide."""
    from .help import generate_help, render_help_terminal, render_help_json

    adapter = _load_adapter_data(project_root)
    adapter_dict = None
    if adapter is not None:
        adapter_dict = {"project_name": adapter.get("project_name")}

    guide = generate_help(project_root, adapter_dict)

    if kwargs.get("json"):
        return render_help_json(guide)
    return render_help_terminal(guide)


def handle_git_sync(project_root: Path, message: str | None = None, **kwargs) -> str:
    # First render status to update STATUS.md
    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"
    ai_state.reconcile(ai_dir, runtime_dir)
    ai_state.render_status(ai_dir, runtime_dir)

    success, msg = ai_git.git_sync(project_root, message)
    return msg


# ── Command Registry ──


HANDLERS = {
    "handle_status": handle_status,
    "handle_help": handle_help,
    "handle_export_memory": handle_export_memory,
    "handle_import_memory": handle_import_memory,
    "handle_rehydrate_db": handle_rehydrate_db,
    "handle_validate": handle_validate,
    "handle_git_sync": handle_git_sync,
    "handle_migrate": handle_migrate,
    "handle_session_memory_export": handle_session_memory_export,
    "handle_session_memory_import": handle_session_memory_import,
    "handle_session_memory_purge": handle_session_memory_purge,
}


def load_command_registry(project_root: Path) -> dict:
    """Load commands.yaml and build a lookup: alias -> handler_name."""
    try:
        import yaml
    except ImportError:
        return {}

    commands_path = project_root / ".ai" / "state" / "commands.yaml"
    if not commands_path.exists():
        return {}

    data = yaml.safe_load(commands_path.read_text()) or {}
    registry = {}
    for cmd in data.get("commands", []):
        handler = cmd.get("handler", "")
        for alias in [cmd.get("name", "")] + cmd.get("aliases", []):
            if alias:
                registry[alias.lower().strip().lstrip("/")] = handler
    return registry


def dispatch_command(project_root: Path, command: str, **kwargs) -> str:
    """Dispatch a command string to its handler."""
    registry = load_command_registry(project_root)
    normalized = command.lower().strip().lstrip("/")

    handler_name = registry.get(normalized)
    if not handler_name:
        return f"Unknown command: '{command}'. Run 'ai --help' for available commands."

    handler = HANDLERS.get(handler_name)
    if not handler:
        return f"Handler '{handler_name}' not implemented."

    return handler(project_root, **kwargs)


# ── Auto-Persistence Helpers ──


def _auto_import_inbox(project_root: Path) -> str | None:
    """Check import_inbox/ for memory packs and auto-import the newest.

    Returns a status message if something was imported, None otherwise.
    """
    from .memory_core.api import SessionMemory

    inbox = project_root / ".ai_runtime" / "import_inbox"
    if not inbox.exists():
        return None

    # Find packs: directories with manifest.json or .zip files
    candidates: list[Path] = []
    for item in inbox.iterdir():
        if item.suffix == ".zip" and item.is_file():
            candidates.append(item)
        elif item.is_dir() and (item / "manifest.json").exists():
            candidates.append(item)

    if not candidates:
        return None

    # Import the newest by modification time
    newest = max(candidates, key=lambda p: p.stat().st_mtime)

    mem = SessionMemory(project_root)
    try:
        counts = mem.import_pack(newest)
    except (FileNotFoundError, ValueError) as e:
        return f"Auto-import failed for {newest.name}: {e}"
    finally:
        mem.close()

    # Move to processed/
    processed = inbox / "processed"
    processed.mkdir(exist_ok=True)
    dest = processed / newest.name
    if dest.exists():
        import shutil
        if dest.is_dir():
            shutil.rmtree(str(dest))
        else:
            dest.unlink()
    newest.rename(dest)

    parts = [f"{k}: {v}" for k, v in counts.items() if v > 0]
    return f"Auto-imported session memory from {newest.name}. {', '.join(parts)}."


def _auto_export_pack(project_root: Path) -> str | None:
    """Export a session memory pack to memory_packs/ on exit.

    Returns path to export, or None on failure.
    """
    from .memory_core.api import SessionMemory

    packs_dir = project_root / ".ai_runtime" / "memory_packs"
    packs_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = packs_dir / f"session_pack_{ts}.zip"

    mem = SessionMemory(project_root)
    try:
        # Only export if there's actually data
        count = mem.get_message_count("default", "orchestrator")
        if count == 0:
            return None
        result = mem.export_pack(str(out_path))
        return result
    except Exception:
        return None
    finally:
        mem.close()


def _check_distillation(
    mem,
    session_id: str,
    namespace: str,
    turn_count: int,
) -> bool:
    """Check if distillation should be triggered. Returns True if due.

    Does NOT call any model. Just checks the interval and returns
    whether the orchestrator should run distillation externally.
    """
    interval = mem.get_distill_interval(namespace)
    if interval <= 0:
        return False
    return (turn_count % interval) == 0 and turn_count > 0


def _log_canonical_event(project_root: Path, event_type: str, detail: str):
    """Log a significant event to the canonical events database."""
    runtime_dir = project_root / ".ai_runtime"
    try:
        conn = ai_db.connect_db(runtime_dir)
        ai_db.add_event(conn, "system", event_type, {"detail": detail})
        conn.close()
    except Exception:
        pass  # Non-critical: don't break flow for logging failures


# ── Protocol Loading ──


def load_protocol(project_root: Path) -> str | None:
    """Load .ai/AGENTS.md operator protocol.

    Returns the protocol text, or None if not found.
    """
    protocol_path = project_root / ".ai" / "AGENTS.md"
    if protocol_path.exists():
        return protocol_path.read_text()
    return None


def get_protocol_summary(project_root: Path) -> dict:
    """Return a machine-readable protocol summary for runtime context.

    Used by external agents (Codex, Claude CLI) to bootstrap deterministic behavior.
    """
    import json

    protocol_text = load_protocol(project_root)
    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

    summary = {
        "protocol_loaded": protocol_text is not None,
        "canonical_state_present": ai_dir.is_dir() and (ai_dir / "state").is_dir(),
        "runtime_present": runtime_dir.is_dir(),
        "command_prefix": "/",
        "available_commands": list(load_command_registry(project_root).keys()),
    }

    # Write to runtime for external tools
    runtime_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = runtime_dir / "protocol_loaded.json"
    snapshot_path.write_text(json.dumps(summary, indent=2))

    return summary


# ── Run Loop (with Auto-Persistence) ──


def run_loop(project_root: Path):
    """Interactive orchestrator loop with automatic session memory persistence.

    On startup:
      - Reconcile canonical YAML into SQLite
      - Auto-import from import_inbox/ if packs are present

    On each turn:
      - Persist user input to session memory (namespace: orchestrator)
      - Persist command response to session memory
      - Check distillation interval; print reminder if due

    On exit:
      - Auto-export session memory pack to memory_packs/
      - Re-render STATUS.md from current canonical state
    """
    from .memory_core.api import SessionMemory

    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

    # Ensure runtime dirs exist (handles fresh clone without full init)
    for subdir in ["session", "import_inbox", "memory_packs"]:
        (runtime_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Reconcile canonical state
    ai_state.reconcile(ai_dir, runtime_dir)

    # Initialize session memory
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    mem = SessionMemory(project_root)

    # Load operator protocol
    protocol = load_protocol(project_root)
    if protocol:
        get_protocol_summary(project_root)
        print("  Protocol loaded.")
    else:
        print("  [WARN] .ai/AGENTS.md not found. Run 'ai init' to create it.")

    # Auto-import from inbox
    import_msg = _auto_import_inbox(project_root)
    if import_msg:
        print(f"  {import_msg}")

    print("Scaffold AI running. Type commands or 'quit' to exit.")
    print("Available: status, export-memory, import-memory, rehydrate-db, validate, git-sync")
    print("Session memory is active. All turns are persisted automatically.")
    print()

    turn_count = 0

    try:
        while True:
            try:
                cmd = input("ai> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not cmd:
                continue
            if cmd.lower() in ("quit", "exit", "q"):
                print("Exiting.")
                break

            # Persist user input
            mem.add_message(session_id, "orchestrator", "user", cmd)
            turn_count += 1

            # Parse simple args
            parts = cmd.split()
            command = parts[0]
            kwargs = {}

            i = 1
            while i < len(parts):
                if parts[i].startswith("--"):
                    key = parts[i][2:].replace("-", "_")
                    if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                        kwargs[key] = parts[i + 1]
                        i += 2
                    else:
                        kwargs[key] = True
                        i += 1
                else:
                    i += 1

            result = dispatch_command(project_root, command, **kwargs)
            print(result)
            print()

            # Persist command response
            mem.add_message(session_id, "orchestrator", "assistant", result)

            # Log state-changing commands as canonical events
            state_cmds = {"status", "git-sync", "validate", "migrate", "rehydrate-db"}
            if command.lower() in state_cmds:
                _log_canonical_event(project_root, f"cmd_{command.lower()}", result[:200])

            # Check distillation interval
            if _check_distillation(mem, session_id, "orchestrator", turn_count):
                print("  [Note] Distillation interval reached. Consider running:")
                print('  "Summarize and distill this session."')
                print()

    finally:
        # Auto-export on exit
        try:
            export_path = _auto_export_pack(project_root)
            if export_path:
                print(f"  Session memory auto-exported to: {export_path}")
        except Exception:
            pass  # Don't crash on export failure

        # Re-render STATUS.md on exit
        try:
            ai_state.render_status(ai_dir, runtime_dir)
        except Exception:
            pass

        mem.close()
