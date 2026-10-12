"""Offline draft planning CLI; no mutation of registered source inputs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .common import repo_root
from ..planning.chapters import CARD_PATH, check_plans, import_cards, parse_chapters
from ..planning.hints import threads_report
from ..planning.books import compare_books


def cmd_plan(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if getattr(args, "root", None) else repo_root()
    try:
        if args.plan_command == "import-cards":
            payload = import_cards(root, source_path=args.source, output=args.output)
        elif args.plan_command == "check":
            chapters = parse_chapters(args.chapters) if args.chapters else None
            payload = check_plans(root, chapters, directory=args.directory,
                                  contracts_directory=getattr(args, "contracts_directory", None))
        elif args.plan_command == "threads":
            payload = threads_report(root, directory=args.directory)
        else:
            payload = compare_books(root, args.books or None)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc), "authority_effect": "NONE"}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("status") == "FAIL" else 0


def add_commands(sub) -> None:
    plan = sub.add_parser("plan", help="Offline draft planning and declaration checks")
    commands = plan.add_subparsers(dest="plan_command", required=True)
    p = commands.add_parser("import-cards")
    p.add_argument("--source", default=CARD_PATH)
    p.add_argument("--output", default="data/planning")
    p = commands.add_parser("check")
    p.add_argument("--chapters", help="positive chapter range/list, e.g. 85-87,89")
    p.add_argument("--directory", help="repository-relative chapter plan directory")
    p.add_argument("--contracts-directory", help="explicit versioned agent overlay selection under data/planning/contracts")
    p = commands.add_parser("threads")
    p.add_argument("--directory")
    p = commands.add_parser("compare-books")
    p.add_argument("books", nargs="*", help="repository-relative book plan paths")
    for p in commands.choices.values():
        p.add_argument("--json", action="store_true", help="JSON output (always enabled)")
        p.set_defaults(func=cmd_plan)
