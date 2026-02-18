# Universal AI Team Skeleton

An orchestration engine and canonical state framework for running AI agent teams on real projects. Single-writer architecture, repo-canonical state, portable memory packs.

## Overview

- **Single orchestrator** with write authority — all workers are read-only
- **YAML-first state** committed to your project repo (human-auditable, git-diffable)
- **SQLite cache** rebuilt on demand from canonical state (never committed)
- **Portable memory packs** for moving context between machines
- **Submodule-ready** — engine updates propagate via pointer bumps, never touching project state

---

## Table of Contents

- [Quick Start](#quick-start)
- [Human Interaction Model](#human-interaction-model)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Authority Model](#authority-model)
- [Persistence Model](#persistence-model)
- [Memory Packs](#memory-packs)
- [Installation](#installation)
- [First Run](#first-run)
- [Command Reference](#command-reference)
- [Status Reporting](#status-reporting)
- [Git Sync](#git-sync)
- [Updating the Skeleton](#updating-the-skeleton)
- [Legacy Migration](#legacy-migration)
- [Blueprint Handling](#blueprint-handling)
- [Workflow Example](#workflow-example)
- [Multi-Machine Continuity](#multi-machine-continuity)
- [Troubleshooting](#troubleshooting)
- [Design Decisions](#design-decisions)
- [Future Extensions](#future-extensions)
- [Quick Reference](#quick-reference)

---

## Quick Start

```bash
# Add skeleton as submodule
git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton

# Initialize
python vendor/ai-skeleton/engine/ai init

# Check status
python vendor/ai-skeleton/engine/ai status

# Validate state
python vendor/ai-skeleton/engine/ai validate
```

Or create a wrapper at your project root:

```bash
#!/usr/bin/env bash
exec python3 "$(dirname "$0")/vendor/ai-skeleton/engine/ai" "$@"
```

---

## Human Interaction Model

> Users interact via prompts, not commands.

| Layer | Who | How |
|---|---|---|
| Human Interaction | You | Natural language — speak in goals |
| AI Execution | Orchestrator | Internal commands, YAML, git ops |

You speak. The Orchestrator acts. You never need to touch the internals.

### Talking to the Orchestrator

The following are real prompts you can use. No commands. No syntax. Just intent.

**Status and Awareness**

```
"Give me a status report."
"What is everyone working on right now?"
"Show progress and blockers."
"Summarize what changed since yesterday."
"What's next?"
```

**Planning and Delegation**

```
"Break this into tasks and assign the team."
"Who should handle this feature?"
"Reprioritize based on current blockers."
"We need to add X to the backlog."
```

**Approvals and Decisions**

```
"Approve this and continue."
"Reject this and revise."
"What decisions are waiting on me?"
"Proceed to release."
```

**Continuity and Handoff**

```
"Prepare a handoff summary."
"Commit current state to the repo."
"Save memory so I can continue on another machine."
"Export the full project memory."
```

**Team Setup**

```
"Set up a team with developers, a PM, and a UI designer."
"I want coding handled by Codex and design by Claude."
"Add another developer worker."
```

### Intent-to-Command Mapping

These commands run under the hood. The Orchestrator maps your intent automatically.

| What you say | Internal action |
|---|---|
| "Give me a status report." | `ai status` |
| "Save / export memory." | `ai export-memory` |
| "Load / import memory." | `ai import-memory` |
| "Commit / sync state." | `ai git-sync` |
| "Rebuild runtime state." | `ai rehydrate-db` |
| "Validate the project state." | `ai validate` |
| "Initialize / set up AI." | `ai init` |
| "Update the engine." | `git submodule update` + `ai migrate` |

### How the Orchestrator Thinks

```
You express intent (natural language)
        |
Orchestrator interprets what you want
        |
Selects internal actions (commands, file updates, git ops)
        |
Updates canonical project state
        |
Produces human-readable output
        |
Commits to repo if state changed
```

### Minimum User Knowledge

**You need to know:**
- How to talk to the Orchestrator in plain language
- How to approve or reject work when asked
- How to ask for status or progress at any time

**You do not need to know:**
- CLI commands, YAML structure, SQLite internals, git operations, or worker delegation logic

If operating this system requires you to understand any of those, that is a gap in the system — not a knowledge gap in you.

---

## Architecture

```
Your Project Repository
|
|-- .ai/                        <- canonical state (committed)
|   |-- state/
|   |   |-- team.yaml           <- roles, workers, authority
|   |   |-- board.yaml          <- task board (kanban)
|   |   |-- approvals.yaml      <- approval triggers and log
|   |   +-- commands.yaml       <- command registry
|   |-- core/                   <- authority model, protocols
|   |-- prompts/                <- orchestrator + role templates
|   |-- STATUS.md               <- rendered project status
|   |-- DECISIONS.md            <- append-only decision log
|   |-- RUNBOOK.md              <- project-specific runbook
|   +-- METADATA.yaml           <- project ID, skeleton version
|
|-- .ai_runtime/                <- local cache (never committed)
|   |-- ai.db                   <- SQLite (rebuildable)
|   |-- logs/
|   |-- session/
|   +-- memory_pack_cache/
|
|-- vendor/ai-skeleton/         <- skeleton submodule
|   +-- engine/
|       |-- ai                  <- CLI entrypoint
|       |-- ai_init.py
|       |-- ai_run.py
|       |-- ai_state.py
|       |-- ai_db.py
|       |-- ai_git.py
|       |-- ai_memory.py
|       +-- ai_validate.py
|
+-- [your project files]
```

### `.ai/` — Canonical State

Source of truth for all orchestration state.

- **Committed** after every meaningful change
- **Human-auditable** — plain YAML and Markdown
- **Portable** — clone the repo and the full state is present
- Always wins over the local database

### `.ai_runtime/` — Local Cache

Exists only on the local machine.

- **Never committed** (`.gitignore` entry created by `ai init`)
- **Fully rebuildable** from canonical state via `ai rehydrate-db`
- Losing it has zero impact on project state

### Submodule

Engine upgrades flow through submodule pointer updates. Your `.ai/state/` files are never touched by a submodule update.

---

## Directory Structure

### `.ai/state/` — Writable Canonical State

| File | Written by | Purpose |
|---|---|---|
| `team.yaml` | `ai init` or orchestrator | Roles, workers, provider/model assignments, authority |
| `board.yaml` | Orchestrator | Kanban board — backlog, ready, in_progress, review, done |
| `approvals.yaml` | `ai init` or orchestrator | Approval trigger definitions and log |
| `commands.yaml` | Skeleton templates | Command registry — names, aliases, handler mappings |

### `.ai/` — Documentation Layer

| File | Written by | Purpose |
|---|---|---|
| `STATUS.md` | `ai git-sync` | Rendered snapshot — phase, tasks, blockers, progress |
| `DECISIONS.md` | Orchestrator | Timestamped decision log (append-only) |
| `RUNBOOK.md` | Project team | Project-specific operational runbook |
| `METADATA.yaml` | `ai init` | Project UUID, skeleton version, init timestamp |
| `core/` | Skeleton templates | Authority model, protocols (read-only) |
| `prompts/` | Skeleton templates | System prompts for orchestrator and role templates |

### `.ai_runtime/` — Ephemeral

| Path | Purpose |
|---|---|
| `ai.db` | SQLite database — rebuilt from YAML on demand |
| `logs/` | Session logs |
| `session/` | Active session state (transient) |
| `memory_pack_cache/` | Export/import staging area |

---

## Authority Model

### Roles

**Orchestrator** — single, write authority
- The only agent that writes canonical state and commits to the repository
- Routes work to workers, integrates output, gates approvals
- Full read/write access to `.ai/state/` and project files

**Workers** — multiple, read-only
- Receive scoped tickets with explicit boundaries
- Produce proposals, patches, and analysis outputs
- Never commit, never modify canonical state, never touch files outside ticket scope

### Why Workers Are Read-Only

When multiple agents have commit access:
- Two workers modify the same file, creating conflicts
- A worker commits partial state that another reads as truth
- Audit trails become ambiguous

The single-writer model eliminates all of these. Workers produce output; the orchestrator decides what to integrate.

### Configuration

```yaml
orchestrator:
  role_id: orchestrator
  title: Orchestrator
  authority: write    # only valid for orchestrator

roles:
  - role_id: developer
    authority: read   # workers: read or review
    workers:
      - id: developer-1
        provider: anthropic
        model: claude-sonnet-4-5-20250929
```

---

## Persistence Model

### Canonical State (Committed)

Files under `.ai/state/` plus `STATUS.md`, `DECISIONS.md`, and `METADATA.yaml`.

- Committed after every meaningful change
- Portable across machines via git
- Source of truth — always wins over the local database

> If the database and YAML disagree, the YAML is correct. The database is a derived view.

### Local Cache (Never Committed)

`.ai_runtime/` holds the SQLite database, session logs, and memory pack staging.

- Created by `ai init`, recreated by `ai rehydrate-db`
- Safe to delete — rebuilds completely from canonical YAML

### Consistency Flow

```
git clone / git pull
        |
   .ai/state/*.yaml          <- canonical truth (from repo)
        |
   ai init / ai rehydrate-db
        |
   .ai_runtime/ai.db         <- rebuilt local cache
        |
   ai status / ai run        <- reads from DB (fast queries)
```

---

## Memory Packs

Portable snapshots of local runtime history. Carries richer continuity than canonical state alone.

### Why

Canonical YAML records what is true now. The memory pack records what happened — every command, transition, and system event.

### Export

```bash
ai export-memory
# -> .ai_runtime/memory_pack_cache/memory_pack_<timestamp>/

ai export-memory --out /path/to/pack.zip
# -> compressed archive
```

Contents: `manifest.json`, `events.jsonl`, `derived_state.json`.

### Import

```bash
ai import-memory --in /path/to/pack.zip
ai import-memory --in /path/to/pack-dir/
```

**Import does:**
- Load events into the local database
- Import derived state if canonical hash matches
- Run full reconciliation from canonical YAML

**Import never:**
- Overwrites `.ai/state/*.yaml`
- Modifies `STATUS.md` or `DECISIONS.md`
- Creates commits

---

## Installation

**Prerequisites:** Python 3.9+, PyYAML (`pip install pyyaml`), Git

### Submodule (Recommended)

```bash
cd /path/to/your/project

git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton
git submodule update --init --recursive

python vendor/ai-skeleton/engine/ai init
```

Engine updates via `git submodule update --remote --merge`. Your state files are never touched.

### Standalone

```bash
git clone https://github.com/sebby26-cyber/ai-lead-project-skeleton.git /tmp/skeleton
cp -r /tmp/skeleton/templates/.ai/ /path/to/your/project/.ai/
export PATH="$PATH:/tmp/skeleton/engine"
```

Works but requires manual engine updates. Use submodule for production.

---

## First Run

When you run `ai init` on a fresh project:

1. **Find project root** — walk up from cwd to locate `.git/`
2. **Copy templates** — seed `.ai/` from skeleton (skips existing files)
3. **Stamp metadata** — write `METADATA.yaml` with project UUID, version, timestamp
4. **Create runtime** — set up `.ai_runtime/` directories
5. **Update gitignore** — add `.ai_runtime/` entry
6. **Ingest state** — reconcile canonical YAML into SQLite
7. **Onboarding** (interactive only) — prompt for project type, roles, approval rules

### Safe Re-run

`ai init` is safe to run at any time:
- Template copy skips existing files
- `METADATA.yaml` preserves existing project ID
- Onboarding skips if workers are already configured

---

## Command Reference

> The Orchestrator handles these automatically. This section is for power users, CI, and debugging.

### ai init

Initialize `.ai/` and `.ai_runtime/` in the project root.

- **Creates:** `.ai/` from templates, `.ai_runtime/`, `.gitignore` entry
- **Never overwrites:** Existing `.ai/state/*.yaml`, project source code
- **Flags:** `--non-interactive` — skip onboarding prompts

### ai run

Start the interactive orchestrator REPL.

- **Does:** Reconcile state, open `ai>` prompt, accept commands
- **Modifies:** Local database events only

### ai status

Generate and print the project status report.

- **Does:** Reconcile YAML into DB, render status, print to stdout
- **Aliases:** `status report`, `/status`

### ai validate

Validate `.ai/state/*.yaml` against JSON schemas.

- **Does:** Check `team.yaml`, `board.yaml`, `approvals.yaml`, `commands.yaml`
- **Modifies:** Nothing (read-only)

### ai rehydrate-db

Rebuild local SQLite database from canonical YAML.

- **Does:** Drop existing DB, create fresh, ingest all state files
- **Modifies:** `.ai_runtime/ai.db` only
- **When to use:** DB corrupted, fresh clone, after pulling YAML changes

### ai export-memory

Export a portable memory pack.

- **Does:** Create `manifest.json`, `events.jsonl`, `derived_state.json`
- **Flags:** `--out <path>` — output path (`.zip` for archive)
- **Modifies:** `.ai_runtime/` only

### ai import-memory

Import a memory pack from another machine or session.

- **Does:** Validate manifest, import events, reconcile from YAML
- **Flags:** `--in <path>` — required, path to pack dir or zip
- **Never modifies:** `.ai/state/*.yaml`, `STATUS.md`, `DECISIONS.md`

### ai git-sync

Commit only canonical `.ai/` state files.

- **Does:** Reconcile, render `STATUS.md`, stage whitelisted paths, commit
- **Never commits:** `.ai_runtime/`, project source code
- **Flags:** `--message <msg>` — custom commit message

### ai migrate

Apply new skeleton templates without destroying state.

- **Does:** Copy missing template files into `.ai/`, update skeleton version
- **Never overwrites:** Existing `.ai/state/*.yaml`
- **When to use:** After submodule updates that add new templates

---

## Status Reporting

Status is rendered from canonical state in `.ai/state/`.

1. `ai status` reconciles YAML into SQLite
2. `render_status()` generates the formatted report
3. Output prints to stdout
4. `STATUS.md` is written during `ai git-sync`

**Report includes:** phase, task board summary, active workers, blockers, pending approvals, recent decisions, skeleton version.

Format is defined in `.ai/core/STATUS_REPORT_PROTOCOL.md`.

---

## Git Sync

`ai git-sync` uses an explicit whitelist. Only these paths are ever staged:

```
.ai/state/          <- all state files
.ai/STATUS.md       <- rendered status
.ai/DECISIONS.md    <- decision log
.ai/METADATA.yaml   <- version metadata
```

Any non-whitelisted file that ends up staged is automatically unstaged before commit.

`.ai_runtime/` is never committed — it would create unnecessary noise, merge conflicts, and carry machine-local data.

---

## Updating the Skeleton

```bash
# Pull latest engine
git submodule update --remote --merge

# Apply new templates (non-destructive)
ai migrate

# Validate
ai validate

# Commit pointer
git add vendor/ai-skeleton
git commit -m "chore: update ai-skeleton engine"
```

**Auto-updates:** CLI behavior, status rendering, validation rules, new template files.

**Never auto-overwrites:** `team.yaml`, `board.yaml`, `approvals.yaml`, `DECISIONS.md`, `STATUS.md`, project files.

---

## Legacy Migration

Adopting the skeleton on an existing project:

```bash
# 1. Add submodule
git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton

# 2. Initialize (non-destructive)
python vendor/ai-skeleton/engine/ai init --non-interactive

# 3. Migrate existing state into .ai/state/
#    - Task list -> board.yaml
#    - Team -> team.yaml
#    - Decision log -> DECISIONS.md

# 4. Validate
python vendor/ai-skeleton/engine/ai validate

# 5. Commit
python vendor/ai-skeleton/engine/ai git-sync --message "chore(ai): adopt skeleton"
```

Preserve existing `STATUS.md` content by copying into `.ai/STATUS.md`. The engine preserves a "Legacy Status Snapshot" section when re-rendering.

---

## Blueprint Handling

Project architecture documents are owned by the project, not the skeleton.

- The orchestrator **reads** blueprint documents to understand requirements
- The orchestrator **does not write** to blueprint documents unless explicitly instructed
- The CLI **never touches** files outside `.ai/` and `.ai_runtime/`
- `ai git-sync` **never stages** blueprint or project source files

If you want the orchestrator to update the blueprint, you instruct it explicitly. The blueprint is a reference, not canonical state.

---

## Workflow Example

### 1. Setup

```bash
cd /path/to/myproject
git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton
python vendor/ai-skeleton/engine/ai init
```

Onboarding: project type `software`, roles `developer` + `reviewer`, approval triggers for scope changes and releases.

### 2. Status check

```bash
ai status
```

### 3. Task decomposition

Orchestrator reads `docs/blueprint/`, populates `board.yaml`, writes phase plan to `STATUS.md`, appends planning decision to `DECISIONS.md`.

```bash
ai git-sync --message "feat(ai): initial phase plan from blueprint"
```

### 4. Worker delegation

Orchestrator produces scoped tickets. Workers execute and write output. Workers never commit.

### 5. Integration

Orchestrator reviews outputs, integrates accepted changes, updates `board.yaml`, appends decisions.

```bash
ai validate
ai git-sync --message "feat: integrate worker outputs for phase 1"
```

### 6. Approval gate

Trigger fires. Orchestrator records pending approval. Execution pauses until human approves.

### 7. Export

```bash
ai export-memory --out /tmp/myproject-memory-phase1.zip
```

---

## Multi-Machine Continuity

### Fresh clone (basic continuity)

```bash
git clone <project-repo>
git submodule update --init --recursive
python vendor/ai-skeleton/engine/ai init --non-interactive
python vendor/ai-skeleton/engine/ai status
```

The committed YAML state is sufficient for a new orchestrator to understand current phase, task board, and decisions.

### With memory pack (richer continuity)

```bash
# Source machine
ai export-memory --out /tmp/pack.zip

# New machine (after init)
ai import-memory --in /tmp/pack.zip
```

| After clone + init | After import-memory |
|---|---|
| Current task board | Full event history |
| Team configuration | Previous session logs |
| Approval log | Derived state cache |
| Decision history | Richer orchestrator context |

---

## Troubleshooting

### Status shows no tasks

`board.yaml` is empty or DB is out of sync.

```bash
ai rehydrate-db
ai status
```

### Database out of sync

```bash
ai rehydrate-db
```

Drops and rebuilds from canonical YAML. No data is lost.

### `ai` command not found

```bash
# Initialize submodule
git submodule update --init --recursive

# Run via full path
python vendor/ai-skeleton/engine/ai status
```

### Invalid YAML

```bash
ai validate
# Read error output, fix the YAML, re-run
```

Common causes: incorrect indentation, missing required fields, invalid enum values.

### `.ai_runtime/` accidentally committed

```bash
git rm -r --cached .ai_runtime/
echo ".ai_runtime/" >> .gitignore
git add .gitignore && git commit -m "fix: remove ai_runtime from tracking"
```

### Memory pack import fails

| Error | Cause |
|---|---|
| `No manifest.json found` | Not a valid memory pack |
| `Unsupported version` | Incompatible skeleton version |
| `Not a valid memory pack` | Path doesn't exist or wrong format |

---

## Design Decisions

**Why YAML as source of truth?**
Human-readable without tooling. Git-diffable. Machine-portable. Schema-validatable. A database would require export to share state and produce binary diffs.

**Why single writer?**
Multi-agent writes produce conflicts. Even with locking, two AI agents writing to canonical files will diverge. The single-writer model eliminates this entirely.

**Why a local DB cache?**
YAML is optimized for readability, not query speed. SQLite trades minimal setup complexity for fast queries. Since it's always rebuildable, it carries no integrity risk.

**Why memory packs?**
Canonical state records what is true now. The memory pack records what happened — the full event timeline for richer continuity across machines and sessions.

**Why submodule architecture?**
Engine upgrades never touch project state. Projects pin exact engine versions. Multiple projects use the skeleton at different versions independently. The skeleton evolves independently of any project.

---

## Future Extensions

Planned for post-v1:

- **Local web Kanban UI** — browser-based task board and event timeline from SQLite
- **Department leads** — intermediate authority level between orchestrator and workers
- **Advanced approvals** — multi-level with quorum requirements
- **Role onboarding expansion** — pre-configured templates for specialized domains

v1 prioritizes stability, correctness, and predictability. No breaking changes to schemas, commands, or persistence without a migration path.

---

## Quick Reference

```
SETUP
  git submodule add <repo-url> vendor/ai-skeleton
  python vendor/ai-skeleton/engine/ai init
  python vendor/ai-skeleton/engine/ai init --non-interactive

DAILY
  ai status
  ai validate
  ai git-sync
  ai git-sync --message "chore(ai): close phase 3"
  ai run

DATABASE
  ai rehydrate-db

MEMORY
  ai export-memory
  ai export-memory --out /path/to/pack.zip
  ai import-memory --in /path/to/pack.zip

ENGINE UPDATE
  git submodule update --remote --merge
  ai migrate
  ai validate
  git add vendor/ai-skeleton
  git commit -m "chore: update ai-skeleton engine"

FRESH CLONE
  git clone <project-repo>
  git submodule update --init --recursive
  python vendor/ai-skeleton/engine/ai init --non-interactive
  python vendor/ai-skeleton/engine/ai status
  python vendor/ai-skeleton/engine/ai import-memory --in /path/to/pack.zip

RECOVERY
  ai rehydrate-db
  ai validate
  git rm -r --cached .ai_runtime/
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*v1 engine. Commands and schemas are stable. Engine updates via submodule will not break existing canonical state.*
