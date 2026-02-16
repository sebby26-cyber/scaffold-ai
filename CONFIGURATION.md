# Project Configuration

**Purpose:** Per-project worker configuration and settings
**Location:** Create this file in your project root as `AI_CONFIG.md` or `.ai/config.md`

---

## Worker Lane Configuration

### Default Configuration

**By default, ALL worker lanes are DISABLED.**

You must explicitly enable the worker lanes you want to use for your project.

### Default Pool Sizes

Each lane supports **5 workers by default**, but this is expandable:

- **Codex Lane:** 5 workers (expandable to 10, 15, or more on request)
- **Claude Lane:** 5 workers (expandable to 10, 15, or more on request)
- **Gemini Lane:** 5 workers (expandable to 10, 15, or more on request)

**When to expand beyond 5 per lane:**
- Very large projects (>6 months)
- Highly parallelizable work with clear boundaries
- User explicitly requests more workers
- Lead has proven integration bandwidth

**Note:** 5 per lane is a **recommendation**, not a hard limit. Adjust based on project needs.

---

## Configuration File Format

**Location:** `AI_CONFIG.md` (project root)

**Format:**

```markdown
# AI Project Configuration

**Project:** [Your Project Name]
**Created:** [YYYY-MM-DD]

---

## Worker Pool Configuration

### Codex Workers (Code Implementation)

**Status:** ENABLED | DISABLED
**Pool Size:** 0-5 workers
**Specialization:** Code implementation, bug fixes, refactoring, test writing

**Enabled Workers:**
- [ ] Codex-Worker-1
- [ ] Codex-Worker-2
- [ ] Codex-Worker-3
- [ ] Codex-Worker-4
- [ ] Codex-Worker-5

---

### Claude Workers (Design/Planning)

**Status:** ENABLED | DISABLED
**Pool Size:** 0-5 workers
**Specialization:** Architecture design, API design, planning, documentation

**Enabled Workers:**
- [ ] Claude-Worker-1
- [ ] Claude-Worker-2
- [ ] Claude-Worker-3
- [ ] Claude-Worker-4
- [ ] Claude-Worker-5

---

### Gemini Workers (Supplemental Analysis)

**Status:** ENABLED | DISABLED
**Pool Size:** 0-5 workers
**Specialization:** Cross-validation, alternative approaches, edge cases

**Enabled Workers:**
- [ ] Gemini-Worker-1
- [ ] Gemini-Worker-2
- [ ] Gemini-Worker-3
- [ ] Gemini-Worker-4
- [ ] Gemini-Worker-5

---

## Total Active Pool Size

**Maximum Concurrent Workers:** [X] (sum of enabled workers)
**Recommended Maximum:** 15
**Your Configuration:** [Calculate based on checked boxes above]

---

## Configuration Notes

[Any project-specific notes about worker usage, constraints, or decisions]
```

---

## Configuration Presets

### Preset 1: Lead Only (No Workers)

**Use case:** Small projects, solo development, tight control

```markdown
## Worker Pool Configuration

### Codex Workers: DISABLED
Pool Size: 0

### Claude Workers: DISABLED
Pool Size: 0

### Gemini Workers: DISABLED
Pool Size: 0

**Total:** 0 workers (lead agent only)
```

**Characteristics:**
- Lead implements all code
- No parallel execution
- Simplest workflow
- Maximum control

---

### Preset 2: Codex Only (Code Focus)

**Use case:** Implementation-heavy projects, refactoring, bug fixes

```markdown
## Worker Pool Configuration

### Codex Workers: ENABLED
Pool Size: 3-5

**Enabled Workers:**
- [x] Codex-Worker-1
- [x] Codex-Worker-2
- [x] Codex-Worker-3
- [ ] Codex-Worker-4 (optional)
- [ ] Codex-Worker-5 (optional)

### Claude Workers: DISABLED
Pool Size: 0

### Gemini Workers: DISABLED
Pool Size: 0

**Total:** 3-5 workers (Codex only)
```

**Characteristics:**
- Parallel code implementation
- Lead handles design
- Good for clear requirements

---

### Preset 3: Claude Only (Design Focus)

**Use case:** Architecture planning, early-stage design, documentation

```markdown
## Worker Pool Configuration

### Codex Workers: DISABLED
Pool Size: 0

### Claude Workers: ENABLED
Pool Size: 3-5

**Enabled Workers:**
- [x] Claude-Worker-1
- [x] Claude-Worker-2
- [x] Claude-Worker-3
- [ ] Claude-Worker-4 (optional)
- [ ] Claude-Worker-5 (optional)

### Gemini Workers: DISABLED
Pool Size: 0

**Total:** 3-5 workers (Claude only)
```

**Characteristics:**
- Design exploration
- Multiple architectural approaches
- Lead implements based on designs

---

### Preset 4: Codex + Claude (Balanced)

**Use case:** Most projects, balanced design + implementation

```markdown
## Worker Pool Configuration

### Codex Workers: ENABLED
Pool Size: 3

**Enabled Workers:**
- [x] Codex-Worker-1
- [x] Codex-Worker-2
- [x] Codex-Worker-3
- [ ] Codex-Worker-4
- [ ] Codex-Worker-5

### Claude Workers: ENABLED
Pool Size: 2

**Enabled Workers:**
- [x] Claude-Worker-1
- [x] Claude-Worker-2
- [ ] Claude-Worker-3
- [ ] Claude-Worker-4
- [ ] Claude-Worker-5

### Gemini Workers: DISABLED
Pool Size: 0

**Total:** 5 workers (3 Codex + 2 Claude)
```

**Characteristics:**
- Design + implementation coverage
- Good balance for most projects
- Manageable orchestration

---

### Preset 5: Full Pool (Maximum Parallelization)

**Use case:** Large projects, aggressive timelines, high complexity

```markdown
## Worker Pool Configuration

### Codex Workers: ENABLED
Pool Size: 5

**Enabled Workers:**
- [x] Codex-Worker-1
- [x] Codex-Worker-2
- [x] Codex-Worker-3
- [x] Codex-Worker-4
- [x] Codex-Worker-5

### Claude Workers: ENABLED
Pool Size: 5

**Enabled Workers:**
- [x] Claude-Worker-1
- [x] Claude-Worker-2
- [x] Claude-Worker-3
- [x] Claude-Worker-4
- [x] Claude-Worker-5

### Gemini Workers: ENABLED
Pool Size: 5

**Enabled Workers:**
- [x] Gemini-Worker-1
- [x] Gemini-Worker-2
- [x] Gemini-Worker-3
- [x] Gemini-Worker-4
- [x] Gemini-Worker-5

**Total:** 15 workers (5 Codex + 5 Claude + 5 Gemini)
```

**Characteristics:**
- Maximum parallelization
- Complex orchestration
- Requires clear scope boundaries
- Best for very large projects

---

## Model Selection

**You can specify different models per worker lane.**

**Don't run expensive reasoning models on trivial tasks!**

Tell the agent which models to use:
- `"Use gpt-5.1-codex-mini for Codex workers"`
- `"Use claude-sonnet-4.5 for Claude workers"`
- `"Use gemini-2.0-flash for Gemini workers"`

Agent will update AI_CONFIG.md and log the decision.

---

## Configuration Decision Factors

### Project Size

**Small (<1 month):**
- Lead only OR 1-3 Codex workers
- Minimal Claude workers
- No Gemini workers

**Medium (1-3 months):**
- 3-5 Codex workers
- 2-3 Claude workers
- Optional: 1-2 Gemini workers

**Large (>3 months):**
- 5 Codex workers
- 3-5 Claude workers
- 2-5 Gemini workers

---

### Project Phase

**Phase 0 (Foundation):**
- Lead only (setup work)
- Maybe 1-2 Codex for parallel setup

**Phase 1-2 (Core Implementation):**
- Enable Codex workers (3-5)
- Enable Claude workers (2-3)

**Phase 3+ (Features/Polish):**
- Full pool if needed
- Gemini for validation

---

### Team Composition

**Solo developer + AI:**
- Start with lead only
- Add 1-2 Codex as needed
- Minimal orchestration overhead

**Small team + AI:**
- 3-5 Codex workers
- 2 Claude workers
- Coordinate with human team

**AI-first team:**
- Full 15-worker pool
- Aggressive parallelization
- Lead as primary integrator

---

## Configuration Guidelines

### Start Conservative

**Recommendation:** Begin with lead only or minimal workers

```markdown
Phase 0: Lead only (foundation)
Phase 1: Add 2 Codex workers (test parallelization)
Phase 2: Add 1 Claude worker (design help)
Phase 3+: Scale up as needed
```

**Why:**
- Learn orchestration patterns
- Understand integration overhead
- Avoid premature complexity

---

### Scale Based on Need

**Add workers when:**
- ✅ Clear parallelizable work exists
- ✅ Lead can define non-overlapping scope
- ✅ Integration bandwidth available
- ✅ Worker outputs provide value

**Don't add workers when:**
- ❌ Work is sequential
- ❌ Scope boundaries unclear
- ❌ Lead is integration-bottlenecked
- ❌ Diminishing returns

---

### Monitor Integration Overhead

**If integration takes longer than implementation:**
- Reduce worker pool
- Simplify scope boundaries
- Increase worker task size

**If workers frequently blocked:**
- Reduce dependencies
- Better task decomposition
- Sequential execution might be better

---

## Configuration Examples

### Example 1: Web API Project

```markdown
# AI Project Configuration

**Project:** REST API for Task Management
**Timeline:** 6 weeks
**Complexity:** Medium

## Worker Pool Configuration

### Codex Workers: ENABLED
**Pool Size:** 4

**Enabled Workers:**
- [x] Codex-Worker-1 (API endpoints)
- [x] Codex-Worker-2 (Database layer)
- [x] Codex-Worker-3 (Business logic)
- [x] Codex-Worker-4 (Tests)

### Claude Workers: ENABLED
**Pool Size:** 2

**Enabled Workers:**
- [x] Claude-Worker-1 (API design)
- [x] Claude-Worker-2 (Architecture planning)

### Gemini Workers: DISABLED

**Total:** 6 workers

**Rationale:**
- API implementation parallelizable by module
- Design work needed for contracts
- No cross-validation needed yet
```

---

### Example 2: CLI Tool Project

```markdown
# AI Project Configuration

**Project:** Command-Line Task Runner
**Timeline:** 4 weeks
**Complexity:** Low-Medium

## Worker Pool Configuration

### Codex Workers: ENABLED
**Pool Size:** 3

**Enabled Workers:**
- [x] Codex-Worker-1 (Command parsing)
- [x] Codex-Worker-2 (Execution engine)
- [x] Codex-Worker-3 (Tests)

### Claude Workers: ENABLED
**Pool Size:** 1

**Enabled Workers:**
- [x] Claude-Worker-1 (CLI design/UX)

### Gemini Workers: DISABLED

**Total:** 4 workers

**Rationale:**
- Small project, moderate parallelization
- CLI UX benefits from design thinking
- Codex handles implementation
```

---

### Example 3: Large Refactoring Project

```markdown
# AI Project Configuration

**Project:** Refactor Legacy Monolith to Microservices
**Timeline:** 16 weeks
**Complexity:** High

## Worker Pool Configuration

### Codex Workers: ENABLED
**Pool Size:** 5

**Enabled Workers:**
- [x] Codex-Worker-1 (Service A extraction)
- [x] Codex-Worker-2 (Service B extraction)
- [x] Codex-Worker-3 (Service C extraction)
- [x] Codex-Worker-4 (Shared library refactor)
- [x] Codex-Worker-5 (Tests)

### Claude Workers: ENABLED
**Pool Size:** 4

**Enabled Workers:**
- [x] Claude-Worker-1 (Service boundary design)
- [x] Claude-Worker-2 (API contract design)
- [x] Claude-Worker-3 (Migration strategy)
- [x] Claude-Worker-4 (Documentation)

### Gemini Workers: ENABLED
**Pool Size:** 3

**Enabled Workers:**
- [x] Gemini-Worker-1 (Validate service boundaries)
- [x] Gemini-Worker-2 (API contract review)
- [x] Gemini-Worker-3 (Migration risk analysis)

**Total:** 12 workers

**Rationale:**
- Large scope requires aggressive parallelization
- Service extraction can run in parallel
- Design decisions benefit from multiple perspectives
- Gemini validates critical architectural decisions
```

---

## Dynamic Configuration

### Changing Configuration Mid-Project

**You can enable/disable worker lanes between phases.**

**Example:**

```markdown
## Phase 0-1: Foundation + Core
- Codex: 3 workers (ENABLED)
- Claude: 1 worker (ENABLED)
- Gemini: DISABLED

## Phase 2-3: Feature Implementation
- Codex: 5 workers (ENABLED - scaled up)
- Claude: 3 workers (ENABLED - scaled up)
- Gemini: 2 workers (ENABLED - added for validation)

## Phase 4: Polish
- Codex: 2 workers (ENABLED - scaled down)
- Claude: 1 worker (ENABLED - scaled down)
- Gemini: DISABLED (no longer needed)
```

**Document changes in DECISIONS.md:**

```markdown
## 2026-02-16: Scaled Up Worker Pool for Phase 2

**Context:** Phase 2 has 8 parallelizable features
**Decision:** Increase from 4 to 8 workers (5 Codex + 3 Claude)
**Rationale:** Features have clear boundaries, can execute in parallel
**Consequence:** Lead integration bandwidth must increase
```

---

## Configuration in STATUS.md

**Always document active configuration in STATUS.md:**

```markdown
## Worker Pool Configuration

**Active Lanes:**
- Codex: ENABLED (3 workers)
- Claude: ENABLED (2 workers)
- Gemini: DISABLED

**Total Active Workers:** 5

**Enabled Workers:**
- Codex-Worker-1, 2, 3
- Claude-Worker-1, 2

**Configuration File:** AI_CONFIG.md (see for details)
```

---

## Version

**Model Version:** 1.0
**Last Updated:** 2026-02-16
