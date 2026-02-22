# Worker Execution Rules

## Fundamental Constraints

1. **Workers never write to the repository.** All file modifications go through the orchestrator.
2. **Workers never run `git commit`, `git push`, or `git merge`.** Git operations are exclusively orchestrator responsibilities.
3. **Workers never modify canonical state files.** Files under `.ai/state/` are off-limits for direct writes.

## Output Format

Workers must produce outputs in one of these strict formats:

### Patchsets (preferred for code changes)
```diff
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,3 +10,5 @@
 existing line
+new line added
 existing line
```

### Markdown Artifacts (for documentation, analysis, plans)
```markdown
# Artifact: <title>
## Task: <task-id>
## Author: <worker-id>

<content>
```

### Structured Reports (for status, reviews)
```yaml
task_id: <id>
worker_id: <id>
status: completed|blocked|needs_review
summary: <one-line summary>
details: |
  <multi-line details>
```

## Approval Requests

When a task matches an approval trigger from `approvals.yaml`, the worker must:
1. Stop work on the triggering action
2. Produce an approval request artifact
3. Wait for orchestrator to confirm approval before continuing

## Communication

- Workers communicate exclusively through their output artifacts
- Workers do not communicate directly with other workers
- All inter-worker coordination goes through the orchestrator
