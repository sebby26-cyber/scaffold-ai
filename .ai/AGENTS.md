# Scaffold AI — Operator Protocol

> This file is the single source of truth for how AI agents operate in this project.
> It is loaded automatically at session startup. You do not need to memorize it.
>
> **Compatibility:** This protocol is provider-agnostic. It is loaded by:
> - **Claude Code** via `CLAUDE.md` (project root shim)
> - **OpenAI Codex** via `AGENTS.md` (project root shim)
> - **Any agent** that reads `.ai/AGENTS.md` directly
>
> All three files point here. This is the canonical source.

---

## 0. Submodule Protection (Invariant)

The skeleton submodule (typically `scaffold/scaffold-ai/`) is a **read-only system layer**.
`vendor/` is reserved for language/package managers (for example Go vendoring), so system/framework submodules must not live there.

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
2. **Init submodules** — if `scaffold/scaffold-ai/` exists but is empty, run `git submodule update --init --recursive`.
3. **Locate canonical state** — verify `.ai/state/` exists. If not, run `ai init`.
4. **Locate runtime** — verify `.ai_runtime/` exists. If not, run `ai init`.
5. **Quick health check** — run `ai validate` to confirm YAML integrity.
6. **Detect orchestration mode** — read `.ai_runtime/mode.yaml` if it exists. Default is `execution`.
7. **Confirm ready** — print "Protocol loaded. Mode: [plan|execution]. Use /help for commands."
8. **Surface help** — show the human prompt guide (run `ai help`), or instruct: "Say 'help' to see what you can ask me to do."

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

#### Core Commands

| Command | Purpose | Options |
|---------|---------|---------|
| `/status` | Project status report | `--json` |
| `/help` | Context-aware usage guide | `--json` |
| `/init` | Initialize project structure | |
| `/validate` | Validate YAML against schemas | `--full`, `--hygiene` |
| `/git-sync` | Commit canonical state to git | `--message` |
| `/scope` | Show project scope | |
| `/migrate` | Apply new template files | |
| `/rehydrate-db` | Rebuild SQLite from YAML | |

#### Worker Management

| Command | Purpose | Options |
|---------|---------|---------|
| `/spawn-workers` | Spawn worker bees | `--force` |
| `/workers-status` | Show worker status | `--stalled` |
| `/stop-workers` | Stop all workers | |
| `/configure-team` | Configure team roles | `--spec` |
| `/workers-resume` | Resume stalled workers | `--worker_id` |
| `/workers-pause` | Pause a worker + checkpoint | `--worker_id` |
| `/workers-restart` | Restart a worker | `--worker_id` |
| `/force-sync` | Force flush + checkpoint | `--git` |
| `/checkpoint-workers` | Checkpoint all workers to canonical state | |
| `/show-checkpoints` | Show latest checkpoint per worker | |

#### Memory & Persistence

| Command | Purpose | Options |
|---------|---------|---------|
| `/export-memory` | Export canonical memory pack | `--out` |
| `/import-memory` | Import memory pack | `--in` |
| `/memory-export` | Export session memory pack | `--out`, `--ns` |
| `/memory-import` | Import session memory pack | `--in` |
| `/memory-purge` | Purge session memory | `--ns`, `--days` |

#### Orchestration & Planning

| Command | Purpose | Options |
|---------|---------|---------|
| `/mode` | Show or set orchestration mode | `plan`, `execution` |
| `/plan-status` | Show current planning status | |
| `/plan-generate` | Generate plan outputs (task DAG, batch plan) | |
| `/plan-approve` | Approve plan and generate execution tickets | |
| `/tickets` | List tickets with status | |
| `/tickets-validate` | Validate all ticket contracts | |
| `/precheck-collisions` | Run file collision checker | |
| `/stage-review-inputs` | Stage worker outputs for review | |
| `/batch-close` | Post-batch canonical sync gate | `--execute` |

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
| "show me what each worker is doing", "worker status" | `/workers-status` |
| "stop all workers", "stop workers" | `/stop-workers` |
| "resume stalled workers", "restart stuck worker" | `/workers-resume` |
| "save everything now", "force sync", "update project state" | `/force-sync` |
| "checkpoint all workers", "save worker progress" | `/checkpoint-workers` |
| "show me each worker's last checkpoint", "worker checkpoints" | `/show-checkpoints` |
| "what's in scope", "is this in scope", "add to scope" | `/scope` |
| "plan mode", "switch to plan mode" | `/mode plan` |
| "execution mode", "switch to execution mode" | `/mode execution` |
| "show plan", "plan status", "current plan" | `/plan-status` |
| "generate plan", "create plan", "task DAG" | `/plan-generate` |
| "approve plan", "finalize plan" | `/plan-approve` |
| "validate tickets", "check ticket contracts" | `/tickets-validate` |
| "list tickets", "show tickets" | `/tickets` |
| "check collisions", "file collision check" | `/precheck-collisions` |
| "stage review", "prepare review bundle" | `/stage-review-inputs` |
| "close batch", "post-batch sync" | `/batch-close` |

The system uses an **intent router** (intents.yaml) that matches natural language variations.
You do not need exact phrasing — common variations of the same intent will route correctly.

If confidence is low, respond:
> "Use `/status` or `/help` for guaranteed execution."

---

## 5. State Awareness

The agent must understand three storage layers:

| Layer | Location | Committed? | Purpose |
|-------|----------|------------|---------|
| Canonical state | `.ai/` | Yes | Project truth — tasks, team, decisions, tickets |
| Ticket contracts | `.ai/tickets/` | Yes | Per-worker scope boundaries and acceptance criteria |
| Runtime cache | `.ai_runtime/` | Never | SQLite, session memory, logs, packs, review staging |

- `.ai/state/*.yaml` always wins over `.ai_runtime/ai.db`.
- If the database seems wrong, run `/rehydrate-db`.
- Session memory persists every turn automatically. No manual save needed.
- Ticket contracts in `.ai/tickets/*.yaml` define what each worker may touch.

---

## 6. Authority Model

- **Orchestrator** = single writer. Only agent that modifies `.ai/state/` and commits.
- **Workers** = read-only. Produce proposals, never commit. Scoped by ticket contracts.
- The agent running this protocol is the orchestrator unless explicitly told otherwise.

### Approval Tiers

Actions require different approval levels depending on risk:

| Tier | Who approves | Examples |
|------|-------------|----------|
| `auto` | System (no human) | Test tickets, docs tickets, research |
| `pm` | PM lead or orchestrator | Prod tickets, scope changes |
| `orchestrator` | Orchestrator only | Batch close, plan approval |
| `user` | Human user | Architecture changes, core truth modifications |

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
| `.ai/state/recovery.yaml` | Worker recovery + stall detection config |
| `.ai/state/persistence.yaml` | Auto-flush and sync configuration |
| `.ai/state/capabilities_advertised.yaml` | Advertised capabilities manifest |
| `.ai/tickets/_index.yaml` | Ticket index (fast lookup) |
| `.ai/tickets/<id>.yaml` | Individual ticket contracts |
| `.ai/core_truths.yaml` | Core truths registry (project invariants) |
| `.ai/STATUS.md` | Auto-generated project status |
| `.ai/DECISIONS.md` | Append-only decision log |
| `.ai/AGENTS.md` | This file — operator protocol |
| `.ai/workers/roster.yaml` | Canonical worker roster (portable) |
| `.ai/workers/checkpoints/` | Portable worker checkpoints (committed) |
| `.ai/workers/summaries/` | Per-worker state summaries (committed) |
| `.ai_runtime/session/memory.db` | Session memory (SQLite) |
| `.ai_runtime/import_inbox/` | Drop memory packs here for auto-import |
| `.ai_runtime/workers/checkpoints/` | Worker checkpoint data (auto-recovery) |
| `.ai_runtime/review_staging/` | Staged review bundles |
| `.ai_runtime/mode.yaml` | Current orchestration mode |
| `.ai_runtime/compaction/` | Context compaction checkpoints |

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

## 11. Worker Recovery & Stall Detection

Workers can stall or hit token/context limits. The system handles this:

- **Heartbeat monitoring** — detects silent workers after timeout.
- **Behavior-based stall detection** — identifies workers with no diffs, log churn, repeated failures, or silence. Configurable in `recovery.yaml` (`stall_no_diff_minutes`, `stall_no_test_minutes`).
- **Checkpointing** — saves worker state to both `.ai_runtime/` (local detail) and `.ai/workers/checkpoints/` (portable, committed).
- **Resume** — builds a resume prompt from the last checkpoint + worker summary.
- **Max retries** — escalates to user after configured retry limit.
- **Portable state** — canonical worker state (roster, checkpoints, summaries) lives in `.ai/workers/` and is committed to git, so workers can resume on any machine.

Say "Resume stalled workers" or run `/workers-resume` to trigger recovery.
Say "Checkpoint all workers" or run `/checkpoint-workers` to save progress.
Say "Show me each worker's last checkpoint" to see what each worker has done.
Use `/workers-status --stalled` to see which workers are stalled and why.

---

## 12. Orchestration Modes

The system operates in one of two modes:

### Plan Mode

- Produces plans, task DAGs, batch assignments, and ownership matrices.
- Only `review`, `research`, and `docs` ticket types are permitted.
- Code-producing tickets (`prod`, `ops`) are blocked unless explicitly overridden.
- Enter with `/mode plan` or "switch to plan mode".

### Execution Mode (default)

- Runs approved tickets. Workers produce code, tests, and deliverables.
- `prod` and `ops` tickets require approval before execution.
- Enter with `/mode execution` or "switch to execution mode".

### Planning Workflow

1. `/plan-generate` — Creates task DAG, batch plan, ownership matrix from board.yaml
2. Review and debate (plan enters `debate` status)
3. `/precheck-collisions` — Verify no file overlaps between tickets
4. `/plan-approve` — Lock the plan and generate execution tickets
5. `/spawn-workers` — Launch workers with approved tickets

---

## 13. Ticket Contracts

Every worker receives a **ticket contract** (`.ai/tickets/<id>.yaml`) that defines:

- **objective** — What the worker must accomplish
- **allowed_files** — Glob patterns the worker may touch (enforced)
- **acceptance_commands** — Commands that must pass for the ticket to close
- **ticket_type** — `prod`, `test`, `docs`, `review`, `research`, `ops`
- **granularity** — `L0_strategic`, `L1_batch`, `L2_worker_ticket`, `L3_micro_task`, `L4_integration`
- **approval_tier** — `auto`, `pm`, `orchestrator`, `user`

### Policy Enforcement

- `review` tickets cannot touch code files (*.py, *.rs, *.go, etc.)
- `docs` tickets must match documentation patterns (*.md, docs/*, etc.)
- `test` tickets must match test patterns or be explicitly allowed
- Post-run violation checks compare actual changes against `allowed_files`
- Diff budget enforcement via `max_files_changed`

### Collision Prevention

Before spawning workers, the system checks for file ownership overlaps across active tickets.
Hard collisions (two `prod` tickets touching the same files) block spawning unless `--force` is used.
Run `/precheck-collisions` manually to check at any time.

---

## 14. Core Truths

The project maintains a set of **core truths** (`.ai/core_truths.yaml`) — machine-checkable invariants that must hold at all times:

- `blueprint_authority` — .ai/state/ YAML is the single source of truth
- `no_scope_drift` — Workers stay within ticket boundaries
- `no_destructive_unauth` — No destructive actions without explicit approval
- `single_writer` — Only the orchestrator commits to canonical state
- `no_provider_bypass` — All worker spawns go through the provider registry

Tickets can reference core truths via `core_truth_refs`. Violations are detected during validation.

---

## 15. Context Compaction

Long-running sessions risk context window exhaustion. The system provides:

- **Automatic detection** — Triggers compaction when estimated tokens exceed threshold or time exceeds interval (configurable in `recovery.yaml`).
- **Checkpoint artifacts** — Saves current state summary, active tickets, recent decisions, and worker status to `.ai_runtime/compaction/`.
- **Provider-aware** — Claude uses `/compact`, other providers get a skeleton-generated summary.
- **Handoff summaries** — Generated for session continuity across context resets.

---

## 16. Batch Close

After a batch of workers completes, run `/batch-close` to execute the post-batch sync gate:

1. Detect integrated vs pending worker slices
2. Run acceptance commands from completed tickets
3. Update board.yaml task statuses
4. Regenerate STATUS.md
5. Check for architecture changes requiring DECISIONS.md update
6. Run full validation
7. Report unsynced canonical files

Default is dry-run. Use `/batch-close --execute` to apply changes.

---

## 17. Review Pipeline

Worker outputs can be staged for review before integration:

1. `/stage-review-inputs` — Creates review bundles in `.ai_runtime/review_staging/`
2. Review tickets examine the bundles and produce comments
3. Comments are classified: `actionable` (must fix), `advisory` (consider), `speculative` (ignore for commits)
4. Only `actionable` and `advisory` comments are safe to commit

---

## 18. Provider Compatibility Notes

This protocol is designed to work across AI providers. The shim files ensure automatic loading:

| Provider | Auto-load file | Location | Behavior |
|----------|---------------|----------|----------|
| **Claude Code** | `CLAUDE.md` | Project root | Loaded into system prompt, redirects to `.ai/AGENTS.md` |
| **OpenAI Codex** | `AGENTS.md` | Project root | Discovered by Codex walker, redirects to `.ai/AGENTS.md` |
| **Other agents** | `.ai/AGENTS.md` | Direct read | Full protocol, no shim needed |

**Codex-specific notes:**
- Codex has a 32KB `project_doc_max_bytes` limit. This file + shim must stay under that.
- Codex concatenates AGENTS.md files from root down. The root `AGENTS.md` shim loads first, then `.ai/AGENTS.md` if Codex walks into `.ai/`.
- Codex respects programmatic checks. If `acceptance_commands` exist in tickets, Codex workers must run them.

**Claude-specific notes:**
- Claude Code loads `CLAUDE.md` at startup and treats it as system-level instructions.
- Claude supports `/compact` for context compaction natively.
- Claude's tool ecosystem (Bash, Read, Write, Edit) should be used for `ai` CLI commands.

**General agent notes:**
- Any agent can read `.ai/AGENTS.md` directly — no shim needed.
- The command catalog and natural language routing tables above are the complete interface.
- All state is in `.ai/state/*.yaml` — agents should read these files, not guess.
