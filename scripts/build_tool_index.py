#!/usr/bin/env python3
"""Build a portable index of local Claude/Clawd skills, commands, and workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path


USER_HOME = Path.home()
CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME", USER_HOME / ".claude")).expanduser()
CLAWD_HOME = Path(os.environ.get("CLAWD_HOME", USER_HOME / "clawd")).expanduser()
OUTPUT = Path(os.environ.get("TOOL_INDEX_PATH", CLAWD_HOME / "tool-index.json")).expanduser()

SOURCES = (
    (CLAUDE_HOME / "skills", "skill", "claude-code"),
    (CLAWD_HOME / "skills", "skill", "clawd"),
    (CLAUDE_HOME / "commands", "command", "claude-code"),
    (CLAWD_HOME / "workflows", "workflow", "clawd"),
)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    result: dict[str, str] = {}
    for line in parts[1].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            value = match.group(2).strip().strip('"').strip("'")
            result[match.group(1)] = value
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidates(root: Path, kind: str):
    if not root.exists():
        return
    if kind == "skill":
        yield from sorted(root.glob("*/SKILL.md"))
    else:
        yield from sorted(p for p in root.rglob("*.md") if p.is_file())


def entry(path: Path, kind: str, env: str) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = parse_frontmatter(text)
    name = meta.get("name") or (path.parent.name if path.name == "SKILL.md" else path.stem)
    description = meta.get("description", "")
    invocation = f"/{name}" if kind in {"command", "workflow"} else "Skill tool"
    return {
        "name": name,
        "kind": kind,
        "invoke": invocation,
        "env": env,
        "invocable_from_cc": env == "claude-code",
        "bridge": None,
        "category": env,
        "summary": description,
        "how_it_works": "",
        "used_for": "",
        "composable_parts": [],
        "path": str(path.resolve()),
        "source_hash": sha256(path),
        "status": "Active",
        "status_reason": "",
        "last_modified": dt.datetime.fromtimestamp(path.stat().st_mtime).date().isoformat(),
        "tags": [],
    }


def build() -> dict:
    entries = []
    seen = set()
    for root, kind, env in SOURCES:
        for path in candidates(root, kind) or ():
            item = entry(path, kind, env)
            key = (item["kind"], item["name"], item["path"])
            if key not in seen:
                seen.add(key)
                entries.append(item)
    entries.sort(key=lambda item: (item["name"].lower(), item["kind"], item["path"]))
    digest = hashlib.sha256(
        json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "built_hash": digest,
        "count": len(entries),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "check"), nargs="?", default="build")
    args = parser.parse_args()
    data = build()
    if args.command == "check":
        if not OUTPUT.exists():
            print(f"MISSING: {OUTPUT}")
            return 1
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        fresh = current.get("built_hash") == data["built_hash"]
        print("FRESH" if fresh else "STALE")
        return 0 if fresh else 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['entries'])} entries to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
