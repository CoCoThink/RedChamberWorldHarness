from __future__ import annotations

import argparse
import json
from pathlib import Path
from ..graph import ProvenanceGraph
from ..history import HistoricalMechanismRegistry, format_mechanism
from ..literals import LiteralRegistry, format_literal
from ..open_interfaces import OpenInterfaceRegistry, format_open_interface
from ..plocks import LiteraryProtectionRegistry, format_plock
from ..regression import format_regression, run_r4_evidence_regression
from ..trace import format_trace
from ..validate import validate_repository
from .common import repo_root


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    errors = validate_repository(root)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: repository integrity valid; check self-contained profiles for source closure")
    return 0

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


def add_commands(sub) -> None:
    p_validate = sub.add_parser("validate")
    p_validate.set_defaults(func=cmd_validate)

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
