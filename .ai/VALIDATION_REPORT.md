# Validation Report

```
============================================================
FULL VALIDATION HARNESS
============================================================

--- 1. Schema Validation ---
  OK    team.yaml
  OK    board.yaml
  OK    approvals.yaml
  OK    commands.yaml
  OK    providers.yaml
  OK    intents.yaml
  OK    persistence.yaml
  OK    recovery.yaml
  OK    project.yaml
  OK    submodule_integrity
  OK    capabilities_consistency
  Schema validation: PASS

--- 2. Capabilities Contract (advertised <= implemented) ---
Capabilities check: PASS
  Advertised: 23  Implemented: 23

--- 3. Intent Routing Tests ---
  PASS  "where are we" -> handle_status (conf: 0.52)
  WARN  "progress update" -> handle_export_memory (expected handle_status, conf: 0.74)
  PASS  "help" -> handle_help (conf: 1.00)
  PASS  "what can you do" -> handle_help (conf: 0.73)
  PASS  "save everything" -> handle_force_sync (conf: 1.00)
  PASS  "save progress" -> handle_force_sync (conf: 1.00)
  PASS  "sync all" -> handle_force_sync (conf: 0.73)
  PASS  "what's pending" -> handle_status (conf: 0.72)
  PASS  "spawn workers" -> handle_spawn_workers (conf: 1.00)
  WARN  "start team" -> handle_init (expected handle_spawn_workers, conf: 0.73)
  PASS  "worker status" -> handle_workers_status (conf: 0.77)
  PASS  "validate the project" -> handle_validate (conf: 0.74)
  PASS  "export memory" -> handle_export_memory (conf: 0.78)
  PASS  "what's in scope" -> handle_check_scope (conf: 0.78)
  PASS  "checkpoint all workers" -> handle_checkpoint_workers (conf: 1.00)
  Intent routing: 13 pass, 2 warn, 0 fail

--- 4. Handler Smoke Tests ---
  PASS  handle_help
  PASS  handle_status
  PASS  handle_validate
  PASS  handle_check_scope
  PASS  handle_workers_status
  PASS  handle_show_checkpoints
  Smoke tests: 6 pass, 0 fail

--- 5. Submodule Safety ---
  PASS  No writes detected in submodules

--- 6. Skeleton Version Lock ---
  SKELETON UPDATED since last lock!
  Locked:  PLACEHOLDER (PLACEHOL)
  Current: ab9fdcf (ab9fdcf9)

  Actions required:
    1. Run 'ai validate --full' to check compatibility
    2. Run 'ai migrate' to apply new templates
    3. Review CAPABILITY_MATRIX.md for changes
  Do NOT proceed without validating.

============================================================
VALIDATION RESULT: ALL PASSED
============================================================
```
