# Smoke Test: Automatic Persistence

Manual verification steps for the auto-persistence feature.

## Prerequisites

- Python 3.9+
- PyYAML installed (`pip install pyyaml`)

## Test 1: Session Memory Persists Across Runs

```bash
# Initialize a test project
mkdir /tmp/test-autopersist && cd /tmp/test-autopersist
git init && git commit --allow-empty -m "init"
python /path/to/engine/ai init --non-interactive

# Run orchestrator and issue commands
python /path/to/engine/ai run
# At the ai> prompt, type:
#   status
#   quit

# Check that session memory DB was created
ls .ai_runtime/session/memory.db
# Expected: file exists

# Check that auto-export pack was created
ls .ai_runtime/memory_packs/
# Expected: session_pack_*.zip file present
```

## Test 2: Auto-Import from Inbox

```bash
# Copy a memory pack into import_inbox
cp .ai_runtime/memory_packs/session_pack_*.zip .ai_runtime/import_inbox/

# Run orchestrator again
python /path/to/engine/ai run
# Expected output: "Auto-imported session memory from session_pack_*.zip"
# At the ai> prompt, type: quit

# Verify the pack was moved to processed/
ls .ai_runtime/import_inbox/processed/
# Expected: session_pack_*.zip moved here
```

## Test 3: STATUS.md Updated on Exit

```bash
# After running ai run and exiting:
cat .ai/STATUS.md
# Expected: contains "# Project Status" with current timestamp
```

## Test 4: Redaction

```bash
python /path/to/engine/ai run
# At the ai> prompt, type:
#   My api_key=sk-test1234567890abcdef1234567890
#   quit

# Check the session memory DB
python3 -c "
import sqlite3
conn = sqlite3.connect('.ai_runtime/session/memory.db')
rows = conn.execute('SELECT content FROM messages WHERE content LIKE \"%api_key%\"').fetchall()
for r in rows:
    print(r[0])
    assert 'sk-test1234567890' not in r[0], 'Key was NOT redacted!'
    assert '[REDACTED]' in r[0], 'Redaction placeholder missing!'
print('PASS: Redaction working')
"
```

## Test 5: Policy Enforcement

```bash
# The default policy sets worker_ephemeral to persist=none
# Verify via self_check:
python /path/to/engine/self_check.py
# Expected: all tests PASS including "Session memory policy enforcement"
```

## Cleanup

```bash
rm -rf /tmp/test-autopersist
```
