"""Session-declared holdout research, separate from provider-qualified runs."""
import json
from pathlib import Path

from ..backtest.session import SessionBacktest
from .common import repo_root


def command(args) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    study = SessionBacktest(root)
    if args.session_action == "prepare":
        payload = study.prepare(args.destination, characters=args.characters,
                                coordinator_session_id=args.coordinator_session_id)
    elif args.session_action == "register":
        payload = study.register(args.text, args.packet, session_id=args.session_id,
                                 session_model_label=args.session_model_label)
    elif args.session_action == "prepare-revision":
        payload = study.prepare_revision(args.destination, args.parent, args.feedback)
    elif args.session_action == "registry":
        payload = study.registry(args.destination, args.rounds)
    elif args.session_action == "export":
        payload = study.export(args.destination, args.registry,
                               coordinator_session_id=args.coordinator_session_id)
    else:
        payload = study.summary(args.registry, mapping_path=args.mapping)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"FAIL": 1, "PENDING": 2, "PASS": 0}[payload["status"]]


def add_commands(sub) -> None:
    parser = sub.add_parser("session-backtest")
    commands = parser.add_subparsers(dest="session_action", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("destination")
    prepare.add_argument("--characters", type=int, default=6000)
    prepare.add_argument("--coordinator-session-id", required=True)
    register = commands.add_parser("register")
    register.add_argument("text")
    register.add_argument("--packet", required=True)
    register.add_argument("--session-id", required=True)
    register.add_argument("--session-model-label", required=True)
    revise = commands.add_parser("prepare-revision")
    revise.add_argument("destination")
    revise.add_argument("--parent", required=True)
    revise.add_argument("--feedback", required=True)
    registry = commands.add_parser("registry")
    registry.add_argument("destination")
    registry.add_argument("rounds", nargs="+")
    export = commands.add_parser("export")
    export.add_argument("destination")
    export.add_argument("--registry", required=True)
    export.add_argument("--coordinator-session-id", required=True)
    summary = commands.add_parser("summary")
    summary.add_argument("registry")
    summary.add_argument("--mapping")
    parser.set_defaults(func=command)
