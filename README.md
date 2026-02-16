# AI Lead Project Skeleton

**A production-tested framework for AI-led software project execution**

[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/yourusername/ai-lead-project-skeleton)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tested](https://img.shields.io/badge/tested-production-brightgreen.svg)](https://github.com/yourusername/ai-lead-project-skeleton)

---

## What Is This?

An **AI project management framework** extracted from a production codebase that enables AI agents to reliably execute large software projects without chaos.

**Think of it as:** The "operating system" that allows AI lead agents to orchestrate multi-month projects with worker agents, persistent context, and guaranteed handoff.

**Extracted from:** [krov](https://github.com/sebby26-cyber/krov.git) - a control-plane-first personal agent runtime with governed skill execution, multi-channel messaging (Telegram/Discord/Slack), and companion-like personalization. Successfully executed 5 phases, maintained 100% test pass rate, and survived multiple lead agent handoffs.

---

## The Problem This Solves

### Without This Framework

❌ **AI Chaos** - Multiple agents making conflicting changes
❌ **Context Loss** - New agent can't resume, restarts from zero
❌ **Scope Creep** - Workers drift into overlapping work
❌ **Documentation Drift** - Docs don't reflect actual code
❌ **Handoff Failure** - Lead replacement requires complete re-discovery
❌ **Test Neglect** - Code committed without verification

### With This Framework

✅ **Controlled Orchestration** - 1 lead + up to 15 workers, clear boundaries
✅ **Context Persistence** - State survives agent replacement (<15 min resume)
✅ **Phase-Gated Execution** - Approval gates prevent unauthorized changes
✅ **Repo Synchronization** - Docs always match code reality
✅ **Transfer-Safe Handoff** - New lead operational in <15 minutes
✅ **Test Gates** - 100% passing before any commit

---

## Quick Start

### 1. Install Framework in Your Project

```bash
# Clone this skeleton
git clone https://github.com/yourusername/ai-lead-project-skeleton.git

# Copy into your project
cd /path/to/your/project
cp -r ../ai-lead-project-skeleton/.ai/ .
cp ../ai-lead-project-skeleton/STATUS.md .
cp ../ai-lead-project-skeleton/DECISIONS.md .
cp ../ai-lead-project-skeleton/AGENTS.md .
cp ../ai-lead-project-skeleton/AI_CONFIG.md .

# Or use as git submodule
git submodule add https://github.com/yourusername/ai-lead-project-skeleton.git .ai
```

---

### 2. Create Blueprint

```bash
mkdir -p docs/blueprint
vim docs/blueprint/IMPLEMENTATION_INSTRUCTIONS.md
```

**Blueprint template:**

```markdown
# [Project Name] Implementation Blueprint

## Vision
[What you're building and why]

## Architecture
[High-level system design]

## Core Features
1. Feature A - [description]
2. Feature B - [description]
3. Feature C - [description]

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Constraints
[Technical, timeline, or resource constraints]
```

---

### 3. Initialize Lead Agent

**Simply tell your AI agent:**

```
Read START_PROMPT.md and execute accordingly.
```

That's it! The agent will:
1. ✅ Read framework files
2. ✅ Present capabilities summary
3. ✅ Ask how many Codex/Claude/Gemini workers you want
4. ✅ Update AI_CONFIG.md automatically
5. ✅ Generate execution plan
6. ✅ Request your approval
7. ✅ Begin execution

**Available at any time:** Say **"Generate status report"** for full project state.

---

### 4. Execute

**Lead agent will:**

1. ✅ Generate phase plan with acceptance criteria
2. ✅ Request user approval
3. ✅ Execute Phase 0 (foundation)
4. ✅ Deploy workers (based on AI_CONFIG.md)
5. ✅ Integrate worker outputs
6. ✅ Update STATUS.md and DECISIONS.md
7. ✅ Request phase approval
8. ✅ Repeat until complete

**You monitor via:**
- `STATUS.md` (always current)
- **"Generate status report"** command (7-section detailed report)

---

## Core Concepts

### Lead-Conductor Pattern

**1 Lead Agent** (write access)
- Orchestrates workers
- Integrates outputs
- Maintains canonical state
- Makes final decisions
- Only agent that commits

**Up to 15 Worker Agents** (read-only)
- Analyze and propose
- Implement features completely
- Generate tests
- Output proposals to `.taskers/runs/`
- Never commit directly

**Think:** Lead is PR reviewer/merger, Workers open PRs

---

### Three Canonical Files

**STATUS.md** - Single source of truth
- Current phase/milestone/deliverable
- Active worker roster
- Prioritized TODO list
- Phase plan with acceptance criteria
- Resume checklist for handoff

**DECISIONS.md** - Append-only decision log
- Timestamped architectural decisions
- Context, alternatives, consequences
- Phase transitions
- Never delete, only append

**AGENTS.md** - Process guardrails
- Lead conductor protocol
- Worker orchestration rules
- Status report format
- Approval gate requirements

---

### Worker Pool Configuration

**All lanes DISABLED by default.** You enable per-project in `AI_CONFIG.md`.

**Codex Lane** (Code Implementation)
- Specialty: Code, tests, refactoring, bug fixes
- Default Pool: 5 workers (expandable on user request)

**Claude Lane** (Design/Planning)
- Specialty: Architecture, API design, documentation, planning
- Default Pool: 5 workers (expandable on user request)

**Gemini Lane** (Supplemental Analysis)
- Specialty: Cross-validation, alternatives, edge cases
- Default Pool: 5 workers (expandable on user request)

**Total:** 15 workers default (expandable based on project needs)

---

### 🔧 Customizing Worker Specializations

**These specialties are NOT hardcoded.** You can customize worker lanes for your project.

**Simple command to agent:**

```
"Change Claude workers to also handle implementation, not just design."
```

**Or:**

```
"Redefine worker lanes:
- Codex: Backend implementation only
- Claude: Frontend implementation + design
- Gemini: Testing and quality assurance"
```

**Agent will:**
1. Update `AI_CONFIG.md` with new specializations
2. Update `AGENTS.md` with lane definitions
3. Log the change in `DECISIONS.md`
4. Keep it persistent for this project

**Example customization:**
```
You: "I want Claude workers to do implementation work, not just design"
Agent: Updates AI_CONFIG.md:
       Claude Lane: Code implementation, design, architecture
       (instead of just design/planning)
Agent: Logs decision in DECISIONS.md
Agent: Continues with new lane definition
```

---

### 💰 Model Selection for Workers

**You can specify different models per worker lane.**

**Don't run expensive reasoning models on trivial tasks!**

**Simple command to agent:**

```
"Use gpt-5.1-codex-mini for Codex workers."
```

**Or specify per lane:**

```
"Configure models:
- Codex: gpt-5.1-codex-mini
- Claude: claude-sonnet-4.5
- Gemini: gemini-2.0-flash"
```

**Agent will:**
1. Update `AI_CONFIG.md` with model specifications
2. Log the decision in `DECISIONS.md`
3. Use specified models for worker deployment

**See:** [CONFIGURATION.md](CONFIGURATION.md) for presets and sizing guidance

---

### Phase-Gated Execution

```
Blueprint
  ↓
Granular Plan → [User Approval Gate]
  ↓
Phase 0 → [Acceptance Gate]
  ↓
Phase 1 → [Acceptance Gate]
  ↓
Phase N → [Acceptance Gate]
  ↓
Project Complete
```

**No shortcuts. No phase skipping. User approval required.**

---

### Transfer-Safe Handoff

**New lead can resume in <15 minutes:**

1. Read STATUS.md (5 min)
2. Read DECISIONS.md recent entries (3 min)
3. Check active workers (2 min)
4. Run smoke tests (3 min)
5. Confirm git status (1 min)
6. Pick next P0 from TODO (1 min)
7. Continue execution

**No questions asked. No context loss.**

---

## Framework Files

### Core Documentation (Read These First)

| File                                     | Purpose                           | When to Read           |
|------------------------------------------|-----------------------------------|------------------------|
| **README.md**                            | This file - framework overview    | First (humans)         |
| **START_PROMPT.md**                      | Agent initialization prompt       | First (AI agents)      |
| **CONFIGURATION.md**                     | Worker pool configuration         | Reference as needed    |
| **LEAD_AGENT_OPERATING_MODEL.md**        | Lead conductor instructions       | Auto-read by agent     |
| **WORKER_AGENT_EXECUTION_RULES.md**      | Worker constraints and protocols  | Auto-read by agent     |

### Execution Guides

| File                                        | Purpose                                            |
|---------------------------------------------|----------------------------------------------------|
| **PROJECT_EXECUTION_LIFECYCLE.md**          | Blueprint → Plan → Phase → Deliverable flow        |
| **BLUEPRINT_TO_PLAN_PROCESS.md**            | Converting concepts into actionable plans          |
| **GRANULAR_TASK_DECOMPOSITION.md**          | Breaking deliverables into worker tasks            |
| **MILESTONE_AND_DELIVERABLE_SYSTEM.md**     | Tracking progress and completion                   |

### Operational Protocols

| File                                     | Purpose                                          |
|------------------------------------------|--------------------------------------------------|
| **STATUS_REPORT_PROTOCOL.md**            | Transfer-safe 7-section status reports           |
| **CONTEXT_PERSISTENCE_SYSTEM.md**        | Canonical state files and resume mechanism       |
| **AGENT_HANDOFF_RESUME_PROTOCOL.md**     | <15 min handoff procedure                        |
| **REPO_SYNC_AND_LOGGING.md**             | Documentation sync and decision logging          |

### Safety and Templates

| File                              | Purpose                                 |
|-----------------------------------|-----------------------------------------|
| **EXECUTION_GUARDRAILS.md**       | Anti-patterns and safety mechanisms     |
| **WORKER_TICKET_TEMPLATE.md**     | Standard worker ticket format           |

---

## Project Structure

```
your-project/
├── .ai/                                 # Framework documentation
│   ├── LEAD_AGENT_OPERATING_MODEL.md
│   ├── WORKER_AGENT_EXECUTION_RULES.md
│   └── [... other framework files ...]
│
├── STATUS.md                            # Current state (canonical)
├── DECISIONS.md                         # Decision log (canonical)
├── AGENTS.md                            # Process rules (canonical)
├── AI_CONFIG.md                         # Worker pool configuration
│
├── docs/
│   ├── blueprint/
│   │   └── IMPLEMENTATION_INSTRUCTIONS.md
│   └── worker-ticket-templates/        # Committed templates
│       ├── codex-1.md ... codex-5.md
│       ├── claude-1.md ... claude-5.md
│       └── gemini-1.md ... gemini-5.md
│
├── .taskers/                            # Git-ignored execution state
│   ├── tickets/                         # Runtime worker tickets
│   └── runs/                            # Worker outputs (timestamped)
│       └── YYYYMMDD_HHMMSS/
│           ├── Codex-Worker-1.txt
│           └── Claude-Worker-2.txt
│
└── [your code, tests, etc.]
```

---

## Worker Configuration Examples

### Small Project (Lead + Minimal Workers)

```markdown
# AI_CONFIG.md

### Codex Workers: ENABLED
Pool Size: 2
- [x] Codex-Worker-1
- [x] Codex-Worker-2

### Claude Workers: DISABLED
### Gemini Workers: DISABLED

Total: 2 workers
```

---

### Medium Project (Balanced)

```markdown
# AI_CONFIG.md

### Codex Workers: ENABLED
Pool Size: 3
- [x] Codex-Worker-1
- [x] Codex-Worker-2
- [x] Codex-Worker-3

### Claude Workers: ENABLED
Pool Size: 2
- [x] Claude-Worker-1
- [x] Claude-Worker-2

### Gemini Workers: DISABLED

Total: 5 workers
```

---

### Large Project (Full Pool)

```markdown
# AI_CONFIG.md

### Codex Workers: ENABLED
Pool Size: 5 (all enabled)

### Claude Workers: ENABLED
Pool Size: 5 (all enabled)

### Gemini Workers: ENABLED
Pool Size: 5 (all enabled)

Total: 15 workers
```

**See:** [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration guidance

---

## Usage Examples

### Scenario 1: Starting New Project

```bash
# 1. Install framework
cp -r ai-lead-project-skeleton/.ai/ .
cp ai-lead-project-skeleton/{STATUS.md,DECISIONS.md,AGENTS.md,AI_CONFIG.md} .

# 2. Write blueprint
vim docs/blueprint/IMPLEMENTATION_INSTRUCTIONS.md

# 3. Tell agent: "Read START_PROMPT.md and execute accordingly"
# Agent asks: "How many Codex/Claude/Gemini workers?"
# You respond: "3 Codex, 2 Claude, 0 Gemini"
# Agent updates AI_CONFIG.md automatically

# 4. Lead generates plan in STATUS.md
# 5. User approves plan
# 6. Lead executes Phase 0
```

---

### Scenario 2: Mid-Project Handoff

```bash
# New lead agent receives project

# 1. Read STATUS.md (current state)
cat STATUS.md

# 2. Read recent DECISIONS.md entries
tail -50 DECISIONS.md

# 3. Check active workers
ls -la .taskers/runs/$(ls -t .taskers/runs/ | head -1)/

# 4. Run smoke tests
make test

# 5. Pick next P0 from STATUS.md TODO
# 6. Continue execution

# Total time: <15 minutes
```

---

### Scenario 3: Scaling Worker Pool

```bash
# Currently: 3 Codex + 2 Claude = 5 workers
# Need: More parallelization for Phase 3

# 1. Ask lead agent to scale workers
# You: "I need 2 more Codex workers and 1 more Claude worker for Phase 3"
# Agent: Updates AI_CONFIG.md (Codex: 5, Claude: 3)
# Agent: Logs decision in DECISIONS.md
# Agent: Updates STATUS.md worker roster
# Agent: Deploys additional workers
# Continues execution with larger pool
```

---

## Key Innovations

### 1. Read-Only Workers = Zero Merge Conflicts

Workers implement features completely but output proposals instead of committing. Lead reviews and integrates. Result: Parallel development without merge hell.

### 2. Append-Only Decision Log = Perfect Memory

DECISIONS.md never deletes entries. Complete architectural history preserved. New leads understand "why" decisions were made.

### 3. Resume Checklist = <15 Min Handoff

Standard 7-step checklist enables any new lead to become operational in <15 minutes without user questions.

### 4. Worker Lane Configuration = Right-Sized Orchestration

Enable only the worker lanes you need. Start small (lead only), scale up (15 workers) based on project complexity.

### 5. Phase Gates = No Scope Creep

User approval required before advancing phases. Prevents AI from racing ahead or making unauthorized changes.

---

## Anti-Patterns Prevented

| Anti-Pattern        | How Framework Prevents                      |
|---------------------|---------------------------------------------|
| AI Chaos            | Worker pool limits, scope boundaries        |
| Context Loss        | Three canonical files, resume checklist     |
| Scope Creep         | Phase gates, approval requirements          |
| Doc Drift           | Commit discipline, sync protocol            |
| Test Neglect        | Pre-commit test gates                       |
| Handoff Failure     | STATUS.md resume checklist                  |
| Overlapping Work    | Explicit scope in worker tickets            |
| Silent Failures     | Blocker documentation in STATUS.md          |

---

## FAQ

### Q: Do I need to use all 15 workers?

**No.** All worker lanes are DISABLED by default. Enable only what you need in `AI_CONFIG.md`.

Start with lead-only, add workers as needed.

---

### Q: Can workers implement features?

**Yes!** "Read-only" means "read-only git commit access" not "read-only code generation."

Workers write complete implementations. Lead reviews and commits them.

---

### Q: How do I know what worker pool size to use?

**Start small.** Begin with lead-only or 2-3 workers. Scale up only when:
- Clear parallelizable work exists
- Scope boundaries are obvious
- Lead has integration bandwidth

See [CONFIGURATION.md](CONFIGURATION.md) for sizing guidance.

---

### Q: Can I change worker configuration mid-project?

**Yes.** Enable/disable lanes between phases. Document changes in DECISIONS.md.

Example: Phase 0-1 (3 workers) → Phase 2-3 (8 workers) → Phase 4 (2 workers)

---

### Q: What if my project is smaller than the framework?

Use what you need. Minimum viable adoption:
- STATUS.md (current state)
- DECISIONS.md (decision log)
- Lead agent only (no workers)

Still get benefits: context persistence, handoff capability, decision history.

---

### Q: How do I test the handoff protocol?

1. Generate status report mid-project
2. Simulate new lead: read only STATUS.md
3. Can you determine next action without asking questions?
4. If yes, handoff works. If no, improve STATUS.md.

Target: <15 minutes to operational.

---

## Getting Help

### Documentation

- **Framework Overview:** This README
- **Lead Instructions:** [LEAD_AGENT_OPERATING_MODEL.md](.ai/LEAD_AGENT_OPERATING_MODEL.md)
- **Worker Instructions:** [WORKER_AGENT_EXECUTION_RULES.md](.ai/WORKER_AGENT_EXECUTION_RULES.md)
- **Configuration Guide:** [CONFIGURATION.md](CONFIGURATION.md)

### Issues & Contributions

- Report issues: [GitHub Issues](https://github.com/yourusername/ai-lead-project-skeleton/issues)
- Contribute improvements: [Pull Requests](https://github.com/yourusername/ai-lead-project-skeleton/pulls)
- Discussions: [GitHub Discussions](https://github.com/yourusername/ai-lead-project-skeleton/discussions)

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Credits

**Extracted from:** krov - A control-plane-first personal agent runtime with governed AI execution, multi-channel messaging (Telegram/Discord/Slack/WhatsApp/Signal/iMessage/Teams/SMS), tiered skill ecosystem (OpenClaw/ClawHub compatible), and companion-like personalization with governed memory

**Framework Version:** 1.0
**Release Date:** 2026-02-16
**Extraction Agent:** Claude Sonnet 4.5

**Acknowledgments:**
- Original krov project for proving framework viability
- Lead-conductor pattern for preventing AI chaos
- Append-only decision log for preserving context
- Resume checklist for enabling handoff

---

## Quick Reference

**Start New Project:**
```bash
cp -r ai-lead-project-skeleton/.ai/ your-project/
cd your-project
touch STATUS.md DECISIONS.md AGENTS.md AI_CONFIG.md
```

**Initialize Lead:**
```
Tell agent: "Read START_PROMPT.md and execute accordingly"

Agent will ask how many workers you want and configure automatically.
```

**Get Status:**
```
Say: "Generate status report"

Agent provides 7-section detailed status.
```

**Monitor Progress:**
```bash
cat STATUS.md  # Always current
```

**Handoff:**
```bash
cat STATUS.md  # Resume in <15 min
```

---

**Ready to build reliable AI-led projects? Start with the Quick Start above.** 🚀
