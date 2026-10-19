"""Standalone local agent-panel commands; no provider or human-lane writes."""
import json
from pathlib import Path

from ..workflow.agent_panel import register, scaffold, status
from .common import repo_root


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.agent_panel_action == "register":
            report = register(root, Path(args.file), origin=args.origin,
                              origin_kind=args.origin_kind, dry_run=args.dry_run)
        elif args.agent_panel_action == "scaffold":
            skeleton = scaffold(root, args.packet, reviewer_id=args.reviewer_id, session_id=args.session_id,
                                subjects=args.subjects.split(",") if args.subjects else None)
            Path(args.out).write_text(json.dumps(skeleton, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": "PASS", "written": args.out, "subjects": len(skeleton["results"]),
                              "note": "Fill every verdict and notes; empty skeletons cannot be registered."},
                             ensure_ascii=False, indent=2))
            return 0
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
    inspect.add_argument("--json", action="store_true", help="Accepted for consistency; output is always JSON")
    skeleton = actions.add_parser("scaffold", help="Write an opinion skeleton with exact packet and subject hashes")
    skeleton.add_argument("packet", help="Repository-relative packet file")
    skeleton.add_argument("--reviewer-id", required=True)
    skeleton.add_argument("--session-id", required=True)
    skeleton.add_argument("--subjects", help="Comma-separated subject ids; default all")
    skeleton.add_argument("--out", required=True, help="Skeleton file to write")
    parser.set_defaults(func=command)
