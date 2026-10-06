from __future__ import annotations

from pathlib import Path

from .competition import CompetitionRegistry
from .graph import ProvenanceGraph
from .io import load_data
from .history import HistoricalMechanismRegistry
from .literals import LiteralRegistry
from .literary_eval import LiteraryEvaluationProfileRegistry
from .open_interfaces import OpenInterfaceRegistry
from .plocks import LiteraryProtectionRegistry
from .regression import run_r4_evidence_regression
from .schema import validate_instance


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
    ]
    for dirname, wrapper, schema_name in wrappers:
        schema = load_data(schema_dir / schema_name)
        for path in sorted((root / "data" / dirname).glob("*.yaml")):
            doc = load_data(path) or {}
            for i, item in enumerate(doc.get(wrapper, [])):
                errs = validate_instance(item, schema)
                errors.extend(f"{path.relative_to(root)} {wrapper}[{i}]: {e}" for e in errs)

    try:
        graph = ProvenanceGraph.from_repo(root)
        errors.extend(graph.validate_integrity())
        literals = LiteralRegistry.from_repo(root)
        errors.extend(literals.validate_integrity(graph))
        mechanisms = HistoricalMechanismRegistry.from_repo(root)
        errors.extend(mechanisms.validate_integrity(graph))
        open_interfaces = OpenInterfaceRegistry.from_repo(root)
        errors.extend(open_interfaces.validate_integrity(graph, literals, mechanisms))
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
        for gate in regression["gates"]:
            if gate["status"] == "FAIL":
                for finding in gate["findings"]:
                    errors.append(f"R4 regression {gate['name']}: {finding}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"provenance/literal/history/open/regression/plock/competition graph: {exc}")

    return errors
