# Capability Matrix — Advertised vs Implemented

> Auto-generated audit. This is the canonical truth for what Scaffold AI supports.
> Last updated: 2026-02-22

## Legend

| Status | Meaning |
|--------|---------|
| IMPLEMENTED | Handler exists and is reachable via CLI + intent router |
| CLI-ONLY | Reachable via `ai run` interactive loop but not direct CLI |
| MISSING | Advertised but not implemented |

## Command / Intent Matrix

| Feature / Intent | Human Aliases | Handler | CLI Direct | Intent Router | Tested | Notes |
|-----------------|---------------|---------|------------|---------------|--------|-------|
| help | help, guide, what can you do | handle_help | Yes | Yes | Yes | |
| status | status, show me the current status | handle_status | Yes | Yes | Yes | |
| init | init, start the project | handle_init | Yes | Yes | Yes | |
| export-memory | save current progress, export memory | handle_export_memory | Yes | Yes | Yes | |
| import-memory | restore previous session, load memory | handle_import_memory | Yes | Yes | Yes | |
| rehydrate-db | rebuild database | handle_rehydrate_db | Yes | Yes | Yes | |
| validate | validate the project, check everything | handle_validate | Yes | Yes | Yes | |
| git-sync | sync project state, commit state | handle_git_sync | Yes | Yes | Yes | |
| migrate | apply new templates | handle_migrate | Yes | Yes | Yes | |
| memory export | export session memory | handle_session_memory_export | Yes | Yes | Yes | |
| memory import | import session memory | handle_session_memory_import | Yes | Yes | Yes | |
| memory purge | purge session memory | handle_session_memory_purge | Yes | Yes | Yes | |
| force-sync | save everything, save progress, sync all | handle_force_sync | Yes | Yes | Yes | FORCE_SYNC intent |
| spawn-workers | spawn worker bees, spin up team | handle_spawn_workers | Yes | Yes | Yes | |
| workers-status | worker status, what each worker is doing | handle_workers_status | Yes | Yes | Yes | |
| stop-workers | stop all workers | handle_stop_workers | Yes | Yes | Yes | |
| configure-team | set up my team, configure team | handle_configure_team | Yes | Yes | Yes | |
| workers-resume | resume stalled workers | handle_workers_resume | Yes | Yes | Yes | |
| workers-pause | pause worker | handle_workers_pause | Yes | Yes | Yes | |
| workers-restart | restart worker | handle_workers_restart | Yes | Yes | Yes | |
| scope | what's in scope, project boundaries | handle_check_scope | Yes | Yes | Yes | |
| checkpoint-workers | checkpoint all workers, save worker progress | handle_checkpoint_workers | Yes | Yes | Yes | |
| show-checkpoints | show worker checkpoints | handle_show_checkpoints | Yes | Yes | Yes | |

## Advertised Features (README / Help)

| Feature | Advertised In | Implemented | Handler |
|---------|--------------|-------------|---------|
| "Save everything now" | README, Help | Yes | handle_force_sync |
| "Set up a team: 3 Codex devs + 1 Claude designer" | README, Help | Yes | handle_configure_team |
| "Spawn worker bees" | README, Help | Yes | handle_spawn_workers |
| "Resume stalled workers" | README, Help | Yes | handle_workers_resume |
| "Show me what each worker is doing" | README, Help | Yes | handle_workers_status |
| "What's in scope?" | README, Help | Yes | handle_check_scope |
| Multi-provider workers | README | Yes | ai_workers + providers.yaml |
| Auto-recovery | README | Yes | ai_recovery.py |
| Portable context / memory packs | README | Yes | ai_memory.py + memory_core/ |
| Scope guardrails | README | Yes | ai_scope.py |
| Submodule safety | README | Yes | guard.py + ai_validate.py |

## Contract Status

- **Advertised commands**: 23
- **Implemented handlers**: 23
- **CLI direct access**: 23 (after update)
- **Intent-routable**: 21 (all intents in intents.yaml)
- **Schema-validated**: 9 YAML files
- **Gaps**: None (all advertised features have handlers)

## Compatibility Gate

The bootstrap step 2 now includes a compatibility check that:
1. Reads capabilities_advertised.yaml
2. Verifies all advertised handlers exist in HANDLERS dict
3. Reports PASS/FAIL with actionable output
4. Blocks readiness on FAIL
