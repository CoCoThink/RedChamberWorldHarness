"""Byte-checked citations shared by draft planners."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..assets.paths import repository_path
from ..io import load_data

BOUNDARY = {"authority_effect": "NONE", "evidence_effect": "NONE"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def citation(path: str, raw: bytes, start: int, end: int) -> dict:
    lines = raw.splitlines(keepends=True)
    if not 1 <= start <= end <= len(lines):
        raise ValueError("invalid citation line range")
    before = sum(map(len, lines[:start - 1]))
    selected = b"".join(lines[start - 1:end])
    return {"path": path, "sha256": digest(raw), "lines": [start, end],
            "byte_range": [before, before + len(selected)], "text_sha256": digest(selected)}


def pointer_value(data: Any, pointer: str) -> Any:
    if pointer == "":
        return data
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with /")
    for part in pointer[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


def record(root: Path, path: str, pointer: str, value: Any) -> dict:
    raw = repository_path(root, path).read_bytes()
    return {"ref": f"{path}#{pointer}", "path": path, "pointer": pointer,
            "sha256": digest(raw), "text_sha256": digest(canonical(value)), "value": value}


def verify_record(root: Path, item: dict) -> list[str]:
    try:
        path = repository_path(root, item["path"])
        if digest(path.read_bytes()) != item["sha256"]:
            return ["SOURCE_BYTES_CHANGED"]
        value = pointer_value(load_data(path), item["pointer"])
        if digest(canonical(value)) != item["text_sha256"] or value != item["value"]:
            return ["SOURCE_RECORD_CHANGED"]
        if item.get("ref") != f"{item['path']}#{item['pointer']}":
            return ["SOURCE_POINTER_MISMATCH"]
        return []
    except (OSError, KeyError, ValueError, TypeError, IndexError) as exc:
        return [f"SOURCE_REFERENCE_INVALID: {exc}"]


def verify_citation(root: Path, item: dict, text: str | None = None) -> list[str]:
    try:
        raw = repository_path(root, item["path"]).read_bytes()
        actual = citation(item["path"], raw, *item["lines"])
        if item != actual:
            return ["SOURCE_CITATION_CHANGED"]
        start, end = item["byte_range"]
        if text is not None and raw[start:end].decode("utf-8") != text:
            return ["SOURCE_TEXT_CHANGED"]
        return []
    except (OSError, KeyError, ValueError, TypeError, UnicodeError) as exc:
        return [f"SOURCE_CITATION_INVALID: {exc}"]


def write_new(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
