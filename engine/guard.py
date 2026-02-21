"""
guard.py — Submodule write guard.

Detects submodule paths and blocks writes into the skeleton's read-only
system layer. All agents must call ``check_write_allowed`` before any
file create/modify/delete operation.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path


class SubmoduleWriteError(Exception):
    """Raised when a write targets the read-only submodule layer."""

    def __init__(self, target: Path, submodule: Path):
        self.target = target
        self.submodule = submodule
        super().__init__(
            f"BLOCKED: Cannot write to '{target}' — it is inside the "
            f"read-only submodule at '{submodule}'. "
            f"All writes must target the parent project (.ai/, .ai_runtime/, etc.)."
        )


@lru_cache(maxsize=1)
def detect_submodule_paths(project_root: Path) -> list[Path]:
    """Return resolved absolute paths of all git submodules in the project.

    Uses ``git submodule status`` for reliable detection. Falls back to
    checking common conventional paths if git is unavailable.
    """
    project_root = project_root.resolve()
    paths: list[Path] = []

    # Primary: ask git
    try:
        result = subprocess.run(
            ["git", "submodule", "status"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                # Format: " <hash> <path> (<description>)" or "-<hash> <path>"
                parts = line.strip().lstrip("-+").split()
                if len(parts) >= 2:
                    sub_path = (project_root / parts[1]).resolve()
                    if sub_path.is_dir():
                        paths.append(sub_path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: check common conventional paths
    if not paths:
        for candidate in ("vendor/scaffold-ai", "skeleton", ".ai_submodules"):
            p = (project_root / candidate).resolve()
            if p.is_dir() and (p / ".git").exists():
                paths.append(p)

    return paths


def is_inside_submodule(target: Path, project_root: Path) -> Path | None:
    """Check if *target* falls inside any submodule.

    Returns the submodule Path if inside one, None otherwise.
    """
    target = target.resolve()
    for sub in detect_submodule_paths(project_root):
        try:
            target.relative_to(sub)
            return sub
        except ValueError:
            continue
    return None


def check_write_allowed(target: Path, project_root: Path) -> None:
    """Validate that *target* is safe to write.

    Raises ``SubmoduleWriteError`` if *target* falls inside a submodule.
    Call this before every file create, modify, or delete operation.
    """
    sub = is_inside_submodule(target, project_root)
    if sub is not None:
        raise SubmoduleWriteError(target, sub)


def suggest_redirect(target: Path, project_root: Path) -> str:
    """Suggest the correct project-level path when a submodule write is blocked.

    Attempts to map common skeleton paths to their project equivalents.
    """
    target = target.resolve()
    sub = is_inside_submodule(target, project_root)
    if sub is None:
        return str(target)

    try:
        rel = target.relative_to(sub)
    except ValueError:
        return str(target)

    rel_str = str(rel)

    # Map templates/.ai/* → .ai/*
    if rel_str.startswith("templates/.ai/"):
        return str(project_root / ".ai" / rel_str[len("templates/.ai/"):])

    # Map templates/* → project root
    if rel_str.startswith("templates/"):
        return str(project_root / rel_str[len("templates/"):])

    # Generic: put in .ai/ or project root
    return str(project_root / rel)
