from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import evaluate_scene_text, overall_status
from .io import load_data
from .runtime import WorldState
from .validate import validate_repository


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    errors = validate_repository(root)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: repository schemas valid")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    contract = load_data(Path(args.contract))
    text = Path(args.text).read_text(encoding="utf-8")

    state = WorldState.from_repo(root)
    precondition_findings = state.assert_contract_preconditions(contract)
    results = evaluate_scene_text(contract, text)
    if precondition_findings:
        results.insert(0, type(results[0])("preconditions", "FAIL", precondition_findings))

    payload = {
        "overall": overall_status(results),
        "results": [r.to_dict() for r in results],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["overall"] == "FAIL" else 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="rcwh")
    parser.add_argument("--root", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate")
    p_validate.set_defaults(func=cmd_validate)

    p_eval = sub.add_parser("evaluate")
    p_eval.add_argument("contract")
    p_eval.add_argument("text")
    p_eval.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
