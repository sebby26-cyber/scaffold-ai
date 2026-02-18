"""
api.py — Public API for session memory.

This is the ONLY file that should be imported from outside memory_core.
All access goes through the SessionMemory class.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import packs as _packs
from . import policy as _policy
from . import search_fts as _search
from . import store_sqlite as _store
from .models import Fact, MemoryPolicy, Message, Summary
from .redact import redact


class SessionMemory:
    """Decoupled persistent session memory.

    Model-agnostic: returns plain {role, content} messages.
    No LLM calls. No API keys required.

    Args:
        project_root: Path to the project root directory.
        policy_path: Path to memory_policy.yaml (optional).
        db_path: Override database path (optional).
    """

    def __init__(
        self,
        project_root: str | Path,
        policy_path: str | Path | None = None,
        db_path: str | Path | None = None,
    ):
        self._project_root = Path(project_root)
        self._db_path = _store.get_db_path(self._project_root, db_path)
        self._conn: sqlite3.Connection | None = None
        self._fts_enabled: bool = False

        # Load policy
        if policy_path is None:
            default_policy = self._project_root / ".ai" / "state" / "memory_policy.yaml"
            if default_policy.exists():
                policy_path = default_policy
        self._policy = _policy.load_policy(policy_path)

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy database connection."""
        if self._conn is None:
            self._conn = _store.connect(self._db_path)
            self._fts_enabled = _store.ensure_fts(self._conn)
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Messages ──

    def add_message(
        self,
        session_id: str,
        namespace: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> int | None:
        """Add a message to session memory.

        Applies redaction and policy checks before persistence.
        Returns the message row id, or None if rejected by policy.
        """
        if not _policy.check_persist(self._policy, namespace):
            return None

        if not _policy.check_role_allowed(self._policy, namespace, role):
            return None

        # Redact sensitive content
        denylist = _policy.get_denylist(self._policy, namespace)
        safe_content = redact(content, denylist)

        return _store.insert_message(
            self.conn, session_id, namespace, role, safe_content, metadata,
        )

    def get_recent_messages(
        self,
        session_id: str,
        namespace: str,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        """Get recent messages as model-ready [{role, content}, ...].

        If limit is None, uses the policy's max_recent_messages.
        """
        if limit is None:
            limit = _policy.get_max_recent(self._policy, namespace)

        messages = _store.get_recent_messages(self.conn, session_id, namespace, limit)
        return [m.to_dict() for m in messages]

    def search(
        self,
        session_id: str,
        namespace: str,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """Search messages by content. Returns model-ready dicts."""
        messages = _search.search_messages(
            self.conn, session_id, namespace, query, limit,
            use_fts=self._fts_enabled,
        )
        return [m.to_dict() for m in messages]

    # ── Context assembly ──

    def get_context(
        self,
        session_id: str,
        namespace: str,
        query: str | None = None,
        max_recent: int = 20,
        max_facts: int = 10,
        max_summary: int = 1,
    ) -> list[dict[str, str]]:
        """Assemble context for model injection.

        Combines summary + relevant facts + recent messages
        into a single list of model-ready messages.

        This is the primary token-reduction mechanism:
        instead of replaying full history, the model receives
        a compact context window.
        """
        context: list[dict[str, str]] = []

        # 1. Rolling summary (if any)
        if max_summary > 0:
            summary = _store.get_summary(self.conn, session_id, namespace)
            if summary:
                context.append({
                    "role": "system",
                    "content": f"[Session Summary]\n{summary.summary_text}",
                })

        # 2. Relevant facts
        if max_facts > 0:
            if query:
                facts = _search.search_facts(
                    self.conn, session_id, namespace, query, max_facts,
                    use_fts=self._fts_enabled,
                )
            else:
                facts_raw = _store.get_facts(self.conn, session_id, namespace, max_facts)
                facts = facts_raw

            if facts:
                fact_lines = [f"- {f.fact_text}" for f in facts]
                context.append({
                    "role": "system",
                    "content": "[Key Facts]\n" + "\n".join(fact_lines),
                })

        # 3. Recent messages
        if max_recent > 0:
            recent = _store.get_recent_messages(self.conn, session_id, namespace, max_recent)
            context.extend(m.to_dict() for m in recent)

        return context

    # ── Summaries ──

    def upsert_summary(
        self,
        session_id: str,
        namespace: str,
        summary_text: str,
        scope: str = "rolling",
    ) -> int:
        """Insert or update a summary for a session/namespace."""
        denylist = _policy.get_denylist(self._policy, namespace)
        safe_text = redact(summary_text, denylist)
        return _store.upsert_summary(self.conn, session_id, namespace, safe_text, scope)

    # ── Facts ──

    def add_fact(
        self,
        session_id: str,
        namespace: str,
        fact_text: str,
        importance: int = 5,
        tags: list[str] | None = None,
    ) -> int | None:
        """Add a distilled fact. Returns row id or None if rejected."""
        if not _policy.check_persist(self._policy, namespace):
            return None

        denylist = _policy.get_denylist(self._policy, namespace)
        safe_text = redact(fact_text, denylist)

        # Enforce max_facts by dropping lowest importance
        max_facts = _policy.get_max_facts(self._policy, namespace)
        current_count = _store.get_fact_count(self.conn, session_id, namespace)
        if current_count >= max_facts:
            self.dedupe_facts(session_id, namespace)

        return _store.insert_fact(
            self.conn, session_id, namespace, safe_text, importance, tags,
        )

    def dedupe_facts(self, session_id: str, namespace: str) -> int:
        """Remove superseded facts. Returns count removed."""
        return _store.delete_superseded_facts(self.conn, session_id, namespace)

    # ── Purge ──

    def purge(
        self,
        namespace: str | None = None,
        older_than_days: int | None = None,
    ) -> dict[str, int]:
        """Purge messages, facts, and summaries.

        Args:
            namespace: Filter by namespace (None = all).
            older_than_days: Only purge records older than N days.

        Returns:
            Dict of counts purged per table.
        """
        older_than_iso = None
        if older_than_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            older_than_iso = cutoff.isoformat()

        return {
            "messages": _store.purge_messages(self.conn, namespace, older_than_iso),
            "facts": _store.purge_facts(self.conn, namespace, older_than_iso),
            "summaries": _store.purge_summaries(self.conn, namespace),
        }

    # ── Packs ──

    def export_pack(
        self,
        out_path: str | Path,
        namespaces: list[str] | None = None,
    ) -> str:
        """Export session memory as a portable pack."""
        return _packs.export_pack(self.conn, out_path, namespaces)

    def import_pack(self, pack_path: str | Path) -> dict[str, int]:
        """Import a session memory pack (append-safe)."""
        return _packs.import_pack(self.conn, pack_path)

    # ── Introspection ──

    def detect_fts5_support(self) -> bool:
        """Check if FTS5 is available in this SQLite build."""
        return _store.detect_fts5(self.conn)

    def get_message_count(self, session_id: str, namespace: str) -> int:
        """Count messages in a session/namespace. Used for distillation triggers."""
        return _store.get_message_count(self.conn, session_id, namespace)

    def get_distill_interval(self, namespace: str) -> int:
        """Get distill_every_n_turns for a namespace."""
        ns_policy = self._policy.get_namespace_policy(namespace)
        return ns_policy.distill_every_n_turns

    def get_policy_field(self, namespace: str, field: str) -> Any:
        """Get an arbitrary policy field for a namespace."""
        ns_policy = self._policy.get_namespace_policy(namespace)
        return getattr(ns_policy, field, None)
