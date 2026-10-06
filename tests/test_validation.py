from pathlib import Path

from rcwh.validate import validate_repository


def test_repository_schemas_are_valid():
    root = Path(__file__).resolve().parents[1]
    assert validate_repository(root) == []
