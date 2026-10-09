from __future__ import annotations

import argparse
import json
from pathlib import Path
from ..competition import CompetitionRegistry, format_competition
from ..implementation_alignment import ImplementationAlignmentRuntime, format_implementation_alignment
from ..literary_production import LiteraryProductionRuntime, format_literary_production
from ..promotion import PromotionRegistry, format_promotion
from ..assets import AssetCatalog
from .common import repo_root


def cmd_competition(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = CompetitionRegistry.from_repo(root)
    if args.competition_id not in registry.records:
        print(f"Unknown competition: {args.competition_id}")
        return 1
    if args.review_packet:
        from ..candidate_reviews import canonical_bytes, review_packet
        try:
            prepared = review_packet(root, registry.records[args.competition_id])
            with Path(args.review_packet).open("xb") as handle:
                handle.write(canonical_bytes(prepared["packet"]))
            print(json.dumps({k: v for k, v in prepared.items() if k != "packet"}, ensure_ascii=False, indent=2))
            return 0
        except (KeyError, OSError, ValueError) as exc:
            print(json.dumps({"overall": "FAIL", "findings": [str(exc)]}, ensure_ascii=False))
            return 1
    payload = registry.evaluate_record(root, registry.records[args.competition_id])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_competition(payload))
    return 1 if payload["consistency_errors"] else 0

def cmd_literary_production(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = LiteraryProductionRuntime.from_repo(root)
    competitions = CompetitionRegistry.from_repo(root)
    try:
        kind = args.literary_production_command
        if kind == "summary":
            payload = runtime.summary()
        elif kind == "chapter":
            payload = runtime.chapter(args.chapter, competitions)
        else:
            raise KeyError(f"Unknown literary production command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_literary_production(kind, payload))
    return 0

def cmd_implementation(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = ImplementationAlignmentRuntime.from_repo(root)
    try:
        kind = args.implementation_command
        if kind == "summary":
            payload = runtime.summary()
        elif kind == "stable":
            payload = runtime.stable()
        elif kind == "chapter":
            payload = runtime.chapter(args.chapter)
        elif kind == "fact":
            payload = runtime.fact(args.key)
        elif kind == "protection":
            payload = runtime.protection(args.chapter)
        elif kind == "competition":
            payload = runtime.competition(args.chapter)
        elif kind == "trace":
            registry = AssetCatalog.from_repo(root)
            payload = runtime.trace(args.kind, args.key, registry)
        else:
            raise KeyError(f"Unknown implementation command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_implementation_alignment(kind, payload))
    return 0

def cmd_promotion(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = PromotionRegistry.from_repo(root)
    if args.promotion_id not in registry.records:
        print(f"Unknown promotion: {args.promotion_id}")
        return 1
    payload = registry.evaluate(root, args.promotion_id)
    if args.output and payload["overall"] in {"PASS", "PENDING"}:
        try:
            raw = registry.build_candidate(root, args.promotion_id)
            with Path(args.output).open("xb") as handle:
                handle.write(raw)
            payload["exported_to"] = str(args.output)
        except (OSError, ValueError) as exc:
            payload["overall"] = "FAIL"
            payload["findings"].append(str(exc))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_promotion(payload))
    return {"PASS": 0, "PENDING": 2, "FAIL": 1}[payload["overall"]]


def add_commands(sub) -> None:
    p_comp = sub.add_parser("competition")
    p_comp.add_argument("competition_id")
    p_comp.add_argument("--review-packet", help="Export a bound anonymous packet to a new file; requires review_protocol")
    p_comp.add_argument("--json", action="store_true")
    p_comp.set_defaults(func=cmd_competition)

    p_promotion = sub.add_parser("promotion")
    p_promotion.add_argument("promotion_id")
    p_promotion.add_argument("--output", help="Write the assembled research candidate to a new file, including when reviews are pending")
    p_promotion.add_argument("--json", action="store_true")
    p_promotion.set_defaults(func=cmd_promotion)

    p_lit_prod = sub.add_parser("literary-production")
    lit_prod_sub = p_lit_prod.add_subparsers(
        dest="literary_production_command", required=True
    )
    p = lit_prod_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_production)
    p = lit_prod_sub.add_parser("chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_production)

    p_impl = sub.add_parser("implementation")
    impl_sub = p_impl.add_subparsers(dest="implementation_command", required=True)
    p = impl_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
    p = impl_sub.add_parser("stable")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
    p = impl_sub.add_parser("chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
    p = impl_sub.add_parser("fact")
    p.add_argument("key")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
    p = impl_sub.add_parser("protection")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
    p = impl_sub.add_parser("competition")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
    p = impl_sub.add_parser("trace")
    p.add_argument("kind", choices=["source", "fact", "chapter", "protection"])
    p.add_argument("key")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_implementation)
