# Status Report Protocol

## Report Generation

Status reports are derived from canonical state:
- **Team composition** from `team.yaml`
- **Task board** from `board.yaml`
- **Approval status** from `approvals.yaml`
- **Event history** from local DB (optional enrichment)

## Report Contents

Every status report must include:

1. **Phase**: Current project phase (initialization, active, paused, complete)
2. **Task Summary**: Count of tasks per board column
3. **Progress Bar**: Visual progress indicator (tasks done / total tasks)
4. **Active Tasks**: Tasks currently in_progress with owners
5. **Blockers**: Tasks that are blocked or waiting on approvals
6. **Pending Approvals**: Approval requests awaiting response
7. **Recent Decisions**: Last 5 entries from the decision log

## Output Targets

- **Terminal**: ASCII-formatted, human-readable output via `ai status`
- **STATUS.md**: Markdown file committed to repo for async visibility

## Update Frequency

- `STATUS.md` is regenerated on every `ai status` or `ai git-sync` call
- Terminal output is generated on-demand only

## Format Example

```
═══════════════════════════════════════
  PROJECT STATUS
═══════════════════════════════════════
  Phase: Active Development

  Tasks:
    backlog      ███░░  3
    ready        █░░░░  1
    in_progress  ██░░░  2
    review       ░░░░░  0
    done         ████░  4

  Progress: [████████░░░░░░░░░░░░] 40%

  Blockers: None
  Pending Approvals: 1 (scope_change on TASK-005)
═══════════════════════════════════════
```
