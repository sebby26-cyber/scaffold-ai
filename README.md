# Scaffold AI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org)
[![State: YAML](https://img.shields.io/badge/State-YAML%20%2B%20Git-orange.svg)](#persistence-model)
[![Memory: SQLite](https://img.shields.io/badge/Cache-SQLite-lightgrey.svg)](#persistence-model)

**A framework for running AI agent teams on real projects.**

One orchestrator leads. Workers execute. State is tracked in plain YAML, committed to your repo, and auditable by humans. Session memory persists automatically. Move between machines without losing context.

### What you get

- **One leader, many workers** — single orchestrator with write authority; workers are read-only
- **Project state in plain files** — YAML and Markdown, committed to git, diffable
- **Automatic persistence** — every turn saved, memory exported on exit, imported on startup
- **Portable context** — memory packs let you resume on any machine
- **Safety gates** — approval triggers pause execution until a human decides
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

> If the database and YAML disagree, the YAML is correct. The database is a derived view, rebuilt on demand.

---

## Quick Start

```bash
# Add skeleton as a submodule
git submodule add https://github.com/sebby26-cyber/scaffold-ai.git vendor/scaffold-ai

# Initialize (does not overwrite existing project files)
python3 vendor/scaffold-ai/engine/ai init

# Check project status
python3 vendor/scaffold-ai/engine/ai status

# Validate state files against schemas
python3 vendor/scaffold-ai/engine/ai validate
```

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

You interact using natural language. No commands to memorize.

```
"Give me a status report."          → ai status
"Save memory for another machine."  → ai export-memory
"Import previous memory."           → ai import-memory
"Commit current state."             → ai git-sync
"Validate project state."           → ai validate
"Rebuild the local database."       → ai rehydrate-db
```

The orchestrator translates intent into internal actions automatically.

---

## Command Reference

> These run under the hood. This table is for power users, CI, and debugging.

| Command | Purpose | Modifies |
|---------|---------|----------|
| `ai init` | Initialize `.ai/` and `.ai_runtime/` | Creates dirs, stamps metadata |
| `ai run` | Start interactive orchestrator loop | Session memory only |
| `ai status` | Print project status report | Renders STATUS.md |
| `ai validate` | Validate YAML against schemas | Nothing (read-only) |
| `ai git-sync` | Commit canonical state to git | Whitelisted `.ai/` files only |
| `ai rehydrate-db` | Rebuild SQLite from YAML | `.ai_runtime/ai.db` only |
| `ai migrate` | Apply new template files | Adds missing files, never overwrites |
| `ai export-memory` | Export canonical memory pack | `.ai_runtime/` only |
| `ai import-memory --in PATH` | Import canonical memory pack | `.ai_runtime/` only |
| `ai memory export` | Export session memory pack | `.ai_runtime/` only |
| `ai memory import --in PATH` | Import session memory pack | `.ai_runtime/` only |
| `ai memory purge` | Purge session memory | `.ai_runtime/session/` only |

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

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*v1 engine. Commands and schemas are stable. Engine updates via submodule will not break existing canonical state.*
