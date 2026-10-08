from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io import load_data

def validate_instance(instance: Any, schema: dict[str, Any] | str | Path) -> list[str]:
    if not isinstance(schema, dict):
        schema = load_data(schema)
    validator = Draft202012Validator(schema)
    return [e.message for e in sorted(validator.iter_errors(instance), key=lambda x: list(x.path))]
