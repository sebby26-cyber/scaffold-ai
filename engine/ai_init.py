"""
ai_init.py — First-run initializer.

Creates .ai/ from templates (if missing), sets up .ai_runtime/,
stamps METADATA.yaml, and ingests canonical state into SQLite.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from . import ai_db, ai_git, ai_state


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
    """Copy template files into the project's .ai/ directory.

    Does not overwrite existing files.
    """
    templates_dir = skeleton_dir / "templates" / ".ai"
    ai_dir = project_root / ".ai"

    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates not found at {templates_dir}")

    for src_file in templates_dir.rglob("*"):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(templates_dir)
        dst = ai_dir / rel
        if dst.exists():
            continue  # Do not overwrite existing files
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_file), str(dst))


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
    for subdir in ["logs", "session", "memory_pack_cache", "import_inbox", "memory_packs"]:
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


def init(project_root: Path | None = None, interactive: bool = True):
    """Full initialization sequence."""
    skeleton_dir = find_skeleton_dir()

    if project_root is None:
        project_root = ai_git.find_project_root()

    ai_dir = project_root / ".ai"
    runtime_dir = project_root / ".ai_runtime"

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

    print("\nInitialization complete.")
    print(f"  Canonical state: {ai_dir}/state/")
    print(f"  Runtime cache:   {runtime_dir}/")
    print(f"  Run 'ai status' to see project status.")
