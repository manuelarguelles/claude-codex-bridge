#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
claude_home="${CLAUDE_HOME:-$HOME/.claude}"
codex_home="${CODEX_HOME:-$HOME/.codex}"
clawd_home="${CLAWD_HOME:-$HOME/clawd}"

mkdir -p "$codex_home/skills" "$claude_home/skills" "$clawd_home/projects-index" "$clawd_home/tools"
cp -R "$repo_root/skills/claude-tool-index-bridge" "$codex_home/skills/"
cp -R "$repo_root/claude-skills/indexar-proyecto" "$claude_home/skills/"
cp -R "$repo_root/claude-skills/recuperar-proyecto" "$claude_home/skills/"
cp "$repo_root/project-memory/pidx.py" "$clawd_home/projects-index/pidx.py"
cp "$repo_root/scripts/build_tool_index.py" "$clawd_home/tools/build_tool_index.py"

if [[ ! -f "$clawd_home/projects-index/index.json" ]]; then
  printf '{"projects": []}\n' > "$clawd_home/projects-index/index.json"
fi

CLAUDE_HOME="$claude_home" CLAWD_HOME="$clawd_home" python "$clawd_home/tools/build_tool_index.py" build
printf 'Installed. Restart Claude Code and Codex.\n'
