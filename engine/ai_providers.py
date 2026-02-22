"""
ai_providers.py — Extensible provider registry.

Loads providers.yaml and exposes lookup functions.
Replaces hardcoded PROVIDER_CLI dict in ai_workers.py.
"""

from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Hardcoded fallback (used if providers.yaml is missing)
_FALLBACK_PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "cli_command": "claude",
        "model_arg": "--model",
        "default_model": "claude-sonnet-4-5-20250929",
        "supports_persistent_session": True,
        "aliases": ["claude"],
    },
    "openai": {
        "cli_command": "codex",
        "model_arg": "--model",
        "default_model": "codex-mini",
        "supports_persistent_session": False,
        "aliases": ["codex"],
    },
    "cursor": {
        "cli_command": "cursor",
        "model_arg": None,
        "default_model": "cursor-default",
        "supports_persistent_session": True,
        "aliases": [],
    },
    "google": {
        "cli_command": "gemini",
        "model_arg": "--model",
        "default_model": "gemini-2.5-pro",
        "supports_persistent_session": False,
        "aliases": ["gemini"],
    },
}


def load_providers(project_root: Path) -> dict[str, dict]:
    """Load providers from .ai/state/providers.yaml, falling back to templates then hardcoded."""
    for base in [
        project_root / ".ai" / "state",
        project_root / "templates" / ".ai" / "state",
    ]:
        path = base / "providers.yaml"
        if path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(path.read_text()) or {}
                providers = data.get("providers", {})
                if providers:
                    return providers
            except Exception:
                pass

    return dict(_FALLBACK_PROVIDERS)


def resolve_provider(name: str, project_root: Path) -> dict | None:
    """Resolve a provider name (including aliases) to its config dict.

    Returns the provider config dict or None if not found.
    """
    providers = load_providers(project_root)
    name_lower = name.lower().strip()

    # Direct match
    if name_lower in providers:
        return providers[name_lower]

    # Alias match
    for pid, pconfig in providers.items():
        if name_lower in [a.lower() for a in pconfig.get("aliases", [])]:
            return pconfig

    return None


def get_cli_command(provider_name: str, project_root: Path) -> str:
    """Return the CLI command for a provider (e.g., 'claude', 'codex', 'gemini')."""
    pconfig = resolve_provider(provider_name, project_root)
    if pconfig:
        return pconfig.get("cli_command", provider_name)
    return provider_name


def get_default_model(provider_name: str, project_root: Path) -> str:
    """Return the default model for a provider."""
    pconfig = resolve_provider(provider_name, project_root)
    if pconfig:
        return pconfig.get("default_model", "default")
    return "default"


def get_model_arg(provider_name: str, project_root: Path) -> str | None:
    """Return the model argument flag (e.g. '--model') or None if provider has no model param."""
    pconfig = resolve_provider(provider_name, project_root)
    if pconfig:
        return pconfig.get("model_arg")
    return None


def supports_persistent_session(provider_name: str, project_root: Path) -> bool:
    """Check if a provider supports keeping sessions open."""
    pconfig = resolve_provider(provider_name, project_root)
    if pconfig:
        return bool(pconfig.get("supports_persistent_session", False))
    return False


def build_provider_alias_map(project_root: Path) -> dict[str, str]:
    """Build alias→canonical_id map for use in team spec parsing.

    Returns e.g. {"claude": "anthropic", "codex": "openai", "gemini": "google",
                   "anthropic": "anthropic", "openai": "openai", ...}
    """
    providers = load_providers(project_root)
    alias_map: dict[str, str] = {}

    for pid, pconfig in providers.items():
        # Canonical name maps to itself
        alias_map[pid.lower()] = pid
        # Each alias maps to canonical
        for alias in pconfig.get("aliases", []):
            alias_map[alias.lower()] = pid

    return alias_map


def list_providers(project_root: Path) -> str:
    """Return formatted list of supported providers."""
    providers = load_providers(project_root)
    lines = ["Supported Providers:\n"]
    for pid, pconfig in providers.items():
        aliases = ", ".join(pconfig.get("aliases", [])) or "(none)"
        model = pconfig.get("default_model", "?")
        cli = pconfig.get("cli_command", "?")
        lines.append(f"  {pid}")
        lines.append(f"    CLI: {cli} | Default model: {model}")
        lines.append(f"    Aliases: {aliases}")
        lines.append("")
    return "\n".join(lines)
