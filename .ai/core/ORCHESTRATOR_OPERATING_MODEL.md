# Orchestrator Operating Model

## Core Responsibilities

### 1. Onboarding
- Generate initial `team.yaml`, `board.yaml`, `approvals.yaml`, `commands.yaml` from user input
- Configure roles, workers, and approval rules
- Initialize the local runtime database

### 2. Task Management
- Create and assign tasks on the board
- Move tasks through columns (backlog → ready → in_progress → review → done)
- Enforce approval gates before sensitive transitions

### 3. Worker Coordination
- Spawn workers with role-specific prompts from `.ai/prompts/role_templates/`
- Assign tasks to workers based on role and availability
- Collect worker outputs as patchsets or artifacts
- Validate outputs before integrating into canonical state

### 4. Approval Enforcement
- Check every state transition against `.ai/state/approvals.yaml`
- Block transitions that require approval until all approvals are obtained
- Log approvals in the approval log

### 5. State Management
- Update canonical YAML files under `.ai/state/`
- Render derived views: `STATUS.md`, `DECISIONS.md`
- Sync canonical state to git via `ai git-sync`

### 6. Portability Guarantee
- The repo canonical state (`.ai/state/*.yaml`) is always sufficient to resume the project
- `ai export-memory` captures local runtime context for transfer
- A fresh clone + `ai init` + optional `ai import-memory` restores full working state

## Operating Loop

```
1. Load canonical state from .ai/state/*.yaml
2. Reconcile with local DB (rehydrate if needed)
3. Check for pending commands or user input
4. Dispatch commands to handlers
5. If running tasks: coordinate workers, collect outputs
6. Apply approved changes to canonical state
7. Render status and decision views
8. Optionally git-sync
```

## Constraints
- Never auto-push unless `auto_push: true` in METADATA.yaml
- Never commit `.ai_runtime/` contents
- Never overwrite user modifications without explicit command
