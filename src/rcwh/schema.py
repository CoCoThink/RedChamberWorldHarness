from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io import load_data

SCHEMA_MAP = {
    "evidence": "evidence.schema.json",
    "character": "character.schema.json",
    "object": "object.schema.json",
    "event": "event.schema.json",
    "scene": "scene_contract.schema.json",
}


def validate_instance(instance: Any, schema: dict[str, Any] | str | Path) -> list[str]:
    if not isinstance(schema, dict):
        schema = load_data(schema)
    validator = Draft202012Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(instance), key=lambda x: list(x.path))]


def validate_file(path: Path, schema_dir: Path, kind: str) -> list[str]:
    instance = load_data(path)
    schema_path = schema_dir / SCHEMA_MAP[kind]
    return validate_instance(instance, schema_path)
