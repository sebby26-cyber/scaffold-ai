#!/usr/bin/env python3
"""
self_check.py — Sanity checks for the AI Team Skeleton engine.

Runs basic tests to verify core functionality:
  1. Project root detection
  2. Init creates required dirs/files
  3. DB creation + ingest works
  4. Export/import pack roundtrip works
  5. Git-sync only commits whitelisted files

Usage:
    python engine/self_check.py
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

# Setup imports
engine_dir = os.path.dirname(os.path.abspath(__file__))
skeleton_dir = os.path.dirname(engine_dir)
if skeleton_dir not in sys.path:
    sys.path.insert(0, skeleton_dir)

passed = 0
failed = 0
errors = []


def check(name, func):
    global passed, failed
    try:
        func()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")


def make_test_project() -> Path:
    """Create a temporary git repo with skeleton templates copied in."""
    import subprocess

    tmpdir = Path(tempfile.mkdtemp(prefix="ai_selfcheck_")).resolve()
    subprocess.run(["git", "init", str(tmpdir)], capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmpdir), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmpdir), capture_output=True,
    )
    # Create an initial commit so git operations work
    (tmpdir / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=str(tmpdir), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmpdir), capture_output=True,
    )
    return tmpdir


# ─── Test 1: Project root detection ───

def test_project_root_detection():
    from engine.ai_git import find_project_root

    tmpdir = make_test_project()
    try:
        # From root
        root = find_project_root(tmpdir)
        assert root == tmpdir, f"Expected {tmpdir}, got {root}"

        # From subdirectory
        subdir = tmpdir / "sub" / "deep"
        subdir.mkdir(parents=True)
        root2 = find_project_root(subdir)
        assert root2 == tmpdir, f"Expected {tmpdir}, got {root2}"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 2: Init creates required dirs/files ───

def test_init_creates_structure():
    from engine.ai_init import copy_templates, setup_runtime, stamp_metadata

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)
        stamp_metadata(tmpdir, skel)

        ai_dir = tmpdir / ".ai"
        runtime_dir = tmpdir / ".ai_runtime"

        # Check required files exist
        assert ai_dir.is_dir(), ".ai/ not created"
        assert (ai_dir / "state" / "team.yaml").exists(), "team.yaml missing"
        assert (ai_dir / "state" / "board.yaml").exists(), "board.yaml missing"
        assert (ai_dir / "state" / "approvals.yaml").exists(), "approvals.yaml missing"
        assert (ai_dir / "state" / "commands.yaml").exists(), "commands.yaml missing"
        assert (ai_dir / "METADATA.yaml").exists(), "METADATA.yaml missing"
        assert (ai_dir / "STATUS.md").exists(), "STATUS.md missing"
        assert (ai_dir / "DECISIONS.md").exists(), "DECISIONS.md missing"
        assert (ai_dir / "RUNBOOK.md").exists(), "RUNBOOK.md missing"
        assert (ai_dir / "core" / "AUTHORITY_MODEL.md").exists(), "AUTHORITY_MODEL.md missing"
        assert (ai_dir / "core" / "WORKER_EXECUTION_RULES.md").exists()
        assert (ai_dir / "prompts" / "orchestrator_system.md").exists()
        assert runtime_dir.is_dir(), ".ai_runtime/ not created"
        assert (runtime_dir / "logs").is_dir(), "logs/ not created"
        assert (runtime_dir / "session").is_dir(), "session/ not created"

        # Check metadata was stamped
        import yaml
        meta = yaml.safe_load((ai_dir / "METADATA.yaml").read_text())
        assert meta.get("project_id") != "PLACEHOLDER", "project_id not stamped"
        assert meta.get("skeleton_version") not in (None, "PLACEHOLDER"), "version not stamped"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 3: DB creation + ingest ───

def test_db_creation_and_ingest():
    from engine.ai_db import connect_db, create_db, get_snapshot, set_snapshot
    from engine.ai_init import copy_templates, setup_runtime
    from engine.ai_state import reconcile

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)

        ai_dir = tmpdir / ".ai"
        runtime_dir = tmpdir / ".ai_runtime"

        # Reconcile should create DB and ingest
        updated = reconcile(ai_dir, runtime_dir)
        assert updated, "Expected reconcile to update DB on first run"

        # DB should exist
        db_path = runtime_dir / "ai.db"
        assert db_path.exists(), "ai.db not created"

        # Check tables have data
        conn = connect_db(runtime_dir)
        workers = conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
        assert workers > 0, f"Expected workers in DB, got {workers}"

        # Check snapshot was stored
        h = get_snapshot(conn, "canonical_hash")
        assert h is not None, "canonical_hash not stored"

        # Second reconcile should be no-op
        conn.close()
        updated2 = reconcile(ai_dir, runtime_dir)
        assert not updated2, "Expected reconcile to be no-op (no changes)"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 4: Export/import roundtrip ───

def test_export_import_roundtrip():
    from engine.ai_init import copy_templates, setup_runtime, stamp_metadata
    from engine.ai_memory import export_memory, import_memory
    from engine.ai_state import reconcile
    from engine.ai_db import connect_db, add_event

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)
        stamp_metadata(tmpdir, skel)

        ai_dir = tmpdir / ".ai"
        runtime_dir = tmpdir / ".ai_runtime"
        reconcile(ai_dir, runtime_dir)

        # Add some events
        conn = connect_db(runtime_dir)
        add_event(conn, "test", "test_event", {"key": "value"})
        add_event(conn, "test", "another_event", {"num": 42})
        conn.close()

        # Export
        pack_path = export_memory(ai_dir, runtime_dir, "test-version")
        assert Path(pack_path).is_dir(), "Pack directory not created"
        assert (Path(pack_path) / "manifest.json").exists(), "manifest.json missing"
        assert (Path(pack_path) / "events.jsonl").exists(), "events.jsonl missing"

        # Check manifest
        manifest = json.loads((Path(pack_path) / "manifest.json").read_text())
        assert manifest["version"] == "1.0"
        assert manifest["skeleton_version"] == "test-version"

        # Export as zip
        zip_path = str(tmpdir / "test_pack.zip")
        zip_result = export_memory(ai_dir, runtime_dir, "test-version", zip_path)
        assert Path(zip_result).exists(), "Zip not created"

        # Import into fresh runtime
        runtime_dir2 = tmpdir / ".ai_runtime2"
        runtime_dir2.mkdir()
        # Temporarily swap runtime dir
        result = import_memory(ai_dir, runtime_dir2, pack_path)
        assert "Imported" in result, f"Import failed: {result}"
        assert "events" in result.lower()

        # Verify events were imported
        conn2 = connect_db(runtime_dir2)
        count = conn2.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert count >= 2, f"Expected >= 2 events, got {count}"
        conn2.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 5: Git-sync only commits whitelisted files ───

def test_git_sync_whitelist():
    import subprocess
    from engine.ai_git import git_sync, ensure_gitignore
    from engine.ai_init import copy_templates, setup_runtime, stamp_metadata
    from engine.ai_state import reconcile

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)
        stamp_metadata(tmpdir, skel)
        ensure_gitignore(tmpdir)
        reconcile(tmpdir / ".ai", tmpdir / ".ai_runtime")

        # Create a non-ai file that should NOT be committed
        (tmpdir / "secret.txt").write_text("should not be committed")

        # Create a runtime file that should NOT be committed
        (tmpdir / ".ai_runtime" / "test.log").write_text("runtime log")

        success, msg = git_sync(tmpdir)

        # Check that secret.txt and .ai_runtime were NOT committed
        result = subprocess.run(
            ["git", "log", "--oneline", "--name-only", "-1"],
            cwd=str(tmpdir), capture_output=True, text=True,
        )
        committed_files = result.stdout

        assert "secret.txt" not in committed_files, "secret.txt was committed!"
        assert ".ai_runtime" not in committed_files, ".ai_runtime was committed!"

        if success:
            # Verify canonical files were committed
            assert ".ai/" in committed_files or ".ai/state" in committed_files, \
                f"Canonical files not committed. Files: {committed_files}"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 6: Validation ───

def test_validation():
    from engine.ai_init import copy_templates
    from engine.ai_validate import validate_all

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        results = validate_all(tmpdir / ".ai", skel / "schemas")
        for fname, errs in results.items():
            assert len(errs) == 0, f"Validation errors in {fname}: {errs}"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 7: Status rendering ───

def test_status_rendering():
    from engine.ai_init import copy_templates, setup_runtime
    from engine.ai_state import reconcile, render_status

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)
        reconcile(tmpdir / ".ai", tmpdir / ".ai_runtime")

        report = render_status(tmpdir / ".ai", tmpdir / ".ai_runtime")
        assert "PROJECT STATUS" in report, "Status report missing header"
        assert "Phase:" in report, "Status report missing phase"
        assert "Progress:" in report, "Status report missing progress"

        # Check STATUS.md was written
        status_md = tmpdir / ".ai" / "STATUS.md"
        assert status_md.exists(), "STATUS.md not updated"
        content = status_md.read_text()
        assert "# Project Status" in content
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 8: Init does not overwrite existing files ───

def test_init_no_overwrite():
    from engine.ai_init import copy_templates

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        # Create a custom team.yaml first
        ai_dir = tmpdir / ".ai" / "state"
        ai_dir.mkdir(parents=True)
        custom_content = "# Custom team config\norcestrator:\n  role_id: custom\n"
        (ai_dir / "team.yaml").write_text(custom_content)

        # Run copy_templates — should NOT overwrite
        copy_templates(skel, tmpdir)

        result = (ai_dir / "team.yaml").read_text()
        assert result == custom_content, "team.yaml was overwritten!"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 9: Session memory DB init + insert/retrieve ───

def test_session_memory_db():
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    try:
        # Setup minimal .ai/state for policy
        ai_state = tmpdir / ".ai" / "state"
        ai_state.mkdir(parents=True, exist_ok=True)
        runtime_session = tmpdir / ".ai_runtime" / "session"
        runtime_session.mkdir(parents=True, exist_ok=True)

        mem = SessionMemory(tmpdir)

        # Insert messages
        id1 = mem.add_message("s1", "orchestrator", "user", "Hello world")
        assert id1 is not None, "Failed to insert message"

        id2 = mem.add_message("s1", "orchestrator", "assistant", "Hi there")
        assert id2 is not None, "Failed to insert second message"

        # Retrieve
        msgs = mem.get_recent_messages("s1", "orchestrator", limit=10)
        assert len(msgs) == 2, f"Expected 2 messages, got {len(msgs)}"
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello world"
        assert msgs[1]["role"] == "assistant"

        # Insert and retrieve fact
        fid = mem.add_fact("s1", "orchestrator", "Project uses Python 3.9+", importance=8, tags=["tech"])
        assert fid is not None, "Failed to insert fact"

        # Insert and retrieve summary
        mem.upsert_summary("s1", "orchestrator", "This is a test project summary.")
        context = mem.get_context("s1", "orchestrator", max_recent=2, max_facts=5)
        assert len(context) > 0, "Context should not be empty"

        mem.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 10: Session memory FTS fallback ───

def test_session_memory_fts_fallback():
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    try:
        runtime_session = tmpdir / ".ai_runtime" / "session"
        runtime_session.mkdir(parents=True, exist_ok=True)

        mem = SessionMemory(tmpdir)

        # Insert searchable content
        mem.add_message("s1", "orchestrator", "user", "The database schema uses PostgreSQL")
        mem.add_message("s1", "orchestrator", "assistant", "I recommend using SQLite for local cache")
        mem.add_message("s1", "orchestrator", "user", "What about Redis?")

        # Search (works with FTS5 or LIKE fallback)
        results = mem.search("s1", "orchestrator", "SQLite")
        assert len(results) >= 1, f"Search should find SQLite message, got {len(results)}"
        assert "SQLite" in results[0]["content"]

        mem.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 11: Session memory redaction ───

def test_session_memory_redaction():
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    try:
        runtime_session = tmpdir / ".ai_runtime" / "session"
        runtime_session.mkdir(parents=True, exist_ok=True)

        mem = SessionMemory(tmpdir)

        # Insert message with sensitive content
        mem.add_message("s1", "orchestrator", "user",
                        "Use api_key=sk-abc123def456ghi789jkl012mno345 for auth")

        msgs = mem.get_recent_messages("s1", "orchestrator", limit=1)
        assert len(msgs) == 1
        assert "sk-abc123def456ghi789jkl012mno345" not in msgs[0]["content"], \
            "API key was not redacted!"
        assert "[REDACTED]" in msgs[0]["content"], "Redaction placeholder missing"

        mem.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 12: Session memory export/import roundtrip ───

def test_session_memory_pack_roundtrip():
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    try:
        runtime_session = tmpdir / ".ai_runtime" / "session"
        runtime_session.mkdir(parents=True, exist_ok=True)

        mem = SessionMemory(tmpdir)

        # Add data
        mem.add_message("s1", "orchestrator", "user", "Test message one")
        mem.add_message("s1", "orchestrator", "assistant", "Test response")
        mem.add_fact("s1", "orchestrator", "Important fact", importance=9)

        # Export as directory
        export_dir = tmpdir / "test_export"
        result = mem.export_pack(export_dir)
        assert Path(result).is_dir(), "Export directory not created"
        assert (Path(result) / "manifest.json").exists(), "manifest.json missing"
        assert (Path(result) / "messages.jsonl").exists(), "messages.jsonl missing"
        assert (Path(result) / "checksums.json").exists(), "checksums.json missing"

        # Export as zip
        zip_path = tmpdir / "test_export.zip"
        zip_result = mem.export_pack(zip_path)
        assert Path(zip_result).exists(), "Zip not created"

        mem.close()

        # Import into fresh instance
        runtime2 = tmpdir / ".ai_runtime2" / "session"
        runtime2.mkdir(parents=True, exist_ok=True)
        mem2 = SessionMemory(tmpdir, db_path=runtime2 / "memory.db")

        counts = mem2.import_pack(export_dir)
        assert counts.get("messages", 0) >= 2, f"Expected >= 2 messages imported, got {counts}"
        assert counts.get("facts", 0) >= 1, f"Expected >= 1 fact imported, got {counts}"

        # Verify data is there
        msgs = mem2.get_recent_messages("s1", "orchestrator", limit=10)
        assert len(msgs) >= 2, "Imported messages not retrievable"

        mem2.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 13: Session memory policy enforcement ───

def test_session_memory_policy():
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    try:
        runtime_session = tmpdir / ".ai_runtime" / "session"
        runtime_session.mkdir(parents=True, exist_ok=True)

        mem = SessionMemory(tmpdir)

        # "worker_ephemeral" namespace has persist=none by default
        result = mem.add_message("s1", "worker_ephemeral", "user", "Should not persist")
        assert result is None, "Message should be rejected for ephemeral namespace"

        # "orchestrator" namespace should accept
        result = mem.add_message("s1", "orchestrator", "user", "Should persist")
        assert result is not None, "Message should be accepted for orchestrator namespace"

        mem.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 14: Auto-import from inbox ───

def test_auto_import_inbox():
    from engine.ai_run import _auto_import_inbox
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        from engine.ai_init import copy_templates, setup_runtime
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)

        # Create a session memory with data, export a pack
        mem = SessionMemory(tmpdir)
        mem.add_message("s1", "orchestrator", "user", "Message for import test")
        mem.add_message("s1", "orchestrator", "assistant", "Response for import test")

        # Export to a zip
        export_zip = tmpdir / "test_inbox_pack.zip"
        mem.export_pack(str(export_zip))
        mem.close()

        # Place the zip in import_inbox
        inbox = tmpdir / ".ai_runtime" / "import_inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        import shutil as _shutil
        _shutil.copy2(str(export_zip), str(inbox / "test_inbox_pack.zip"))

        # Wipe the original DB so we can verify import brings data back
        db_path = tmpdir / ".ai_runtime" / "session" / "memory.db"
        if db_path.exists():
            db_path.unlink()

        # Run auto-import
        result = _auto_import_inbox(tmpdir)
        assert result is not None, "Auto-import should have found and imported a pack"
        assert "Auto-imported" in result, f"Unexpected result: {result}"

        # Verify pack was moved to processed/
        processed = inbox / "processed"
        assert (processed / "test_inbox_pack.zip").exists(), "Pack not moved to processed/"
        assert not (inbox / "test_inbox_pack.zip").exists(), "Pack still in inbox"

        # Verify data was imported
        mem2 = SessionMemory(tmpdir)
        msgs = mem2.get_recent_messages("s1", "orchestrator", limit=10)
        assert len(msgs) >= 2, f"Expected >= 2 imported messages, got {len(msgs)}"
        mem2.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 15: Auto-export pack ───

def test_auto_export_pack():
    from engine.ai_run import _auto_export_pack
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        from engine.ai_init import copy_templates, setup_runtime
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)

        # Create session data (must use session_id "default" and namespace "orchestrator"
        # since _auto_export_pack checks for count > 0 on those)
        mem = SessionMemory(tmpdir)
        mem.add_message("default", "orchestrator", "user", "Test for auto-export")
        mem.add_message("default", "orchestrator", "assistant", "Acknowledged")
        mem.close()

        # Run auto-export
        result = _auto_export_pack(tmpdir)
        assert result is not None, "Auto-export should have produced a pack"
        assert Path(result).exists(), f"Export file missing: {result}"

        # Check memory_packs/ has the file
        packs_dir = tmpdir / ".ai_runtime" / "memory_packs"
        packs = list(packs_dir.glob("session_pack_*.zip"))
        assert len(packs) >= 1, f"Expected at least 1 pack in memory_packs/, got {len(packs)}"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 16: Distillation check ───

def test_distillation_check():
    from engine.ai_run import _check_distillation
    from engine.memory_core.api import SessionMemory

    tmpdir = make_test_project()
    try:
        runtime_session = tmpdir / ".ai_runtime" / "session"
        runtime_session.mkdir(parents=True, exist_ok=True)

        mem = SessionMemory(tmpdir)

        # Default orchestrator distill_every_n_turns = 20
        assert not _check_distillation(mem, "s1", "orchestrator", 0), "Should not distill at turn 0"
        assert not _check_distillation(mem, "s1", "orchestrator", 5), "Should not distill at turn 5"
        assert _check_distillation(mem, "s1", "orchestrator", 20), "Should distill at turn 20"
        assert _check_distillation(mem, "s1", "orchestrator", 40), "Should distill at turn 40"
        assert not _check_distillation(mem, "s1", "orchestrator", 21), "Should not distill at turn 21"

        mem.close()
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 17: STATUS.md updates on state change ───

def test_status_md_auto_update():
    from engine.ai_init import copy_templates, setup_runtime
    from engine.ai_state import reconcile, render_status

    tmpdir = make_test_project()
    skel = Path(skeleton_dir)
    try:
        copy_templates(skel, tmpdir)
        setup_runtime(tmpdir)

        ai_dir = tmpdir / ".ai"
        runtime_dir = tmpdir / ".ai_runtime"

        reconcile(ai_dir, runtime_dir)
        render_status(ai_dir, runtime_dir)

        status_path = ai_dir / "STATUS.md"
        assert status_path.exists(), "STATUS.md not created"
        content = status_path.read_text()
        assert "# Project Status" in content, "STATUS.md missing header"
        assert "Last updated:" in content, "STATUS.md missing timestamp"

        # Modify board.yaml to simulate a state change
        import yaml
        board_path = ai_dir / "state" / "board.yaml"
        board = yaml.safe_load(board_path.read_text()) or {}
        board.setdefault("tasks", []).append({
            "id": "test-task-1",
            "title": "Test task for STATUS.md update",
            "status": "in_progress",
            "owner_role": "developer",
        })
        board_path.write_text(yaml.dump(board, default_flow_style=False, sort_keys=False))

        # Re-reconcile and re-render
        reconcile(ai_dir, runtime_dir)
        render_status(ai_dir, runtime_dir)

        content2 = status_path.read_text()
        assert "test-task-1" in content2 or "Test task" in content2, \
            "STATUS.md should reflect the new task"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Test 18: Init creates import_inbox and memory_packs dirs ───

def test_init_creates_autopersist_dirs():
    from engine.ai_init import setup_runtime

    tmpdir = make_test_project()
    try:
        setup_runtime(tmpdir)
        runtime_dir = tmpdir / ".ai_runtime"
        assert (runtime_dir / "import_inbox").is_dir(), "import_inbox/ not created"
        assert (runtime_dir / "memory_packs").is_dir(), "memory_packs/ not created"
    finally:
        shutil.rmtree(str(tmpdir))


# ─── Run all ───

def main():
    global passed, failed

    print("\n=== AI Team Skeleton — Self Check ===\n")

    # Check PyYAML
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required. Install it: pip install pyyaml")
        sys.exit(1)

    check("Project root detection", test_project_root_detection)
    check("Init creates structure", test_init_creates_structure)
    check("DB creation + ingest", test_db_creation_and_ingest)
    check("Export/import roundtrip", test_export_import_roundtrip)
    check("Git-sync whitelist", test_git_sync_whitelist)
    check("Schema validation", test_validation)
    check("Status rendering", test_status_rendering)
    check("Init no-overwrite", test_init_no_overwrite)
    check("Session memory DB init + CRUD", test_session_memory_db)
    check("Session memory FTS fallback", test_session_memory_fts_fallback)
    check("Session memory redaction", test_session_memory_redaction)
    check("Session memory pack roundtrip", test_session_memory_pack_roundtrip)
    check("Session memory policy enforcement", test_session_memory_policy)
    check("Auto-import from inbox", test_auto_import_inbox)
    check("Auto-export pack", test_auto_export_pack)
    check("Distillation check", test_distillation_check)
    check("STATUS.md auto-update", test_status_md_auto_update)
    check("Init creates autopersist dirs", test_init_creates_autopersist_dirs)

    print(f"\n{'=' * 40}")
    print(f"  Results: {passed} passed, {failed} failed")
    if errors:
        print("\n  Failures:")
        for name, err in errors:
            print(f"    {name}: {err}")
    print(f"{'=' * 40}\n")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
