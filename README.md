# Universal AI Team Skeleton — Operator Manual

**Version:** 1.0 | **License:** MIT | **Engine:** Python 3 | **Source:** `engine/`

This document is the single authoritative operator guide for the Universal AI Team Skeleton.
If you cloned this repository and need to run an AI team on a real project, start here.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Core Philosophy — AI ≠ Humans](#2-core-philosophy--ai--humans)
3. [Architecture Overview](#3-architecture-overview)
4. [Directory Structure Breakdown](#4-directory-structure-breakdown)
5. [Authority Model](#5-authority-model)
6. [Persistence Model](#6-persistence-model)
7. [Exportable Memory Pack](#7-exportable-memory-pack)
8. [Installation and Setup](#8-installation-and-setup)
9. [First Run Lifecycle](#9-first-run-lifecycle)
10. [Full Command Reference](#10-full-command-reference)
11. [Status Reporting System](#11-status-reporting-system)
12. [Git Sync Behavior](#12-git-sync-behavior)
13. [Updating the Skeleton](#13-updating-the-skeleton)
14. [Migration — Legacy Projects](#14-migration--legacy-projects)
15. [Blueprint and Project Docs Handling](#15-blueprint-and-project-docs-handling)
16. [Typical Workflow Example](#16-typical-workflow-example)
17. [Multi-Machine Continuity](#17-multi-machine-continuity)
18. [Troubleshooting Guide](#18-troubleshooting-guide)
19. [Design Decisions Explained](#19-design-decisions-explained)
20. [Future Extensions](#20-future-extensions)
21. [Quick Reference Cheat Sheet](#21-quick-reference-cheat-sheet)

---

## 1. What This Project Is

The Universal AI Team Skeleton is an **orchestration engine and canonical state framework** for running AI agent teams on real projects.

It provides:
- A structured runtime for a single orchestrator agent and a pool of read-only worker agents.
- Canonical YAML state files that are committed to your project repository.
- A local SQLite cache that is rebuilt on demand and never committed.
- A portable memory pack for moving context between machines.
- A CLI (`ai`) that drives initialization, status, sync, memory, and validation.

### What this skeleton is NOT

The skeleton is **not your project**. It is the execution engine that plugs into your project.

Your project owns:
- Its source code, tests, and build artifacts.
- Its architecture decisions and documentation.
- Its `STATUS.md`, `DECISIONS.md`, and blueprint files.

The skeleton provides:
- The orchestration engine (`engine/`).
- Canonical state templates (`.ai/state/`).
- The CLI and all runtime logic.

### What project types does this support?

Any. The skeleton decouples orchestration from project domain. It has been used for:
- Software engineering projects (code, tests, deployments).
- Marketing and content operations.
- Research and analysis workflows.
- Internal operations and process automation.

The team composition, roles, and authority model are all configurable per project via YAML.

---

## 2. Core Philosophy — AI ≠ Humans

AI agents are not human developers. This framework is designed with that fact as a first principle.

### Why AI agents need different rules

**Branch chaos:** When multiple AI agents have write access, they produce conflicting branches,
redundant commits, and diverging state. This is not a discipline problem — it is a structural problem.
The solution is to give only one agent write access.

**Context loss:** An AI agent's context window is finite. Across sessions, handoffs, or machine
changes, all context is lost unless it is written to durable storage. This framework commits state
after every meaningful change.

**Scope drift:** Without explicit boundaries, AI workers extend their scope into neighboring work.
This framework enforces non-overlapping ticket scopes and explicit worker boundaries.

**Approvals:** AI agents will proceed autonomously unless forced to stop. Phase gates and approval
triggers enforce human checkpoints at the right moments.

### Design Principles

| Principle | What it means in practice |
|---|---|
| **Safety over autonomy** | Workers cannot commit. Orchestrator gates all merges. |
| **Deterministic state** | YAML files are the source of truth. DB is always rebuildable. |
| **Portable context** | State survives machine changes via memory packs and repo commits. |
| **Restartable workflows** | Any interrupted workflow can resume from the last committed state. |
| **Repo-first continuity** | If the repo is clean, any new agent can resume in under 15 minutes. |

---

## 3. Architecture Overview

```
Your Project Repository
├── .ai/                        ← canonical state (COMMITTED to git)
│   ├── state/
│   │   ├── team.yaml           ← roles, workers, authority
│   │   ├── board.yaml          ← task board (kanban columns + tasks)
│   │   ├── approvals.yaml      ← approval triggers and log
│   │   └── commands.yaml       ← command registry and aliases
│   ├── core/                   ← authority model, protocols (read-only docs)
│   ├── prompts/                ← orchestrator system prompt, role templates
│   ├── STATUS.md               ← human-readable project status
│   ├── DECISIONS.md            ← append-only decision log
│   ├── RUNBOOK.md              ← project-specific runbook
│   └── METADATA.yaml           ← project ID, skeleton version, init time
│
├── .ai_runtime/                ← local cache (NEVER committed, git-ignored)
│   ├── ai_state.db             ← SQLite database (rebuildable)
│   ├── logs/                   ← session logs
│   ├── session/                ← active session state
│   └── memory_pack_cache/      ← export/import staging area
│
├── vendor/ai-skeleton/         ← skeleton as git submodule (recommended)
│   └── engine/                 ← CLI and all runtime logic
│       ├── ai                  ← CLI entrypoint
│       ├── ai_init.py
│       ├── ai_run.py
│       ├── ai_state.py
│       ├── ai_db.py
│       ├── ai_git.py
│       ├── ai_memory.py
│       └── ai_validate.py
│
└── [your project code, tests, docs, etc.]
```

### `.ai/` — Canonical State

This directory is the source of truth for all orchestration state. It is:
- **Committed to git** after every meaningful change.
- **Human-auditable** — plain YAML and Markdown, no binary blobs.
- **Portable** — clone the repo on any machine and the full state is present.

Canonical state always wins. If the SQLite database disagrees with the YAML files,
the YAML files are correct and the database is rebuilt.

### `.ai_runtime/` — Local Cache

This directory exists only on the local machine. It is:
- **Never committed** (`.gitignore` entry is created automatically by `ai init`).
- **Fully rebuildable** from canonical state at any time via `ai rehydrate-db`.
- Used for fast querying, event logging, and memory pack staging.

Losing `.ai_runtime/` has zero impact on project state. Running `ai init` or
`ai rehydrate-db` on a fresh clone recreates it completely.

### Submodule — Engine Source

The recommended usage model is to add this skeleton as a git submodule:

```
vendor/ai-skeleton/  ←  engine, templates, schemas
```

Engine upgrades flow through submodule pointer updates. Your `.ai/state/` files
are never touched by a submodule update.

---

## 4. Directory Structure Breakdown

### `.ai/state/` — Writable Canonical State

These files are written by the orchestrator and committed via `ai git-sync`.

```
.ai/state/
├── team.yaml        Written by: ai init (onboarding) or orchestrator
│                    Purpose:    Defines orchestrator role, worker roles,
│                                provider/model assignments, authority levels.
│
├── board.yaml       Written by: orchestrator (via task updates)
│                    Purpose:    Kanban task board. Columns: backlog, ready,
│                                in_progress, review, done.
│
├── approvals.yaml   Written by: ai init (onboarding) or orchestrator
│                    Purpose:    Approval trigger definitions and running log
│                                of approval decisions.
│
└── commands.yaml    Written by: skeleton templates (do not modify manually)
                     Purpose:    Maps command names and aliases to handler
                                 functions in the engine.
```

### `.ai/` — Documentation Layer

```
.ai/
├── STATUS.md        Written by: ai git-sync (rendered from state)
│                    Purpose:    Human-readable snapshot of current phase,
│                                tasks, blockers, and progress.
│
├── DECISIONS.md     Written by: orchestrator (append-only)
│                    Purpose:    Timestamped log of architectural decisions.
│                                Never deleted. New entries appended only.
│
├── RUNBOOK.md       Written by: project team
│                    Purpose:    Project-specific operational runbook.
│
├── METADATA.yaml    Written by: ai init
│                    Purpose:    Project UUID, skeleton version, init timestamp,
│                                submodule path detection.
│
├── core/            Written by: skeleton templates (read-only)
│                    Purpose:    Authority model, orchestrator protocol,
│                                status report format, worker execution rules.
│
└── prompts/         Written by: skeleton templates (read-only)
                     Purpose:    System prompts for orchestrator and role
                                 templates for workers.
```

### `.ai_runtime/` — Ephemeral Local State

```
.ai_runtime/
├── ai_state.db              SQLite database. Rebuilt from YAML on demand.
├── logs/                    Session logs. Appended per run.
├── session/                 Active session state (transient).
└── memory_pack_cache/       Staging area for export/import operations.
```

---

## 5. Authority Model

### Roles

**Orchestrator (single, write authority)**
- The only agent that writes canonical state files.
- The only agent that commits to the repository.
- Routes work to workers, integrates their output, and gates approvals.
- Has full read and write access to `.ai/state/` and project files.

**Workers (multiple, read-only authority)**
- Receive scoped tickets with explicit boundaries.
- Produce proposals, patches, and analysis outputs.
- Write to their designated output area only (e.g., `.taskers/runs/`).
- Never commit directly to the repository.
- Never modify canonical state.
- Never modify files outside their ticket scope.

**Optional Leads (future)**
- Department-level leads that own a domain and delegate to sub-workers.
- Not implemented in v1. All workers report directly to orchestrator.

### Why workers are read-only

When multiple agents have commit access, the following failure modes emerge:
- Two workers modify the same file at different times, creating conflicts.
- A worker commits a partial state that another worker then reads as truth.
- Audit trails become ambiguous because multiple agents wrote to canonical files.

The single-writer model eliminates all of these. Workers produce output; the orchestrator
decides what to integrate. This is the same model as a human code review workflow — workers
are the engineers who open pull requests, the orchestrator is the tech lead who merges them.

### Authority defined in `team.yaml`

```yaml
orchestrator:
  role_id: orchestrator
  title: Orchestrator
  authority: write

roles:
  - role_id: developer
    authority: read        # Workers have read authority only
    workers:
      - id: developer-1
        provider: anthropic
        model: claude-sonnet-4-5-20250929
```

Valid authority values: `write` (orchestrator only), `read`, `review`.

---

## 6. Persistence Model

Understanding this model is critical for safe operation.

### Canonical State — Committed

The files under `.ai/state/` plus `.ai/STATUS.md`, `.ai/DECISIONS.md`, and `.ai/METADATA.yaml`
form the canonical state. These are the only files the engine commits via `ai git-sync`.

**Properties:**
- Committed to git after every meaningful change.
- Portable: checking out the repo on any machine gives full state.
- Human-auditable: plain YAML and Markdown.
- Source of truth: always wins over the local database.

**Consistency rule:**
If your database and your YAML disagree, the YAML is correct.
The database is a derived view, not a primary store.

### Local Runtime Cache — Never Committed

`.ai_runtime/` is a local-only cache. It holds:
- `ai_state.db`: SQLite database for fast queries and event history.
- Session logs and staging areas for memory packs.

**Properties:**
- Created by `ai init`. Recreated by `ai rehydrate-db`.
- `.gitignore` entry added automatically — it is never committed.
- Safe to delete. Rebuilds completely from canonical YAML.

### Rehydration

If you clone the project on a new machine, or if `.ai_runtime/` is ever deleted or corrupted:

```bash
ai init
# or, if .ai/ is already set up:
ai rehydrate-db
```

This drops the existing database and rebuilds it entirely from `.ai/state/*.yaml`.
No data is lost because canonical state lives in the committed YAML files.

### Consistency Flow

```
git clone / git pull
        ↓
   .ai/state/*.yaml          ← canonical truth (from repo)
        ↓
   ai init / ai rehydrate-db
        ↓
   .ai_runtime/ai_state.db   ← rebuilt local cache
        ↓
   ai status / ai run        ← reads from DB (fast queries)
```

---

## 7. Exportable Memory Pack

The memory pack is a portable snapshot of local runtime history. It carries richer continuity
than canonical state alone because it includes the full event timeline and derived state.

### Why it exists

Canonical YAML state records what is true now. The memory pack records what happened:
- Every command run and its result.
- Every task state transition.
- Every system event (init, rehydrate, import, etc.).
- Derived state snapshots for fast resumption.

When moving between machines, importing the memory pack gives a new session
the full event history of the previous one without needing to replay all work.

### Export

```bash
ai export-memory
# Exports to .ai_runtime/memory_pack_cache/memory_pack_<timestamp>/

ai export-memory --out /path/to/pack.zip
# Exports as a zip archive to the specified path
```

The export includes:
- `manifest.json`: version, project UUID, skeleton version, canonical hash, timestamp.
- `events.jsonl`: full event timeline as JSON Lines.
- `derived_state.json`: derived state snapshot for fast import.

### Import

```bash
ai import-memory --in /path/to/pack.zip
# or a directory:
ai import-memory --in /path/to/pack/
```

**What import does:**
- Loads events from `events.jsonl` into the local database.
- Imports `derived_state.json` only if the canonical hash matches (schema-compatible).
- Runs a full reconciliation from canonical YAML after import — YAML always wins.

**What import never does:**
- Overwrite canonical state YAML files.
- Modify `.ai/state/`, `.ai/STATUS.md`, or `.ai/DECISIONS.md`.
- Create commits.

The memory pack adds historical context to the local cache. It does not change
what is true — only what is remembered.

---

## 8. Installation and Setup

### Prerequisites

- Python 3.9+
- `pip install pyyaml` (required for YAML parsing)
- Git (required for `ai git-sync` and submodule management)

### Option A — Standalone (Simple)

Copy the skeleton into your project manually:

```bash
git clone https://github.com/sebby26-cyber/ai-lead-project-skeleton.git /tmp/skeleton

cd /path/to/your/project

# Copy canonical state templates
cp -r /tmp/skeleton/templates/.ai/ ./.ai/

# The CLI is at /tmp/skeleton/engine/ai — add to PATH or use full path
export PATH="$PATH:/tmp/skeleton/engine"
```

This works but has one downside: engine updates require manual re-copy. Use the submodule
model for production projects.

### Option B — Submodule (Recommended)

```bash
cd /path/to/your/project

git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton
git submodule update --init --recursive
```

Run the CLI via the submodule path:

```bash
python vendor/ai-skeleton/engine/ai init
python vendor/ai-skeleton/engine/ai status
```

Or create a shell alias:

```bash
alias ai="python $(pwd)/vendor/ai-skeleton/engine/ai"
```

**Why submodule?**
- Engine updates come from `git submodule update --remote --merge` + commit the pointer.
- Your `.ai/state/` files are never touched by a submodule update.
- The project repo records exactly which engine version it is using via the submodule pointer.

---

## 9. First Run Lifecycle

When you run `ai init` on a fresh project, the following sequence executes:

```
1. find_project_root()
   Walk up from cwd to find .git/ — establishes project root.

2. copy_templates()
   Copy .ai/ templates from skeleton into project.
   Does NOT overwrite existing files. Safe to re-run.

3. stamp_metadata()
   Write .ai/METADATA.yaml with:
   - project_id (UUID, generated once)
   - skeleton_version (current skeleton git commit hash)
   - initialized_at (UTC timestamp)
   - submodule_path (if skeleton is a submodule)

4. setup_runtime()
   Create .ai_runtime/ with subdirectories:
   logs/, session/, memory_pack_cache/

5. ensure_gitignore()
   Add .ai_runtime/ to .gitignore if not already present.

6. reconcile() — ingest canonical YAML into SQLite
   Read .ai/state/*.yaml and sync to .ai_runtime/ai_state.db.

7. stamp skeleton version in DB
   Write version event to database for audit trail.

8. run_onboarding() (interactive mode only)
   If team.yaml has no workers configured, prompt for:
   - Project type (software / marketing / ops / mixed)
   - Default or custom role definitions
   - Provider and model per role
   - Approval trigger rules
   Write results to team.yaml and approvals.yaml.
```

### Safe re-run behavior

`ai init` is safe to re-run at any time:
- Template copy skips files that already exist (no overwrite).
- METADATA.yaml preserves existing `project_id` and `initialized_at`.
- Onboarding skips if workers are already configured in `team.yaml`.

---

## 10. Full Command Reference

All commands are invoked as:

```bash
ai <command> [--flag value]
# or via submodule:
python vendor/ai-skeleton/engine/ai <command> [--flag value]
```

---

### `ai init`

**Purpose:** Initialize `.ai/` and `.ai_runtime/` in the project root.

**What it modifies:**
- Creates `.ai/` from templates (skips existing files).
- Creates `.ai_runtime/` with subdirectories.
- Creates or updates `.ai/METADATA.yaml`.
- Adds `.ai_runtime/` to `.gitignore`.
- Ingests canonical YAML into SQLite.

**What it never modifies:**
- Existing `.ai/state/*.yaml` files (no overwrite).
- Project source code.
- Git history.

**Flags:**
```
--non-interactive    Skip onboarding prompts. Useful for CI or scripted setup.
```

**Example:**
```bash
ai init
ai init --non-interactive
```

---

### `ai run`

**Purpose:** Start the interactive orchestrator REPL loop.

**What it does:**
- Reconciles canonical state into SQLite.
- Opens an interactive prompt (`ai> `).
- Accepts any registered command by name or alias.
- Type `quit` or `exit` to stop.

**What it modifies:**
- Writes events to the local database.
- Does not commit anything.

**Example:**
```bash
ai run
# ai> status
# ai> export-memory
# ai> quit
```

**Use case:** Running the orchestrator loop interactively during a session.

---

### `ai status`

**Purpose:** Generate and print the project status report.

**What it does:**
- Reconciles canonical YAML into SQLite.
- Renders a status report from the current state.
- Prints to stdout.

**What it modifies:**
- Reconciles the DB (in-memory sync). No file writes unless called via `git-sync`.

**Aliases:** `status report`, `generate status report`, `/status`

**Example:**
```bash
ai status
```

---

### `ai validate`

**Purpose:** Validate all `.ai/state/*.yaml` files against their JSON schemas.

**What it does:**
- Loads schemas from `schemas/` in the skeleton.
- Validates `team.yaml`, `board.yaml`, `approvals.yaml`, `commands.yaml`.
- Reports PASS or FAIL with specific error messages.

**What it modifies:** Nothing. Read-only check.

**Example:**
```bash
ai validate
# Validation: ALL PASSED
#   OK    team.yaml
#   OK    board.yaml
#   OK    approvals.yaml
#   OK    commands.yaml
```

---

### `ai rehydrate-db`

**Purpose:** Rebuild the local SQLite database from scratch using canonical YAML state.

**What it does:**
- Deletes the existing `ai_state.db`.
- Creates a fresh database.
- Ingests all `.ai/state/*.yaml` files.

**What it modifies:**
- `.ai_runtime/ai_state.db` only. No canonical state files touched.

**When to use:**
- Database is corrupted or out of sync.
- After cloning the repo on a new machine.
- After pulling changes that updated canonical YAML.

**Example:**
```bash
ai rehydrate-db
# Database rehydrated from canonical YAML state.
```

---

### `ai export-memory`

**Purpose:** Export a portable memory pack containing the full event timeline and derived state.

**What it does:**
- Creates a timestamped directory in `.ai_runtime/memory_pack_cache/`.
- Writes `manifest.json`, `events.jsonl`, `derived_state.json`.
- Optionally compresses to a zip file.

**What it modifies:** Creates files in `.ai_runtime/`. Nothing in `.ai/`. Nothing committed.

**Flags:**
```
--out <path>    Output path. If ends with .zip, creates a zip archive.
                If a directory path, copies pack there.
```

**Examples:**
```bash
ai export-memory
# Exported to: .ai_runtime/memory_pack_cache/memory_pack_20260217_120000_000000/

ai export-memory --out /tmp/myproject-memory.zip
# Exported to: /tmp/myproject-memory.zip
```

---

### `ai import-memory`

**Purpose:** Import a memory pack from another machine or session into the local cache.

**What it does:**
- Validates the pack manifest (version must be `1.0`).
- Imports events from `events.jsonl` into the local database.
- Imports `derived_state.json` only if canonical hash matches (schema-compatible).
- Runs full reconciliation from canonical YAML after import.

**What it never modifies:**
- `.ai/state/*.yaml` — canonical state is never overwritten.
- `.ai/STATUS.md`, `.ai/DECISIONS.md`.
- Git history.

**Flags:**
```
--in <path>    Required. Path to memory pack directory or zip file.
```

**Examples:**
```bash
ai import-memory --in /tmp/myproject-memory.zip
ai import-memory --in /path/to/memory_pack_dir/
```

---

### `ai git-sync`

**Purpose:** Commit only canonical `.ai/` state files to git.

**What it does:**
- Reconciles canonical state and renders `STATUS.md`.
- Stages only whitelisted paths (see Section 12).
- Verifies no non-whitelisted files are staged.
- Creates a commit with a standard message.

**What it never commits:**
- `.ai_runtime/` — always excluded.
- Project source code — only `.ai/` canonical files.

**Flags:**
```
--message <msg>    Custom commit message. Default: "chore(ai): update canonical state"
```

**Examples:**
```bash
ai git-sync
ai git-sync --message "chore(ai): close phase 2 tasks"
```

---

### `ai migrate`

**Purpose:** Safely apply new skeleton templates to an existing project without destroying project state.

**What it does:**
- Applies new template files from the skeleton that do not yet exist in `.ai/`.
- Updates `METADATA.yaml` with the new skeleton version.
- Never overwrites existing `.ai/state/*.yaml` files.

**When to use:**
- After a submodule update that adds new template files.
- When onboarding a legacy project that has partial `.ai/` setup.

**Example:**
```bash
git submodule update --remote --merge
ai migrate
```

---

## 11. Status Reporting System

The status report is rendered from canonical state. It reflects what is committed in `.ai/state/`.

### How it works

1. `ai status` calls `ai_state.reconcile()` to sync YAML into SQLite.
2. `ai_state.render_status()` reads from the DB and generates a formatted report.
3. Output is printed to stdout.
4. `.ai/STATUS.md` is written with the same content during `ai git-sync`.

### What a status report includes

- **Phase and milestone**: current project phase, active milestone.
- **Task board summary**: counts by column (backlog / ready / in_progress / review / done).
- **Active workers**: which workers are currently assigned tasks.
- **Blockers**: tasks flagged as blocked with reasons.
- **Approvals pending**: any triggered approval gates awaiting human sign-off.
- **Recent decisions**: last few entries from `DECISIONS.md`.
- **Skeleton version**: the engine version in use (from `METADATA.yaml`).

### Status report format

The format is defined in `.ai/core/STATUS_REPORT_PROTOCOL.md`. It uses a fixed 7-section
layout designed to be transfer-safe for new lead agents. The format may evolve via skeleton
updates — the protocol file is the authoritative definition.

### Human-readable output

`.ai/STATUS.md` is the committed, human-readable version. It is updated every time
`ai git-sync` runs. You can read it at any time to understand current project state.

---

## 12. Git Sync Behavior

`ai git-sync` uses an explicit whitelist to control what is committed. Only the following
paths are ever staged:

```
.ai/state/          ← all files in state directory
.ai/STATUS.md       ← rendered status snapshot
.ai/DECISIONS.md    ← append-only decision log
.ai/METADATA.yaml   ← project and skeleton version metadata
```

If any other file somehow ends up staged, the engine unstages it before committing.
This is a safety mechanism, not a workaround — non-canonical files must never enter
the git-sync commit.

### Why runtime files are excluded

`.ai_runtime/` is a derived cache. Committing it would:
- Create unnecessary noise in git history.
- Cause merge conflicts when multiple machines sync.
- Carry machine-local paths and session data that are meaningless to other machines.

The canonical YAML files carry everything that matters. The runtime cache is rebuilt on demand.

---

## 13. Updating the Skeleton

Because the skeleton is a git submodule, engine updates are clean and non-destructive.

### Update procedure

```bash
# 1. Pull the latest skeleton engine
git submodule update --remote --merge

# 2. Apply any new templates (does not overwrite existing state)
python vendor/ai-skeleton/engine/ai migrate

# 3. Validate that YAML is still schema-compliant
python vendor/ai-skeleton/engine/ai validate

# 4. Commit the submodule pointer update
git add vendor/ai-skeleton
git commit -m "chore: update ai-skeleton engine to latest"
```

### What updates automatically

When you pull a new skeleton version:
- CLI commands and their behavior.
- Status rendering logic.
- Schema validation rules.
- Runtime orchestration behavior.
- New template files (added by `ai migrate` only for files that do not exist yet).

### What does NOT auto-overwrite

- `.ai/state/team.yaml` — your team configuration.
- `.ai/state/board.yaml` — your task board.
- `.ai/state/approvals.yaml` — your approval rules and log.
- `.ai/DECISIONS.md` — your decision history.
- `.ai/STATUS.md` — rendered from your state.
- Any project-owned files outside `.ai/`.

### `ai migrate`

The `migrate` command is the safe update path for template-side changes.
It copies new files from the skeleton templates into `.ai/` only for files that
do not already exist. This means:
- New core docs or prompt templates from a skeleton upgrade get applied.
- Existing state files are never touched.

Run `ai migrate` after every submodule update as a matter of habit.

---

## 14. Migration — Legacy Projects

If you have an existing project that was previously managed without this skeleton,
you can adopt it without losing history.

### Step-by-step

```bash
# 1. Add the skeleton submodule
git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton

# 2. Initialize without overwriting anything
python vendor/ai-skeleton/engine/ai init --non-interactive

# 3. Manually migrate existing state into .ai/state/
#    - Copy relevant task list into .ai/state/board.yaml
#    - Define your team in .ai/state/team.yaml
#    - Copy existing decision log entries into .ai/DECISIONS.md

# 4. Validate
python vendor/ai-skeleton/engine/ai validate

# 5. Commit canonical state
python vendor/ai-skeleton/engine/ai git-sync --message "chore(ai): adopt skeleton on existing project"
```

### Rules for legacy adoption

- Preserve your existing `STATUS.md` content by copying it into `.ai/STATUS.md`.
- Preserve your existing decision log by appending to `.ai/DECISIONS.md`.
- Do not force workers to re-run work that was already completed. Update `board.yaml`
  to reflect the actual current state of tasks.
- Use `--non-interactive` to skip the onboarding wizard and configure `team.yaml` manually.

---

## 15. Blueprint and Project Docs Handling

**Project architecture documents are owned by the project, not the skeleton.**

If your project has a `docs/blueprint/` directory, an `IMPLEMENTATION_INSTRUCTIONS.md`,
or any other architecture document, the skeleton must never overwrite, relocate, or
take ownership of those files.

### Rules

- The orchestrator can read blueprint documents to understand project requirements.
- The orchestrator does not write to blueprint documents unless explicitly instructed.
- The skeleton CLI never touches files outside `.ai/` and `.ai_runtime/`.
- `ai git-sync` will never stage blueprint or project source files.

### Practical implication

Your project blueprint lives at a path like `docs/blueprint/IMPLEMENTATION_INSTRUCTIONS.md`.
The skeleton is aware of this pattern but does not manage it. The orchestrator reads
the blueprint to drive task decomposition and phase planning — it does not own the blueprint.

If you want the orchestrator to update the blueprint (e.g., add a new section after a
decision), you instruct it explicitly. It treats the blueprint as a reference, not as
part of its canonical state.

---

## 16. Typical Workflow Example

Here is a complete example of a software project from first clone to memory export.

### Step 1 — Set up the project

```bash
cd /path/to/myproject
git submodule add https://github.com/sebby26-cyber/ai-lead-project-skeleton.git vendor/ai-skeleton
python vendor/ai-skeleton/engine/ai init
```

The onboarding wizard runs. You define:
- Project type: `software`
- Roles: `developer` (Codex, gpt-5), `reviewer` (Claude, claude-sonnet-4-5-20250929)
- Approval triggers: scope changes and releases

### Step 2 — Check initial status

```bash
python vendor/ai-skeleton/engine/ai status
# Shows empty task board, initialized team, skeleton version.
```

### Step 3 — Orchestrator loads blueprint and decomposes tasks

The orchestrator agent reads `docs/blueprint/IMPLEMENTATION_INSTRUCTIONS.md`.
It populates `board.yaml` with tasks in the `backlog` column.
It writes a phase plan to `.ai/STATUS.md`.
It appends a planning decision to `.ai/DECISIONS.md`.

```bash
python vendor/ai-skeleton/engine/ai git-sync --message "feat(ai): initial phase plan from blueprint"
```

### Step 4 — Orchestrator delegates to workers

The orchestrator produces scoped tickets for each worker.
Workers execute their tickets and write output to `.taskers/runs/`.
Workers never commit.

### Step 5 — Orchestrator integrates worker output

Orchestrator reviews worker outputs, integrates accepted changes into project files,
updates `board.yaml` to move tasks to `done`, and appends integration decisions.

```bash
python vendor/ai-skeleton/engine/ai validate
python vendor/ai-skeleton/engine/ai git-sync --message "feat: integrate worker outputs for phase 1"
```

### Step 6 — Approval gate

An approval trigger fires (e.g., scope change). The orchestrator records the pending
approval in `approvals.yaml`. Execution pauses until the human approves.

After approval:
```bash
python vendor/ai-skeleton/engine/ai git-sync --message "chore(ai): record phase 1 approval"
```

### Step 7 — Export memory before moving machines

```bash
python vendor/ai-skeleton/engine/ai export-memory --out /tmp/myproject-memory-phase1.zip
```

---

## 17. Multi-Machine Continuity

This framework is designed for the case where you continue work on a different machine
or a new session starts with a fresh context window.

### Scenario: clone on a new machine

```bash
# On new machine:
git clone <your-project-repo>
git submodule update --init --recursive

python vendor/ai-skeleton/engine/ai init --non-interactive
# .ai_runtime/ is created and DB is built from committed YAML.

python vendor/ai-skeleton/engine/ai status
# Full project state is visible from the committed canonical files.
```

No memory pack needed for basic continuity. The committed YAML state is sufficient
for a new orchestrator to understand the current phase, task board, and recent decisions.

### Scenario: richer continuity with memory pack

If you want the event history (not just current state) on the new machine:

```bash
# On old machine:
python vendor/ai-skeleton/engine/ai export-memory --out /tmp/pack.zip
# Transfer pack.zip to new machine (USB, cloud storage, etc.)

# On new machine (after init):
python vendor/ai-skeleton/engine/ai import-memory --in /tmp/pack.zip
# Imports event timeline. Canonical YAML state is reconciled after import.
```

### What continuity guarantees

| After git clone + init | After import-memory |
|---|---|
| Current task board state | Full event history |
| Team configuration | Previous session logs |
| Approval log | Derived state cache |
| Decision history | Richer context for orchestrator |
| Phase and milestone | — |

Both paths give the orchestrator enough context to resume. The memory pack gives more.

---

## 18. Troubleshooting Guide

### Status is empty or shows no tasks

**Cause:** `board.yaml` has no tasks, or the database is out of sync with YAML.

**Fix:**
```bash
ai rehydrate-db
ai status
```

If the board is genuinely empty, tasks need to be added to `board.yaml` by the orchestrator.

---

### Database out of sync with YAML

**Symptom:** `ai status` shows stale data or errors referencing missing records.

**Fix:**
```bash
ai rehydrate-db
```

This drops and rebuilds the database from canonical YAML. No data is lost.

---

### `ai` command not found

**Cause:** The CLI is not on PATH, or the submodule is not initialized.

**Fix:**
```bash
# Initialize submodule if not done:
git submodule update --init --recursive

# Run via full path:
python vendor/ai-skeleton/engine/ai status

# Or add alias to shell:
alias ai="python $(pwd)/vendor/ai-skeleton/engine/ai"
```

---

### Submodule not initialized

**Symptom:** `vendor/ai-skeleton/` directory is empty.

**Fix:**
```bash
git submodule update --init --recursive
```

---

### Invalid YAML in state files

**Symptom:** `ai validate` reports schema errors, or `ai init` / `ai status` fails.

**Fix:**
```bash
ai validate
# Read the error output to identify which file and which field is invalid.
# Edit the YAML file to fix the issue.
# Re-run: ai validate
```

Common causes:
- Incorrect indentation (YAML is indent-sensitive).
- Missing required fields defined in the schema.
- Invalid enum values (e.g., `authority: admin` instead of `authority: write`).

---

### `.ai_runtime/` accidentally committed

**Symptom:** `git status` shows `.ai_runtime/` files in the index.

**Fix:**
```bash
git rm -r --cached .ai_runtime/
echo ".ai_runtime/" >> .gitignore
git add .gitignore
git commit -m "fix: remove ai_runtime from tracking"
```

Then verify `.gitignore` has the entry. `ai init` also adds this automatically — it may
have been run before `.gitignore` existed.

---

### Memory pack import fails

**Symptom:** `ai import-memory` returns an error.

**Causes and fixes:**

| Error | Fix |
|---|---|
| `No manifest.json found` | Pack is not a valid memory pack directory or zip. |
| `Unsupported memory pack version` | Pack was created by an incompatible skeleton version. |
| `is not a valid memory pack` | Path does not exist or is not a directory/zip. |

---

### Worker outputs not being integrated

**Cause:** Workers produced output in `.taskers/runs/` but the orchestrator has not
reviewed and integrated it yet.

**Fix:** This is not a technical failure. The orchestrator must explicitly review worker
output and integrate accepted changes. Workers do not self-integrate.

---

## 19. Design Decisions Explained

### Why YAML instead of a database as the source of truth?

YAML files are:
- **Human-readable** without tooling. Any team member can audit state directly.
- **Git-diffable**. Every change to canonical state is visible in git history.
- **Machine-portable**. Checking out a repo gives full state immediately.
- **Schema-validatable** against JSON schemas for correctness checking.

A database would require export to share state across machines, would produce binary
diffs in git, and would require tooling to inspect. YAML has none of these drawbacks.

### Why a single writer?

Multi-agent writes produce conflicts. Even with careful locking, two AI agents writing
to the same canonical file will produce diverging state. The single-writer model avoids
this entirely. The orchestrator is the merge function; workers are the producers.

### Why a local DB cache at all?

YAML files are optimized for human readability and git portability, not for query speed.
As task boards grow, rendering a status report by parsing YAML on every call becomes slow.
The SQLite cache trades a small amount of setup complexity for fast, queryable state.
Since the cache is always rebuildable, it carries no integrity risk.

### Why an exportable memory pack?

The canonical YAML state records what is true now. It does not record the full event
history: what commands ran, what transitions happened, what was tried and rejected.
The memory pack carries this richer history for the cases where it matters (continuity
across machines or sessions with a new agent that benefits from seeing the event stream).

### Why the submodule architecture?

The submodule model separates the engine (this skeleton) from the project. This means:
- Engine upgrades never touch project state.
- Projects can pin exact engine versions via the submodule pointer.
- Multiple projects can use the same skeleton at different versions independently.
- The skeleton can be updated and tested independently of any specific project.

---

## 20. Future Extensions

The following capabilities are planned for future versions. They are not in v1.

**v2 local web Kanban UI**
A local web server that renders the task board, approval queue, and event timeline
in a browser. Reads from `.ai_runtime/ai_state.db`. No external services.

**Department leads**
An intermediate authority level between orchestrator and workers. A lead owns a domain
(e.g., `engineering`), delegates to workers in that domain, and reports rollups to the
orchestrator. This enables larger teams without overloading the orchestrator.

**Advanced approval flows**
Multi-level approvals with explicit quorum requirements. For example: a release requires
approval from both the orchestrator and an external human reviewer before proceeding.

**Role onboarding expansion**
Richer onboarding for specialized domains (research, marketing, operations) with
pre-configured role templates and approval policies suited to those contexts.

**v1 stability commitment**
v1 prioritizes stability, correctness, and predictability. No breaking changes to canonical
state schemas, command interfaces, or persistence model without a migration path.

---

## 21. Quick Reference Cheat Sheet

```
SETUP
─────────────────────────────────────────────────────────────────
# Add skeleton as submodule (recommended)
git submodule add <repo-url> vendor/ai-skeleton

# Initialize project
python vendor/ai-skeleton/engine/ai init

# Initialize without prompts (CI / scripted)
python vendor/ai-skeleton/engine/ai init --non-interactive


DAILY OPERATIONS
─────────────────────────────────────────────────────────────────
# Check project status
ai status

# Validate canonical YAML
ai validate

# Commit canonical state to git
ai git-sync

# Commit with custom message
ai git-sync --message "chore(ai): close phase 3"

# Start interactive orchestrator loop
ai run


DATABASE
─────────────────────────────────────────────────────────────────
# Rebuild DB from canonical YAML (use when DB is stale or corrupted)
ai rehydrate-db


MEMORY / CONTINUITY
─────────────────────────────────────────────────────────────────
# Export memory pack (timestamped directory)
ai export-memory

# Export memory pack as zip
ai export-memory --out /path/to/pack.zip

# Import memory pack
ai import-memory --in /path/to/pack.zip
ai import-memory --in /path/to/pack-dir/


ENGINE UPDATES (submodule model)
─────────────────────────────────────────────────────────────────
# Pull latest skeleton engine
git submodule update --remote --merge

# Apply new templates (no overwrite of existing state)
ai migrate

# Validate after update
ai validate

# Commit submodule pointer
git add vendor/ai-skeleton
git commit -m "chore: update ai-skeleton engine"


NEW MACHINE / FRESH CLONE
─────────────────────────────────────────────────────────────────
git clone <project-repo>
git submodule update --init --recursive
python vendor/ai-skeleton/engine/ai init --non-interactive
python vendor/ai-skeleton/engine/ai status
# Optional: restore event history
python vendor/ai-skeleton/engine/ai import-memory --in /path/to/pack.zip


RECOVERY
─────────────────────────────────────────────────────────────────
# DB corrupted or out of sync
ai rehydrate-db

# Validate state files
ai validate

# Remove accidentally committed runtime files
git rm -r --cached .ai_runtime/
echo ".ai_runtime/" >> .gitignore
git add .gitignore && git commit -m "fix: remove ai_runtime from tracking"
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*This manual reflects the v1 engine implementation. Commands and schemas are stable.
Engine updates via submodule will not break existing canonical state.*
