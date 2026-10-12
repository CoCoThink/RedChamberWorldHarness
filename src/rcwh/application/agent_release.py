"""CLI for isolated agent-reviewed research editions; no stable publication flags."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..workflow.agent_release import AgentRelease
from .common import repo_root


def cmd_agent_release(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        release = AgentRelease(root)
        if args.agent_release_command == "build":
            payload = release.build(args.request, allow_pending=args.allow_pending)
        else:
            payload = release.evaluate(args.request)
    except (KeyError, OSError, UnicodeError, TypeError, ValueError) as exc:
        payload = {"status": "FAIL", "scope": "AGENT_RESEARCH_RELEASE", "findings": [str(exc)],
                   "authority_effect": "NONE", "stable_active_effect": "NONE"}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"AGENT RESEARCH RELEASE: {payload['status']}")
        print("stable_active_effect: NONE")
        if "provenance" in payload:
            print(f"provenance: {payload['provenance']}")
        for finding in payload.get("findings", []):
            print(f"- {finding}")
        for pending in payload.get("pending", []):
            print(f"- pending: {pending}")
    return {"PASS": 0, "PENDING": 2, "FAIL": 1}[payload["status"]]


def add_commands(sub) -> None:
    parser = sub.add_parser("agent-release", help="Isolated agent-only research release, never stable adoption")
    commands = parser.add_subparsers(dest="agent_release_command", required=True)
    for command in ("evaluate", "build"):
        child = commands.add_parser(command)
        child.add_argument("request", help="Repository-relative release request JSON/YAML")
        child.add_argument("--json", action="store_true")
        if command == "build":
            child.add_argument("--allow-pending", action="store_true", help="Emit staging manifest only; do not publish reviewed prose")
        child.set_defaults(func=cmd_agent_release)
