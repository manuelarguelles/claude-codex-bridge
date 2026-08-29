---
name: claude-tool-index-bridge
description: Discover and reuse local Claude Code skills, slash commands, workflows, and project-memory routines from Codex through a portable JSON index. Use when the user references a Claude capability such as /indexar-proyecto or /recuperar-proyecto, asks Codex to consult Claude files or memory, or wants to bridge an existing Claude workflow into Codex without copying secrets.
---

# Claude Tool Index Bridge

Treat the local Claude/Clawd catalog as a first-class discovery source.

## Resolve a capability

1. Run:

   ```bash
   python scripts/lookup.py "<query>"
   ```

2. If the manifest is missing or stale, rebuild it from the repository root:

   ```bash
   python scripts/build_tool_index.py build
   ```

3. Run the lookup again and read the complete source file returned by the exact or best-ranked match.
4. Follow that source exactly when it uses ordinary files, scripts, Git, shell, or CLIs.
5. Adapt Claude-only runtime primitives to equivalent Codex tools and report any capability that cannot be bridged.

## Safety

- Never copy API keys, tokens, browser profiles, Claude credentials, transcripts, or personal memory into the bridge repository.
- Read skills in place; do not duplicate them during ordinary use.
- Prefer exact matches by name, slash invocation, and path basename.
- Rebuild the manifest instead of editing it manually.
- Treat commands that mutate external state according to normal Codex approval rules.

## Paths

The scripts use these environment variables when present:

- `CLAUDE_HOME` (default `~/.claude`)
- `CODEX_HOME` (default `~/.codex`)
- `CLAWD_HOME` (default `~/clawd`)
- `TOOL_INDEX_PATH` (default `$CLAWD_HOME/tool-index.json`)

Read `references/PORTABILITY.md` only when installing, migrating, or debugging paths across operating systems.
