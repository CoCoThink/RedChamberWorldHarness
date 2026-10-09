from __future__ import annotations

import argparse
import json
from pathlib import Path
from ..blind_microdraft_review import BlindMicrodraftReviewRuntime
from ..literary_ecology import LiteraryEcologyRuntime
from ..literary_stress import ScenarioLiteraryStressRuntime
from ..literary_suite import LiteraryEvaluatorSuite
from ..microdraft import ControlledMicrodraftRuntime
from ..narrative_discourse import NarrativeDiscourseRuntime
from ..revision_ablation import CrossRouteRevisionAblationRuntime
from .common import repo_root


def cmd_literary_stress(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = ScenarioLiteraryStressRuntime.from_repo(root)
    ecology = LiteraryEcologyRuntime.from_repo(root)
    try:
        kind = args.literary_stress_command
        if kind == "summary":
            payload = runtime.evaluate_all(ecology)
        elif kind == "scenario":
            payload = runtime.evaluate(args.key, ecology)
        elif kind == "compare":
            payload = runtime.compare(args.left, args.right, ecology)
        else:
            raise KeyError(f"Unknown literary-stress command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if kind == "scenario":
        return 0 if payload["status"] == "STRESS_CONTRACT_READY" else 1
    if kind == "summary":
        return 0 if payload["status"] == "PASS" else 1
    return 0

def cmd_narrative_discourse(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = NarrativeDiscourseRuntime.from_repo(root)
    stress = ScenarioLiteraryStressRuntime.from_repo(root)
    try:
        kind = args.narrative_discourse_command
        if kind == "summary":
            payload = runtime.evaluate_all(stress)
        elif kind == "scenario":
            payload = runtime.evaluate(args.key, stress)
        elif kind == "card":
            payload = runtime.card(args.scenario, args.probe, stress)
        elif kind == "compare":
            payload = runtime.compare(args.left, args.right, stress)
        else:
            raise KeyError(f"Unknown narrative-discourse command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if kind == "summary":
        return 0 if payload["status"] == "PASS" else 1
    if kind == "scenario":
        return 0 if payload["status"] == "DISCOURSE_RUNTIME_READY" else 1
    return 0

def cmd_microdraft(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = ControlledMicrodraftRuntime.from_repo(root)
    discourse = NarrativeDiscourseRuntime.from_repo(root)
    stress = ScenarioLiteraryStressRuntime.from_repo(root)
    suite = LiteraryEvaluatorSuite.from_repo(root)
    try:
        kind = args.microdraft_command
        if kind == "summary":
            payload = runtime.evaluate_all(discourse, stress, suite)
        elif kind == "screen":
            payload = runtime.screen(args.token, discourse, stress, suite)
        elif kind == "cell":
            payload = runtime.cell_packet(args.cell)
        else:
            raise KeyError(f"Unknown microdraft command: {kind}")
    except (KeyError, FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if kind == "summary":
        return 0 if payload["status"] == "PASS" else 1
    if kind == "screen":
        return 0 if payload["status"] == "READY_FOR_BLIND_MICRODRAFT_REVIEW" else 1
    return 0

def cmd_blind_microdraft_review(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = BlindMicrodraftReviewRuntime.from_repo(root)
    try:
        kind = args.blind_microdraft_review_command
        if kind == "summary":
            payload = runtime.summary()
        elif kind == "scenario":
            payload = runtime.scenario(args.key)
        elif kind == "token":
            payload = runtime.token(args.token)
        else:
            raise KeyError(f"Unknown blind-microdraft-review command: {kind}")
    except (KeyError, FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

def cmd_revision_ablation(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = CrossRouteRevisionAblationRuntime.from_repo(root)
    p6 = ControlledMicrodraftRuntime.from_repo(root)
    p7 = BlindMicrodraftReviewRuntime.from_repo(root)
    discourse = NarrativeDiscourseRuntime.from_repo(root)
    stress = ScenarioLiteraryStressRuntime.from_repo(root)
    suite = LiteraryEvaluatorSuite.from_repo(root)
    try:
        kind = args.revision_ablation_command
        if kind == "summary":
            payload = runtime.evaluate_all(p6, p7, discourse, stress, suite)
        elif kind == "pair":
            payload = runtime.pair(args.token, p6, p7, discourse, stress, suite)
        else:
            raise KeyError(f"Unknown revision-ablation command: {kind}")
    except (KeyError, FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if kind == "summary":
        return 0 if payload["status"] == "PASS" else 1
    if kind == "pair":
        return 0 if payload["status"] == "ABLATION_READY" else 1
    return 0


def add_commands(sub) -> None:
    p_stress = sub.add_parser("literary-stress")
    stress_sub = p_stress.add_subparsers(dest="literary_stress_command", required=True)
    p = stress_sub.add_parser("summary")
    p.set_defaults(func=cmd_literary_stress)
    p = stress_sub.add_parser("scenario")
    p.add_argument("key")
    p.set_defaults(func=cmd_literary_stress)
    p = stress_sub.add_parser("compare")
    p.add_argument("left")
    p.add_argument("right")
    p.set_defaults(func=cmd_literary_stress)

    p_discourse = sub.add_parser("narrative-discourse")
    discourse_sub = p_discourse.add_subparsers(
        dest="narrative_discourse_command", required=True
    )
    p = discourse_sub.add_parser("summary")
    p.set_defaults(func=cmd_narrative_discourse)
    p = discourse_sub.add_parser("scenario")
    p.add_argument("key")
    p.set_defaults(func=cmd_narrative_discourse)
    p = discourse_sub.add_parser("card")
    p.add_argument("scenario")
    p.add_argument("probe")
    p.set_defaults(func=cmd_narrative_discourse)
    p = discourse_sub.add_parser("compare")
    p.add_argument("left")
    p.add_argument("right")
    p.set_defaults(func=cmd_narrative_discourse)

    p_micro = sub.add_parser("microdraft")
    micro_sub = p_micro.add_subparsers(dest="microdraft_command", required=True)
    p = micro_sub.add_parser("summary")
    p.set_defaults(func=cmd_microdraft)
    p = micro_sub.add_parser("screen")
    p.add_argument("token")
    p.set_defaults(func=cmd_microdraft)
    p = micro_sub.add_parser("cell")
    p.add_argument("cell")
    p.set_defaults(func=cmd_microdraft)

    p_p7 = sub.add_parser("blind-microdraft-review")
    p7_sub = p_p7.add_subparsers(
        dest="blind_microdraft_review_command", required=True
    )
    p = p7_sub.add_parser("summary")
    p.set_defaults(func=cmd_blind_microdraft_review)
    p = p7_sub.add_parser("scenario")
    p.add_argument("key")
    p.set_defaults(func=cmd_blind_microdraft_review)
    p = p7_sub.add_parser("token")
    p.add_argument("token")
    p.set_defaults(func=cmd_blind_microdraft_review)

    p_p8 = sub.add_parser("revision-ablation")
    p8_sub = p_p8.add_subparsers(
        dest="revision_ablation_command", required=True
    )
    p = p8_sub.add_parser("summary")
    p.set_defaults(func=cmd_revision_ablation)
    p = p8_sub.add_parser("pair")
    p.add_argument("token")
    p.set_defaults(func=cmd_revision_ablation)
