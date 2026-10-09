from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from ..competition import CompetitionRegistry
from ..evaluate import evaluate_scene_text, overall_status
from ..history import HistoricalMechanismRegistry
from ..io import load_data
from ..knowledge import CharacterKnowledgeRuntime, format_knowledge
from ..literary_eval import evaluate_literary_candidate, format_literary_evaluation
from ..literary_suite import LiteraryEvaluatorSuite, format_literary_suite
from ..mechanism_adapters import HistoricalAdapterRuntime, format_adapter
from .common import repo_root


def cmd_evaluate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else repo_root()
    contract = load_data(Path(args.contract))
    text = Path(args.text).read_bytes().decode("utf-8")

    from ..evaluation.state import SceneStateAdapter
    state = SceneStateAdapter(root, contract)
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
    reading = load_data(Path(args.semantic_reading)) if args.semantic_reading else None
    authors = load_data(Path(args.authors)) if args.authors else []
    results = evaluate_scene_text(
        contract,
        text,
        knowledge_runtime=knowledge,
        mechanism_adapter_runtime=historical_adapters,
        historical_mechanisms=historical_mechanisms,
        semantic_reading=reading,
        entry_state=state.snapshot(),
        candidate_authors=authors,
        root=root,
    )
    if precondition_findings:
        results.insert(0, type(results[0])("preconditions", "FAIL", precondition_findings))

    payload = {
        "overall": overall_status(results),
        "results": [r.to_dict() for r in results],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"FAIL": 1, "PENDING": 2, "WARN": 0, "PASS": 0}[payload["overall"]]

def cmd_semantic(args: argparse.Namespace) -> int:
    from ..evaluation.semantics import make_request, check_reading, run_extractor
    from ..evaluation.state import SceneStateAdapter
    from ..candidate_reviews import canonical_bytes, digest
    root = Path(args.root).resolve() if args.root else repo_root()
    try:
        if args.semantic_command == "prepare":
            contract = load_data(Path(args.contract))
            text = Path(args.text).read_bytes().decode()
            authors = load_data(Path(args.authors)) if args.authors else []
            packet = make_request(contract, text, SceneStateAdapter(root, contract).snapshot(), authors)
            with Path(args.output).open("xb") as handle:
                handle.write(canonical_bytes(packet))
            payload = {"status": "PASS", "request_sha256": digest(canonical_bytes(packet)), "output": args.output,
                       "semantic_status": "NOT_EVALUATED"}
        elif args.semantic_command == "run":
            request = load_data(Path(args.request))
            producer = load_data(Path(args.producer))
            schema = load_data(root / "schemas/semantic_reading.schema.json")
            trace = run_extractor(request, shlex.split(args.command), producer, schema)
            with Path(args.output).open("xb") as handle:
                handle.write(canonical_bytes(trace))
            payload = {"status": trace["status"], "trace_sha256": digest(canonical_bytes(trace)), "output": args.output}
        else:
            request = load_data(Path(args.request))
            reading = load_data(Path(args.reading))
            payload = check_reading(request, reading, load_data(root / "schemas/semantic_reading.schema.json"),
                                    CharacterKnowledgeRuntime.from_repo(root), root)
    except (KeyError, OSError, ValueError) as exc:
        payload = {"status": "FAIL", "findings": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return {"FAIL": 1, "PENDING": 2, "PASS": 0}[payload["status"]]

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
                competitions.records[args.competition_id],
                Path(args.output_dir) if args.output_dir else None,
            )
        else:
            raise KeyError(f"Unknown literary-suite command: {kind}")
    except (KeyError, ValueError, OSError) as exc:
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
        return 0 if payload["status"] in {"PASS", "WARN"} else 1
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
        return 0 if payload["status"] in {"PASS", "WARN"} else 1
    return 0


def add_commands(sub) -> None:
    p_eval = sub.add_parser("evaluate")
    p_eval.add_argument("contract")
    p_eval.add_argument("text")
    p_eval.add_argument("--semantic-reading")
    p_eval.add_argument("--authors", help="Bound candidate author identities as a JSON list")
    p_eval.set_defaults(func=cmd_evaluate)

    p_semantic = sub.add_parser("semantic")
    semantic_sub = p_semantic.add_subparsers(dest="semantic_command", required=True)
    p = semantic_sub.add_parser("prepare")
    p.add_argument("contract")
    p.add_argument("text")
    p.add_argument("--authors")
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_semantic)
    p = semantic_sub.add_parser("check")
    p.add_argument("request")
    p.add_argument("reading")
    p.set_defaults(func=cmd_semantic)
    p = semantic_sub.add_parser("run")
    p.add_argument("request")
    p.add_argument("--command", required=True)
    p.add_argument("--producer", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_semantic)

    p_lit_eval = sub.add_parser("literary-evaluate")
    p_lit_eval.add_argument("plock_id")
    p_lit_eval.add_argument("text", nargs="+")
    p_lit_eval.add_argument("--json", action="store_true")
    p_lit_eval.set_defaults(func=cmd_literary_evaluate)

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
    p.add_argument("--output-dir", help="Export anonymous texts and packet.json to a new directory")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_literary_suite)

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
