from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import evaluate_scene_text, overall_status
from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry, format_mechanism
from .io import load_data
from .literals import LiteralRegistry, format_literal
from .open_interfaces import OpenInterfaceRegistry, format_open_interface
from .regression import format_regression, run_r4_evidence_regression
from .runtime import WorldState
from .trace import format_trace
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
    print("PASS: repository schemas and full R4 Evidence Core regression valid")
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


def cmd_trace(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    graph = ProvenanceGraph.from_repo(root)
    try:
        payload = graph.trace(args.node_id)
    except KeyError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_trace(payload))
    return 0


def cmd_literal(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    graph = ProvenanceGraph.from_repo(root)
    registry = LiteralRegistry.from_repo(root)
    try:
        payload = registry.describe(args.literal_id, graph)
    except KeyError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_literal(payload))
    return 0


def cmd_mechanism(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    graph = ProvenanceGraph.from_repo(root)
    registry = HistoricalMechanismRegistry.from_repo(root)
    try:
        payload = registry.describe(args.mechanism_id, graph)
    except KeyError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_mechanism(payload))
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    graph = ProvenanceGraph.from_repo(root)
    literals = LiteralRegistry.from_repo(root)
    mechanisms = HistoricalMechanismRegistry.from_repo(root)
    registry = OpenInterfaceRegistry.from_repo(root)
    try:
        payload = registry.describe(args.interface_id, graph, literals, mechanisms)
    except KeyError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_open_interface(payload))
    return 0


def cmd_regression(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    payload = run_r4_evidence_regression(root)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_regression(payload))
    return 0 if payload["overall"] == "PASS" else 1


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

    p_trace = sub.add_parser("trace")
    p_trace.add_argument("node_id")
    p_trace.add_argument("--json", action="store_true")
    p_trace.set_defaults(func=cmd_trace)

    p_literal = sub.add_parser("literal")
    p_literal.add_argument("literal_id")
    p_literal.add_argument("--json", action="store_true")
    p_literal.set_defaults(func=cmd_literal)

    p_mechanism = sub.add_parser("mechanism")
    p_mechanism.add_argument("mechanism_id")
    p_mechanism.add_argument("--json", action="store_true")
    p_mechanism.set_defaults(func=cmd_mechanism)

    p_open = sub.add_parser("open")
    p_open.add_argument("interface_id")
    p_open.add_argument("--json", action="store_true")
    p_open.set_defaults(func=cmd_open)

    p_regression = sub.add_parser("regression")
    p_regression.add_argument("--json", action="store_true")
    p_regression.set_defaults(func=cmd_regression)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
