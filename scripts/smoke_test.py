#!/usr/bin/env python3
"""Cross-platform smoke test for an installed bridge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def run(command, env):
    return subprocess.run(command, env=env, text=True, capture_output=True, check=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        claude = root / ".claude"
        codex = root / ".codex"
        clawd = root / "clawd"
        skill = claude / "skills" / "hello-bridge"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: hello-bridge\ndescription: Test bridge discovery.\n---\n\n# Test\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.update({
            "CLAUDE_HOME": str(claude),
            "CODEX_HOME": str(codex),
            "CLAWD_HOME": str(clawd),
        })
        run([sys.executable, str(REPO / "scripts" / "build_tool_index.py"), "build"], env)
        lookup = run([
            sys.executable,
            str(REPO / "skills" / "claude-tool-index-bridge" / "scripts" / "lookup.py"),
            "/hello-bridge",
        ], env)
        assert "#1 hello-bridge" in lookup.stdout
        data = json.loads((clawd / "tool-index.json").read_text(encoding="utf-8"))
        assert data["count"] == 1
        print("PASS: build + exact lookup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
