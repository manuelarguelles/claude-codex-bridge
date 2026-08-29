# Claude ↔ Codex Local Bridge

Portable, file-based bridge that lets Codex discover and run local Claude Code skills, commands, workflows, and explicit project-memory routines. It does not use a private Claude API and does not copy credentials.

## Included

- Codex skill: `claude-tool-index-bridge`
- Claude skills: `/indexar-proyecto` and `/recuperar-proyecto`
- Cross-platform tool-index builder and lookup
- `pidx.py` project-memory engine
- PowerShell installer for Windows
- Bash installer for macOS/Linux
- Sanitized examples and smoke tests

## Windows installation

Requirements: Python 3.11+, Claude Code, Codex, and PowerShell 5.1+.

```powershell
git clone https://github.com/manuelarguelles/claude-codex-bridge.git
cd claude-codex-bridge
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Restart Claude Code and Codex, then test:

```powershell
python "$HOME\.codex\skills\claude-tool-index-bridge\scripts\lookup.py" "/recuperar-proyecto"
python "$HOME\clawd\projects-index\pidx.py" list
```

## macOS/Linux installation

```bash
git clone https://github.com/manuelarguelles/claude-codex-bridge.git
cd claude-codex-bridge
chmod +x install.sh
./install.sh
```

## Architecture

```text
~/.claude/skills ─┐
~/.claude/commands ├─ build_tool_index.py → ~/clawd/tool-index.json
~/clawd/skills ────┤                         ↑
~/clawd/workflows ─┘                    lookup.py
                                             ↓
                                  Codex reads the real source

~/clawd/projects-index/pidx.py → explicit PROGRAM/PROJECT/session memory
```

Configuration variables: `CLAUDE_HOME`, `CODEX_HOME`, `CLAWD_HOME`, `TOOL_INDEX_PATH`, and `PIDX_HOME`.

## Security boundary

Do not commit `tool-index.json` from a real machine because it contains absolute local paths. Do not commit transcripts, browser profiles, `.env` files, credentials, or personal project memory. The installer generates a local manifest and an empty project index.

See [HANDOFF.md](HANDOFF.md) for maintenance and migration details.
