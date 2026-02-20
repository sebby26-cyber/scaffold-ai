# Scaffold AI — Operator Protocol

> This file is the single source of truth for how AI agents operate in this project.
> It is loaded automatically at session startup. You do not need to memorize it.

---

## 1. Startup Checklist

On every new session, do these steps in order:

1. **Confirm repo root** — locate `.git/` to establish the project root.
2. **Init submodules** — if `vendor/scaffold-ai/` exists but is empty, run `git submodule update --init --recursive`.
3. **Locate canonical state** — verify `.ai/state/` exists. If not, run `ai init`.
4. **Locate runtime** — verify `.ai_runtime/` exists. If not, run `ai init`.
5. **Quick health check** — run `ai validate` to confirm YAML integrity.
6. **Confirm ready** — print "Protocol loaded." and proceed.

If any step fails, stop and report the exact failure. Do not improvise around it.

---

## 2. Command Mode

### Prefix: `/`

Any user message starting with `/` is a **command**. Always.

**Rules:**
- Parse as `/command args` (e.g. `/status`, `/help --json`, `/export-memory --out pack.zip`).
- Route to the repo's command handler. Never fabricate output.
- If the command fails, report the exact error and suggest fix steps.
- Never guess what a command "might" return. Execute it or say it failed.

### Command Catalog

| Command | Aliases | Purpose | JSON mode |
|---------|---------|---------|-----------|
| `/status` | `/status report` | Project status report | `--json` |
| `/help` | `/guide`, `/commands` | Context-aware usage guide | `--json` |
| `/validate` | | Validate YAML against schemas | |
| `/git-sync` | | Commit canonical state to git | `--message` |
| `/export-memory` | | Export canonical memory pack | `--out` |
| `/import-memory` | | Import memory pack | `--in` |
| `/rehydrate-db` | | Rebuild SQLite from YAML | |
| `/migrate` | | Apply new template files | |
| `/memory-export` | | Export session memory pack | `--out`, `--ns` |
| `/memory-import` | | Import session memory pack | `--in` |
| `/memory-purge` | | Purge session memory | `--ns`, `--days` |

---

## 3. No-Freestyle Rule

For **status**, **help**, **report**, and **guide** requests:

- **MUST** run the repo's generator (`ai status`, `ai help`).
- **MUST** read canonical state from `.ai/state/`.
- **MUST NOT** improvise a "generic status" or invent project information.

If the generator is unavailable, say so. Do not substitute.

---

## 4. Natural Language Routing

If the user speaks naturally (no `/` prefix), match high-confidence intents:

| User says | Route to |
|-----------|----------|
| "status report", "give me status", "what's the progress" | `/status` |
| "help", "guide me", "what can you do", "how do I use this" | `/help` |
| "save memory", "export memory" | `/export-memory` |
| "import memory", "load memory" | `/import-memory` |
| "validate", "check the state" | `/validate` |
| "commit state", "sync to git" | `/git-sync` |

If confidence is low, respond:
> "Use `/status` or `/help` for guaranteed execution."

---

## 5. State Awareness

The agent must understand two storage layers:

| Layer | Location | Committed? | Purpose |
|-------|----------|------------|---------|
| Canonical state | `.ai/` | Yes | Project truth — tasks, team, decisions |
| Runtime cache | `.ai_runtime/` | Never | SQLite, session memory, logs, packs |

- `.ai/state/*.yaml` always wins over `.ai_runtime/ai.db`.
- If the database seems wrong, run `/rehydrate-db`.
- Session memory persists every turn automatically. No manual save needed.

---

## 6. Authority Model

- **Orchestrator** = single writer. Only agent that modifies `.ai/state/` and commits.
- **Workers** = read-only. Produce proposals, never commit.
- The agent running this protocol is the orchestrator unless explicitly told otherwise.

---

## 7. File Quick Reference

| File | What it is |
|------|-----------|
| `.ai/state/team.yaml` | Roles, workers, provider/model assignments |
| `.ai/state/board.yaml` | Task board (kanban columns + tasks) |
| `.ai/state/approvals.yaml` | Approval triggers and log |
| `.ai/state/commands.yaml` | Command registry (names, aliases, handlers) |
| `.ai/STATUS.md` | Auto-generated project status |
| `.ai/DECISIONS.md` | Append-only decision log |
| `.ai/AGENTS.md` | This file — operator protocol |
| `.ai_runtime/session/memory.db` | Session memory (SQLite) |
| `.ai_runtime/import_inbox/` | Drop memory packs here for auto-import |
