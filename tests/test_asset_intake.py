from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError, CatalogStore
from rcwh.assets.ingest import AssetIntake
from rcwh.assets import transactions
from rcwh.cli import main


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def intake_repo(tmp_path):
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    for name in ("asset_catalog", "asset_origin", "asset_receipt", "source", "implementation"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    raw = b"Existing fixed carrier.\r\n"
    sha = hashlib.sha256(raw).hexdigest()
    (root / "sources").mkdir()
    (root / "sources/existing.txt").write_bytes(raw)
    asset = {
        "id": "asset:test:existing", "path": "sources/existing.txt", "sha256": sha, "bytes": len(raw),
        "media_type": "text/plain", "kind": "PROJECT_REFERENCE", "immutable": True, "origin_refs": ["origin:test:existing"],
    }
    origin = {
        "id": "origin:test:existing", "asset_ref": asset["id"], "sha256": sha, "batch_id": "test",
        "origin_type": "TEST", "origin_container": "test", "original_path": "existing.txt", "disposition": "RETAINED",
    }
    (root / "data/catalog").mkdir(parents=True)
    store = CatalogStore(root)
    for relative, data in store.serialized_records({asset["id"]: asset}, {origin["id"]: origin}).items():
        (root / relative).write_bytes(data)
    file = tmp_path / "原始材料.md"
    file.write_bytes("材料\r\n第二行\r\n".encode("utf-8"))
    return root, file


def test_receive_preserves_bytes_and_has_no_authority_or_git_side_effects(intake_repo):
    root, file = intake_repo
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    before = deepcopy(AssetCatalog.from_repo(root).assets)
    payload = AssetIntake(root).ingest(file, origin="chat:2026-10-08", role="GOVERNANCE")
    assert payload["classification_status"] == "RECEIVED"
    assert payload["classification"] is None
    assert payload["binding_refs"] == []
    assert payload["authority_effect"] == "NONE" and payload["tracked"] is False
    catalog = AssetCatalog.from_repo(root)
    received = catalog.resolve(payload["asset_ref"])
    assert received.path.read_bytes() == file.read_bytes()
    assert catalog.assets[received.id]["kind"] == "UNCLASSIFIED_INPUT"
    assert received.relative_path.startswith("sources/inbox/")
    assert catalog.compare_immutable({"assets": list(before.values())}) == []
    assert all(catalog.assets[key] == value for key, value in before.items())
    assert catalog.validate() == []
    assert subprocess.check_output(["git", "ls-files"], cwd=root) == b""
    assert any("receipts/" in e for e in catalog.validate(require_tracked=True))
    subprocess.run(["git", "add", "sources", "data/catalog"], cwd=root, check=True)
    assert catalog.validate(require_tracked=True) == []
    assert AssetIntake(root).receipt(payload["receipt_id"])["tracked"] is True


def test_same_request_replays_and_distinct_occurrences_deduplicate(intake_repo):
    root, file = intake_repo
    intake = AssetIntake(root)
    first = intake.ingest(file, origin="chat:first", receipt_key="occurrence-1")
    before = {p: (root / p).read_bytes() for p in CatalogStore(root).metadata_paths()}
    replay = intake.ingest(file, origin="chat:first", receipt_key="occurrence-1")
    assert replay["replayed"] and replay["receipt_id"] == first["receipt_id"]
    assert all((root / p).read_bytes() == raw for p, raw in before.items())
    default = intake.ingest(file, origin="chat:second")
    assert intake.ingest(file, origin="chat:second")["replayed"]
    second = intake.ingest(file, origin="chat:first", receipt_key="occurrence-2")
    assert first["asset_ref"] == second["asset_ref"] == default["asset_ref"]
    catalog = AssetCatalog.from_repo(root)
    assert len(catalog.assets[first["asset_ref"]]["origin_refs"]) == 3
    assert catalog.origins[second["origin_ref"]]["disposition"] == "DEDUPLICATED"
    assert catalog.validate() == []
    with pytest.raises(AssetError, match="different intake request"):
        intake.ingest(file, origin="changed", receipt_key="occurrence-1")


def test_existing_sha_retains_original_identity(intake_repo):
    root, file = intake_repo
    file.write_bytes((root / "sources/existing.txt").read_bytes())
    before = AssetCatalog.from_repo(root)
    received = AssetIntake(root).ingest(file, origin="another occurrence")
    after = AssetCatalog.from_repo(root)
    assert received["asset_ref"] == "asset:test:existing"
    assert received["classification_status"] == "CLASSIFIED"
    assert len(before.assets) == len(after.assets)
    assert after.compare_immutable({"assets": list(before.assets.values())}) == []
    assert after.validate() == []


def test_same_filename_different_bytes_is_a_new_version(intake_repo):
    root, file = intake_repo
    intake = AssetIntake(root)
    first = intake.ingest(file, origin="chat:one")
    original = file.read_bytes()
    file.write_bytes(b"New version")
    second = intake.ingest(file, origin="chat:one")
    assert first["asset_ref"] != second["asset_ref"]
    catalog = AssetCatalog.from_repo(root)
    assert catalog.resolve(first["asset_ref"]).path.read_bytes() == original
    assert catalog.resolve(second["asset_ref"]).path.read_bytes() == b"New version"


def test_classification_moves_bytes_updates_all_receipts_and_keeps_identity(intake_repo):
    root, file = intake_repo
    intake = AssetIntake(root)
    first = intake.ingest(file, origin="one", role="MASTER_DRAFT")
    second = intake.ingest(file, origin="two", role="GOVERNANCE")
    before = AssetCatalog.from_repo(root)
    old_path = root / first["asset"]["path"]
    result = intake.classify(first["receipt_id"], kind="PROJECT_REFERENCE")
    assert result["classification_status"] == "CLASSIFIED"
    assert result["classification"]["roles"] == ["MASTER_DRAFT"]
    assert intake.receipt(second["receipt_id"])["classification"]["roles"] == ["GOVERNANCE"]
    after = AssetCatalog.from_repo(root)
    assert not old_path.exists()
    assert after.resolve(first["asset_ref"]).path.read_bytes() == file.read_bytes()
    assert after.compare_immutable({"assets": list(before.assets.values())}) == []
    assert after.validate() == []
    assert intake.classify(first["receipt_id"], kind="PROJECT_REFERENCE")["asset_ref"] == first["asset_ref"]
    with pytest.raises(AssetError, match="already classified"):
        intake.classify(first["receipt_id"], kind="REVIEW_RECORD")


def test_bound_state_follows_actual_valid_source_and_reverts_when_removed(intake_repo):
    root, file = intake_repo
    intake = AssetIntake(root)
    payload = intake.ingest(file, origin="one", kind="PROJECT_REFERENCE")
    directory = root / "data/provenance/sources"
    directory.mkdir(parents=True)
    source = {
        "id": "src:test:received", "type": "SECONDARY_RESEARCH", "title": "test", "witness": {"label": "test"},
        "locator": {"lines": "1"}, "locator_verification": {"status": "UNVERIFIED", "reason": "pending alignment"},
        "text": "材料", "text_sha256": hashlib.sha256("材料".encode()).hexdigest(),
        "container": {"ref": payload["asset_ref"], "sha256": payload["sha256"]},
    }
    path = directory / "test.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "sources": [source]}, allow_unicode=True), encoding="utf-8")
    bound = intake.receipt(payload["receipt_id"])
    assert bound["classification_status"] == "BOUND" and bound["binding_refs"] == [source["id"]]
    source["container"]["sha256"] = "0" * 64
    path.write_text(yaml.safe_dump({"schema_version": 1, "sources": [source]}), encoding="utf-8")
    assert intake.receipt(payload["receipt_id"])["classification_status"] == "CLASSIFIED"
    path.unlink()
    assert intake.receipt(payload["receipt_id"])["binding_refs"] == []


@pytest.mark.parametrize("interrupted_write", [1, 2, 3, 4])
def test_interrupted_intake_blocks_reads_and_recovers_exactly_once(intake_repo, monkeypatch, interrupted_write):
    root, file = intake_repo
    intake = AssetIntake(root)
    original = transactions.apply_operation
    calls = 0

    def interrupt(store, directory, operation):
        nonlocal calls
        original(store, directory, operation)
        calls += 1
        if calls == interrupted_write:
            raise OSError("simulated process interruption")

    monkeypatch.setattr(transactions, "apply_operation", interrupt)
    with pytest.raises(OSError, match="interruption"):
        intake.ingest(file, origin="one", receipt_key="retry")
    with pytest.raises(AssetError, match="unfinished asset transaction"):
        AssetCatalog.from_repo(root)
    monkeypatch.setattr(transactions, "apply_operation", original)
    assert len(intake.recover()["recovered_transactions"]) == 1
    replay = intake.ingest(file, origin="one", receipt_key="retry")
    assert replay["replayed"]
    assert intake.recover()["recovered_transactions"] == []
    assert AssetCatalog.from_repo(root).validate() == []


def test_recovery_refuses_intervening_edits(intake_repo, monkeypatch):
    root, file = intake_repo
    original = transactions.apply_operation

    def interrupt(*args):
        raise OSError("interrupted before writes")

    monkeypatch.setattr(transactions, "apply_operation", interrupt)
    intake = AssetIntake(root)
    with pytest.raises(OSError):
        intake.ingest(file, origin="one")
    path = root / "data/catalog/assets.yaml"
    changed = path.read_bytes() + b"# concurrent manual edit\n"
    path.write_bytes(changed)
    monkeypatch.setattr(transactions, "apply_operation", original)
    with pytest.raises(AssetError, match="transaction conflict"):
        intake.recover()
    assert path.read_bytes() == changed
    assert CatalogStore(root).pending_transactions()


@pytest.mark.parametrize("interrupted_write", [1, 2, 3, 4])
def test_interrupted_classification_recovers_path_and_receipt_together(intake_repo, monkeypatch, interrupted_write):
    root, file = intake_repo
    intake = AssetIntake(root)
    received = intake.ingest(file, origin="one")
    old_path = root / received["asset"]["path"]
    original = transactions.apply_operation
    calls = 0

    def interrupt(store, directory, operation):
        nonlocal calls
        original(store, directory, operation)
        calls += 1
        if calls == interrupted_write:
            raise OSError("interrupted classification")

    monkeypatch.setattr(transactions, "apply_operation", interrupt)
    with pytest.raises(OSError, match="classification"):
        intake.classify(received["receipt_id"], kind="PROJECT_REFERENCE")
    monkeypatch.setattr(transactions, "apply_operation", original)
    intake.recover()
    result = intake.receipt(received["receipt_id"])
    assert result["classification_status"] == "CLASSIFIED"
    assert result["asset_ref"] == received["asset_ref"]
    assert not old_path.exists()
    assert (root / result["asset"]["path"]).read_bytes() == file.read_bytes()
    assert AssetCatalog.from_repo(root).validate() == []


def test_intake_refuses_invalid_existing_storage_before_mutation(intake_repo):
    root, file = intake_repo
    (root / "sources/existing.txt").write_bytes(b"Unexpected replacement")
    before = (root / "data/catalog/assets.yaml").read_bytes()
    with pytest.raises(AssetError, match="invalid asset storage"):
        AssetIntake(root).ingest(file, origin="one")
    assert (root / "data/catalog/assets.yaml").read_bytes() == before
    assert CatalogStore(root).receipt_paths() == []


def test_writer_lock_prevents_a_second_process_from_receiving(intake_repo):
    root, file = intake_repo
    import os
    import sys
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    with CatalogStore(root).lock(exclusive=True):
        result = subprocess.run(
            [sys.executable, "-m", "rcwh.cli", "--root", str(root), "assets", "ingest", str(file), "--origin", "one"],
            env=environment, capture_output=True, text=True, check=False,
        )
    assert result.returncode == 1
    assert "locked" in json.loads(result.stdout)["findings"][0]
    assert len(AssetCatalog.from_repo(root).assets) == 1


def test_destination_conflicts_and_symlinks_fail_without_catalog_mutation(intake_repo):
    root, file = intake_repo
    before = (root / "data/catalog/assets.yaml").read_bytes()
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    destination = root / "sources/inbox" / sha / file.name
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"Unregistered conflicting file")
    with pytest.raises(AssetError, match="overwrite"):
        AssetIntake(root).ingest(file, origin="one")
    assert (root / "data/catalog/assets.yaml").read_bytes() == before
    destination.unlink()
    destination.symlink_to(file)
    with pytest.raises(AssetError, match="symlink"):
        AssetIntake(root).ingest(file, origin="one")
    destination.unlink()
    link = file.parent / "alias.md"
    link.symlink_to(file)
    with pytest.raises(AssetError, match="symlink"):
        AssetIntake(root).ingest(link, origin="one")


def test_case_collision_with_unregistered_destination_is_rejected(intake_repo):
    root, file = intake_repo
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    directory = root / "sources/INBOX" / sha
    directory.mkdir(parents=True)
    with pytest.raises(AssetError, match="case-colliding"):
        AssetIntake(root).ingest(file, origin="one")


def test_receipt_tampering_blocks_validation(intake_repo):
    root, file = intake_repo
    received = AssetIntake(root).ingest(file, origin="one")
    path = root / CatalogStore(root).receipt_path(received["receipt_id"])
    record = json.loads(path.read_text())
    record["origin"] = "fabricated"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert any("receipt disagrees with origin" in error for error in AssetCatalog.from_repo(root).validate())
    record["classification_status"] = "BOUND"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert any("invalid receipt" in error for error in AssetCatalog.from_repo(root).validate())


def test_intake_cli_reports_received_and_classified_facts(intake_repo, monkeypatch, capsys):
    root, file = intake_repo

    def run(*arguments):
        monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), "assets", *arguments])
        with pytest.raises(SystemExit) as result:
            main()
        return result.value.code, json.loads(capsys.readouterr().out)

    code, received = run("ingest", str(file), "--origin", "chat:2026-10-08", "--role", "GOVERNANCE")
    assert code == 0 and received["classification_status"] == "RECEIVED"
    code, classified = run("classify", received["receipt_id"], "--kind", "PROJECT_REFERENCE")
    assert code == 0 and classified["classification_status"] == "CLASSIFIED"
    code, current = run("receipt", received["receipt_id"])
    assert code == 0 and current["sha256"] == received["sha256"]
    code, recovered = run("recover")
    assert code == 0 and recovered["status"] == "PASS"
    code, failure = run("ingest", str(file.parent / "missing.md"), "--origin", "one")
    assert code == 1 and "regular file" in failure["findings"][0]
