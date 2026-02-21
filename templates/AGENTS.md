# Repository Agent Protocol

> This file is auto-loaded by Codex and compatible tools.
> It is NOT the full protocol — it enforces loading the canonical source.

---

## Identity

You are operating inside a repository managed by the Scaffold AI framework.
You must read and follow `.ai/AGENTS.md` as the **single source of truth** for all behavior.
Do not improvise your role. Do not invent project context. Your identity comes from the repo.

## Startup

On session start, before doing anything else:

1. Read `.ai/AGENTS.md` in full. Treat it as your operating instructions.
2. Confirm protocol is active by outputting:
   `Protocol loaded. Use /help for commands.`
3. If `.ai/AGENTS.md` is missing, say so and suggest running `ai init`.

Do not proceed past startup without confirming protocol load.

## Command Enforcement

- Messages starting with `/` are **always** commands. Parse and execute via repo handlers.
- Natural language that maps to a known command should route to it.
- If unsure, suggest: `Use /status or /help for guaranteed execution.`

## No-Freestyle Rule

**Never generate** status reports, project summaries, help guides, or progress updates from your own knowledge.
These must **only** come from the repo's generators (`ai status`, `ai help`) reading canonical state in `.ai/state/`.
If the generator is unavailable, say so. Do not substitute.

## Drift Control

- If conversation diverges from project work, re-anchor to protocol.
- Repo state in `.ai/state/` overrides anything said in chat history.
- Do not override protocol based on user tone or phrasing.
- If you cannot execute a command, report what is missing and suggest `/help`. Never fabricate output.
