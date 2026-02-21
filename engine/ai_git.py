"""
ai_git.py — Git sync helpers.

Handles committing only canonical .ai/ files. Never commits .ai_runtime/.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

WHITELISTED_PATHS = [
    ".ai/state/",
    ".ai/STATUS.md",
    ".ai/DECISIONS.md",
    ".ai/METADATA.yaml",
]


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def find_project_root(start: Path | None = None) -> Path:
    """Walk up directories to find the project root (containing .git/)."""
    current = start or Path.cwd()
    current = current.resolve()
    while current != current.parent:
        if (current / ".git").exists() or (current / ".git").is_file():
            return current
        current = current.parent
    raise FileNotFoundError(
        "Could not find project root (.git/ directory). "
        "Are you inside a git repository?"
    )


def get_skeleton_version(skeleton_dir: Path) -> str:
    """Get the current commit hash of the skeleton repo."""
    result = run_git(["rev-parse", "--short", "HEAD"], cwd=skeleton_dir)
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def is_repo_clean(project_root: Path) -> bool:
    result = run_git(["status", "--porcelain"], cwd=project_root)
    return result.stdout.strip() == ""


def _get_submodule_paths(project_root: Path) -> list[str]:
    """Return relative submodule paths to exclude from commits."""
    result = run_git(["submodule", "status"], cwd=project_root)
    paths = []
    if result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            parts = line.strip().lstrip("-+").split()
            if len(parts) >= 2:
                paths.append(parts[1])
    return paths


def git_sync(project_root: Path, message: str | None = None) -> tuple[bool, str]:
    """Stage and commit only whitelisted canonical .ai/ files.

    Never stages submodule changes. Returns (success, message).
    """
    submodule_paths = _get_submodule_paths(project_root)
    staged_any = False

    for pattern in WHITELISTED_PATHS:
        full = project_root / pattern
        if pattern.endswith("/"):
            if full.is_dir():
                result = run_git(["add", pattern], cwd=project_root)
                if result.returncode == 0:
                    staged_any = True
        else:
            if full.exists():
                result = run_git(["add", pattern], cwd=project_root)
                if result.returncode == 0:
                    staged_any = True

    # Check if anything was actually staged
    diff_result = run_git(["diff", "--cached", "--name-only"], cwd=project_root)
    staged_files = diff_result.stdout.strip()

    if not staged_files:
        return False, "No canonical changes to commit."

    # Verify only whitelisted files are staged — unstage anything else
    # including anything inside submodules
    for line in staged_files.splitlines():
        allowed = any(line.startswith(wp.rstrip("/")) for wp in WHITELISTED_PATHS)
        in_submodule = any(line.startswith(sp) for sp in submodule_paths)
        if not allowed or in_submodule:
            run_git(["reset", "HEAD", line], cwd=project_root)

    commit_msg = message or "chore(ai): update canonical state"
    result = run_git(["commit", "-m", commit_msg], cwd=project_root)

    if result.returncode == 0:
        return True, f"Committed: {commit_msg}"
    else:
        return False, f"Commit failed: {result.stderr.strip()}"


def ensure_gitignore(project_root: Path, entry: str = ".ai_runtime/"):
    """Ensure .ai_runtime/ is in the project .gitignore."""
    gitignore = project_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if entry not in content:
            with open(gitignore, "a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n# AI runtime (local cache, never committed)\n{entry}\n")
    else:
        gitignore.write_text(
            f"# AI runtime (local cache, never committed)\n{entry}\n"
        )
