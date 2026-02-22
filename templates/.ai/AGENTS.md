# Scaffold AI — Operator Protocol

> This file is the single source of truth for how AI agents operate in this project.
> It is loaded automatically at session startup. You do not need to memorize it.

---

## 0. Submodule Protection (Invariant)

The skeleton submodule (typically `vendor/scaffold-ai/`) is a **read-only system layer**.

**Rules (no exceptions, all agents):**
- **NEVER** create, modify, or delete any file inside the submodule directory.
- **NEVER** stage or commit changes to the submodule.
- All writes MUST go to the parent project: `.ai/`, `.ai_runtime/`, or project-level files.
- Submodule updates happen ONLY via `git submodule update --remote`.

If you are about to write a file, resolve its absolute path first. If it falls inside the submodule, **stop and redirect** to the correct project directory.

**System layer lookup:** If unsure about available commands, capabilities, or workflows, **consult the skeleton submodule** (read its docs, command registry, and help templates) before responding. Do not guess or invent features. If a capability does not exist in the system layer, say so plainly and suggest alternatives.

---

## 1. Startup Checklist

On every new session, do these steps in order:

1. **Confirm repo root** — locate `.git/` to establish the project root.
2. **Init submodules** — if `vendor/scaffold-ai/` exists but is empty, run `git submodule update --init --recursive`.
3. **Locate canonical state** — verify `.ai/state/` exists. If not, run `ai init`.
4. **Locate runtime** — verify `.ai_runtime/` exists. If not, run `ai init`.
5. **Quick health check** — run `ai validate` to confirm YAML integrity.
6. **Confirm ready** — print "Protocol loaded." and proceed.
7. **Surface help** — show the human prompt guide (run `ai help`), or instruct: "Say 'help' to see what you can ask me to do."

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

| Command | Purpose | Options |
|---------|---------|---------|
| `/status` | Project status report | `--json` |
| `/help` | Context-aware usage guide | `--json` |
| `/validate` | Validate YAML against schemas | |
| `/git-sync` | Commit canonical state to git | `--message` |
| `/export-memory` | Export canonical memory pack | `--out` |
| `/import-memory` | Import memory pack | `--in` |
| `/rehydrate-db` | Rebuild SQLite from YAML | |
| `/migrate` | Apply new template files | |
| `/memory-export` | Export session memory pack | `--out`, `--ns` |
| `/memory-import` | Import session memory pack | `--in` |
| `/memory-purge` | Purge session memory | `--ns`, `--days` |
| `/spawn-workers` | Spawn worker bees | |
| `/workers-status` | Show worker status | |
| `/stop-workers` | Stop all workers | |
| `/configure-team` | Configure team roles | `--spec` |
| `/workers-resume` | Resume stalled workers | `--worker_id` |
| `/workers-pause` | Pause a worker + checkpoint | `--worker_id` |
| `/workers-restart` | Restart a worker | `--worker_id` |
| `/force-sync` | Force flush + checkpoint | `--git` |
| `/scope` | Show project scope | |

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
| "show me the current status", "what's the progress", "are there any blockers" | `/status` |
| "help", "guide me", "what can you do", "what can I say" | `/help` |
| "start or initialize the project", "initialize" | `/init` |
| "save current progress", "save memory", "export memory" | `/export-memory` |
| "export project memory" | `/memory-export` |
| "restore previous session", "import memory", "load memory" | `/import-memory` |
| "validate the project", "check if everything is working" | `/validate` |
| "sync project state", "commit state", "sync to git" | `/git-sync` |
| "resume where we left off" | `/run` |
| "spawn worker bees", "spin up worker bees", "run tasks in parallel" | `/spawn-workers` |
| "set up my team", "set up worker bees", "3 Codex devs and 1 Claude designer" | `/configure-team` |
| "3 Gemini analysts and 2 Codex devs" | `/configure-team` |
| "show me what each worker is doing", "worker status" | `/workers-status` |
| "stop all workers", "stop workers" | `/stop-workers` |
| "resume stalled workers", "restart stuck worker" | `/workers-resume` |
| "save everything now", "force sync", "update project state" | `/force-sync` |
| "what's in scope", "is this in scope", "add to scope" | `/scope` |

The system uses an **intent router** (intents.yaml) that matches natural language variations.
You do not need exact phrasing — common variations of the same intent will route correctly.

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
| `.ai/state/providers.yaml` | Provider registry (CLI tools, models, aliases) |
| `.ai/state/intents.yaml` | Intent registry (natural language routing) |
| `.ai/state/project.yaml` | Project scope definition (guardrails) |
| `.ai/state/recovery.yaml` | Worker recovery configuration |
| `.ai/state/persistence.yaml` | Auto-flush and sync configuration |
| `.ai/STATUS.md` | Auto-generated project status |
| `.ai/DECISIONS.md` | Append-only decision log |
| `.ai/AGENTS.md` | This file — operator protocol |
| `.ai_runtime/session/memory.db` | Session memory (SQLite) |
| `.ai_runtime/import_inbox/` | Drop memory packs here for auto-import |
| `.ai_runtime/workers/checkpoints/` | Worker checkpoint data (auto-recovery) |

---

## 8. Multi-Provider Workers

Worker bees support **any CLI provider** registered in `.ai/state/providers.yaml`:

- **Claude** (Anthropic) — `claude` CLI
- **Codex** (OpenAI) — `codex` CLI
- **Gemini** (Google) — `gemini` CLI
- **Cursor** — `cursor` IDE

Each provider has: CLI command, model argument flag, default model, session support.
Add new providers by editing `providers.yaml` — no code changes needed.

Team specs accept any registered provider:
- "3 Codex devs and 1 Gemini analyst"
- "Use Gemini for research, Codex for coding, Claude for design"

---

## 9. Scope Guardrails

Before executing any intent, the system checks `.ai/state/project.yaml`.

- **enforcement: off** — No checks performed.
- **enforcement: warn** — Warn the user but proceed.
- **enforcement: block** — Refuse execution and explain why.

If a request appears out of scope, say:
> "This appears to be out of scope for this project. See `/scope` for boundaries."

Users can expand scope: "Add this to project scope" → updates project.yaml.

---

## 10. Auto-Persistence

The system automatically keeps project state up to date:

- **Session memory** persists every turn automatically (no manual save needed).
- **Canonical state** auto-flushes on task transitions, worker changes, decisions.
- **Worker checkpoints** are saved on pause/resume/stall.

To force a full sync: say "Save everything now" or run `/force-sync`.

---

## 11. Worker Recovery

Workers can stall or hit token/context limits. The system handles this:

- **Heartbeat monitoring** — detects silent workers after timeout.
- **Checkpointing** — saves worker state to `.ai_runtime/workers/checkpoints/`.
- **Resume** — builds a resume prompt from the last checkpoint.
- **Max retries** — escalates to user after configured retry limit.

Say "Resume stalled workers" or run `/workers-resume` to trigger recovery.
