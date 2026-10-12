"""Offline CLI adapters; registration is deliberately left to the main CLI."""
import json
from pathlib import Path

from ..backtest.study import BacktestStudy, HOLDOUT_PATH
from .common import repo_root


def command(args):
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        study = BacktestStudy(root, args.config)
        if args.backtest_action == "prepare":
            report = study.prepare(Path(args.output))
        elif args.backtest_action == "export":
            report = study.export(Path(args.output), args.records)
        elif args.backtest_action == "summary":
            bindings = json.loads(Path(args.reviews).read_bytes()) if args.reviews else []
            if not isinstance(bindings, list):
                raise ValueError("review selection must be an array of raw-bound review references")
            report = study.summary(args.records, args.export_root, bindings)
        else:
            report = study.check()
    except (KeyError, OSError, TypeError, ValueError, ImportError) as exc:
        report = {"status": "FAIL", "findings": [str(exc)], "controlled_workflow_effect": "NOT_ESTIMABLE", "authority_effect": "NONE"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {"PASS": 0, "FAIL": 1, "PENDING": 2}[report["status"]]


def add_commands(sub):
    parser = sub.add_parser("backtest", help="Prepare and inspect given-plan holdout research; no generation or authority")
    actions = parser.add_subparsers(dest="backtest_action", required=True)
    for action in ("prepare", "check", "export", "summary"):
        child = actions.add_parser(action)
        child.add_argument("--config", default=HOLDOUT_PATH)
        if action in {"prepare", "export"}:
            child.add_argument("--output", required=True)
        if action in {"export", "summary"}:
            child.add_argument("--records", required=action == "export", help="Repository-relative frozen backtest run registry")
        if action == "summary":
            child.add_argument("--export-root")
            child.add_argument("--reviews", help="JSON array of bound independent review receipts")
    parser.set_defaults(func=command)
