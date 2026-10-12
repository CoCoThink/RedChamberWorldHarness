from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from rcwh import io
from rcwh.schema import validate_instance


@pytest.mark.parametrize("text", [
    "",
    "name: 林黛玉\nlines: |\n  冷药\n  未成稿\n",
    "values: [yes, false, null, 012, 0x10, 1.25, 2026-10-10]\n",
    "base: &base {name: 紫鹃}\ncopy: {<<: *base, role: attendant}\n",
    "name: first\nname: second\n",
])
def test_safe_yaml_matches_python_loader(text):
    expected = yaml.safe_load(text)
    assert io.parse_yaml(text) == expected
    assert io.parse_yaml(text.encode("utf-8")) == expected


def test_yaml_scalar_types_are_preserved():
    values = io.parse_yaml("[yes, null, 012, 1.25, 2026-10-10]")
    assert [type(value) for value in values] == [bool, type(None), int, float, date]


@pytest.mark.parametrize("text", [
    "[unterminated",
    "value: *missing",
    "---\nfirst\n---\nsecond\n",
    "value: !unknown item",
    "!!python/object/apply:builtins.str [unsafe]",
])
def test_safe_yaml_rejects_invalid_or_unsafe_documents(text):
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(text)
    with pytest.raises(yaml.YAMLError):
        io.parse_yaml(text)


def test_safe_yaml_falls_back_without_c_loader(monkeypatch):
    monkeypatch.delattr(yaml, "CSafeLoader", raising=False)
    assert io.parse_yaml("name: 紫鹃") == {"name": "紫鹃"}
    with pytest.raises(yaml.YAMLError):
        io.parse_yaml("!!python/object/apply:builtins.str [unsafe]")


def test_parse_memo_isolates_documents_and_preserves_aliases():
    memo = io.ParseMemo()
    text = "first: &list [紫鹃]\nsecond: *list\nrecursive: &loop [*loop]\n"
    first = io.parse_yaml(text, memo=memo)
    assert first["first"] is first["second"]
    assert first["recursive"][0] is first["recursive"]
    first["first"].append("宝玉")
    second = io.parse_yaml(text, memo=memo)
    assert second["first"] == ["紫鹃"]
    assert second["first"] is second["second"]
    assert second["recursive"][0] is second["recursive"]


def test_memo_reads_fresh_files_and_reduces_only_parsing(tmp_path, monkeypatch):
    path = tmp_path / "input.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    memo = io.ParseMemo()
    original_read = Path.read_text
    original_loads = io.json.loads
    reads, parses = [], []

    def read(current, *args, **kwargs):
        reads.append(current)
        return original_read(current, *args, **kwargs)

    def loads(text):
        parses.append(text)
        return original_loads(text)

    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(io.json, "loads", loads)
    first = io.load_data(path, memo=memo)
    first["value"] = 99
    assert io.load_data(path, memo=memo) == {"value": 1}
    path.write_text('{"value": 2}', encoding="utf-8")
    assert io.load_data(path, memo=memo) == {"value": 2}
    assert len(reads) == 3 and len(parses) == 2
    path.unlink()
    with pytest.raises(FileNotFoundError):
        io.load_data(path, memo=memo)


def test_safe_yaml_matches_python_loader_for_registered_inputs():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "data").rglob("*.yaml"))
    assert paths
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert io.parse_yaml(text) == yaml.safe_load(text), path


def test_memo_does_not_confuse_formats_loaders_or_roots(tmp_path, monkeypatch):
    memo = io.ParseMemo()
    for directory, value in (("first", 1), ("second", 2)):
        path = tmp_path / directory / "input.json"
        path.parent.mkdir()
        path.write_text(str(value), encoding="utf-8")
        assert io.load_data(path, memo=memo) == value
    assert io.parse_yaml("yes", memo=memo) is True
    path = tmp_path / "input.json"
    path.write_text("yes", encoding="utf-8")
    with pytest.raises(ValueError):
        io.load_data(path, memo=memo)
    calls = []
    original = yaml.load

    def load(text, Loader):
        calls.append(Loader)
        return original(text, Loader=Loader)

    monkeypatch.setattr(yaml, "load", load)
    io.parse_yaml("value: same", memo=memo)
    accelerated = calls[0] is not yaml.SafeLoader
    monkeypatch.delattr(yaml, "CSafeLoader", raising=False)
    io.parse_yaml("value: same", memo=memo)
    assert len(calls) == (2 if accelerated else 1)


def test_memo_bounds_eviction_oversized_inputs_and_failures():
    memo = io.ParseMemo(max_entries=2, max_bytes=4)
    calls = []

    def parse(text):
        calls.append(text)
        if text == "bad":
            raise ValueError("bad")
        return [text]

    for text in ("a", "b", "a", "c", "b"):
        memo.parse(text, parse)
    assert calls == ["a", "b", "c", "b"]
    memo.parse("large", parse)
    memo.parse("large", parse)
    assert calls[-2:] == ["large", "large"]
    for _ in range(2):
        with pytest.raises(ValueError, match="bad"):
            memo.parse("bad", parse)
    assert calls[-2:] == ["bad", "bad"]
    bytes_memo = io.ParseMemo(max_entries=10, max_bytes=3)
    calls.clear()
    for text in ("aa", "bb", "aa"):
        bytes_memo.parse(text, parse)
    assert calls == ["aa", "bb", "aa"]
    disabled = io.ParseMemo(max_entries=0)
    calls.clear()
    disabled.parse("a", parse)
    disabled.parse("a", parse)
    assert calls == ["a", "a"]
    zero_bytes = io.ParseMemo(max_bytes=0)
    calls.clear()
    zero_bytes.parse("a", parse)
    zero_bytes.parse("a", parse)
    assert calls == ["a", "a"]


def test_memo_capacity_limits_are_validated():
    with pytest.raises(ValueError):
        io.ParseMemo(max_entries=-1)
    with pytest.raises(ValueError):
        io.ParseMemo(max_bytes=-1)


def test_validation_uses_fresh_schema_and_runs_on_memo_hits(tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text('{"type": "integer"}', encoding="utf-8")
    memo = io.ParseMemo()
    assert validate_instance(1, schema, memo=memo) == []
    assert validate_instance("wrong", schema, memo=memo)
    schema.write_text('{"type": "string"}', encoding="utf-8")
    assert validate_instance("valid", schema, memo=memo) == []
    assert validate_instance(1, schema, memo=memo)
    document = {"type": "integer"}
    assert validate_instance(1, document, memo=memo) == []
    document["type"] = "string"
    assert validate_instance(1, document, memo=memo)


def test_load_data_preserves_utf8_and_format_errors(tmp_path):
    path = tmp_path / "input.YML"
    path.write_text("name: 紫鹃", encoding="utf-8")
    assert io.load_data(path) == {"name": "紫鹃"}
    path.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        io.load_data(path)
    other = tmp_path / "input.txt"
    other.write_text("value", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported data format"):
        io.load_data(other)
