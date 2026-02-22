# Repo Hygiene — What Saves Where

> This is the authoritative reference for what gets committed, what stays local,
> and how to move between machines safely.

---

## The Four Buckets

### A) Canonical (COMMITTED — travels with `git clone`)

These files are the project's source of truth. They are committed and pushed.

| Path | Purpose |
|------|---------|
| `.ai/state/*.yaml` | Team, board, providers, intents, commands, project scope, locks |
| `.ai/STATUS.md` | Current project status report |
| `.ai/DECISIONS.md` | Architectural decision log |
| `.ai/METADATA.yaml` | Project ID, skeleton version, init timestamp |
| `.ai/AGENTS.md` | Operator protocol (AI behavior rules) |
| `.ai/RUNBOOK.md` | Quick reference guide |
| `.ai/core/**` | Authority model, worker rules, status protocol |
| `.ai/prompts/**` | System prompts (orchestrator, role templates) |
| `.ai/workers/roster.yaml` | Worker registry (who exists) |
| `.ai/workers/assignments.yaml` | Worker-to-ticket mappings |
| `.ai/workers/checkpoints/**/*.md` | Worker progress checkpoints (portable) |
| `.ai/workers/summaries/**/*.md` | Worker output summaries |
| `.ai/CAPABILITY_MATRIX.md` | Advertised vs implemented audit |
| `.ai/VALIDATION_REPORT.md` | Latest validation results |
| `.ai/REPO_HYGIENE.md` | This file |
| `AGENTS.md` | Root bridge (Codex auto-load) |
| `CLAUDE.md` | Root bridge (Claude Code auto-load) |

**Rule:** If you clone the repo on a new machine, all of the above is present.
Worker checkpoints survive. Project state survives. Nothing is lost.

### B) Runtime (LOCAL ONLY — `.gitignore`d)

These files are machine-local and never committed. They are rebuilt automatically.

| Path | Purpose |
|------|---------|
| `.ai_runtime/ai.db` | SQLite cache (derived from YAML, rebuildable) |
| `.ai_runtime/session/memory.db` | Session chat history (local) |
| `.ai_runtime/workers/registry.json` | Worker process references (local) |
| `.ai_runtime/workers/checkpoints/**/*.json` | Detailed runtime checkpoints (local) |
| `.ai_runtime/logs/` | Runtime logs |
| `.ai_runtime/memory_packs/` | Auto-exported session packs |
| `.ai_runtime/import_inbox/` | Drop memory packs here for auto-import |
| `.ai_runtime/system_index.json` | Cached system capability index |
| `.ai_runtime/protocol_loaded.json` | Protocol load snapshot |

**Rule:** Deleting `.ai_runtime/` loses nothing permanent. Run `ai init` or `ai rehydrate-db` to rebuild.

### C) Temp / Cache (LOCAL ONLY — safe to delete anytime)

| Path | Purpose |
|------|---------|
| `.tmp/` | Scratch workspace for transient operations |
| `.tmp_cache/` | Provider-specific or build caches |
| `__pycache__/` | Python bytecode cache |
| `*.pyc`, `*.pyo` | Compiled Python files |

**Rule:** These directories can be deleted at any time with zero impact. They are never committed.

### D) Portable Export (ON DEMAND — for switching machines)

| Artifact | How to create | How to restore |
|----------|--------------|----------------|
| Memory pack (session history) | `ai memory export` or auto-exported on exit | Drop into `.ai_runtime/import_inbox/` |
| Canonical memory pack | `ai export-memory` | `ai import-memory --in PATH` |

**Rule:** Memory packs carry session chat history. Canonical state (A) doesn't need them — it's already in git.

---

## Am I Losing Anything When Switching Computers?

| What | Kept? | How |
|------|-------|-----|
| Project state (tasks, team, decisions) | Yes | In `.ai/state/` — committed |
| Worker checkpoints | Yes | In `.ai/workers/checkpoints/` — committed |
| Worker assignments and roster | Yes | In `.ai/workers/` — committed |
| Project status report | Yes | In `.ai/STATUS.md` — committed |
| Session chat history | No | Local in `.ai_runtime/session/` — export with memory pack |
| Runtime database | No | Rebuilt from YAML automatically |
| Temp files | No | Safe to lose |

**To move machines with full chat history:**
1. `ai memory export` (or let auto-export handle it on session exit)
2. Copy the `.zip` to the new machine
3. Place it in `.ai_runtime/import_inbox/`
4. Run `ai run` — it auto-imports on startup

**Without a memory pack:** Everything still works. You have full project state, checkpoints, and decisions. You just won't have the chat transcript from previous sessions.

---

## Naming Conventions

### Worker IDs
Format: `<provider>-<role>-<n>`
Examples: `codex-dev-1`, `gemini-reviewer-1`, `claude-designer-1`

### Checkpoints
Format: `<YYYYMMDD-HHMM>-<shortlabel>.md` (canonical) or `.json` (runtime)
Examples: `20260222-1430-progress.md`, `20260222-1430-progress.json`

### Tickets
Format: `T-####` or project-specific scheme
Defined in `.ai/state/board.yaml`

### Scopes
Path globs stored in `team.yaml` per role.
Examples: `proto/**`, `cmd/**`, `docs/blueprint/**`

### State Files
All lowercase, hyphenated: `team.yaml`, `providers.yaml`, `skeleton-lock.yaml`

---

## Enforcement

These rules are enforced by:

1. **`.gitignore`** — prevents committing runtime/temp files
2. **`ai validate --hygiene`** — checks for violations
3. **`ai git-sync`** — only stages whitelisted canonical paths
4. **Protocol (`.ai/AGENTS.md`)** — agents follow these rules by design

Run `ai validate --hygiene` to check your repo's health anytime.
