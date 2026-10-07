from __future__ import annotations

from pathlib import Path

from .competition import CompetitionRegistry
from .completion import CompletionGateRuntime
from .coverage import CoverageAuditRuntime
from .graph import ProvenanceGraph
from .io import load_data
from .history import HistoricalMechanismRegistry
from .hypotheses import HypothesisRuntime
from .implementation_alignment import ImplementationAlignmentRuntime
from .knowledge import CharacterKnowledgeRuntime
from .literals import LiteralRegistry
from .literary_eval import LiteraryEvaluationProfileRegistry
from .literary_ecology import LiteraryEcologyRuntime
from .literary_production import LiteraryProductionRuntime
from .literary_stress import ScenarioLiteraryStressRuntime
from .literary_suite import LiteraryEvaluatorSuite
from .mechanism_adapters import HistoricalAdapterRuntime
from .microdraft import ControlledMicrodraftRuntime
from .narrative_discourse import NarrativeDiscourseRuntime
from .open_interfaces import OpenInterfaceRegistry
from .object_network import ObjectNetworkRuntime
from .pareto import ParetoEvaluationRuntime
from .plocks import LiteraryProtectionRegistry
from .promotion import PromotionRegistry
from .prewrite import V5PrewriteRuntime
from .registry import MigrationRegistry
from .reconstruction import ReconstructionRegistry
from .regression import run_r4_evidence_regression
from .schema import validate_instance
from .scenarios import ScenarioRuntime
from .scenario_replay import CounterfactualReplayRuntime
from .world import WorldRuntime


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    schema_dir = root / "schemas"

    for path in sorted((root / "data" / "characters").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "character.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    for path in sorted((root / "data" / "objects").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "object.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    for path in sorted((root / "data" / "scenes").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "scene_contract.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    evidence_schema = load_data(schema_dir / "evidence.schema.json")
    for path in sorted((root / "data" / "evidence").glob("*.yaml")):
        doc = load_data(path)
        for i, claim in enumerate(doc.get("claims", [])):
            errs = validate_instance(claim, evidence_schema)
            errors.extend(f"{path.relative_to(root)} claims[{i}]: {e}" for e in errs)

    event_schema = load_data(schema_dir / "event.schema.json")
    for path in sorted((root / "data" / "events").glob("*.yaml")):
        doc = load_data(path)
        for i, event in enumerate(doc.get("events", [])):
            errs = validate_instance(event, event_schema)
            errors.extend(f"{path.relative_to(root)} events[{i}]: {e}" for e in errs)

    wrappers = [
        ("sources", "sources", "source.schema.json"),
        ("claims", "claims", "claim.schema.json"),
        ("decisions", "decisions", "decision.schema.json"),
        ("implementations", "implementations", "implementation.schema.json"),
        ("axes", "title_axes", "title_axis.schema.json"),
        ("literals", "literal_constraints", "literal_constraint.schema.json"),
        ("mechanisms", "historical_mechanisms", "historical_mechanism.schema.json"),
        ("open_interfaces", "open_interfaces", "open_interface.schema.json"),
        ("regression", "regression_manifests", "regression_manifest.schema.json"),
        ("plocks", "literary_locks", "plock.schema.json"),
        ("literary_eval", "literary_evaluation_profiles", "literary_evaluation_profile.schema.json"),
        ("competitions", "competition_records", "competition.schema.json"),
        ("promotions", "promotions", "promotion.schema.json"),
    ]
    for dirname, wrapper, schema_name in wrappers:
        schema = load_data(schema_dir / schema_name)
        for path in sorted((root / "data" / dirname).glob("*.yaml")):
            doc = load_data(path) or {}
            for i, item in enumerate(doc.get(wrapper, [])):
                errs = validate_instance(item, schema)
                errors.extend(f"{path.relative_to(root)} {wrapper}[{i}]: {e}" for e in errs)

    migration_registry_path = root / "data" / "registry" / "m1.json"
    if migration_registry_path.exists():
        errs = validate_instance(
            load_data(migration_registry_path),
            load_data(schema_dir / "migration_registry.schema.json"),
        )
        errors.extend(
            f"{migration_registry_path.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_path = root / "data" / "registry" / "m2.json"
    if migration_extension_path.exists():
        errs = validate_instance(
            load_data(migration_extension_path),
            load_data(schema_dir / "migration_registry_extension.schema.json"),
        )
        errors.extend(
            f"{migration_extension_path.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_m3 = root / "data" / "registry" / "m3.json"
    if migration_extension_m3.exists():
        errs = validate_instance(
            load_data(migration_extension_m3),
            load_data(schema_dir / "migration_registry_extension_m3.schema.json"),
        )
        errors.extend(
            f"{migration_extension_m3.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_m4 = root / "data" / "registry" / "m4.json"
    if migration_extension_m4.exists():
        errs = validate_instance(
            load_data(migration_extension_m4),
            load_data(schema_dir / "migration_registry_extension_m4.schema.json"),
        )
        errors.extend(
            f"{migration_extension_m4.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_m5 = root / "data" / "registry" / "m5.json"
    if migration_extension_m5.exists():
        errs = validate_instance(
            load_data(migration_extension_m5),
            load_data(schema_dir / "migration_registry_extension_m5.schema.json"),
        )
        errors.extend(
            f"{migration_extension_m5.relative_to(root)}: {e}" for e in errs
        )

    project_state_m8 = root / "data" / "project_state" / "m8.json"
    if project_state_m8.exists():
        errs = validate_instance(
            load_data(project_state_m8),
            load_data(schema_dir / "project_state_m8.schema.json"),
        )
        errors.extend(
            f"{project_state_m8.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_m8 = root / "data" / "registry" / "m8.json"
    if migration_extension_m8.exists():
        errs = validate_instance(
            load_data(migration_extension_m8),
            load_data(schema_dir / "migration_registry_extension_m8.schema.json"),
        )
        errors.extend(
            f"{migration_extension_m8.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_m7 = root / "data" / "registry" / "m7.json"
    if migration_extension_m7.exists():
        errs = validate_instance(
            load_data(migration_extension_m7),
            load_data(schema_dir / "migration_registry_extension_m7.schema.json"),
        )
        errors.extend(
            f"{migration_extension_m7.relative_to(root)}: {e}" for e in errs
        )

    project_state_m7 = root / "data" / "project_state" / "m7.json"
    if project_state_m7.exists():
        errs = validate_instance(
            load_data(project_state_m7),
            load_data(schema_dir / "project_state_m7.schema.json"),
        )
        errors.extend(
            f"{project_state_m7.relative_to(root)}: {e}" for e in errs
        )

    negative_archive_m7 = root / "data" / "coverage" / "negative_archive.json"
    if negative_archive_m7.exists():
        errs = validate_instance(
            load_data(negative_archive_m7),
            load_data(schema_dir / "negative_archive_m7.schema.json"),
        )
        errors.extend(
            f"{negative_archive_m7.relative_to(root)}: {e}" for e in errs
        )

    migration_extension_m6 = root / "data" / "registry" / "m6.json"
    if migration_extension_m6.exists():
        errs = validate_instance(
            load_data(migration_extension_m6),
            load_data(schema_dir / "migration_registry_extension_m6.schema.json"),
        )
        errors.extend(
            f"{migration_extension_m6.relative_to(root)}: {e}" for e in errs
        )

    implementation_alignment_path = (
        root / "data" / "implementation_alignment" / "m6.json"
    )
    if implementation_alignment_path.exists():
        errs = validate_instance(
            load_data(implementation_alignment_path),
            load_data(schema_dir / "implementation_alignment.schema.json"),
        )
        errors.extend(
            f"{implementation_alignment_path.relative_to(root)}: {e}"
            for e in errs
        )

    mechanism_adapter_path = root / "data" / "mechanism_adapters" / "v04.json"
    if mechanism_adapter_path.exists():
        errs = validate_instance(
            load_data(mechanism_adapter_path),
            load_data(schema_dir / "historical_mechanism_adapter.schema.json"),
        )
        errors.extend(
            f"{mechanism_adapter_path.relative_to(root)}: {e}" for e in errs
        )

    knowledge_graph_path = root / "data" / "knowledge" / "v03_slice1.json"
    if knowledge_graph_path.exists():
        errs = validate_instance(
            load_data(knowledge_graph_path),
            load_data(schema_dir / "character_knowledge_graph.schema.json"),
        )
        errors.extend(
            f"{knowledge_graph_path.relative_to(root)}: {e}" for e in errs
        )

    literary_resume_state = root / "data" / "project_state" / "literary_43_0_resume.json"
    if literary_resume_state.exists():
        errs = validate_instance(
            load_data(literary_resume_state),
            load_data(schema_dir / "literary_resume_state.schema.json"),
        )
        errors.extend(
            f"{literary_resume_state.relative_to(root)}: {e}" for e in errs
        )

    repository_governance = (
        root / "data" / "project_state" / "repository_governance_20261007.json"
    )
    if repository_governance.exists():
        errs = validate_instance(
            load_data(repository_governance),
            load_data(schema_dir / "repository_governance.schema.json"),
        )
        errors.extend(
            f"{repository_governance.relative_to(root)}: {e}" for e in errs
        )


    hypothesis_state_path = root / "data" / "project_state" / "hypothesis_runtime_v07.json"
    if hypothesis_state_path.exists():
        errs = validate_instance(
            load_data(hypothesis_state_path),
            load_data(schema_dir / "hypothesis_runtime_state.schema.json"),
        )
        errors.extend(
            f"{hypothesis_state_path.relative_to(root)}: {e}" for e in errs
        )

    fidelity_audit_path = root / "data" / "fidelity" / "audit_registry.json"
    if fidelity_audit_path.exists():
        errs = validate_instance(
            load_data(fidelity_audit_path),
            load_data(schema_dir / "fidelity_audit.schema.json"),
        )
        errors.extend(
            f"{fidelity_audit_path.relative_to(root)}: {e}" for e in errs
        )

    fidelity_backfill_path = root / "data" / "fidelity" / "hypothesis_source_backfill.json"
    if fidelity_backfill_path.exists():
        errs = validate_instance(
            load_data(fidelity_backfill_path),
            load_data(schema_dir / "hypothesis_source_backfill.schema.json"),
        )
        errors.extend(
            f"{fidelity_backfill_path.relative_to(root)}: {e}" for e in errs
        )

    hypothesis_schema = load_data(schema_dir / "hypothesis.schema.json")
    for path in sorted((root / "data" / "hypotheses").glob("*.json")):
        doc = load_data(path) or {}
        for i, item in enumerate(doc.get("hypotheses", [])):
            errs = validate_instance(item, hypothesis_schema)
            errors.extend(
                f"{path.relative_to(root)} hypotheses[{i}]: {e}" for e in errs
            )

    compatibility_path = root / "data" / "hypotheses" / "compatibility.json"
    if compatibility_path.exists():
        errs = validate_instance(
            load_data(compatibility_path),
            load_data(schema_dir / "hypothesis_compatibility.schema.json"),
        )
        errors.extend(
            f"{compatibility_path.relative_to(root)}: {e}" for e in errs
        )

    scenario_schema = load_data(schema_dir / "scenario_bundle.schema.json")
    for path in sorted((root / "data" / "scenarios").glob("*.json")):
        doc = load_data(path) or {}
        for i, item in enumerate(doc.get("scenarios", [])):
            errs = validate_instance(item, scenario_schema)
            errors.extend(
                f"{path.relative_to(root)} scenarios[{i}]: {e}" for e in errs
            )


    scenario_replay_path = root / "data" / "scenario_replay" / "v08.json"
    if scenario_replay_path.exists():
        errs = validate_instance(
            load_data(scenario_replay_path),
            load_data(schema_dir / "scenario_replay.schema.json"),
        )
        errors.extend(
            f"{scenario_replay_path.relative_to(root)}: {e}" for e in errs
        )

    scenario_replay_state = root / "data" / "project_state" / "scenario_replay_v08.json"
    if scenario_replay_state.exists():
        errs = validate_instance(
            load_data(scenario_replay_state),
            load_data(schema_dir / "scenario_replay_state.schema.json"),
        )
        errors.extend(
            f"{scenario_replay_state.relative_to(root)}: {e}" for e in errs
        )


    pareto_path = root / "data" / "pareto" / "v09.json"
    if pareto_path.exists():
        errs = validate_instance(
            load_data(pareto_path),
            load_data(schema_dir / "pareto_evaluation.schema.json"),
        )
        errors.extend(
            f"{pareto_path.relative_to(root)}: {e}" for e in errs
        )

    pareto_state_path = root / "data" / "project_state" / "pareto_evaluation_v09.json"
    if pareto_state_path.exists():
        errs = validate_instance(
            load_data(pareto_state_path),
            load_data(schema_dir / "pareto_evaluation_state.schema.json"),
        )
        errors.extend(
            f"{pareto_state_path.relative_to(root)}: {e}" for e in errs
        )


    literary_stress_path = root / "data" / "literary_stress" / "v010.json"
    if literary_stress_path.exists():
        errs = validate_instance(
            load_data(literary_stress_path),
            load_data(schema_dir / "scenario_literary_stress.schema.json"),
        )
        errors.extend(
            f"{literary_stress_path.relative_to(root)}: {e}" for e in errs
        )

    literary_stress_state = (
        root / "data" / "project_state" / "scenario_literary_stress_v010.json"
    )
    if literary_stress_state.exists():
        errs = validate_instance(
            load_data(literary_stress_state),
            load_data(schema_dir / "scenario_literary_stress_state.schema.json"),
        )
        errors.extend(
            f"{literary_stress_state.relative_to(root)}: {e}" for e in errs
        )


    narrative_discourse_path = root / "data" / "narrative_discourse" / "v011.json"
    if narrative_discourse_path.exists():
        errs = validate_instance(
            load_data(narrative_discourse_path),
            load_data(schema_dir / "narrative_discourse.schema.json"),
        )
        errors.extend(
            f"{narrative_discourse_path.relative_to(root)}: {e}" for e in errs
        )

    narrative_discourse_state = (
        root / "data" / "project_state" / "narrative_discourse_v011.json"
    )
    if narrative_discourse_state.exists():
        errs = validate_instance(
            load_data(narrative_discourse_state),
            load_data(schema_dir / "narrative_discourse_state.schema.json"),
        )
        errors.extend(
            f"{narrative_discourse_state.relative_to(root)}: {e}" for e in errs
        )


    microdraft_path = root / "data" / "microdraft" / "v012.json"
    if microdraft_path.exists():
        errs = validate_instance(
            load_data(microdraft_path),
            load_data(schema_dir / "controlled_microdraft.schema.json"),
        )
        errors.extend(
            f"{microdraft_path.relative_to(root)}: {e}" for e in errs
        )

    microdraft_state = (
        root / "data" / "project_state" / "controlled_microdraft_v012.json"
    )
    if microdraft_state.exists():
        errs = validate_instance(
            load_data(microdraft_state),
            load_data(schema_dir / "controlled_microdraft_state.schema.json"),
        )
        errors.extend(
            f"{microdraft_state.relative_to(root)}: {e}" for e in errs
        )

    prewrite_path = root / "data" / "prewrite" / "v06.json"
    if prewrite_path.exists():
        errs = validate_instance(
            load_data(prewrite_path),
            load_data(schema_dir / "v5_prewrite.schema.json"),
        )
        errors.extend(
            f"{prewrite_path.relative_to(root)}: {e}" for e in errs
        )

    literary_suite_path = root / "data" / "literary_eval" / "v05_suite.json"
    if literary_suite_path.exists():
        errs = validate_instance(
            load_data(literary_suite_path),
            load_data(schema_dir / "literary_evaluator_suite.schema.json"),
        )
        errors.extend(
            f"{literary_suite_path.relative_to(root)}: {e}" for e in errs
        )

    literary_ecology_path = root / "data" / "literary_ecology" / "m5.json"
    if literary_ecology_path.exists():
        errs = validate_instance(
            load_data(literary_ecology_path),
            load_data(schema_dir / "literary_ecology.schema.json"),
        )
        errors.extend(
            f"{literary_ecology_path.relative_to(root)}: {e}" for e in errs
        )

    object_network_path = root / "data" / "objects" / "m4.json"
    if object_network_path.exists():
        errs = validate_instance(
            load_data(object_network_path),
            load_data(schema_dir / "object_network.schema.json"),
        )
        errors.extend(
            f"{object_network_path.relative_to(root)}: {e}" for e in errs
        )

    reconstruction_path = root / "data" / "reconstruction" / "m2.json"
    if reconstruction_path.exists():
        errs = validate_instance(
            load_data(reconstruction_path),
            load_data(schema_dir / "reconstruction.schema.json"),
        )
        errors.extend(
            f"{reconstruction_path.relative_to(root)}: {e}" for e in errs
        )

    try:
        registry = MigrationRegistry.from_repo(root)
        errors.extend(registry.validate_integrity())
        graph = ProvenanceGraph.from_repo(root)
        errors.extend(graph.validate_integrity())
        literals = LiteralRegistry.from_repo(root)
        errors.extend(literals.validate_integrity(graph))
        mechanisms = HistoricalMechanismRegistry.from_repo(root)
        errors.extend(mechanisms.validate_integrity(graph))
        historical_adapters = HistoricalAdapterRuntime.from_repo(root)
        errors.extend(historical_adapters.validate_integrity(mechanisms, registry))
        open_interfaces = OpenInterfaceRegistry.from_repo(root)
        errors.extend(open_interfaces.validate_integrity(graph, literals, mechanisms))
        reconstruction = ReconstructionRegistry.from_repo(root)
        errors.extend(reconstruction.validate_integrity(registry, open_interfaces))
        hypotheses = HypothesisRuntime.from_repo(root)
        errors.extend(
            hypotheses.validate_integrity(
                graph, open_interfaces, mechanisms, reconstruction
            )
        )
        scenarios = ScenarioRuntime.from_repo(root)
        errors.extend(scenarios.validate_integrity(hypotheses, open_interfaces))
        world = WorldRuntime.from_repo(root)
        scenario_replay = CounterfactualReplayRuntime.from_repo(root)
        errors.extend(
            scenario_replay.validate_integrity(hypotheses, scenarios, world)
        )
        pareto = ParetoEvaluationRuntime.from_repo(root)
        errors.extend(
            pareto.validate_integrity(
                hypotheses, scenarios, scenario_replay, world
            )
        )
        errors.extend(
            validate_instance(
                world.data,
                load_data(schema_dir / "world_runtime.schema.json"),
            )
        )
        errors.extend(world.validate_integrity(registry, reconstruction))
        objects = ObjectNetworkRuntime.from_repo(root)
        errors.extend(objects.validate_integrity(root, registry, reconstruction))
        literary_ecology = LiteraryEcologyRuntime.from_repo(root)
        errors.extend(literary_ecology.validate_integrity(registry))
        literary_stress = ScenarioLiteraryStressRuntime.from_repo(root)
        errors.extend(
            literary_stress.validate_integrity(
                pareto,
                hypotheses,
                scenarios,
                scenario_replay,
                world,
                literary_ecology,
            )
        )
        narrative_discourse = NarrativeDiscourseRuntime.from_repo(root)
        errors.extend(
            narrative_discourse.validate_integrity(
                literary_stress,
                literary_ecology,
            )
        )
        microdraft = ControlledMicrodraftRuntime.from_repo(root)
        errors.extend(
            microdraft.validate_integrity(
                narrative_discourse,
                literary_stress,
                LiteraryEvaluatorSuite.from_repo(root),
            )
        )
        knowledge_runtime = CharacterKnowledgeRuntime.from_repo(root)
        errors.extend(knowledge_runtime.validate_integrity(world, literary_ecology))
        regression = run_r4_evidence_regression(root)
        plocks = LiteraryProtectionRegistry.from_repo(root)
        errors.extend(
            plocks.validate_integrity(
                graph,
                literals,
                mechanisms,
                open_interfaces,
                regression["stable_active"],
            )
        )
        literary_profiles = LiteraryEvaluationProfileRegistry.from_repo(root)
        errors.extend(literary_profiles.validate_integrity(plocks))
        prewrite = V5PrewriteRuntime.from_repo(root)
        errors.extend(
            prewrite.validate_integrity(
                registry,
                reconstruction,
                literary_ecology,
                plocks,
                historical_adapters,
            )
        )
        competitions = CompetitionRegistry.from_repo(root)
        errors.extend(
            competitions.validate_integrity(
                root,
                plocks,
                regression["stable_active"],
            )
        )
        literary_suite = LiteraryEvaluatorSuite.from_repo(root)
        errors.extend(literary_suite.validate_integrity(competitions))
        promotions = PromotionRegistry.from_repo(root)
        implementation_alignment = ImplementationAlignmentRuntime.from_repo(root)
        errors.extend(
            implementation_alignment.validate_integrity(
                root,
                registry,
                reconstruction,
                world,
                objects,
                literary_ecology,
                plocks,
                competitions,
                promotions,
            )
        )
        coverage_audit = CoverageAuditRuntime.from_repo(root)
        errors.extend(
            coverage_audit.validate_integrity(
                registry,
                reconstruction,
                world,
                objects,
                literary_ecology,
                implementation_alignment,
                regression,
            )
        )
        completion_gate = CompletionGateRuntime.from_repo(root)
        completion_payload = completion_gate.evaluate(
            registry,
            coverage_audit,
            reconstruction,
            world,
            objects,
            literary_ecology,
            implementation_alignment,
            graph,
            literals,
            mechanisms,
            open_interfaces,
            plocks,
            competitions,
            promotions,
            regression,
        )
        errors.extend(completion_gate.validate_integrity(completion_payload, registry))
        literary_production = LiteraryProductionRuntime.from_repo(root)
        errors.extend(
            literary_production.validate_integrity(
                completion_gate,
                competitions,
            )
        )
        for promotion_id in promotions.records:
            payload = promotions.evaluate(root, promotion_id)
            if payload["overall"] != "PASS":
                errors.extend(
                    f"promotion {promotion_id}: {x}" for x in payload["findings"]
                )
        for gate in regression["gates"]:
            if gate["status"] == "FAIL":
                for finding in gate["findings"]:
                    errors.append(f"R4 regression {gate['name']}: {finding}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"registry/reconstruction/world/object/literary_ecology/knowledge/prewrite/literary_suite/literary_production/implementation_alignment/coverage/completion/provenance/literal/history/historical_adapters/open/regression/plock/competition graph: {exc}")

    return errors
