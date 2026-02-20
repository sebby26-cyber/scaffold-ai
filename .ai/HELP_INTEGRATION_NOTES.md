# Help/Guide Integration Notes

## What Exists

### Skeleton (engine/help/)
- **model.py** — `HelpGuide` dataclass (JSON-serializable), mirrors reporting architecture
- **builder.py** — `generate_help(project_root, adapter=None)` inspects project state
- **renderer.py** — `render_help_terminal(guide)` produces clean terminal output
- **json_output.py** — `render_help_json(guide)` for Kanban UI integration

### CLI
- `ai help` — terminal output
- `ai help --json` — JSON output
- `ai guide` — alias

### Orchestrator (ai run loop)
Natural language intents handled via commands.yaml:
- "help", "guide", "guide me", "how do I use this", "what can you do", "show me the guide", "commands"

### State Awareness
The help builder inspects:
- `.ai/` exists and has `state/team.yaml` → `initialized`
- `team.yaml` has workers configured → `assignments_configured` + `worker_count`
- `board.yaml` task count → `task_count`
- `.ai_runtime/session/memory.db` exists → `memory_runtime_present`
- `.ai_runtime/memory_packs/` or `import_inbox/` has files → `memory_pack_available`

Quick start steps adapt based on these findings.

## KROV Integration Pattern

KROV (or any project using the skeleton as a submodule) should:

1. **Invoke only** — call `handle_help(project_root)` or use the CLI
2. **Optionally provide an adapter** — `report_adapter.py` can include a `project_name` that the help system picks up
3. **Never duplicate** help logic — all rendering and state detection lives in the submodule

### Example adapter override:
```python
# In KROV's report_adapter.py
def build_adapter_data(project_root):
    return {
        "project_name": "KROV",
        # ... other adapter fields for status reporting
    }
```

The help system reads `project_name` from the adapter if available, falls back to METADATA.yaml.

## Test Coverage
- Test 19: Help/guide generation (model, terminal, JSON)
- Test 20: Help command handler (terminal + JSON modes)
