from __future__ import annotations

from pathlib import Path

from .assets import AssetCatalog, AssetError
from .assets.catalog import repository_path
from .provenance import ProvenanceRepository
from .workflow import ProjectState
from .blind_microdraft_review import BlindMicrodraftReviewRuntime
from .competition import CompetitionRegistry
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
from .reconstruction import ReconstructionRegistry
from .regression import run_r4_evidence_regression
from .revision_ablation import CrossRouteRevisionAblationRuntime
from .schema import validate_instance
from .contracts import project_chapters
from .scenarios import ScenarioRuntime
from .scenario_replay import CounterfactualReplayRuntime
from .world import WorldRuntime

REQUIRED_DOCUMENTS = (
    ('data/implementation_alignment/m6.json', 'implementation_alignment.schema.json'),
    ('data/mechanism_adapters/v04.json', 'historical_mechanism_adapter.schema.json'),
    ('data/knowledge/v03_slice1.json', 'character_knowledge_graph.schema.json'),
    ('data/research/fidelity_audit.json', 'fidelity_audit.schema.json'),
    ('data/research/hypothesis_source_backfill.json', 'hypothesis_source_backfill.schema.json'),
    ('data/research/hypothesis_compatibility.json', 'hypothesis_compatibility.schema.json'),
    ('data/research/scenario_replay.json', 'scenario_replay.schema.json'),
    ('data/research/pareto.json', 'pareto_evaluation.schema.json'),
    ('data/research/literary_stress.json', 'scenario_literary_stress.schema.json'),
    ('data/research/narrative_discourse.json', 'narrative_discourse.schema.json'),
    ('data/microdraft/v012.json', 'controlled_microdraft.schema.json'),
    ('data/blind_review/v013.json', 'blind_microdraft_review.schema.json'),
    ('data/prewrite/v06.json', 'v5_prewrite.schema.json'),
    ('data/literary_eval/v05_suite.json', 'literary_evaluator_suite.schema.json'),
    ('data/literary_ecology/m5.json', 'literary_ecology.schema.json'),
    ('data/objects/m4.json', 'object_network.schema.json'),
    ('data/reconstruction/m2.json', 'reconstruction.schema.json'),
)


def validate_required_document(root: Path, relative_path: str, schema_name: str) -> list[str]:
    """A required document must exist and satisfy its schema."""
    try:
        path = repository_path(root, relative_path)
        errors = validate_instance(load_data(path), root / "schemas" / schema_name)
        return [f"{relative_path}: {error}" for error in errors]
    except (AssetError, OSError, ValueError) as exc:
        return [f"{relative_path}: {exc}"]


def validate_required_documents(root: Path) -> list[str]:
    errors = []
    for path, schema in REQUIRED_DOCUMENTS:
        errors.extend(validate_required_document(root, path, schema))
    try:
        project = ProjectState.from_repo(root)
        for owner, schema in (("capability", "capability_selection"), ("literary", "literary_resume_state"), ("plan_constraints", "plan_constraints")):
            errors.extend(validate_required_document(root, project.data["owners"][owner], f"{schema}.schema.json"))
        selection = project.owner("capability")
        errors.extend(validate_required_document(root, selection["experiment_ref"], "revision_ablation.schema.json"))
    except (AssetError, OSError, ValueError) as exc:
        errors.append(f"selected project documents: {exc}")
    return errors


def validate_repository(root: Path) -> list[str]:
    errors = validate_required_documents(root)
    if errors:
        return errors
    schema_dir = root / "schemas"

    try:
        project_chapters(root)
        catalog = AssetCatalog.from_repo(root)
        errors.extend(catalog.validate())
        errors.extend(ProvenanceRepository.from_repo(root).validate_assets())
        errors.extend(ProjectState.from_repo(root).validate(catalog))
    except (AssetError, OSError, ValueError) as exc:
        errors.append(f"asset/provenance integrity: {exc}")

    for path in sorted((root / "data" / "characters").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "character.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    for path in sorted((root / "data" / "objects").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "object.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    for path in sorted((root / "data" / "scenes").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "scene_contract.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

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
        directory = root / "data" / dirname
        if dirname in {"sources", "claims", "decisions", "implementations", "axes"}:
            directory = root / "data" / "provenance" / dirname
        for path in sorted(directory.glob("*.yaml")):
            doc = load_data(path) or {}
            for i, item in enumerate(doc.get(wrapper, [])):
                errs = validate_instance(item, schema)
                errors.extend(f"{path.relative_to(root)} {wrapper}[{i}]: {e}" for e in errs)

    hypothesis_schema = load_data(schema_dir / "hypothesis.schema.json")
    for path in sorted((root / "data" / "research").glob("*hypotheses.json")):
        doc = load_data(path) or {}
        for i, item in enumerate(doc.get("hypotheses", [])):
            errs = validate_instance(item, hypothesis_schema)
            errors.extend(
                f"{path.relative_to(root)} hypotheses[{i}]: {e}" for e in errs
            )


    scenario_schema = load_data(schema_dir / "scenario_bundle.schema.json")
    for path in sorted((root / "data" / "research").glob("scenarios.json")):
        doc = load_data(path) or {}
        for i, item in enumerate(doc.get("scenarios", [])):
            errs = validate_instance(item, scenario_schema)
            errors.extend(
                f"{path.relative_to(root)} scenarios[{i}]: {e}" for e in errs
            )

    try:
        registry = AssetCatalog.from_repo(root)
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
        blind_review = BlindMicrodraftReviewRuntime.from_repo(root)
        errors.extend(blind_review.validate_integrity(microdraft))
        revision_ablation = CrossRouteRevisionAblationRuntime.from_repo(root)
        errors.extend(
            revision_ablation.validate_integrity(
                microdraft,
                blind_review,
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
            )
        )
        literary_production = LiteraryProductionRuntime.from_repo(root)
        errors.extend(
            literary_production.validate_integrity(
                competitions,
            )
        )
        for promotion_id in promotions.records:
            payload = promotions.evaluate(root, promotion_id)
            if payload["overall"] == "FAIL":
                errors.extend(
                    f"promotion {promotion_id}: {x}" for x in payload["findings"]
                )
        for gate in regression["gates"]:
            if gate["status"] == "FAIL":
                for finding in gate["findings"]:
                    errors.append(f"R4 regression {gate['name']}: {finding}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"registry/reconstruction/world/object/literary_ecology/knowledge/prewrite/literary_suite/literary_production/implementation_alignment/provenance/literal/history/historical_adapters/open/regression/plock/competition graph: {exc}")

    return errors
