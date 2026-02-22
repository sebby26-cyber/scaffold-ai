# Scaffold AI

```
            ─────────────╦══════════════╗
                         ║              ╠═╗
                         ║              ║ │
                         ║              ║ ◆
                         ║
                         ║   S C A F F O L D  A I
                         ║
                         ║   AI agent orchestration
                         ║   for real projects.
                         ║
                         ║   One leader. Many workers.
                         ║   State you can read.
                         ║   Memory that travels.
                         ║
                       ══╩══
                      ▓▓▓▓▓▓▓
```

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org)
[![State: YAML](https://img.shields.io/badge/State-YAML%20%2B%20Git-orange.svg)](#persistence-model)
[![Memory: SQLite](https://img.shields.io/badge/Cache-SQLite-lightgrey.svg)](#persistence-model)

**A framework for running AI agent teams on real projects.**

One orchestrator leads. Workers execute. State is tracked in plain YAML, committed to your repo, and auditable by humans. Session memory persists automatically. Move between machines without losing context.

### What you get

- **One leader, many workers** — single orchestrator with write authority; worker bees run in parallel across departments
- **Project state in plain files** — YAML and Markdown, committed to git, diffable
- **Automatic persistence** — every turn saved, memory exported on exit, imported on startup
- **Portable context** — memory packs let you resume on any machine
- **Safety gates** — approval triggers pause execution until a human decides
- **Multi-provider workers** — Claude, Codex, Gemini, and any future CLI tool; provider + model per role
- **Auto-recovery** — workers that stall or hit token limits are checkpointed and resumed automatically
- **Stays focused** — scope guardrails prevent drift outside project boundaries
- **Works with any AI model** — no vendor lock-in, no API keys in the framework itself
- **Submodule-ready** — engine updates via pointer bump, never touches your project state

### Who this is for

| Good fit | Not a fit |
|----------|-----------|
| Teams using AI agents to manage software projects | End users looking for a chat app |
| Developers who want auditable, git-tracked AI state | Projects that need a hosted SaaS platform |
| Multi-machine workflows needing portable context | Single-prompt, one-shot AI usage |

---

## How It Works

```mermaid
graph LR
    H["Human"] -->|plain language| O["Orchestrator"]
    O -->|scoped tickets| W["Workers"]
    W -->|proposals| O
    O -->|writes| Y[".ai/state/*.yaml"]
    Y -->|reconcile| DB[".ai_runtime/ai.db"]
    O -->|auto-saves| SM["Session Memory"]
    SM -->|export| MP["Memory Packs"]
    O -->|git-sync| G["Git Repo"]

    style H fill:#e8f5e9,stroke:#388e3c
    style O fill:#e3f2fd,stroke:#1976d2
    style W fill:#fff3e0,stroke:#f57c00
    style Y fill:#fce4ec,stroke:#c62828
    style DB fill:#f5f5f5,stroke:#757575
    style SM fill:#f3e5f5,stroke:#7b1fa2
    style MP fill:#f3e5f5,stroke:#7b1fa2
    style G fill:#fce4ec,stroke:#c62828
```

**Two storage layers, clear separation:**

| Layer | Location | Committed? | Purpose |
|-------|----------|------------|---------|
| Canonical state | `.ai/` | Yes | Project truth — tasks, team, decisions, status |
| Runtime cache | `.ai_runtime/` | Never | SQLite DB, session memory, logs, memory packs |
| Temp / cache | `.tmp/`, `.tmp_cache/` | Never | Scratch space, safe to delete anytime |

> If the database and YAML disagree, the YAML is correct. The database is a derived view, rebuilt on demand.

**Switching computers?** You're safe — your checkpoints and project state travel with the repo. Import a memory pack only if you want full chat history. See [Repo Hygiene](.ai/REPO_HYGIENE.md) for details.

---

## Quick Start (Talk to AI)

You don't need to run commands. Just tell your AI what to do.

### Step 1 — Set up the project

If this is a new project or the system isn't set up yet, tell your AI:

```
Pull the Scaffold AI skeleton from https://github.com/sebby26-cyber/scaffold-ai.git into this project as a submodule at vendor/scaffold-ai, then run its initializer to set up the .ai/ directory and runtime.
```

The AI will handle cloning, submodule setup, and initialization. No terminal required.

If the skeleton is already present, skip to the next step.

### Step 2 — Activate the protocol

Paste this at the start of any new AI session:

```
Load `.ai/AGENTS.md` as your operating protocol, align to the current project state (resume if it exists, initialize if not), enforce command-first behavior with no freestyle outputs, and confirm readiness by summarizing project status and listing available commands.
```

This is the single activation prompt. It works with Claude Code, OpenAI Codex CLI, and Cursor (partial support). These tools may auto-load protocol files, but this prompt guarantees correct behavior.

On activation, the system runs a **compatibility gate** that verifies:
- All advertised capabilities have matching engine handlers (PASS/FAIL)
- Skeleton version matches the parent project's lock (detects updates)
- If any capability is missing, the system reports it and blocks readiness

After activation, the system will show the help guide automatically (or tell you to say "help"). Help only shows features that are actually implemented — never advertises unsupported commands.

### Step 3 — Talk to it

Once active, just say what you need. You don't need exact wording — the system understands common phrasing.

- **"Show me the current status"** — see project state and progress
- **"What's been completed and what's next?"** — task overview
- **"Start or initialize the project"** — set up from scratch
- **"Save everything now"** — force flush state + checkpoint workers
- **"Set up a team: 3 Codex devs + 1 Gemini analyst + 1 Claude designer"** — configure workers with provider/model
- **"Spawn worker bees"** — activate workers in parallel
- **"Resume stalled workers"** — recover workers that hit token limits
- **"Show me what each worker is doing"** — check worker status
- **"What's in scope?"** — see project boundaries
- **"Help"** — see the full prompt guide

The system maps your intent to the right action automatically. No commands to memorize.

---

## Requirements (AI CLI Setup)

This system uses AI tools installed on your computer. You need to install and log into one of these tools before using this project.

**Supported tools:**

| Tool | Status | Official setup |
|------|--------|----------------|
| Claude Code | Fully supported | [Installation guide](https://docs.anthropic.com/en/docs/claude-code/overview) |
| OpenAI Codex CLI | Fully supported | [Installation guide](https://github.com/openai/codex) |
| Gemini CLI | Supported (pass-through) | [Gemini CLI](https://ai.google.dev/gemini-api/docs) |
| Cursor | Partial support | [Getting started](https://docs.cursor.com) |

Add new providers by editing `.ai/state/providers.yaml` — no code changes needed.

Install the CLI for the AI you want to use and log in to your account. Follow the official setup instructions from each provider.

Once installed, this project uses those tools automatically through your terminal. You don't need to manage API keys inside this project.

---

### Developer Setup (CLI)

If you prefer terminal commands or need to set up CI/automation:

```bash
# Add skeleton as a submodule
git submodule add https://github.com/sebby26-cyber/scaffold-ai.git vendor/scaffold-ai

# Initialize (does not overwrite existing project files)
python3 vendor/scaffold-ai/engine/ai init

# Check project status
python3 vendor/scaffold-ai/engine/ai status

# Validate state files against schemas
python3 vendor/scaffold-ai/engine/ai validate

# Context-aware help guide
python3 vendor/scaffold-ai/engine/ai help
```

The orchestrator loads `.ai/AGENTS.md` automatically at startup. Root bridge files (`AGENTS.md`, `CLAUDE.md`) are auto-read by Codex and Claude Code respectively, so AI tools inherit project identity on session start with zero setup.

Optional: create a wrapper script at your project root:

```bash
#!/usr/bin/env bash
exec python3 "$(dirname "$0")/vendor/scaffold-ai/engine/ai" "$@"
```

**Prerequisites:** Python 3.9+, PyYAML (`pip install pyyaml`), Git

---

## Core Concepts

### Single-Writer Authority

The orchestrator is the only agent that writes canonical state and commits to the repository. Workers receive scoped tickets, produce output, and never modify shared state directly. This eliminates merge conflicts, ambiguous audit trails, and partial-state bugs.

### Persistence Model

**Canonical state** (`.ai/state/*.yaml`, `STATUS.md`, `DECISIONS.md`) is committed after every meaningful change. Clone the repo and the full project state is present.

**Runtime cache** (`.ai_runtime/`) holds the SQLite database, session memory, and logs. It is never committed and is fully rebuildable from canonical YAML via `ai rehydrate-db`.

**Session memory** persists every orchestrator turn to a local SQLite database. A memory pack is auto-exported on exit and auto-imported from `.ai_runtime/import_inbox/` on startup. No manual save commands needed.

### Memory Packs

Portable snapshots of session history. Canonical YAML records what is true now; memory packs record what happened. Export as zip, drop into `import_inbox/` on a new machine, and the orchestrator resumes with full context.

### Git Sync Safety

`ai git-sync` stages only whitelisted paths (`.ai/state/`, `STATUS.md`, `DECISIONS.md`, `METADATA.yaml`). Any non-whitelisted file that ends up staged is automatically unstaged before commit. `.ai_runtime/` is never committed.

---

## Talking to the Orchestrator

You interact using natural language. No commands to memorize. The orchestrator translates your intent into internal actions automatically.

| You say | What happens |
|---------|-------------|
| "Show me the current status" | Generates project status report |
| "What's been completed and what's next?" | Shows task progress and priorities |
| "Are there any blockers?" | Surfaces blocked tasks and issues |
| "Save current progress" | Exports memory pack for continuity |
| "Restore previous session" | Imports a memory pack |
| "Sync project state" | Commits canonical state to git |
| "Validate the project" | Checks YAML integrity against schemas |
| "Help" | Shows the full human prompt guide |

**Worker bees:**

| You say | What happens |
|---------|-------------|
| "Set up a team: 3 Codex devs + 1 Claude designer + 1 Gemini analyst" | Parses spec, writes team.yaml with provider/model per role |
| "Spawn worker bees" | Generates role prompts, writes registry, prints CLI commands |
| "Show me what each worker is doing" | Shows worker status from registry |
| "Resume stalled workers" | Recovers workers that hit token limits or went silent |
| "Stop all workers" | Marks workers as stopped |

**State and scope:**

| You say | What happens |
|---------|-------------|
| "Save everything now" | Force flush state + checkpoint all workers |
| "What's in scope?" | Shows project boundaries and guardrails |

Under the hood, the system creates role tickets for each worker, generates a provider-specific prompt file, and gives you the exact CLI command to run per worker in a separate terminal. State is auto-flushed on every task transition, worker change, and decision — no manual save needed.

### Workers Don't Forget

Worker progress is saved automatically via checkpoints and summaries in `.ai/workers/` (committed to git). If a worker hits token limits, stalls, or restarts, it resumes from its last checkpoint — not from scratch. Switching computers is safe because canonical worker state travels with the repo.

```
Checkpoint all workers, then show me what's pending.
```

---

## Example: Real-World Team Setup

This is a real team structure you can deploy with a single prompt. Copy-paste the prompt below into your AI session to set up the full team.

```
Orchestrator (Codex)
|
+-- codex-pm-tl-1            [PM / Tech Lead]         model: default
|   authority: write (planning + execution coordination)
|   |
|   +-- codex-dev-a          [Rust Core Dev]          model: gpt-5.1-codex-mini
|   |   scope: proto/**, internal/rust_core/**
|   |
|   +-- codex-dev-b          [Go Surface Dev]         model: gpt-5.1-codex-mini
|   |   scope: cmd/**, daemon wiring, gRPC client integration
|   |
|   +-- codex-dev-c          [Docs + Tests Dev]       model: gpt-5.1-codex-mini
|   |   scope: docs/blueprint/**, acceptance/parity test docs/scripts
|   |
|   +-- codex-dev-d          [General Dev / Support]  model: gpt-5.1-codex-mini
|   |   scope: non-overlapping implementation slices as assigned
|   |
|   +-- codex-tester-1       [Tester]                 model: gpt-5.1-codex-mini
|       scope: go test / smoke / acceptance / regression verification
|
+-- gemini-reviewer-1        [Independent Reviewer]   model: gemini-2.5-pro
    authority: review-only (advisory, no coding)
    reports_to: Orchestrator directly
    scope: risk / regression / scope-drift / bloat analysis only
```

**Set up this team by pasting this prompt:**

```
Set up and start an AI team for this project with the following structure.
Use the provider registry defaults unless a model is explicitly specified.
Persist the team to `.ai/state/team.yaml`, then spawn the workers and
show me worker status.

Orchestrator: Codex (default model)

Team Lead (PM / Tech Lead):
* 1 worker
* provider: Codex
* model: default
* authority: write (planning/execution coordination)

Reports to PM/Tech Lead:

1. Rust Core Dev
   * 1 worker
   * provider: Codex
   * model: gpt-5.1-codex-mini
   * scope: proto/**, internal/rust_core/**

2. Go Surface Dev
   * 1 worker
   * provider: Codex
   * model: gpt-5.1-codex-mini
   * scope: cmd/**, daemon wiring, gRPC client integration

3. Docs + Tests Dev
   * 1 worker
   * provider: Codex
   * model: gpt-5.1-codex-mini
   * scope: docs/blueprint/**, acceptance/parity test docs/scripts

4. General Dev / Support
   * 1 worker
   * provider: Codex
   * model: gpt-5.1-codex-mini
   * scope: non-overlapping implementation slices as assigned

5. Tester
   * 1 worker
   * provider: Codex
   * model: gpt-5.1-codex-mini
   * scope: go test / smoke / acceptance / regression verification

Peer to PM/Tech Lead (independent, advisory only):
* 1 worker
* role: Codebase Review / Analysis
* provider: Gemini
* model: gemini-2.5-pro
* authority: review-only (no coding)
* reports_to: Orchestrator directly
* scope: risk / regression / scope-drift / bloat analysis only
```

The orchestrator will parse this into `team.yaml`, write the provider/model config, spawn all workers, and display their status. No commands to memorize.

---

## Command Reference

> These run under the hood. This table is for power users, CI, and debugging.

| Command | Purpose | Modifies |
|---------|---------|----------|
| `ai help` | Context-aware help guide (supports `--json`) | Nothing (read-only) |
| `ai init` | Initialize `.ai/` and `.ai_runtime/` | Creates dirs, stamps metadata |
| `ai run` | Start interactive orchestrator loop | Session memory only |
| `ai status` | Print project status report | Renders STATUS.md |
| `ai validate` | Validate YAML against schemas | Nothing (read-only) |
| `ai validate --full` | Full capability + intent + safety harness | Writes VALIDATION_REPORT.md |
| `ai git-sync` | Commit canonical state to git | Whitelisted `.ai/` files only |
| `ai rehydrate-db` | Rebuild SQLite from YAML | `.ai_runtime/ai.db` only |
| `ai migrate` | Apply new template files | Adds missing files, never overwrites |
| `ai export-memory` | Export canonical memory pack | `.ai_runtime/` only |
| `ai import-memory --in PATH` | Import canonical memory pack | `.ai_runtime/` only |
| `ai memory export` | Export session memory pack | `.ai_runtime/` only |
| `ai memory import --in PATH` | Import session memory pack | `.ai_runtime/` only |
| `ai memory purge` | Purge session memory | `.ai_runtime/session/` only |
| `ai force-sync` | Force flush state + checkpoint workers | `.ai/state/` + `.ai_runtime/` |
| `ai spawn-workers` | Spawn worker bees | `.ai_runtime/workers/` |
| `ai workers-status` | Show worker status | Nothing (read-only) |
| `ai stop-workers` | Stop all workers | `.ai_runtime/workers/` |
| `ai configure-team` | Configure team from spec | `.ai/state/team.yaml` |
| `ai workers-resume` | Resume stalled workers | `.ai_runtime/workers/` |
| `ai workers-pause` | Pause + checkpoint a worker | `.ai_runtime/workers/` |
| `ai workers-restart` | Restart a worker from scratch | `.ai_runtime/workers/` |
| `ai checkpoint-workers` | Force checkpoint all workers | `.ai/workers/` |
| `ai show-checkpoints` | Show latest checkpoint per worker | Nothing (read-only) |
| `ai scope` | Show project scope boundaries | Nothing (read-only) |

---

## Resuming on a New Machine

```bash
git clone <your-project-repo>
git submodule update --init --recursive
python3 vendor/scaffold-ai/engine/ai init --non-interactive
```

This rebuilds the local runtime from committed state. The orchestrator knows the current phase, task board, and decisions immediately.

**For richer continuity**, drop a memory pack into `.ai_runtime/import_inbox/` before running `ai run`. It auto-imports on startup and moves the pack to `processed/`.

---

## How It's Meant to Be Used

This is **infrastructure you add to a project** to help AI agents run it reliably. It is not an application you deploy to end users.

- Humans interact by asking for status, giving approvals, and setting direction
- The orchestrator manages tasks, delegates to workers, and commits state changes
- Workers produce output within scoped boundaries; they never commit directly
- Everything is tracked in version-controlled YAML that humans can read and audit

The skeleton is **submodule-ready**: add it to any git project, initialize, and the orchestrator takes over project management. Engine updates propagate via `git submodule update` and `ai migrate` without touching your project state.

---

## System Safety

The AI engine lives in a protected layer (the skeleton submodule). It is never modified during normal operation.

- The system code is read-only. No agent can write to it, and no command will change it.
- Your project data is stored separately in `.ai/` (committed) and `.ai_runtime/` (local cache).
- Updates to the system happen through `git submodule update` and will not overwrite your project state.
- The `validate` command checks that the system layer has not been tampered with.

### How it stays consistent

The skeleton submodule is the system's reference for what it can do. When the AI is unsure about a command, feature, or workflow, it checks the system layer rather than guessing. This means:

- Answers about capabilities are based on what actually exists, not assumptions.
- When you pull system updates (`git submodule update`), the AI automatically picks up new features.
- If something isn't supported yet, the AI will tell you plainly instead of making it up.

### Update safety

When the skeleton submodule is updated, the system detects the change automatically:

1. A **skeleton lock** (`.ai/state/skeleton_lock.yaml`) records the last verified version
2. On startup, the compatibility gate compares the lock to the current skeleton HEAD
3. If the skeleton changed, it re-validates all capabilities and reports any drift
4. If a breaking change is detected, it blocks readiness and tells you exactly what to do

Run `ai validate --full` at any time to verify the full contract: schema compliance, capability coverage, intent routing accuracy, handler smoke tests, and submodule safety.

---

## Help / Guide

Say **"help"**, **"guide me"**, or **"what can you do?"** to get a context-aware guide tailored to your project's current state. The guide shows human-friendly prompts organized by category (Getting Started, Project Visibility, Memory & Continuity, System Actions) with CLI commands listed as an advanced reference at the bottom.

For the CLI: `ai help` (terminal) or `ai help --json` (for Kanban UI integration).

---

## Docs Map

| Document | What it covers |
|----------|---------------|
| [Authority Model](templates/.ai/core/AUTHORITY_MODEL.md) | Single-writer architecture, role permissions |
| [Worker Execution Rules](templates/.ai/core/WORKER_EXECUTION_RULES.md) | Worker boundaries, ticket format, read-only policy |
| [Orchestrator System Prompt](templates/.ai/prompts/orchestrator_system.md) | Orchestrator behavior and responsibilities |
| [Status Report Protocol](templates/.ai/core/STATUS_REPORT_PROTOCOL.md) | How status reports are generated |
| [Project Execution Lifecycle](PROJECT_EXECUTION_LIFECYCLE.md) | End-to-end workflow phases |
| [Execution Guardrails](EXECUTION_GUARDRAILS.md) | Safety constraints and approval gates |
| [Lead Agent Operating Model](LEAD_AGENT_OPERATING_MODEL.md) | Orchestrator operational patterns |
| [Context Persistence System](CONTEXT_PERSISTENCE_SYSTEM.md) | Persistence architecture details |
| [Agent Handoff/Resume Protocol](AGENT_HANDOFF_RESUME_PROTOCOL.md) | Cross-machine continuity procedures |
| [Smoke Test: Auto-Persistence](docs/SMOKE_TEST_AUTOPERSIST.md) | Manual verification steps |
| [Engine README](engine/README.md) | Engine internals, module map |
| [Operator Protocol](templates/.ai/AGENTS.md) | Agent behavior rules, command routing, startup checklist |

### AGENTS.md / Operator Protocol

**Protocol location:** `.ai/AGENTS.md` (canonical), root bridges: `AGENTS.md`, `CLAUDE.md`.

`.ai/AGENTS.md` is the single source of truth for how AI agents behave in this project. It is copied from templates during `ai init` and loaded automatically at the start of every session. Root-level bridge files (`AGENTS.md` for Codex, `CLAUDE.md` for Claude Code) are also created by `ai init` — these instruct the tool to read and follow the canonical protocol, giving agents project identity on first interaction.

It defines: a startup checklist, deterministic command mode (prefix `/` always routes to handlers), the no-freestyle rule (status/help/report must use the repo's generators, never improvise), drift control (repo state always overrides chat history), and natural language shortcuts. To force command mode from any agent, prefix your message with `/` (e.g. `/status`, `/help --json`).

**Supported tools:** Claude Code (auto-loads `CLAUDE.md`), OpenAI Codex (auto-loads `AGENTS.md`), Cursor (partial/evolving support). On session start, the agent confirms protocol load before proceeding.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*v1 engine. Commands and schemas are stable. Engine updates via submodule will not break existing canonical state.*
