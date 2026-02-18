"""
policy.py — Load and enforce memory policies from YAML.

Policies control per-namespace retention, persistence mode,
redaction denylist, and role filtering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import MemoryPolicy, NamespacePolicy

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def _parse_namespace_policy(data: dict[str, Any]) -> NamespacePolicy:
    """Parse a single namespace policy dict into a NamespacePolicy."""
    return NamespacePolicy(
        persist=data.get("persist", "full"),
        retention_days=data.get("retention_days", 90),
        max_recent_messages=data.get("max_recent_messages", 200),
        distill_every_n_turns=data.get("distill_every_n_turns", 20),
        max_facts=data.get("max_facts", 500),
        allowed_roles=data.get("allowed_roles", ["user", "assistant", "system"]),
        denylist=data.get("denylist", []),
    )


def load_policy(policy_path: Path | str | None = None) -> MemoryPolicy:
    """Load memory policy from a YAML file.

    Args:
        policy_path: Path to memory_policy.yaml. If None, returns defaults.

    Returns:
        Parsed MemoryPolicy with namespace configurations.
    """
    if policy_path is None:
        return _default_policy()

    path = Path(policy_path)
    if not path.exists():
        return _default_policy()

    if yaml is None:
        return _default_policy()

    data = yaml.safe_load(path.read_text()) or {}

    global_denylist = data.get("global_denylist", [])
    namespaces: dict[str, NamespacePolicy] = {}

    for ns_name, ns_data in data.get("namespaces", {}).items():
        if isinstance(ns_data, dict):
            namespaces[ns_name] = _parse_namespace_policy(ns_data)

    return MemoryPolicy(
        namespaces=namespaces,
        global_denylist=global_denylist,
        auto_export_on_exit=data.get("auto_export_on_exit", True),
        auto_import_inbox=data.get("auto_import_inbox", True),
    )


def _default_policy() -> MemoryPolicy:
    """Return hardcoded default policy."""
    return MemoryPolicy(
        namespaces={
            "orchestrator": NamespacePolicy(persist="full"),
            "shared": NamespacePolicy(persist="distilled_only"),
            "worker_default": NamespacePolicy(persist="summary_only"),
            "worker_ephemeral": NamespacePolicy(persist="none"),
        },
        global_denylist=[],
        auto_export_on_exit=True,
        auto_import_inbox=True,
    )


def check_persist(policy: MemoryPolicy, namespace: str) -> bool:
    """Return True if messages should be persisted for this namespace."""
    ns_policy = policy.get_namespace_policy(namespace)
    return ns_policy.persist != "none"


def check_role_allowed(policy: MemoryPolicy, namespace: str, role: str) -> bool:
    """Return True if this role is allowed by the namespace policy."""
    ns_policy = policy.get_namespace_policy(namespace)
    return role in ns_policy.allowed_roles


def get_denylist(policy: MemoryPolicy, namespace: str) -> list[str]:
    """Get combined denylist (global + namespace-specific)."""
    ns_policy = policy.get_namespace_policy(namespace)
    return policy.global_denylist + ns_policy.denylist


def get_retention_days(policy: MemoryPolicy, namespace: str) -> int:
    """Get retention days for a namespace."""
    return policy.get_namespace_policy(namespace).retention_days


def get_max_recent(policy: MemoryPolicy, namespace: str) -> int:
    """Get max recent messages for a namespace."""
    return policy.get_namespace_policy(namespace).max_recent_messages


def get_max_facts(policy: MemoryPolicy, namespace: str) -> int:
    """Get max facts for a namespace."""
    return policy.get_namespace_policy(namespace).max_facts
