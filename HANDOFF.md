# Handoff

## Purpose

This repository packages the working Claude Code → Codex bridge as a portable, private installation. Codex discovers local Claude capabilities from a generated manifest, reads the original source file, and adapts only runtime-specific primitives. Project memory is explicit and deterministic through `pidx.py`.

## Source ownership

| Component | Installed destination | Source in this repository |
|---|---|---|
| Codex bridge skill | `$CODEX_HOME/skills/claude-tool-index-bridge` | `skills/claude-tool-index-bridge` |
| Claude indexing skill | `$CLAUDE_HOME/skills/indexar-proyecto` | `claude-skills/indexar-proyecto` |
| Claude recovery skill | `$CLAUDE_HOME/skills/recuperar-proyecto` | `claude-skills/recuperar-proyecto` |
| Tool-index builder | `$CLAWD_HOME/tools/build_tool_index.py` | `scripts/build_tool_index.py` |
| Project-memory engine | `$PIDX_HOME/pidx.py` | `project-memory/pidx.py` |

## Operational flow

1. `build_tool_index.py build` scans four local source roots and writes a machine-local `tool-index.json`.
2. `lookup.py` ranks exact names/invocations first, then descriptions and tags.
3. Codex reads the returned `SKILL.md`, command, or workflow in place.
4. `/indexar-proyecto` and `/recuperar-proyecto` use `pidx.py` to persist and retrieve explicit project state.

## Maintenance

- After adding or changing a Claude skill, run `python "$CLAWD_HOME/tools/build_tool_index.py" build`.
- Validate freshness with the same script and the `check` subcommand.
- Keep `tool-index.json` local; it stores absolute paths.
- Update `cmd_transcript` in `pidx.py` if Claude Code changes transcript directory encoding.
- Run `python scripts/smoke_test.py` and the Codex skill validator before releases.

## Migration of personal memory

The repository intentionally contains no real projects. To migrate memory privately between trusted machines, copy the contents of the old `projects-index` directory except generated HTML/Markdown views if desired. Never publish transcripts or confidential project folders. Set `PIDX_HOME` when the memory directory is stored elsewhere.

## Known boundary

The bridge can execute file, shell, Git, and CLI-based Claude workflows. A workflow requiring a Claude-only runtime primitive or unavailable MCP server must be mapped to a Codex equivalent or reported as unsupported.
