"""Consecutive trial preparation, author execution and comparative reading."""
import json
from pathlib import Path
import shlex

from ..candidate_reviews import canonical_bytes, digest
from ..evaluation.comparison import comparative_reviews
from ..evaluation.pilot import PilotStudy
from ..io import load_data
from .common import repo_root


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        study = PilotStudy(root)
        if args.pilot_action == "summary":
            payload = study.summary()
        elif args.pilot_action == "export":
            payload = study.export(Path(args.destination))
        elif args.pilot_action == "reviews":
            payload = comparative_reviews(Path(args.export_directory), load_data(Path(args.bindings)) if args.bindings else [],
                                          digest(canonical_bytes(study.context())))
        elif args.pilot_action == "prepare-author":
            request = study.author_request(args.workflow, args.route)
            with Path(args.output).open("xb") as handle:
                handle.write(canonical_bytes(request))
            payload = {"status": "PASS", "scope": "AUTHOR_REQUEST_PREPARATION", "output": args.output,
                       "input_sha256": digest(canonical_bytes(request)), "literary_acceptance": "PENDING"}
        elif getattr(args, "runner", "command") == "anthropic":
            from ..generation.tasks import prepare_task, execute_task
            from ..generation.runner import AnthropicRunner, Budget
            from ..generation.render import request_for
            request = study.author_request(args.workflow, args.route)
            budget = Budget(max_tokens=args.max_tokens, max_output_tokens=args.max_tokens,
                            max_input_bytes=args.max_input_bytes)
            if not args.execute:
                rendered = prepare_task(root, request)
                api_request = request_for(rendered, budget, args.model)
                if len(canonical_bytes(api_request)) > budget.max_input_bytes:
                    raise ValueError("author request exceeds input byte ceiling")
                payload = {"status": "PASS", "mode": "DRY_RUN",
                           "request": api_request,
                           "budget": budget.to_dict(), "literary_acceptance": "PENDING"}
            else:
                if Path(args.output).exists():
                    raise FileExistsError("refusing to overwrite author execution output")
                payload = execute_task(root, request,
                    AnthropicRunner(execute=True, network_consent=args.network_consent), budget, model=args.model)
                with Path(args.output).open("xb") as handle:
                    handle.write(canonical_bytes(payload))
        else:
            if not args.command:
                raise ValueError("command runner requires --command")
            payload = study.run_author(args.workflow, args.route, shlex.split(args.command), Path(args.output))
    except (KeyError, OSError, TypeError, ValueError, StopIteration) as exc:
        payload = {"status": "FAIL", "findings": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"FAIL": 1, "PENDING": 2, "PASS": 0}[payload["status"]]


def add_commands(sub) -> None:
    parser = sub.add_parser("pilot")
    commands = parser.add_subparsers(dest="pilot_action", required=True)
    commands.add_parser("summary")
    export = commands.add_parser("export")
    export.add_argument("destination")
    reviews = commands.add_parser("reviews")
    reviews.add_argument("export_directory")
    reviews.add_argument("--bindings", help="JSON list of bound review paths relative to the export directory")
    for action in ("prepare-author", "run-author"):
        p = commands.add_parser(action)
        p.add_argument("--route", choices=["medical", "books"], required=True)
        p.add_argument("--workflow", choices=["DIRECT_WRITING", "LEGACY_HARNESS", "IMPROVED_HARNESS"], required=True)
        p.add_argument("--output", required=True)
        if action == "run-author":
            p.add_argument("--command", help="Caller-selected stdin/stdout author program; executed without a shell")
            p.add_argument("--runner", choices=["command", "anthropic"], default="command")
            p.add_argument("--model", default="claude-fable-5-1")
            p.add_argument("--max-tokens", type=int, default=8192)
            p.add_argument("--max-input-bytes", type=int, default=1000000)
            p.add_argument("--execute", action="store_true")
            p.add_argument("--network-consent", action="store_true")
    parser.set_defaults(func=command)
