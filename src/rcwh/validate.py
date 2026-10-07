from __future__ import annotations

from pathlib import Path

from .competition import CompetitionRegistry
from .coverage import CoverageAuditRuntime
from .graph import ProvenanceGraph
from .io import load_data
from .history import HistoricalMechanismRegistry
from .implementation_alignment import ImplementationAlignmentRuntime
from .literals import LiteralRegistry
from .literary_eval import LiteraryEvaluationProfileRegistry
from .literary_ecology import LiteraryEcologyRuntime
from .open_interfaces import OpenInterfaceRegistry
from .object_network import ObjectNetworkRuntime
from .plocks import LiteraryProtectionRegistry
from .promotion import PromotionRegistry
from .registry import MigrationRegistry
from .reconstruction import ReconstructionRegistry
from .regression import run_r4_evidence_regression
from .schema import validate_instance
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
        open_interfaces = OpenInterfaceRegistry.from_repo(root)
        errors.extend(open_interfaces.validate_integrity(graph, literals, mechanisms))
        reconstruction = ReconstructionRegistry.from_repo(root)
        errors.extend(reconstruction.validate_integrity(registry, open_interfaces))
        world = WorldRuntime.from_repo(root)
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
        competitions = CompetitionRegistry.from_repo(root)
        errors.extend(
            competitions.validate_integrity(
                root,
                plocks,
                regression["stable_active"],
            )
        )
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
        errors.append(f"registry/reconstruction/world/object/literary_ecology/implementation_alignment/coverage/provenance/literal/history/open/regression/plock/competition graph: {exc}")

    return errors
