from __future__ import annotations

from pathlib import Path

from .io import load_data
from .schema import validate_instance


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    schema_dir = root / "schemas"

    # singleton files
    for path in sorted((root / "data" / "characters").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "character.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    for path in sorted((root / "data" / "objects").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "object.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    for path in sorted((root / "data" / "scenes").glob("*.yaml")):
        errs = validate_instance(load_data(path), load_data(schema_dir / "scene_contract.schema.json"))
        errors.extend(f"{path.relative_to(root)}: {e}" for e in errs)

    # list wrappers
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

    return errors
