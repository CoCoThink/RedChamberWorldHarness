from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError, CatalogStore
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.layout import INDEX, LAYOUT, shard_path
from rcwh.assets import transactions
from test_asset_intake import intake_repo


ROOT = Path(__file__).resolve().parents[1]


def prepare(root):
    shutil.copyfile(ROOT / "schemas/asset_catalog_layout.schema.json", root / "schemas/asset_catalog_layout.schema.json")


def commit(root):
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "test"], cwd=root, check=True)


def test_migration_preserves_all_records_and_reads_old_and_new_git(intake_repo):
    root, file = intake_repo
    prepare(root)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    commit(root)
    old = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    store = CatalogStore(root); before = deepcopy(store.read())
    assert store.migrate_shards()["status"] == "PASS"
    assert store.read() == before
    assert not (root / store.asset_path).exists() and not (root / store.origin_path).exists()
    assert AssetCatalog.from_repo(root).compare_git_baseline(old) == []
    commit(root)
    assert AssetCatalog.from_repo(root).compare_git_baseline("HEAD") == []
    receipt = AssetIntake(root).ingest(file, origin="new", kind="PROJECT_REFERENCE")
    c = AssetCatalog.from_repo(root)
    assert c.validate() == []
    assert receipt["asset_ref"] in c.assets
    assert store.index_report()["status"] == "PASS"
    assert store.migrate_shards()["status"] == "PASS"
    assert all(shard_path(key, "assets") in store.metadata_paths() for key in c.assets)


@pytest.mark.parametrize("change,error", [
    ("missing", "SHARD_SET_MISMATCH"), ("extra", "SHARD_SET_MISMATCH"),
    ("legacy", "AMBIGUOUS_CATALOG_LAYOUT"), ("misplaced", "MISPLACED_CATALOG_RECORD"),
    ("duplicate", "duplicate asset id"), ("traversal", "invalid catalog layout"),
])
def test_shard_declaration_and_identity_fail_closed(intake_repo, change, error):
    root, _ = intake_repo
    prepare(root); store = CatalogStore(root); store.migrate_shards()
    config = json.loads((root / LAYOUT).read_bytes()); path = root / config["assets"][0]
    if change == "missing": path.unlink()
    elif change == "extra": (path.parent / "ff.yaml").write_bytes(path.read_bytes())
    elif change == "legacy": (root / store.asset_path).write_bytes(path.read_bytes())
    elif change == "traversal":
        config["assets"] = ["../outside.yaml"]; (root / LAYOUT).write_text(json.dumps(config))
    else:
        doc = yaml.safe_load(path.read_bytes())
        if change == "misplaced": doc["assets"][0]["id"] = "asset:wrong:shard"
        if change == "duplicate": doc["assets"].append(deepcopy(doc["assets"][0]))
        path.write_text(yaml.safe_dump(doc))
    with pytest.raises(AssetError, match=error): AssetCatalog.from_repo(root)


def test_deleted_stale_index_rebuilds_and_formal_shard_tampering_does_not(intake_repo):
    root, _ = intake_repo
    prepare(root); store = CatalogStore(root); store.migrate_shards()
    raw = (root / INDEX).read_bytes(); (root / INDEX).unlink()
    assert store.index_report()["status"] == "FAIL"
    assert store.index_report(rebuild=True)["status"] == "PASS"
    assert (root / INDEX).read_bytes() == raw
    (root / INDEX).write_bytes(b"forged index")
    assert any("STALE_CATALOG_INDEX" in f for f in AssetCatalog.from_repo(root).validate())
    assert store.index_report(rebuild=True)["status"] == "PASS"
    doc = json.loads((root / LAYOUT).read_bytes())
    asset_path = root / doc["assets"][0]
    asset = yaml.safe_load(asset_path.read_bytes()); asset["assets"][0]["sha256"] = "0" * 64
    asset_path.write_text(yaml.safe_dump(asset))
    store.index_report(rebuild=True)
    assert any("byte mismatch" in f for f in AssetCatalog.from_repo(root).validate())


@pytest.mark.parametrize("stop", [1, 3, 5])
def test_interrupted_layout_switch_recovers_and_retains_intake(intake_repo, monkeypatch, stop):
    root, file = intake_repo
    prepare(root); store = CatalogStore(root); before = deepcopy(store.read())
    original = transactions.apply_operation; calls = 0
    def interrupt(store, directory, operation):
        nonlocal calls
        original(store, directory, operation); calls += 1
        if calls == stop: raise OSError("interrupted migration")
    monkeypatch.setattr(transactions, "apply_operation", interrupt)
    with pytest.raises(OSError, match="interrupted migration"): store.migrate_shards()
    with pytest.raises(AssetError, match="unfinished asset transaction"): store.read()
    monkeypatch.setattr(transactions, "apply_operation", original)
    assert AssetIntake(root).recover()["status"] == "PASS"
    assert store.read() == before
    AssetIntake(root).ingest(file, origin="after recovery")
    assert AssetCatalog.from_repo(root).validate() == []
