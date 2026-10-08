"""Collection identity and explicitly configured project scope."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from .io import load_data
from .schema import validate_instance


def record_sha256(value: Any) -> str:
    """Bind a parsed record independently of JSON formatting and line endings."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unique_index(items: list[dict[str, Any]], key: str = "id") -> dict:
    result = {}
    for item in items:
        identity = item[key]
        if identity in result:
            raise ValueError(f"duplicate {key}: {identity}")
        result[identity] = item
    return result


def project_chapters(root: Path) -> tuple[int, ...]:
    scope = load_data(root / "data/project/scope.json")
    errors = validate_instance(scope, root / "schemas/project_scope.schema.json")
    if errors:
        raise ValueError("invalid project scope: " + "; ".join(errors))
    chapters = tuple(scope["chapters"])
    if tuple(sorted(chapters)) != chapters:
        raise ValueError("project chapters must be in increasing order")
    return chapters


def coverage_errors(actual: Any, expected: Any, label: str) -> list[str]:
    present, required = set(actual), set(expected)
    if present == required:
        return []
    return [f"{label}: missing={sorted(required - present)} extra={sorted(present - required)}"]


def validate_plan_constraints(catalog: Any, domain: str, view: dict) -> list[str]:
    """Check the selected implementation version without granting evidence authority."""
    from .workflow import ProjectState

    errors = []
    try:
        plan = ProjectState.from_repo(catalog.root).plan_constraints(catalog)
        rules = plan["rules"][domain]
    except (OSError, KeyError, ValueError) as exc:
        return [f"{domain} plan constraints: {exc}"]
    for rule in rules:
        try:
            actual = view
            for key in rule["path"]:
                actual = actual[key]
            if record_sha256(actual) != record_sha256(rule["equals"]):
                errors.append(f"{domain} plan {plan['id']}/{rule['id']}: expected {rule['equals']!r}, got {actual!r}")
        except (KeyError, IndexError, TypeError) as exc:
            errors.append(f"{domain} plan {plan['id']}/{rule['id']}: unresolved path {rule['path']}: {exc}")
    return errors
