# Portability

## Directory mapping

| Purpose | macOS/Linux | Windows |
|---|---|---|
| Claude home | `~/.claude` | `%USERPROFILE%\.claude` |
| Codex home | `~/.codex` | `%USERPROFILE%\.codex` |
| Shared data | `~/clawd` | `%USERPROFILE%\clawd` |

All Python paths use `pathlib.Path`. Override a nonstandard installation with `CLAUDE_HOME`, `CODEX_HOME`, `CLAWD_HOME`, or `TOOL_INDEX_PATH`.

## Transcript discovery

Claude Code stores transcripts below `.claude/projects`. The bundled `pidx.py transcript` command encodes the current working directory by replacing non-alphanumeric characters with hyphens and selects the newest JSONL file. This is best-effort. If a Claude Code release changes its directory naming, pass `--cwd` or update only `cmd_transcript`.

## Python launcher

Documentation uses `python`. On Windows, `py -3` is also valid. On systems where only `python3` exists, substitute it without changing the scripts.
