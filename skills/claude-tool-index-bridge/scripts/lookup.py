#!/usr/bin/env python3
"""Lookup Claude Code/Clawd tools for Codex bridge usage."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


HOME = Path.home()
CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME", HOME / ".claude")).expanduser()
CLAWD_HOME = Path(os.environ.get("CLAWD_HOME", HOME / "clawd")).expanduser()
MANIFEST = Path(os.environ.get("TOOL_INDEX_PATH", CLAWD_HOME / "tool-index.json")).expanduser()
SOURCE_DIRS = [
    CLAUDE_HOME / "skills",
    CLAWD_HOME / "skills",
    CLAUDE_HOME / "commands",
    CLAWD_HOME / "workflows",
]


def norm(value: str) -> str:
    return value.strip().lower().removeprefix("/")


def is_stale() -> bool:
    if not MANIFEST.exists():
        return True
    manifest_mtime = MANIFEST.stat().st_mtime
    for root in SOURCE_DIRS:
        if not root.exists():
            continue
        if root.stat().st_mtime > manifest_mtime:
            return True
        if any(path.is_file() and path.stat().st_mtime > manifest_mtime for path in root.rglob("*")):
            return True
    return False


def load_entries() -> list[dict[str, Any]]:
    with MANIFEST.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return list(data.get("entries", []))


def score(entry: dict[str, Any], query: str) -> int:
    q = norm(query)
    name = norm(str(entry.get("name", "")))
    invoke = norm(str(entry.get("invoke", "")))
    path = norm(os.path.basename(str(entry.get("path", ""))))

    if q in {name, invoke, path}:
        return 100
    if q and (q in name or q in invoke):
        return 80

    haystack_parts = [
        str(entry.get("summary", "")),
        str(entry.get("used_for", "")),
        str(entry.get("how_it_works", "")),
        " ".join(str(tag) for tag in entry.get("tags", [])),
    ]
    haystack = norm(" ".join(haystack_parts))
    terms = [term for term in q.replace("-", " ").split() if term]
    if not terms:
        return 0
    return sum(10 for term in terms if term in haystack)


def display(entry: dict[str, Any], rank: int) -> None:
    print(f"#{rank} {entry.get('name', '')}")
    print(f"kind: {entry.get('kind', '')}")
    print(f"invoke: {entry.get('invoke', '')}")
    print(f"env: {entry.get('env', '')}")
    print(f"invocable_from_cc: {entry.get('invocable_from_cc', '')}")
    if entry.get("bridge"):
        print(f"bridge: {entry.get('bridge')}")
    if entry.get("path"):
        print(f"path: {entry.get('path')}")
    print(f"summary: {entry.get('summary', '')}")
    if entry.get("used_for"):
        print(f"used_for: {entry.get('used_for')}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lookup Claude Code/Clawd indexed tools.")
    parser.add_argument("query", help="Skill, command, workflow, or task query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    print(f"manifest: {MANIFEST}")
    print(f"staleness: {'STALE' if is_stale() else 'FRESH'}")
    if not MANIFEST.exists():
        print("error: manifest missing; run the repository script: python scripts/build_tool_index.py build")
        return 2

    ranked = [(score(entry, args.query), entry) for entry in load_entries()]
    ranked = [(points, entry) for points, entry in ranked if points > 0]
    ranked.sort(key=lambda item: item[0], reverse=True)

    if not ranked:
        print("matches: 0")
        return 1

    print(f"matches: {len(ranked)}")
    for rank, (points, entry) in enumerate(ranked[: args.limit], start=1):
        print(f"score: {points}")
        display(entry, rank)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
