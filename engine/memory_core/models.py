"""
models.py — Data classes for session memory.

Pure data structures with no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A single chat message in model-ready format."""
    id: int | None
    session_id: str
    namespace: str
    role: str
    content: str
    ts: str
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, str]:
        """Return model-ready {role, content} dict."""
        return {"role": self.role, "content": self.content}


@dataclass
class Fact:
    """A distilled fact extracted from conversation."""
    id: int | None
    session_id: str
    namespace: str
    fact_text: str
    ts: str
    importance: int = 5
    tags: list[str] = field(default_factory=list)
    supersedes_id: int | None = None


@dataclass
class Summary:
    """A rolling or scoped summary of conversation history."""
    id: int | None
    session_id: str
    namespace: str
    summary_text: str
    ts: str
    scope: str = "rolling"


@dataclass
class NamespacePolicy:
    """Policy configuration for a single namespace."""
    persist: str = "full"  # full | summary_only | distilled_only | none
    retention_days: int = 90
    max_recent_messages: int = 200
    distill_every_n_turns: int = 20
    max_facts: int = 500
    allowed_roles: list[str] = field(default_factory=lambda: ["user", "assistant", "system"])
    denylist: list[str] = field(default_factory=list)


@dataclass
class MemoryPolicy:
    """Full policy configuration across all namespaces."""
    namespaces: dict[str, NamespacePolicy] = field(default_factory=dict)
    global_denylist: list[str] = field(default_factory=list)
    auto_export_on_exit: bool = True
    auto_import_inbox: bool = True

    def get_namespace_policy(self, namespace: str) -> NamespacePolicy:
        """Get policy for a namespace, falling back to defaults."""
        if namespace in self.namespaces:
            return self.namespaces[namespace]
        # Check wildcard patterns (e.g. worker_* matches worker_dev)
        for pattern, policy in self.namespaces.items():
            if pattern.endswith("*") and namespace.startswith(pattern[:-1]):
                return policy
        return NamespacePolicy()
