# AI Project Configuration

**Project:** [Your Project Name]
**Created:** [YYYY-MM-DD]
**Last Updated:** [YYYY-MM-DD]

---

## Worker Pool Configuration

### Codex Workers (Code Implementation)

**Status:** DISABLED
**Default Pool Size:** 5 workers (expandable on request)
**Specialization:** Code implementation, bug fixes, refactoring, test writing

**Note:** Specialization can be customized. Tell the agent:
"Change Codex workers to focus on [your custom specialty]"
Agent will update this file and log the decision.

**Enabled Workers (Default Set):**
- [ ] Codex-Worker-1
- [ ] Codex-Worker-2
- [ ] Codex-Worker-3
- [ ] Codex-Worker-4
- [ ] Codex-Worker-5

**Expandable (if needed):**
- [ ] Codex-Worker-6
- [ ] Codex-Worker-7
- [ ] Codex-Worker-8
- [ ] Codex-Worker-9
- [ ] Codex-Worker-10
- [ ] ... (expand as needed for very large projects)

**When to enable:**
- Implementation-heavy work
- Parallel feature development
- Bug fixing across modules
- Test suite implementation

---

### Claude Workers (Design/Planning)

**Status:** DISABLED
**Default Pool Size:** 5 workers (expandable on request)
**Specialization:** Architecture design, API design, planning, documentation

**Note:** Specialization can be customized. Tell the agent:
"Change Claude workers to also handle implementation"
Agent will update this file and log the decision.

**Enabled Workers (Default Set):**
- [ ] Claude-Worker-1
- [ ] Claude-Worker-2
- [ ] Claude-Worker-3
- [ ] Claude-Worker-4
- [ ] Claude-Worker-5

**Expandable (if needed):**
- [ ] Claude-Worker-6
- [ ] Claude-Worker-7
- [ ] Claude-Worker-8
- [ ] Claude-Worker-9
- [ ] Claude-Worker-10
- [ ] ... (expand as needed for very large projects)

**When to enable:**
- Architecture decisions needed
- API contract design
- Implementation planning
- Technical documentation

---

### Gemini Workers (Supplemental Analysis)

**Status:** DISABLED
**Default Pool Size:** 5 workers (expandable on request)
**Specialization:** Cross-validation, alternative approaches, edge case discovery

**Note:** Specialization can be customized. Tell the agent:
"Change Gemini workers to focus on testing and QA"
Agent will update this file and log the decision.

**Enabled Workers (Default Set):**
- [ ] Gemini-Worker-1
- [ ] Gemini-Worker-2
- [ ] Gemini-Worker-3
- [ ] Gemini-Worker-4
- [ ] Gemini-Worker-5

**Expandable (if needed):**
- [ ] Gemini-Worker-6
- [ ] Gemini-Worker-7
- [ ] Gemini-Worker-8
- [ ] Gemini-Worker-9
- [ ] Gemini-Worker-10
- [ ] ... (expand as needed for very large projects)

**When to enable:**
- Critical architecture validation
- Cross-checking other workers
- Alternative approach exploration
- Risk analysis

---

## Total Active Pool Size

**Maximum Concurrent Workers:** 0 (all lanes disabled)
**Recommended Maximum:** 15
**Your Configuration:** Update as you enable workers above

---

## Configuration History

### [YYYY-MM-DD]: Initial Configuration

**Status:** All lanes disabled
**Rationale:** Start with lead-only mode, add workers as needed

---

## Notes

[Add any project-specific notes about worker usage, constraints, or decisions]

---

## Quick Configuration Presets

**To enable a preset, check the appropriate boxes above.**

### Preset 1: Lead Only (Current)
- Codex: 0 workers
- Claude: 0 workers
- Gemini: 0 workers
- **Total: 0 workers**

### Preset 2: Minimal (Code Focus)
- Codex: 2-3 workers
- Claude: 0 workers
- Gemini: 0 workers
- **Total: 2-3 workers**

### Preset 3: Balanced
- Codex: 3 workers
- Claude: 2 workers
- Gemini: 0 workers
- **Total: 5 workers**

### Preset 4: Full Pool
- Codex: 5 workers
- Claude: 5 workers
- Gemini: 5 workers
- **Total: 15 workers**

---

**See CONFIGURATION.md for detailed guidance on sizing and configuration decisions.**
