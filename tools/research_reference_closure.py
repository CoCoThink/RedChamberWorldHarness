"""List research artifacts still bound by live repository data (read-only).

Live roots are data/, src/, schemas/, tools/ and artifacts/ outside
agent_research, minus the panel records being archived. A research file named
there by exact path in a machine-readable record stays in place (a live input),
transitively; prose mentions bind nothing. Everything else may be archived.
Prints JSON: {"live": [...], "archivable": [...], "missing": [...]}.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

RESEARCH = "artifacts/agent_research/"
LIVE_ROOTS = ("data", "src", "schemas", "tools", "artifacts")
NOT_LIVE = ("data/agent_panel/", RESEARCH)
# Only machine-readable records bind bytes; prose notes that mention a path do not.
TEXT_SUFFIXES = {".json", ".jsonl", ".yaml", ".yml", ".py"}
PATH = re.compile(re.escape(RESEARCH) + r"[^\s\"'`\\)\]},，：]+")


def _files(root: Path, base: str):
    for directory, dirs, names in os.walk(root / base):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".rcwh-cache"}]
        for name in names:
            path = Path(directory) / name
            yield path.relative_to(root).as_posix(), path


def _mentions(path: Path) -> set[str]:
    if path.suffix not in TEXT_SUFFIXES:
        return set()
    return {m.rstrip(".:;") for m in PATH.findall(path.read_text(encoding="utf-8", errors="ignore"))}


def closure(root: Path) -> dict:
    """Transitive: live research files may bind further research files."""
    root = Path(root).resolve()
    present = {relative: path for relative, path in _files(root, RESEARCH.rstrip("/"))}
    live: dict[str, set[str]] = {}
    frontier = []
    for base in LIVE_ROOTS:
        for relative, path in _files(root, base):
            if not relative.startswith(NOT_LIVE):
                frontier.append((relative, path))
    seen = set()
    while frontier:
        relative, path = frontier.pop()
        if relative in seen:
            continue
        seen.add(relative)
        for mention in _mentions(path):
            live.setdefault(mention, set()).add(relative)
            if mention in present and mention not in seen:
                frontier.append((mention, present[mention]))
    kept = {p for p in present if p in live}
    return {"live": sorted(kept), "archivable": sorted(set(present) - kept),
            "missing": sorted(m for m in live if m not in present),
            "referrers": {p: sorted(live[p]) for p in sorted(kept)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--summary", action="store_true", help="Print counts only")
    args = parser.parse_args()
    report = closure(Path(args.root))
    if args.summary:
        report = {key: len(value) for key, value in report.items()}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
