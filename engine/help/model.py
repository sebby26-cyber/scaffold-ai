"""
model.py — Help/guide data model (JSON-serializable).

Single source of truth for help structure.
Terminal and JSON renderers both consume this model.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class HelpCommand:
    name: str
    description: str
    example: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HelpFileLocation:
    path: str
    description: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HelpCurrentState:
    initialized: bool = False
    assignments_configured: bool = False
    memory_runtime_present: bool = False
    memory_pack_available: bool = False
    task_count: int = 0
    worker_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HelpGuide:
    generated_at: str
    project_name: str
    current_state: HelpCurrentState = field(default_factory=HelpCurrentState)
    quick_start_steps: list[str] = field(default_factory=list)
    common_prompts: list[str] = field(default_factory=list)
    commands: list[HelpCommand] = field(default_factory=list)
    how_to_resume_on_new_machine: list[str] = field(default_factory=list)
    troubleshooting: list[str] = field(default_factory=list)
    where_to_find_files: list[HelpFileLocation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "project_name": self.project_name,
            "current_state": self.current_state.to_dict(),
            "quick_start_steps": self.quick_start_steps,
            "common_prompts": self.common_prompts,
            "commands": [c.to_dict() for c in self.commands],
            "how_to_resume_on_new_machine": self.how_to_resume_on_new_machine,
            "troubleshooting": self.troubleshooting,
            "where_to_find_files": [f.to_dict() for f in self.where_to_find_files],
        }
