from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.history import HistoryArchive, apply_patch, checksum_manifest_text, make_patch, project_csv
from rcwh.cli import main


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("anchor,historical", [
    (b"a\r\nb\r\n", b"a\r\nc\r\n"),
    (b"a\nb", b"a\nb\n"),
    (b"a\nb\n", b"a\nb"),
    ("甲\n乙\n".encode(), "甲\n丙\n".encode()),
    (b"", b"\xef\xbb\xbftext\r\n"),
])
def test_exact_history_roundtrip_including_line_endings(anchor, historical):
    assert apply_patch(anchor, make_patch(anchor, historical)) == historical


def test_out_of_bounds_and_overlapping_ranges_are_rejected():
    for changes in (
        [{"start": 0, "stop": 3, "text": ""}],
        [{"start": 1, "stop": 2, "text": ""}, {"start": 0, "stop": 1, "text": ""}],
    ):
        with pytest.raises(AssetError, match="line ranges"):
            apply_patch(b"a\nb\n", changes)


def test_checksum_csv_recovery_preserves_order_unicode_and_quoted_paths():
    raw = ("\ufeffpath,sha256,bytes\r\n"
           '"乙,稿.md",' + "b" * 64 + ",12\r\n"
           "甲.md," + "a" * 64 + ",8\r\n").encode("utf-8")
    assert checksum_manifest_text(raw) == (
        "b" * 64 + "  乙,稿.md\n" + "a" * 64 + "  甲.md\n"
    ).encode("utf-8")


@pytest.mark.parametrize("raw", [b"path,bytes\na.md,1\n", b"path,sha256\na.md,invalid\n"])
def test_invalid_checksum_csv_cannot_be_used_as_recovery_anchor(raw):
    with pytest.raises(AssetError, match="checksum CSV"):
        checksum_manifest_text(raw)


def test_csv_view_keeps_selected_order_quoting_bom_and_line_endings():
    raw = 'name,included,sha\n甲,YES,a\n"乙,稿",NO,b\n丙,NO,c\n'.encode()
    projection = {"columns": ["sha", "name"], "where": {"included": "NO"},
                  "encoding": "utf-8-sig", "lineterminator": "\r\n"}
    assert project_csv(raw, projection) == '\ufeffsha,name\r\nb,"乙,稿"\r\nc,丙\r\n'.encode()
    projection["where"] = {"missing": "NO"}
    with pytest.raises(AssetError, match="missing columns"):
        project_csv(raw, projection)


def test_every_retired_import_is_recoverable_but_not_a_runtime_asset():
    catalog = AssetCatalog.from_repo(ROOT)
    archive = HistoryArchive(catalog)
    assert archive.records
    assert archive.validate() == []
    for key, record in archive.records.items():
        assert hashlib.sha256(archive.restore(key)).hexdigest() == record["asset"]["sha256"]
        assert not (ROOT / record["asset"]["path"]).exists()
        assert key not in catalog.assets
        assert not set(record["asset"]["origin_refs"]) & set(catalog.origins)
        with pytest.raises(AssetError, match="unknown asset"):
            catalog.resolve(key)


@pytest.fixture
def altered_archive(tmp_path):
    source = AssetCatalog.from_repo(ROOT)
    archive = HistoryArchive(source)
    record = next(iter(archive.records.values()))
    pack_ref = record["pack_ref"]
    anchor_ref = record["anchor_ref"]
    assets = [deepcopy(source.assets[ref]) for ref in (pack_ref, anchor_ref)]
    origins = [deepcopy(source.origins[oid]) for a in assets for oid in a["origin_refs"]]
    for asset in assets:
        # Only this record is needed in the fixture; its unrelated original
        # derivation declarations are not fixture inputs.
        asset.pop("derived_from", None)
        target = tmp_path / asset["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / asset["path"], target)
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    data = tmp_path / "data/catalog"
    data.mkdir(parents=True)
    (data / "history.json").write_text(json.dumps({"schema_version": 1, "pack_refs": [pack_ref]}))
    pack_asset = assets[0]
    pack = {"schema_version": 1, "date": "2026-10-08", "authority_effect": "NONE",
            "records": [{k: v for k, v in record.items() if k != "pack_ref"}]}

    def write():
        raw = (json.dumps(pack, ensure_ascii=False) + "\n").encode()
        sha = hashlib.sha256(raw).hexdigest()
        pack_asset.update(sha256=sha, bytes=len(raw))
        # Use a stable fixture ID to isolate record-content integrity from
        # content-addressed pack identity checks.
        pack_asset["id"] = "asset:test:history"
        (data / "history.json").write_text(json.dumps({"schema_version": 1, "pack_refs": [pack_asset["id"]]}))
        (tmp_path / pack_asset["path"]).write_bytes(raw)
        for origin in origins:
            if origin["id"] in pack_asset["origin_refs"]:
                origin.update(asset_ref=pack_asset["id"], sha256=sha)
        (data / "assets.yaml").write_text(yaml.safe_dump({"schema_version": 1, "assets": assets}))
        (data / "origins.jsonl").write_text("".join(json.dumps(o) + "\n" for o in origins))
    write()
    return tmp_path, pack, write


def test_declaring_a_new_pack_hash_does_not_hide_lost_historical_content(altered_archive):
    root, pack, write = altered_archive
    assert AssetCatalog.from_repo(root).validate() == []
    pack["records"][0]["changes"][0]["text"] += "Lost historical provenance\n"
    write()
    assert any("recovery mismatch" in e for e in AssetCatalog.from_repo(root).validate())


def test_retired_origin_must_keep_its_original_identity(altered_archive):
    root, pack, write = altered_archive
    pack["records"][0]["origins"][0]["sha256"] = "0" * 64
    write()
    assert any("inconsistent retired origin" in e for e in AssetCatalog.from_repo(root).validate())


def test_missing_history_index_fails_storage_validation(altered_archive):
    root, _, _ = altered_archive
    (root / "data/catalog/history.json").unlink()
    assert any("without their index" in e for e in AssetCatalog.from_repo(root).validate())


def test_history_cli_recovers_exact_bytes_and_refuses_overwrite(tmp_path, monkeypatch, capsys):
    archive = HistoryArchive(AssetCatalog.from_repo(ROOT))
    key = next(iter(archive.records))
    output = tmp_path / "historical.md"
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(ROOT), "assets", "history", key, "--restore-to", str(output)])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    assert json.loads(capsys.readouterr().out)["authority_effect"] == "NONE"
    assert output.read_bytes() == archive.restore(key)
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 1
    capsys.readouterr()
    assert output.read_bytes() == archive.restore(key)
