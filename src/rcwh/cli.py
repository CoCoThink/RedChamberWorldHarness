from __future__ import annotations

import argparse
import json
from pathlib import Path

from .competition import CompetitionRegistry, format_competition
from .evaluate import evaluate_scene_text, overall_status
from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry, format_mechanism
from .io import load_data
from .literals import LiteralRegistry, format_literal
from .literary_eval import evaluate_literary_candidate, format_literary_evaluation
from .open_interfaces import OpenInterfaceRegistry, format_open_interface
from .plocks import LiteraryProtectionRegistry, format_plock
from .regression import format_regression, run_r4_evidence_regression
from .promotion import PromotionRegistry, format_promotion
from .registry import (
    MigrationRegistry,
    format_current_authority,
    format_registry_document,
    format_registry_package,
)
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
    print("PASS: R4 Evidence Core frozen; Literary Harness and competition ledger valid")
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


def cmd_plock(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = LiteraryProtectionRegistry.from_repo(root)
    try:
        lock = registry.describe(args.lock_id)
    except KeyError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(lock, ensure_ascii=False, indent=2))
    else:
        print(format_plock(lock))
    return 0


def cmd_literary_evaluate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    payloads = []
    worst = 0
    order = {
        "READY_FOR_BLIND_READ": 0,
        "REPLACEMENT_CASE": 1,
        "REJECT_BEFORE_BLIND_READ": 2,
        "INFRASTRUCTURE_BLOCKED": 3,
    }
    for text_path in args.text:
        path = Path(text_path)
        payload = evaluate_literary_candidate(
            root,
            args.plock_id,
            path.read_text(encoding="utf-8"),
            candidate_name=path.name,
        )
        payloads.append(payload)
        worst = max(worst, order[payload["machine_status"]])

    if args.json:
        print(json.dumps(payloads, ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(format_literary_evaluation(x) for x in payloads))

    # A ready candidate still requires human review, but exits 0 so it may proceed.
    # Replacement cases exit 2; explicit blockers / infrastructure failures exit 1.
    if worst >= 2:
        return 1
    if worst == 1:
        return 2
    return 0


def cmd_competition(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = CompetitionRegistry.from_repo(root)
    if args.competition_id not in registry.records:
        print(f"Unknown competition: {args.competition_id}")
        return 1
    payload = registry.evaluate_record(root, registry.records[args.competition_id])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_competition(payload))
    return 1 if payload["consistency_errors"] else 0


def cmd_registry(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = MigrationRegistry.from_repo(root)
    try:
        if args.registry_command == "package":
            payload = registry.package(args.key)
            rendered = format_registry_package(payload)
        elif args.registry_command == "document":
            payload = registry.document(args.key)
            rendered = format_registry_document(payload)
        elif args.registry_command == "hash":
            payload = registry.content_hash(args.key)
            rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        elif args.registry_command == "current":
            payload = registry.current_summary()
            rendered = format_current_authority(payload)
        else:
            raise KeyError(f"Unknown registry command: {args.registry_command}")
    except KeyError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(rendered)
    return 0


def cmd_promotion(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = PromotionRegistry.from_repo(root)
    if args.promotion_id not in registry.records:
        print(f"Unknown promotion: {args.promotion_id}")
        return 1
    payload = registry.evaluate(root, args.promotion_id)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_promotion(payload))
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

    p_plock = sub.add_parser("plock")
    p_plock.add_argument("lock_id")
    p_plock.add_argument("--json", action="store_true")
    p_plock.set_defaults(func=cmd_plock)

    p_lit_eval = sub.add_parser("literary-evaluate")
    p_lit_eval.add_argument("plock_id")
    p_lit_eval.add_argument("text", nargs="+")
    p_lit_eval.add_argument("--json", action="store_true")
    p_lit_eval.set_defaults(func=cmd_literary_evaluate)

    p_comp = sub.add_parser("competition")
    p_comp.add_argument("competition_id")
    p_comp.add_argument("--json", action="store_true")
    p_comp.set_defaults(func=cmd_competition)

    p_promotion = sub.add_parser("promotion")
    p_promotion.add_argument("promotion_id")
    p_promotion.add_argument("--json", action="store_true")
    p_promotion.set_defaults(func=cmd_promotion)

    p_registry = sub.add_parser("registry")
    registry_sub = p_registry.add_subparsers(dest="registry_command", required=True)
    for name in ("package", "document", "hash"):
        p = registry_sub.add_parser(name)
        p.add_argument("key")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_registry)
    p = registry_sub.add_parser("current")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_registry)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
