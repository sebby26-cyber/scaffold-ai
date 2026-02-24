"""
ai_init.py — First-run initializer.

Creates .ai/ from templates (if missing), sets up .ai_runtime/,
stamps METADATA.yaml, and ingests canonical state into SQLite.
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from . import ai_db, ai_git, ai_state

# Registry files that support append-only merging during upgrades.
# Each entry: (filename, list_key, identity_key)
# list_key = YAML key containing the list of entries
# identity_key = field that uniquely identifies each entry
_MERGEABLE_REGISTRIES = [
    ("state/commands.yaml", "commands", "name"),
    ("state/intents.yaml", "intents", "id"),
    ("state/capabilities_advertised.yaml", "capabilities", "id"),
    ("state/recovery.yaml", None, None),  # top-level keys, merge missing
]

from .submodule_paths import (
    CANONICAL_SUBMODULE_PATH,
    LEGACY_SUBMODULE_PATH,
    SUBMODULE_POLICY_SUMMARY,
    detect_submodule_layout,
    relpath_from_project,
)


class InitBlockedError(RuntimeError):
    """Raised when init detects a required explicit migration step."""


def _yaml_dump(data: dict) -> str:
    if yaml:
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    raise ImportError("PyYAML is required. Install it: pip install pyyaml")


def _yaml_load(text: str) -> dict:
    if yaml:
        return yaml.safe_load(text) or {}
    raise ImportError("PyYAML is required. Install it: pip install pyyaml")


def find_skeleton_dir() -> Path:
    """Find the skeleton repo directory (where this engine lives)."""
    return Path(__file__).resolve().parent.parent


def copy_templates(skeleton_dir: Path, project_root: Path):
    """Copy template files into the project.

    Copies .ai/ templates into project's .ai/ directory, and root-level
    bridge files (AGENTS.md, CLAUDE.md) into the project root.
    Does not overwrite existing files.
    """
    templates_dir = skeleton_dir / "templates" / ".ai"
    ai_dir = project_root / ".ai"

    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates not found at {templates_dir}")

    # Copy .ai/ templates
    for src_file in templates_dir.rglob("*"):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(templates_dir)
        dst = ai_dir / rel
        if dst.exists():
            continue  # Do not overwrite existing files
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_file), str(dst))

    # Copy root-level bridge files (AGENTS.md, CLAUDE.md)
    root_templates = skeleton_dir / "templates"
    for name in ("AGENTS.md", "CLAUDE.md"):
        src = root_templates / name
        dst = project_root / name
        if src.exists() and not dst.exists():
            shutil.copy2(str(src), str(dst))


def merge_registry_updates(skeleton_dir: Path, project_root: Path) -> list[str]:
    """Append-only merge of new entries from template registries into project state.

    For list-based registries (commands, intents, capabilities): appends entries
    whose identity_key doesn't already exist in the project file.

    For dict-based registries (recovery): adds top-level keys that are missing.

    Never removes or overwrites existing entries. Returns a log of changes.
    """
    if yaml is None:
        return ["PyYAML required for registry merge"]

    templates_dir = skeleton_dir / "templates" / ".ai"
    ai_dir = project_root / ".ai"
    log: list[str] = []

    for filename, list_key, id_key in _MERGEABLE_REGISTRIES:
        src = templates_dir / filename
        dst = ai_dir / filename
        if not src.exists():
            continue
        if not dst.exists():
            # File doesn't exist yet — copy it wholesale
            dst.parent.mkdir(parents=True, exist_ok=True)
            import shutil as _shutil
            _shutil.copy2(str(src), str(dst))
            log.append(f"  + {filename} (new file)")
            continue

        try:
            src_data = yaml.safe_load(src.read_text()) or {}
            dst_data = yaml.safe_load(dst.read_text()) or {}
        except Exception as e:
            log.append(f"  ! {filename}: parse error ({e})")
            continue

        if list_key and id_key:
            # List-based merge: append entries with new identity keys
            src_items = src_data.get(list_key, [])
            dst_items = dst_data.get(list_key, [])
            existing_ids = {item.get(id_key) for item in dst_items if isinstance(item, dict)}
            added = 0
            for item in src_items:
                if isinstance(item, dict) and item.get(id_key) not in existing_ids:
                    dst_items.append(item)
                    added += 1
            if added > 0:
                dst_data[list_key] = dst_items
                dst.write_text(yaml.dump(dst_data, default_flow_style=False, sort_keys=False))
                log.append(f"  + {filename}: {added} new entries added")
            else:
                log.append(f"  = {filename}: up to date")
        else:
            # Dict-based merge: add missing top-level keys
            added = 0
            for key, value in src_data.items():
                if key not in dst_data:
                    dst_data[key] = value
                    added += 1
            if added > 0:
                dst.write_text(yaml.dump(dst_data, default_flow_style=False, sort_keys=False))
                log.append(f"  + {filename}: {added} new keys added")
            else:
                log.append(f"  = {filename}: up to date")

    # Also update bridge files (AGENTS.md, CLAUDE.md) — these are always overwritten
    # from templates since they are shims, not user-customized content
    root_templates = skeleton_dir / "templates"
    for name in ("AGENTS.md", "CLAUDE.md"):
        src = root_templates / name
        dst = project_root / name
        if src.exists():
            import shutil as _shutil
            _shutil.copy2(str(src), str(dst))
            log.append(f"  * {name}: updated from template")

    # Update .ai/AGENTS.md (the full protocol)
    src_protocol = root_templates / ".ai" / "AGENTS.md"
    dst_protocol = ai_dir / "AGENTS.md"
    if src_protocol.exists():
        import shutil as _shutil
        _shutil.copy2(str(src_protocol), str(dst_protocol))
        log.append(f"  * .ai/AGENTS.md: updated from template")

    return log


def stamp_metadata(project_root: Path, skeleton_dir: Path):
    """Stamp METADATA.yaml with project_id, skeleton_version, and timestamp."""
    metadata_path = project_root / ".ai" / "METADATA.yaml"

    if metadata_path.exists():
        meta = _yaml_load(metadata_path.read_text())
    else:
        meta = {}

    if not meta.get("project_id") or meta["project_id"] == "PLACEHOLDER":
        meta["project_id"] = str(uuid.uuid4())

    version = ai_git.get_skeleton_version(skeleton_dir)
    meta["skeleton_version"] = version

    if not meta.get("initialized_at") or meta["initialized_at"] == "PLACEHOLDER":
        meta["initialized_at"] = datetime.now(timezone.utc).isoformat()

    meta.setdefault("auto_push", False)
    meta.setdefault("paths", {"ai_dir": ".ai", "runtime_dir": ".ai_runtime"})

    # Detect submodule
    skeleton_rel = None
    try:
        skeleton_rel = str(skeleton_dir.relative_to(project_root))
    except ValueError:
        pass
    meta["submodule_path"] = skeleton_rel

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(_yaml_dump(meta))

    return meta


def setup_runtime(project_root: Path):
    """Create .ai_runtime/ directory structure."""
    runtime_dir = project_root / ".ai_runtime"
    for subdir in ["logs", "session", "memory_pack_cache", "import_inbox", "memory_packs", "workers/checkpoints"]:
        (runtime_dir / subdir).mkdir(parents=True, exist_ok=True)


def run_onboarding(project_root: Path):
    """Interactive onboarding flow for first-time setup.

    Asks user about project type, team composition, and approval rules,
    then writes canonical YAML files.
    """
    ai_dir = project_root / ".ai"
    team_path = ai_dir / "state" / "team.yaml"

    # Check if team.yaml has workers configured already
    if team_path.exists():
        team = _yaml_load(team_path.read_text())
        has_workers = False
        for role in team.get("roles", []):
            if role.get("workers"):
                has_workers = True
                break
        if has_workers:
            return  # Already configured, skip onboarding

    print("\n=== AI Team Onboarding ===\n")

    # 1) Project type
    print("Project types: software, marketing, ops, mixed")
    project_type = input("Project type [software]: ").strip().lower() or "software"

    # 2) Team composition
    print(f"\nConfiguring team for '{project_type}' project.")
    print("Define roles (press Enter with empty role_id to finish):\n")

    roles = []
    default_roles = {
        "software": [
            {"role_id": "developer", "title": "Developer", "department": "engineering"},
            {"role_id": "reviewer", "title": "Code Reviewer", "department": "engineering"},
        ],
        "marketing": [
            {"role_id": "content_writer", "title": "Content Writer", "department": "marketing"},
            {"role_id": "analyst", "title": "Analyst", "department": "marketing"},
        ],
        "ops": [
            {"role_id": "sre", "title": "SRE", "department": "operations"},
            {"role_id": "devops", "title": "DevOps Engineer", "department": "operations"},
        ],
        "mixed": [
            {"role_id": "developer", "title": "Developer", "department": "engineering"},
            {"role_id": "pm", "title": "Project Manager", "department": "management"},
        ],
    }

    use_defaults = input(
        f"Use default roles for '{project_type}'? [Y/n]: "
    ).strip().lower()

    if use_defaults != "n":
        roles = default_roles.get(project_type, default_roles["software"])
        for role in roles:
            role["reports_to"] = "orchestrator"
            role["authority"] = "read"
            role["workers"] = []

            print(f"\n  Role: {role['title']} ({role['role_id']})")
            provider = input(f"    Provider [anthropic]: ").strip() or "anthropic"
            model = input(f"    Model [claude-sonnet-4-5-20250929]: ").strip() or "claude-sonnet-4-5-20250929"
            worker_id = input(f"    Worker ID [{role['role_id']}-1]: ").strip() or f"{role['role_id']}-1"
            role["workers"].append({
                "id": worker_id,
                "provider": provider,
                "model": model,
            })
    else:
        while True:
            role_id = input("  Role ID (empty to finish): ").strip()
            if not role_id:
                break
            title = input(f"  Title [{role_id}]: ").strip() or role_id
            dept = input(f"  Department [engineering]: ").strip() or "engineering"
            provider = input(f"  Provider [anthropic]: ").strip() or "anthropic"
            model = input(f"  Model [claude-sonnet-4-5-20250929]: ").strip() or "claude-sonnet-4-5-20250929"
            worker_id = input(f"  Worker ID [{role_id}-1]: ").strip() or f"{role_id}-1"
            roles.append({
                "role_id": role_id,
                "title": title,
                "department": dept,
                "reports_to": "orchestrator",
                "authority": "read",
                "workers": [{"id": worker_id, "provider": provider, "model": model}],
            })

    if not roles:
        roles = default_roles.get("software", [])
        for r in roles:
            r["reports_to"] = "orchestrator"
            r["authority"] = "read"
            r["workers"] = []

    # 3) Approval rules
    print("\nApproval rules (which actions require user approval?):")
    print("  Default: scope changes + releases")
    custom = input("Add custom trigger? [n]: ").strip().lower()

    triggers = [
        {
            "trigger_id": "scope_change",
            "description": "Any change to project scope or requirements",
            "condition": "task.requires_approval contains 'scope_change'",
            "required_approvals": ["user", "pm"],
        },
        {
            "trigger_id": "release",
            "description": "Any release or deployment action",
            "condition": "task.requires_approval contains 'release'",
            "required_approvals": ["user"],
        },
    ]

    while custom == "y":
        tid = input("  Trigger ID: ").strip()
        if not tid:
            break
        desc = input("  Description: ").strip()
        triggers.append({
            "trigger_id": tid,
            "description": desc,
            "condition": f"task.requires_approval contains '{tid}'",
            "required_approvals": ["user"],
        })
        custom = input("Add another? [n]: ").strip().lower()

    # Write canonical files
    team_data = {
        "orchestrator": {"role_id": "orchestrator", "title": "Orchestrator", "authority": "write"},
        "roles": roles,
    }
    approvals_data = {"triggers": triggers, "approval_log": []}

    team_path.parent.mkdir(parents=True, exist_ok=True)
    team_path.write_text(_yaml_dump(team_data))
    (ai_dir / "state" / "approvals.yaml").write_text(_yaml_dump(approvals_data))

    print("\nOnboarding complete. Team and approval rules saved.")


def _legacy_migration_instructions(project_root: Path, dry_run: bool = False) -> str:
    lines = [
        "Legacy Scaffold AI submodule path detected at 'vendor/scaffold-ai'.",
        f"Canonical path is now '{CANONICAL_SUBMODULE_PATH}'.",
        SUBMODULE_POLICY_SUMMARY,
        "",
        "Migration options:",
        "  1) Preview automated migration:",
        "     ai init --migrate-submodule --dry-run",
        "  2) Run automated migration:",
        "     ai init --migrate-submodule",
        "",
        "Manual fallback (if you have local submodule changes):",
        "  git status --porcelain vendor/scaffold-ai",
        "  git mv vendor/scaffold-ai scaffold/scaffold-ai",
        "  git submodule sync -- scaffold/scaffold-ai",
        "  ai init",
        "  ai validate",
    ]
    if dry_run:
        lines.insert(0, "Dry-run requested.")
    return "\n".join(lines)


def _submodule_is_dirty(path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"Could not inspect submodule status: {e}"
    if result.returncode != 0:
        return False, result.stderr.strip() or "git status failed"
    return bool(result.stdout.strip()), result.stdout.strip()


def _migrate_legacy_submodule(project_root: Path, dry_run: bool = False) -> str:
    legacy = project_root / LEGACY_SUBMODULE_PATH
    canonical = project_root / CANONICAL_SUBMODULE_PATH

    if canonical.exists() and not legacy.exists():
        return (
            f"Submodule already uses canonical path '{CANONICAL_SUBMODULE_PATH}'. "
            "No migration needed."
        )
    if not legacy.exists() and not canonical.exists():
        return "No Scaffold AI submodule detected at legacy/canonical paths. Continuing without submodule migration."
    if legacy.exists() and canonical.exists():
        raise InitBlockedError(
            "Both legacy and canonical Scaffold AI submodule paths exist.\n"
            "Refusing automated migration to avoid destructive behavior.\n\n"
            f"Legacy:    {LEGACY_SUBMODULE_PATH}\n"
            f"Canonical: {CANONICAL_SUBMODULE_PATH}\n"
            "Resolve manually, then rerun 'ai init'."
        )

    dirty, detail = _submodule_is_dirty(legacy)
    if dirty:
        raise InitBlockedError(
            "Legacy submodule has local changes; refusing automated migration.\n"
            "Preserve or commit/stash your submodule work first, then rerun.\n\n"
            f"{detail}\n\n" + _legacy_migration_instructions(project_root)
        )

    lines = [
        f"Submodule migration: {LEGACY_SUBMODULE_PATH} -> {CANONICAL_SUBMODULE_PATH}",
    ]
    if dry_run:
        lines.extend([
            "Dry-run only. Planned actions:",
            f"  - mkdir -p {Path(CANONICAL_SUBMODULE_PATH).parent}",
            f"  - git mv {LEGACY_SUBMODULE_PATH} {CANONICAL_SUBMODULE_PATH}",
            f"  - git submodule sync -- {CANONICAL_SUBMODULE_PATH}",
            "  - ai init (continue normal initialization and restamp metadata)",
        ])
        return "\n".join(lines)

    canonical.parent.mkdir(parents=True, exist_ok=True)

    mv_result = subprocess.run(
        ["git", "mv", LEGACY_SUBMODULE_PATH, CANONICAL_SUBMODULE_PATH],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    if mv_result.returncode != 0:
        raise InitBlockedError(
            "Automated submodule migration failed during 'git mv'.\n"
            f"{mv_result.stderr.strip() or mv_result.stdout.strip()}\n\n"
            + _legacy_migration_instructions(project_root)
        )

    gitmodules = project_root / ".gitmodules"
    if gitmodules.exists():
        text = gitmodules.read_text()
        if LEGACY_SUBMODULE_PATH in text:
            gitmodules.write_text(text.replace(LEGACY_SUBMODULE_PATH, CANONICAL_SUBMODULE_PATH))

    subprocess.run(
        ["git", "submodule", "sync", "--", CANONICAL_SUBMODULE_PATH],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )

    lines.append("  [OK] Moved submodule path in git index/worktree")
    lines.append("  [OK] Synced submodule config")
    return "\n".join(lines)


def init(
    project_root: Path | None = None,
    interactive: bool = True,
    migrate_submodule: bool = False,
    dry_run: bool = False,
):
    """Full initialization sequence."""
    skeleton_dir = find_skeleton_dir()

    if project_root is None:
        project_root = ai_git.find_project_root()

    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

    layout = detect_submodule_layout(project_root)
    skeleton_rel = relpath_from_project(project_root, skeleton_dir)

    if layout["legacy_exists"] and layout["canonical_exists"]:
        raise InitBlockedError(
            "Both legacy and canonical Scaffold AI submodule paths exist.\n"
            f"Legacy:    {LEGACY_SUBMODULE_PATH}\n"
            f"Canonical: {CANONICAL_SUBMODULE_PATH}\n"
            "Resolve the duplicate before running init."
        )

    if layout["legacy_exists"]:
        if migrate_submodule:
            print(_migrate_legacy_submodule(project_root, dry_run=dry_run))
            if dry_run:
                return
            skeleton_dir = (project_root / CANONICAL_SUBMODULE_PATH).resolve()
            skeleton_rel = CANONICAL_SUBMODULE_PATH
        elif skeleton_rel == LEGACY_SUBMODULE_PATH or skeleton_rel is None:
            raise InitBlockedError(_legacy_migration_instructions(project_root))
    elif migrate_submodule:
        print(_migrate_legacy_submodule(project_root, dry_run=dry_run))
        if dry_run:
            return

    print(f"Initializing AI team in: {project_root}")

    # 1) Copy templates if .ai/ missing or incomplete
    copy_templates(skeleton_dir, project_root)
    print("  [OK] Templates applied")

    # 2) Stamp metadata
    meta = stamp_metadata(project_root, skeleton_dir)
    print(f"  [OK] Metadata stamped (version: {meta['skeleton_version']})")

    # 3) Setup runtime directories
    setup_runtime(project_root)
    print("  [OK] Runtime directory created")

    # 4) Ensure .gitignore has .ai_runtime/
    ai_git.ensure_gitignore(project_root)
    print("  [OK] .gitignore updated")

    # 5) Ingest canonical state into SQLite
    ai_state.reconcile(ai_dir, runtime_dir)
    print("  [OK] Canonical state ingested into SQLite")

    # 6) Stamp skeleton version in DB
    conn = ai_db.connect_db(runtime_dir)
    ai_db.set_snapshot(conn, "skeleton_version", meta["skeleton_version"])
    ai_db.add_event(conn, "system", "init", {
        "project_root": str(project_root),
        "skeleton_version": meta["skeleton_version"],
    })
    conn.close()

    # 7) Run onboarding if team is default
    if interactive:
        try:
            run_onboarding(project_root)
        except (EOFError, KeyboardInterrupt):
            print("\nOnboarding skipped (non-interactive).")

    # 8) Verify protocol file
    protocol_path = ai_dir / "AGENTS.md"
    if protocol_path.exists():
        print("  [OK] Operator protocol loaded (.ai/AGENTS.md)")
    else:
        print("  [WARN] .ai/AGENTS.md not found in templates")

    # 9) Verify root bridge files
    bridges = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        if (project_root / name).exists():
            bridges.append(name)
    if bridges:
        print(f"  [OK] Root bridge files: {', '.join(bridges)}")
    else:
        print("  [WARN] No root bridge files (AGENTS.md, CLAUDE.md) created")

    # 10) Build system index from skeleton
    try:
        from . import system_index
        system_index.build_system_index(skeleton_dir, runtime_dir)
        print("  [OK] System index built")
    except Exception:
        print("  [WARN] System index build failed (non-critical)")

    # 11) Write skeleton version lock
    try:
        from . import ai_compat
        lock = ai_compat.write_skeleton_lock(project_root, skeleton_dir)
        print(f"  [OK] Skeleton lock written (version: {lock.get('skeleton_version', '?')})")
    except Exception:
        print("  [WARN] Skeleton lock write failed (non-critical)")

    # 12) Run compatibility gate
    try:
        from . import ai_compat
        cap_result = ai_compat.check_capabilities(project_root)
        print(f"  [OK] Capabilities check: {cap_result['status']} "
              f"({cap_result['advertised_count']} advertised, "
              f"{cap_result['implemented_count']} implemented)")
        if cap_result['missing']:
            for m in cap_result['missing']:
                print(f"        MISSING: {m['id']} ({m['handler']})")
    except Exception:
        print("  [WARN] Capabilities check skipped (non-critical)")

    print("\nInitialization complete.")
    print(f"  Canonical state: {ai_dir}/state/")
    print(f"  Runtime cache:   {runtime_dir}/")
    print(f"  Run 'ai status' to see project status.")
