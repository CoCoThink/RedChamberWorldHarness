from __future__ import annotations

import argparse
import json
from pathlib import Path

from .competition import CompetitionRegistry, format_competition
from .completion import CompletionGateRuntime, format_completion
from .coverage import CoverageAuditRuntime, format_coverage
from .evaluate import evaluate_scene_text, overall_status
from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry, format_mechanism
from .hypotheses import HypothesisRuntime
from .implementation_alignment import ImplementationAlignmentRuntime, format_implementation_alignment
from .io import load_data
from .knowledge import CharacterKnowledgeRuntime, format_knowledge
from .literals import LiteralRegistry, format_literal
from .literary_eval import evaluate_literary_candidate, format_literary_evaluation
from .literary_ecology import LiteraryEcologyRuntime, format_literary_ecology
from .literary_production import LiteraryProductionRuntime, format_literary_production
from .literary_stress import ScenarioLiteraryStressRuntime
from .literary_suite import LiteraryEvaluatorSuite, format_literary_suite
from .microdraft import ControlledMicrodraftRuntime
from .mechanism_adapters import HistoricalAdapterRuntime, format_adapter
from .narrative_discourse import NarrativeDiscourseRuntime
from .open_interfaces import OpenInterfaceRegistry, format_open_interface
from .object_network import ObjectNetworkRuntime, format_object
from .pareto import ParetoEvaluationRuntime
from .plocks import LiteraryProtectionRegistry, format_plock
from .regression import format_regression, run_r4_evidence_regression
from .promotion import PromotionRegistry, format_promotion
from .prewrite import V5PrewriteRuntime, format_prewrite
from .registry import (
    MigrationRegistry,
    format_current_authority,
    format_registry_document,
    format_registry_package,
)
from .reconstruction import ReconstructionRegistry, format_reconstruction
from .runtime import WorldState
from .scenarios import ScenarioRuntime
from .scenario_replay import CounterfactualReplayRuntime
from .world import WorldRuntime, format_world
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
    print("PASS: Full Migration Completion Gate valid; R4 Evidence Core frozen; stable ACTIVE unchanged")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    contract = load_data(Path(args.contract))
    text = Path(args.text).read_text(encoding="utf-8")

    state = WorldState.from_repo(root)
    precondition_findings = state.assert_contract_preconditions(contract)
    knowledge = (
        CharacterKnowledgeRuntime.from_repo(root)
        if (root / "data" / "knowledge" / "v03_slice1.json").exists()
        else None
    )
    historical_adapters = (
        HistoricalAdapterRuntime.from_repo(root)
        if (root / "data" / "mechanism_adapters" / "v04.json").exists()
        else None
    )
    historical_mechanisms = HistoricalMechanismRegistry.from_repo(root)
    results = evaluate_scene_text(
        contract,
        text,
        knowledge_runtime=knowledge,
        mechanism_adapter_runtime=historical_adapters,
        historical_mechanisms=historical_mechanisms,
    )
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


def cmd_prewrite(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = V5PrewriteRuntime.from_repo(root)
    reconstruction = ReconstructionRegistry.from_repo(root)
    literary = LiteraryEcologyRuntime.from_repo(root)
    plocks = LiteraryProtectionRegistry.from_repo(root)
    adapters = HistoricalAdapterRuntime.from_repo(root)
    registry = MigrationRegistry.from_repo(root)
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


def cmd_literary_suite(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    suite = LiteraryEvaluatorSuite.from_repo(root)
    try:
        kind = args.literary_suite_command
        if kind == "summary":
            payload = suite.summary()
        elif kind == "prose":
            path = Path(args.text)
            payload = suite.evaluate_prose(
                path.read_text(encoding="utf-8"),
                candidate_name=path.name,
            )
        elif kind in {"poetry-screen", "poetry-blind"}:
            paths = [Path(x) for x in args.text]
            candidates = {
                label: path.read_text(encoding="utf-8")
                for label, path in zip(("A", "B", "C"), paths, strict=True)
            }
            payload = (
                suite.poetry_screen(candidates)
                if kind == "poetry-screen"
                else suite.poetry_blind_packet(candidates)
            )
        elif kind == "blind":
            competitions = CompetitionRegistry.from_repo(root)
            if args.competition_id not in competitions.records:
                raise KeyError(f"Unknown competition: {args.competition_id}")
            payload = suite.competition_blind_packet(
                competitions.records[args.competition_id]
            )
        else:
            raise KeyError(f"Unknown literary-suite command: {kind}")
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(str(exc))
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_literary_suite(kind, payload))

    if kind == "prose" and payload["status"] == "REJECT_BEFORE_BLIND_READ":
        return 1
    if kind == "poetry-screen" and payload["lane_status"].startswith("BLOCKED"):
        return 1
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


def cmd_reconstruction(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    registry = ReconstructionRegistry.from_repo(root)
    try:
        kind = args.reconstruction_command
        if kind == "summary":
            payload = registry.summary()
        elif kind == "chapter":
            payload = registry.chapter(args.key)
        elif kind == "r":
            payload = registry.r(args.key)
        elif kind == "p":
            payload = registry.p(args.key)
        elif kind == "timeline":
            payload = registry.timeline_at(args.key)
        elif kind == "state":
            payload = registry.state_at(args.key)
        elif kind == "jade":
            payload = registry.data["jade_logistics"]
        elif kind == "prison":
            payload = registry.data["prison_case"]
        elif kind == "legacy":
            payload = registry.legacy(args.key)
        elif kind == "cross":
            payload = registry.cross(args.key)
        else:
            raise KeyError(f"Unknown reconstruction command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_reconstruction(kind, payload))
    return 0


def cmd_world(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    world = WorldRuntime.from_repo(root)
    try:
        kind = args.world_command
        if kind == "summary":
            payload = world.summary()
        elif kind == "chapter":
            payload = world.chapter(args.chapter)
        elif kind == "character":
            payload = world.character_state(args.character_id, args.chapter)
        elif kind == "knowledge":
            payload = world.knowledge(args.character_id, args.chapter)
        elif kind == "location":
            payload = world.location(args.location_id)
        elif kind == "relation":
            payload = world.relation(args.relation_id, args.chapter)
        elif kind == "economy":
            payload = world.economy(args.chapter)
        else:
            raise KeyError(f"Unknown world command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_world(kind, payload))
    return 0


def cmd_object(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    objects = ObjectNetworkRuntime.from_repo(root)
    try:
        kind = args.object_command
        if kind == "summary":
            payload = objects.summary()
        elif kind == "get":
            payload = objects.snapshot(args.object_id, args.chapter)
        elif kind == "history":
            payload = objects.history(args.object_id)
        elif kind == "jade":
            payload = objects.jade(args.chapter)
        elif kind == "location":
            payload = objects.at_location(args.location, args.chapter)
        elif kind == "continuity":
            payload = objects.continuity_report()
        elif kind == "trace":
            migration_registry = MigrationRegistry.from_repo(root)
            reconstruction = ReconstructionRegistry.from_repo(root)
            payload = objects.trace(args.object_id, migration_registry, reconstruction)
        else:
            raise KeyError(f"Unknown object command: {kind}")
    except KeyError as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_object(kind, payload))
    if kind == "continuity":
        return 0 if payload["status"] == "PASS" else 1
    return 0


def cmd_literary_ecology(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    ecology = LiteraryEcologyRuntime.from_repo(root)
    try:
        kind = args.literary_ecology_command
        if kind == "summary":
            payload = ecology.summary()
        elif kind == "dimension":
            payload = ecology.dimension(args.key)
        elif kind == "voice":
            payload = ecology.voice(args.key)
        elif kind == "technique":
            payload = ecology.technique(args.key)
        elif kind == "evidence":
            payload = ecology.evidence_node(args.key)
        elif kind == "chapter":
            payload = ecology.chapter(args.chapter)
        elif kind == "qingbang":
            payload = ecology.qingbang()
        elif kind == "ten-du-yin":
            payload = ecology.ten_du_yin()
        elif kind == "xu-zhuangzi":
            payload = ecology.xu_zhuangzi()
        elif kind == "daiyu":
            payload = ecology.daiyu_interfaces()
        elif kind == "g":
            payload = ecology.g(args.key)
        elif kind == "search":
            payload = ecology.search(args.term)
        elif kind == "trace":
            registry = MigrationRegistry.from_repo(root)
            payload = ecology.trace(args.kind, args.key, registry)
        else:
            raise KeyError(f"Unknown literary-ecology command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_literary_ecology(kind, payload))
    return 0


def cmd_historical_adapter(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = HistoricalAdapterRuntime.from_repo(root)
    mechanisms = HistoricalMechanismRegistry.from_repo(root)
    try:
        kind = args.historical_adapter_command
        if kind == "summary":
            payload = runtime.summary()
        elif kind == "describe":
            payload = runtime.describe(args.adapter_id, mechanisms)
        elif kind == "scene":
            contract = load_data(Path(args.contract))
            text_value = Path(args.text).read_text(encoding="utf-8")
            payload = runtime.scene_status(contract, text_value, mechanisms)
        else:
            raise KeyError(f"Unknown historical-adapter command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_adapter(kind, payload))
    if kind == "scene":
        return 0 if payload["status"] == "PASS" else 1
    return 0


def cmd_knowledge(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    runtime = CharacterKnowledgeRuntime.from_repo(root)
    try:
        kind = args.knowledge_command
        if kind == "summary":
            payload = runtime.summary()
        elif kind == "scene":
            payload = runtime.scene(args.scene_id, args.checkpoint)
        elif kind == "character":
            payload = runtime.character(args.scene_id, args.character_id, args.checkpoint)
        elif kind == "voice":
            payload = runtime.voice(args.character_id)
        elif kind == "mask":
            text_value = Path(args.text).read_text(encoding="utf-8")
            payload = runtime.mask(args.character_id, text_value)
        elif kind == "guard":
            contract = load_data(Path(args.contract))
            text_value = Path(args.text).read_text(encoding="utf-8")
            payload = runtime.text_guard(contract["id"], contract, text_value)
        else:
            raise KeyError(f"Unknown knowledge command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_knowledge(kind, payload))
    if kind == "guard":
        return 0 if payload["status"] == "PASS" else 1
    if kind == "mask" and payload["status"] == "FAIL_FORBIDDEN_VOICE":
        return 1
    return 0


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
        elif kind == "quarantine":
            payload = runtime.quarantine()
        else:
            raise KeyError(f"Unknown literary production command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_literary_production(kind, payload))
    if kind == "quarantine":
        return 0 if payload["status"] == "PASS" else 1
    return 0


def cmd_completion(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    gate = CompletionGateRuntime.from_repo(root)
    registry = MigrationRegistry.from_repo(root)
    coverage = CoverageAuditRuntime.from_repo(root)
    graph = ProvenanceGraph.from_repo(root)
    try:
        kind = args.completion_command
        if kind == "summary":
            payload = gate.state
        elif kind == "traceability":
            payload = gate.traceability(registry, coverage, graph)
        elif kind == "gate":
            reconstruction = ReconstructionRegistry.from_repo(root)
            world = WorldRuntime.from_repo(root)
            objects = ObjectNetworkRuntime.from_repo(root)
            literary = LiteraryEcologyRuntime.from_repo(root)
            implementation = ImplementationAlignmentRuntime.from_repo(root)
            literals = LiteralRegistry.from_repo(root)
            mechanisms = HistoricalMechanismRegistry.from_repo(root)
            opens = OpenInterfaceRegistry.from_repo(root)
            plocks = LiteraryProtectionRegistry.from_repo(root)
            competitions = CompetitionRegistry.from_repo(root)
            promotions = PromotionRegistry.from_repo(root)
            evidence = run_r4_evidence_regression(root)
            payload = gate.evaluate(
                registry, coverage, reconstruction, world, objects, literary,
                implementation, graph, literals, mechanisms, opens, plocks,
                competitions, promotions, evidence
            )
        else:
            raise KeyError(f"Unknown completion command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_completion(kind, payload))
    if kind == "gate":
        return 0 if payload["overall"] == "PASS" else 1
    if kind == "traceability":
        return 0 if payload["status"] == "PASS" else 1
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    coverage = CoverageAuditRuntime.from_repo(root)
    registry = MigrationRegistry.from_repo(root)
    try:
        kind = args.coverage_command
        if kind == "summary":
            payload = coverage.summary(registry)
        elif kind == "document":
            payload = coverage.document(args.key, registry)
        elif kind == "target":
            payload = coverage.target(args.key)
        elif kind == "layer":
            payload = coverage.layer(args.key)
        elif kind == "gaps":
            payload = coverage.gaps()
        elif kind == "regression":
            reconstruction = ReconstructionRegistry.from_repo(root)
            world = WorldRuntime.from_repo(root)
            objects = ObjectNetworkRuntime.from_repo(root)
            literary = LiteraryEcologyRuntime.from_repo(root)
            implementation = ImplementationAlignmentRuntime.from_repo(root)
            evidence = run_r4_evidence_regression(root)
            payload = coverage.regression(
                registry,
                reconstruction,
                world,
                objects,
                literary,
                implementation,
                evidence,
            )
        else:
            raise KeyError(f"Unknown coverage command: {kind}")
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_coverage(kind, payload))
    if kind == "regression":
        return 0 if payload["overall"] == "PASS" else 1
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
            registry = MigrationRegistry.from_repo(root)
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

    p_lit_suite = sub.add_parser("literary-suite")
    lit_suite_sub = p_lit_suite.add_subparsers(
        dest="literary_suite_command", required=True
    )
    p = lit_suite_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_suite)
    p = lit_suite_sub.add_parser("prose")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_suite)
    for name in ("poetry-screen", "poetry-blind"):
        p = lit_suite_sub.add_parser(name)
        p.add_argument("text", nargs=3)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_literary_suite)
    p = lit_suite_sub.add_parser("blind")
    p.add_argument("competition_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_suite)

    p_comp = sub.add_parser("competition")
    p_comp.add_argument("competition_id")
    p_comp.add_argument("--json", action="store_true")
    p_comp.set_defaults(func=cmd_competition)

    p_promotion = sub.add_parser("promotion")
    p_promotion.add_argument("promotion_id")
    p_promotion.add_argument("--json", action="store_true")
    p_promotion.set_defaults(func=cmd_promotion)

    p_recon = sub.add_parser("reconstruction")
    recon_sub = p_recon.add_subparsers(dest="reconstruction_command", required=True)
    p = recon_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_reconstruction)
    for name in ("chapter", "timeline", "state"):
        p = recon_sub.add_parser(name)
        p.add_argument("key", type=int)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_reconstruction)
    for name in ("r", "p", "legacy", "cross"):
        p = recon_sub.add_parser(name)
        p.add_argument("key")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_reconstruction)
    for name in ("jade", "prison"):
        p = recon_sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_reconstruction)

    p_world = sub.add_parser("world")
    world_sub = p_world.add_subparsers(dest="world_command", required=True)
    p = world_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("character")
    p.add_argument("character_id")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("knowledge")
    p.add_argument("character_id")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("location")
    p.add_argument("location_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("relation")
    p.add_argument("relation_id")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)
    p = world_sub.add_parser("economy")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_world)

    p_lit_ecology = sub.add_parser("literary-ecology")
    lit_ecology_sub = p_lit_ecology.add_subparsers(
        dest="literary_ecology_command", required=True
    )
    p = lit_ecology_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)
    for name in ("dimension", "voice", "technique", "evidence", "g"):
        p = lit_ecology_sub.add_parser(name)
        p.add_argument("key")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_literary_ecology)
    p = lit_ecology_sub.add_parser("chapter")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)
    for name in ("qingbang", "ten-du-yin", "xu-zhuangzi", "daiyu"):
        p = lit_ecology_sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_literary_ecology)
    p = lit_ecology_sub.add_parser("search")
    p.add_argument("term")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)
    p = lit_ecology_sub.add_parser("trace")
    p.add_argument(
        "kind",
        choices=[
            "dimension", "voice", "technique", "evidence", "g", "chapter",
            "qingbang", "ten_du_yin", "xu_zhuangzi"
        ],
    )
    p.add_argument("key")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_ecology)

    p_hist_adapter = sub.add_parser("historical-adapter")
    hist_adapter_sub = p_hist_adapter.add_subparsers(
        dest="historical_adapter_command", required=True
    )
    p = hist_adapter_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_historical_adapter)
    p = hist_adapter_sub.add_parser("describe")
    p.add_argument("adapter_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_historical_adapter)
    p = hist_adapter_sub.add_parser("scene")
    p.add_argument("contract")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_historical_adapter)

    p_knowledge = sub.add_parser("knowledge")
    knowledge_sub = p_knowledge.add_subparsers(dest="knowledge_command", required=True)
    p = knowledge_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_knowledge)
    p = knowledge_sub.add_parser("scene")
    p.add_argument("scene_id")
    p.add_argument("--checkpoint")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_knowledge)
    p = knowledge_sub.add_parser("character")
    p.add_argument("scene_id")
    p.add_argument("character_id")
    p.add_argument("--checkpoint")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_knowledge)
    p = knowledge_sub.add_parser("voice")
    p.add_argument("character_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_knowledge)
    p = knowledge_sub.add_parser("mask")
    p.add_argument("character_id")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_knowledge)
    p = knowledge_sub.add_parser("guard")
    p.add_argument("contract")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_knowledge)

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
    p = lit_prod_sub.add_parser("quarantine")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_production)

    p_completion = sub.add_parser("completion")
    completion_sub = p_completion.add_subparsers(dest="completion_command", required=True)
    for name in ("summary", "traceability", "gate"):
        p = completion_sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_completion)

    p_coverage = sub.add_parser("coverage")
    coverage_sub = p_coverage.add_subparsers(dest="coverage_command", required=True)
    p = coverage_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_coverage)
    for name in ("document", "target", "layer"):
        p = coverage_sub.add_parser(name)
        p.add_argument("key")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_coverage)
    for name in ("gaps", "regression"):
        p = coverage_sub.add_parser(name)
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_coverage)

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

    p_object = sub.add_parser("object")
    object_sub = p_object.add_subparsers(dest="object_command", required=True)
    p = object_sub.add_parser("summary")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("get")
    p.add_argument("object_id")
    p.add_argument("--chapter", type=int, default=100)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("history")
    p.add_argument("object_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("jade")
    p.add_argument("--chapter", type=int, default=100)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("location")
    p.add_argument("location")
    p.add_argument("chapter", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("continuity")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)
    p = object_sub.add_parser("trace")
    p.add_argument("object_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_object)

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
