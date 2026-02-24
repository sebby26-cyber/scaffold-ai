# Worktree Design (Phase 2 Roadmap)

> **Status:** Design document. Implementation deferred to phase 2.

## Overview

Per-worker `git worktree` isolation eliminates file collisions at the filesystem level. Instead of relying on allowed_files enforcement alone, each worker operates in its own worktree branch.

## Branch Naming

```
worker/<worker_id>
```

Example: `worker/dev-1`, `worker/tester-2`

## Lifecycle

1. **Spawn**: `git worktree add .ai_runtime/worktrees/<worker_id> -b worker/<worker_id>`
2. **Execute**: Worker runs in its worktree directory
3. **Harvest**: Orchestrator cherry-picks changes during batch-close
4. **Cleanup**: `git worktree remove .ai_runtime/worktrees/<worker_id>`

## Integration via Cherry-Pick

During `batch-close`:
1. For each completed worker branch:
   - `git cherry-pick worker/<worker_id>` onto main
   - Run acceptance commands
   - If fail: discard (partial harvest)
2. Delete worker branches after integration

## Advantages

- Zero file collisions (separate filesystem)
- Natural git history per worker
- Easy partial harvest/discard
- Existing allowed_files enforcement still applies as validation

## Limitations

- Requires git worktree support (git 2.5+)
- Disk space increases linearly with worker count
- Cherry-pick conflicts possible (collision checker still needed)

## Prerequisites

- Collision checker must pass before worktree spawn
- Worker prompts must include worktree path
- Checkpoint artifacts must record worktree branch name
