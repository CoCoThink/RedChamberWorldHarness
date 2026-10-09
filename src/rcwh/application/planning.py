from __future__ import annotations

import argparse
import json
from pathlib import Path
from ..hypotheses import HypothesisRuntime
from ..literary_ecology import LiteraryEcologyRuntime
from ..mechanism_adapters import HistoricalAdapterRuntime
from ..open_interfaces import OpenInterfaceRegistry
from ..pareto import ParetoEvaluationRuntime
from ..plocks import LiteraryProtectionRegistry
from ..prewrite import V5PrewriteRuntime, format_prewrite
from ..assets import AssetCatalog
from ..reconstruction import ReconstructionRegistry
from ..scenarios import ScenarioRuntime
from ..scenario_replay import CounterfactualReplayRuntime
from ..world import WorldRuntime
from .common import repo_root


def cmd_hypothesis(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = HypothesisRuntime.from_repo(root)
    try:
        kind = args.hypothesis_command
        if kind == "list":
            payload = runtime.summary()
            payload["ids"] = sorted(runtime.hypotheses)
        elif kind == "get":
            payload = runtime.get(args.key)
        elif kind == "alternatives":
            payload = {
                "open_id": args.key,
                "alternatives": runtime.alternatives(args.key),
            }
        else:
            raise KeyError(f"Unknown hypothesis command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

def cmd_scenario(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    hypotheses = HypothesisRuntime.from_repo(root)
    runtime = ScenarioRuntime.from_repo(root)
    opens = OpenInterfaceRegistry.from_repo(root)
    replay = CounterfactualReplayRuntime.from_repo(root)
    world = WorldRuntime.from_repo(root)
    try:
        kind = args.scenario_command
        if kind == "generate":
            payload = runtime.generate()
        elif kind == "validate":
            scenario = runtime.get(args.key)
            findings = runtime.validate_bundle(scenario, hypotheses, opens)
            payload = {
                "scenario_id": args.key,
                "status": "PASS" if not findings else "FAIL",
                "findings": findings,
            }
        elif kind == "compare":
            payload = runtime.compare(args.keys, hypotheses)
        elif kind == "frontier":
            payload = replay.frontier(runtime, world)
        elif kind == "replay":
            payload = replay.evaluate(args.key, runtime, world, args.chapter)
        elif kind == "replay-all":
            payload = replay.evaluate_all(runtime, world)
        elif kind == "conflicts":
            result = replay.evaluate(args.key, runtime, world)
            payload = {
                "scenario_id": args.key,
                "status": result["status"],
                "blockers": result["blockers"],
                "pressures": result["pressures"],
            }
        elif kind == "summary":
            payload = runtime.summary(hypotheses)
        else:
            raise KeyError(f"Unknown scenario command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if kind == "validate":
        return 0 if payload["status"] == "PASS" else 1
    if kind == "replay-all":
        return 0 if payload["status"] == "PASS" else 1
    if kind == "replay":
        return 0 if payload["status"] != "REPLAY_BLOCKED" else 1
    if kind == "conflicts":
        return 0 if not payload["blockers"] else 1
    return 0

def cmd_pareto(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    hypotheses = HypothesisRuntime.from_repo(root)
    scenarios = ScenarioRuntime.from_repo(root)
    replay = CounterfactualReplayRuntime.from_repo(root)
    world = WorldRuntime.from_repo(root)
    pareto = ParetoEvaluationRuntime.from_repo(root)
    try:
        kind = args.pareto_command
        if kind == "summary":
            payload = pareto.summary(hypotheses, scenarios, replay, world)
        elif kind == "scenario":
            payload = pareto.evaluate_scenario(
                args.key, hypotheses, scenarios, replay, world
            )
        elif kind == "frontier":
            payload = pareto.frontier(hypotheses, scenarios, replay, world)
        elif kind == "compare":
            payload = pareto.compare(
                args.left, args.right, hypotheses, scenarios, replay, world
            )
        else:
            raise KeyError(f"Unknown pareto command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if kind == "scenario":
        return 0 if payload["status"] == "PARETO_ELIGIBLE" else 1
    return 0

def cmd_prewrite(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = V5PrewriteRuntime.from_repo(root)
    reconstruction = ReconstructionRegistry.from_repo(root)
    literary = LiteraryEcologyRuntime.from_repo(root)
    plocks = LiteraryProtectionRegistry.from_repo(root)
    adapters = HistoricalAdapterRuntime.from_repo(root)
    registry = AssetCatalog.from_repo(root)
    try:
        kind = args.prewrite_command
        if kind == "summary":
            payload = runtime.summary()
        elif kind == "corpus":
            payload = runtime.corpus(args.profile_id)
        elif kind == "gap":
            payload = runtime.gap(args.chapter)
        elif kind == "scenes":
            payload = runtime.scenes(args.chapter)
        elif kind == "step":
            payload = runtime.step(args.step, args.chapter, literary, adapters)
        elif kind == "contract":
            payload = runtime.contract(
                args.chapter, reconstruction, literary, plocks, adapters, registry
            )
        elif kind == "stage":
            payload = runtime.staging_packet(
                args.chapter, reconstruction, literary, plocks, adapters, registry
            )
        else:
            raise KeyError(f"Unknown prewrite command: {kind}")
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_prewrite(kind, payload))
    return 0


def add_commands(sub) -> None:
    p_hyp = sub.add_parser("hypothesis")
    hyp_sub = p_hyp.add_subparsers(dest="hypothesis_command", required=True)
    p = hyp_sub.add_parser("list")
    p.set_defaults(func=cmd_hypothesis)
    p = hyp_sub.add_parser("get")
    p.add_argument("key")
    p.set_defaults(func=cmd_hypothesis)
    p = hyp_sub.add_parser("alternatives")
    p.add_argument("key")
    p.set_defaults(func=cmd_hypothesis)

    p_scenario = sub.add_parser("scenario")
    scenario_sub = p_scenario.add_subparsers(dest="scenario_command", required=True)
    p = scenario_sub.add_parser("summary")
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("generate")
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("validate")
    p.add_argument("key")
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("compare")
    p.add_argument("keys", nargs="+")
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("frontier")
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("replay")
    p.add_argument("key")
    p.add_argument("--chapter", type=int)
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("replay-all")
    p.set_defaults(func=cmd_scenario)
    p = scenario_sub.add_parser("conflicts")
    p.add_argument("key")
    p.set_defaults(func=cmd_scenario)

    p_pareto = sub.add_parser("pareto")
    pareto_sub = p_pareto.add_subparsers(dest="pareto_command", required=True)
    p = pareto_sub.add_parser("summary")
    p.set_defaults(func=cmd_pareto)
    p = pareto_sub.add_parser("scenario")
    p.add_argument("key")
    p.set_defaults(func=cmd_pareto)
    p = pareto_sub.add_parser("frontier")
    p.set_defaults(func=cmd_pareto)
    p = pareto_sub.add_parser("compare")
    p.add_argument("left")
    p.add_argument("right")
    p.set_defaults(func=cmd_pareto)

    p_prewrite = sub.add_parser("prewrite")
    prewrite_sub = p_prewrite.add_subparsers(
        dest="prewrite_command", required=True
    )
    p = prewrite_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
    p = prewrite_sub.add_parser("corpus")
    p.add_argument("profile_id", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
    p = prewrite_sub.add_parser("gap")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
    p = prewrite_sub.add_parser("scenes")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
    p = prewrite_sub.add_parser("step")
    p.add_argument("step", type=int)
    p.add_argument("--chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
    p = prewrite_sub.add_parser("contract")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
    p = prewrite_sub.add_parser("stage")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prewrite)
