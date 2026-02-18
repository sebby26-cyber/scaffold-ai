# Implementation Plan: Automatic Persistence

## What Exists

- **memory_core/** module with full API: add_message, get_context, search, facts, summaries, packs, redaction, policy
- **Policy template** at `templates/.ai/state/memory_policy.yaml` with per-namespace persist modes
- **CLI hooks** for manual `ai memory export/import/purge`
- **Canonical persistence** via explicit `ai git-sync` (whitelist enforced)
- **STATUS.md** updated only on `ai status` or `ai git-sync`
- **Run loop** is a simple REPL with no persistence between turns
- **Session memory commands** not registered in `commands.yaml`

## What Is Missing

1. **No auto-persistence** — run_loop does not persist user/assistant turns to session memory
2. **No auto git-sync** — canonical state changes (board, decisions) require manual commit
3. **No auto STATUS.md update** — only happens on explicit status/git-sync commands
4. **No auto memory pack export** — no shutdown hook, no periodic export
5. **No auto memory pack import** — no import_inbox check on startup
6. **No distillation trigger** — distill_every_n_turns policy field is unused
7. **Missing command registrations** — migrate, session-memory commands absent from commands.yaml

## What Will Change

### ai_run.py
- `run_loop()` gains a `SessionMemory` instance, persists every user input and command response
- `run_loop()` calls `_maybe_distill()` every N turns (per policy)
- `run_loop()` auto-exports session memory pack on graceful exit
- `run_loop()` checks `import_inbox/` on startup for auto-import
- Handlers that modify canonical state (`handle_git_sync`, board/approval changes) trigger STATUS.md re-render

### ai_init.py
- `setup_runtime()` creates `import_inbox/` directory alongside existing dirs

### engine/memory_core/api.py
- Add `get_message_count()` method for distillation trigger checks

### templates/.ai/state/commands.yaml
- Register `migrate`, `memory-export`, `memory-import`, `memory-purge`

### templates/.ai/state/memory_policy.yaml
- Add `auto_export_on_exit: true` and `auto_import_inbox: true` fields

## What Remains Stable

- **memory_core/ API boundary** — no breaking changes to public methods
- **Canonical state model** — `.ai/state/*.yaml` structure unchanged
- **Git-sync whitelist** — same paths, same enforcement
- **Policy enforcement** — persist modes, redaction, role filtering unchanged
- **Self-check tests 1-13** — all existing tests remain passing
- **README 3-layer structure** — no reorganization

## Refactors Required

- None breaking. All changes are additive hooks wired into existing lifecycle points.
