from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable

import yaml


class ParseMemo:
    """Bounded parsed-value reuse; callers must supply freshly read content."""

    def __init__(self, *, max_entries: int = 32, max_bytes: int = 256 * 1024):
        if max_entries < 0 or max_bytes < 0:
            raise ValueError("parse memo limits must be nonnegative")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries: OrderedDict[tuple[Any, str | bytes], tuple[Any, int]] = OrderedDict()
        self._bytes = 0

    def parse(self, content: str | bytes, parser: Callable, *, identity: Any = None) -> Any:
        size = len(content.encode("utf-8")) if isinstance(content, str) else len(content)
        if not self.max_entries or size > self.max_bytes:
            return parser(content)
        key = (parser if identity is None else identity, content)
        if key in self._entries:
            self._entries.move_to_end(key)
            return deepcopy(self._entries[key][0])
        value = parser(content)
        while self._entries and (len(self._entries) >= self.max_entries or self._bytes + size > self.max_bytes):
            _, (_, removed_size) = self._entries.popitem(last=False)
            self._bytes -= removed_size
        self._entries[key] = (value, size)
        self._bytes += size
        return deepcopy(value)


def parse_yaml(content: str | bytes, *, memo: ParseMemo | None = None) -> Any:
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    if memo is None:
        return yaml.load(content, Loader=loader)
    return memo.parse(content, lambda text: yaml.load(text, Loader=loader), identity=("yaml", loader))


def load_data(path: str | Path, *, memo: ParseMemo | None = None) -> Any:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return parse_yaml(text, memo=memo)
    if path.suffix.lower() == ".json":
        return json.loads(text) if memo is None else memo.parse(text, json.loads)
    raise ValueError(f"Unsupported data format: {path}")
