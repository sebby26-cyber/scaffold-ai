# Authority Model

## Roles and Permissions

### Orchestrator
- **Authority**: WRITE
- **Scope**: All canonical state files under `.ai/state/`, status/decision documents
- **Responsibilities**:
  - Create, update, and delete tasks on the board
  - Update team configuration
  - Approve or reject worker outputs
  - Commit canonical state via `ai git-sync`
  - Render status reports and decision logs

### Workers
- **Authority**: READ-ONLY
- **Scope**: May read any file in the repo; may NOT write to repo directly
- **Responsibilities**:
  - Produce outputs as patchsets, diffs, or markdown artifacts
  - Place outputs under `.ai/runs/<run-id>/` (if configured)
  - Request approvals when triggers are matched
  - Report completion status back to orchestrator

### Reviewers
- **Authority**: REVIEW
- **Scope**: May read any file; may approve/reject worker outputs
- **Responsibilities**:
  - Review patchsets and artifacts produced by workers
  - Provide approval or rejection with rationale
  - Cannot directly modify canonical state

## Hard Rules

1. **No direct repo edits by workers.** Workers never run `git add`, `git commit`, `git push`, or directly modify files under `.ai/state/`.
2. **Single-writer enforcement.** Only the orchestrator process writes canonical state. This prevents merge conflicts and state corruption.
3. **Approval gates are mandatory.** When a task matches an approval trigger, work cannot proceed until all required approvals are obtained.
4. **Canonical YAML is the source of truth.** The SQLite database is a derived cache. If they diverge, canonical YAML wins unconditionally.
