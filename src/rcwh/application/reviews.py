"""Operator tools for receiving independent review inputs."""
import json
from pathlib import Path

from ..workflow.review_intake import LANES, register, resolve_spans, scene_template, status
from .common import repo_root


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.review_action == "register":
            report = register(root, args.lane, Path(args.file), origin=args.origin, identity=args.id,
                              dry_run=args.dry_run, request_path=Path(args.request) if args.request else None)
        elif args.review_action == "resolve-spans":
            report = resolve_spans(Path(args.file), Path(args.texts), Path(args.output))
        elif args.review_action == "scene-template":
            report = scene_template(Path(args.request), Path(args.output))
        else:
            report = status(root)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        report = {"status": "FAIL", "findings": [str(exc)], "authority_effect": "NONE"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {"PASS": 0, "FAIL": 1, "PENDING": 2}[report["status"]]


def add_commands(sub) -> None:
    parser = sub.add_parser("reviews", help="Receive review inputs without granting adoption authority")
    actions = parser.add_subparsers(dest="review_action", required=True)
    intake = actions.add_parser("register")
    intake.add_argument("lane", choices=LANES)
    intake.add_argument("file")
    intake.add_argument("--origin", required=True)
    intake.add_argument("--id")
    intake.add_argument("--dry-run", action="store_true")
    intake.add_argument("--request", help="Frozen semantic request, required for scene-reading")
    spans = actions.add_parser("resolve-spans")
    spans.add_argument("file")
    spans.add_argument("--texts", required=True, help="Anonymous public directory, or the exact scene candidate file")
    spans.add_argument("--output", required=True)
    template = actions.add_parser("scene-template")
    template.add_argument("request")
    template.add_argument("--output", required=True)
    actions.add_parser("status")
    parser.set_defaults(func=command)
