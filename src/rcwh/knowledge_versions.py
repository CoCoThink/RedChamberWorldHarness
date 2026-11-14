"""Explicit selectors for immutable character-knowledge carriers."""
from pathlib import Path

from .io import load_data
from .knowledge import CharacterKnowledgeRuntime

KNOWLEDGE_VERSIONS = {
    "v0.3:slice2": "data/knowledge/v03_slice2.json",
    "v0.4:ch86": "data/knowledge/v04_ch86.json",
}


def load_knowledge_version(root: Path, version: str) -> CharacterKnowledgeRuntime:
    """Load a named carrier and reject unknown versions or identity mismatches."""
    try:
        path = KNOWLEDGE_VERSIONS[version]
    except KeyError as exc:
        raise ValueError(f"unknown character knowledge version: {version}") from exc
    runtime = CharacterKnowledgeRuntime(root, load_data(root / path) or {})
    expected = f"character-truth:{version}"
    if runtime.data.get("id") != expected:
        raise ValueError(f"knowledge version identity mismatch: expected {expected}")
    return runtime
