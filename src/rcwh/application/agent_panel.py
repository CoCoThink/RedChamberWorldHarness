"""Standalone local agent-panel commands; no provider or human-lane writes."""
import json
from pathlib import Path

from ..workflow.agent_panel import register, status
from .common import repo_root


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.agent_panel_action == "register":
            report = register(root, Path(args.file), origin=args.origin,
                              origin_kind=args.origin_kind, dry_run=args.dry_run)
        else:
            report = status(root, packet=args.packet)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        report = {"status": "FAIL", "findings": [str(exc)], "authority_effect": "NONE",
                  "usage": "RESEARCH_ONLY", "independent_human_admission": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {"PASS": 0, "FAIL": 1, "PENDING": 2}[report["status"]]


def add_commands(sub) -> None:
    parser = sub.add_parser("agent-panel", help="Register and inspect local research-only model opinions")
    actions = parser.add_subparsers(dest="agent_panel_action", required=True)
    intake = actions.add_parser("register", help="Retain actual local JSON model output unchanged")
    intake.add_argument("file")
    intake.add_argument("--origin", required=True, help="Custody/source description, not provider verification")
    intake.add_argument("--origin-kind", choices=["FILE"], default="FILE")
    intake.add_argument("--dry-run", action="store_true")
    inspect = actions.add_parser("status", help="Inspect every registered record, optionally report one packet")
    inspect.add_argument("--packet", help="Repository-relative packet file; does not filter record integrity")
    parser.set_defaults(func=command)
