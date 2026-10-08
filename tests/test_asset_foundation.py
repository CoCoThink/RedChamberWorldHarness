from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError
from rcwh.provenance import ProvenanceRepository
from rcwh.graph import ProvenanceGraph
from rcwh.publication import ReleaseManifest
from rcwh.cli import main


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def asset_repo(tmp_path):
    (tmp_path / "schemas").mkdir()
    for name in ("asset_catalog", "asset_origin", "release_manifest"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", tmp_path / f"schemas/{name}.schema.json")
    (tmp_path / "sources").mkdir()
    raw = b"A fixed witness carrier.\n"
    (tmp_path / "sources/carrier.txt").write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    document = {
        "schema_version": 1,
        "assets": [{
            "id": "asset:test:carrier:v1", "path": "sources/carrier.txt",
            "sha256": sha, "bytes": len(raw), "media_type": "text/plain",
            "kind": "PROJECT_REFERENCE", "immutable": True,
            "origin_refs": ["origin:test:carrier"],
        }],
    }
    origin = {
        "id": "origin:test:carrier", "asset_ref": "asset:test:carrier:v1",
        "sha256": sha, "batch_id": "test", "origin_type": "TEST",
        "origin_container": "test input", "original_path": "carrier.txt",
        "disposition": "RETAINED",
    }
    (tmp_path / "data/catalog").mkdir(parents=True)
    write_catalog(tmp_path, document, [origin])
    return tmp_path, document, origin


def write_catalog(root, document, origins):
    (root / "data/catalog/assets.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    (root / "data/catalog/origins.jsonl").write_text(
        "".join(json.dumps(o) + "\n" for o in origins), encoding="utf-8",
    )


def test_resolution_checks_bytes_again_after_edit(asset_repo):
    root, document, _ = asset_repo
    catalog = AssetCatalog.from_repo(root)
    assert catalog.resolve(document["assets"][0]["id"]).path.read_bytes().startswith(b"A fixed")
    (root / "sources/carrier.txt").write_bytes(b"An altered carrier.\n")
    with pytest.raises(AssetError, match="byte mismatch"):
        catalog.resolve(document["assets"][0]["id"])


def test_missing_carrier_fails(asset_repo):
    root, _, _ = asset_repo
    (root / "sources/carrier.txt").unlink()
    assert any("missing file" in e for e in AssetCatalog.from_repo(root).validate())


@pytest.mark.parametrize("path", ["../escape", "/tmp/escape", "C:/escape", "sources\\carrier.txt", "sources/../carrier.txt", "sources//carrier.txt"])
def test_external_or_noncanonical_paths_fail(asset_repo, path):
    root, document, origin = asset_repo
    document["assets"][0]["path"] = path
    write_catalog(root, document, [origin])
    assert any("unsafe repository path" in e for e in AssetCatalog.from_repo(root).validate())


def test_symlinked_carrier_is_rejected_even_inside_repo(asset_repo):
    root, document, origin = asset_repo
    (root / "sources/link.txt").symlink_to("carrier.txt")
    document["assets"][0]["path"] = "sources/link.txt"
    write_catalog(root, document, [origin])
    assert any("symlink" in e for e in AssetCatalog.from_repo(root).validate())


def test_duplicate_identity_and_unknown_schema_version_fail(asset_repo):
    root, document, origin = asset_repo
    document["assets"].append(deepcopy(document["assets"][0]))
    write_catalog(root, document, [origin])
    with pytest.raises(AssetError, match="duplicate asset id"):
        AssetCatalog.from_repo(root)
    document["schema_version"] = 99
    write_catalog(root, document, [origin])
    with pytest.raises(AssetError, match="invalid asset catalog"):
        AssetCatalog.from_repo(root)


def test_hash_only_dedup_cannot_discard_origins(asset_repo):
    root, document, origin = asset_repo
    extra = {**origin, "id": "origin:test:second", "original_path": "other-name.txt"}
    document["assets"][0]["origin_refs"].append(extra["id"])
    write_catalog(root, document, [origin, extra])
    assert AssetCatalog.from_repo(root).validate() == []
    write_catalog(root, document, [origin])
    assert any("unknown origin" in e for e in AssetCatalog.from_repo(root).validate())


def test_changing_both_file_and_declaration_does_not_preserve_identity(asset_repo):
    root, document, origin = asset_repo
    previous = deepcopy(document)
    raw = b"Replacement content.\n"
    (root / "sources/carrier.txt").write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    document["assets"][0].update(sha256=sha, bytes=len(raw))
    origin["sha256"] = sha
    write_catalog(root, document, [origin])
    catalog = AssetCatalog.from_repo(root)
    assert catalog.validate() == []
    assert catalog.compare_immutable(previous) == ["immutable asset changed or removed: asset:test:carrier:v1"]


def test_path_move_preserves_asset_version(asset_repo):
    root, document, origin = asset_repo
    previous = deepcopy(document)
    (root / "sources/carrier.txt").rename(root / "sources/renamed.txt")
    document["assets"][0]["path"] = "sources/renamed.txt"
    write_catalog(root, document, [origin])
    catalog = AssetCatalog.from_repo(root)
    assert catalog.validate() == []
    assert catalog.compare_immutable(previous) == []


def test_derivation_cycle_is_rejected(asset_repo):
    root, document, origin = asset_repo
    document["assets"][0]["derived_from"] = [document["assets"][0]["id"]]
    write_catalog(root, document, [origin])
    assert any("derived asset cycle" in e for e in AssetCatalog.from_repo(root).validate())


def test_untracked_formal_inputs_do_not_pass_clean_checkout_gate(asset_repo):
    root, _, _ = asset_repo
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    catalog = AssetCatalog.from_repo(root)
    assert any("untracked formal asset" in e for e in catalog.validate(require_tracked=True))
    subprocess.run(["git", "add", "sources", "data/catalog"], cwd=root, check=True, capture_output=True)
    assert catalog.validate(require_tracked=True) == []


def test_git_baseline_rejects_replacement_under_same_asset_id(asset_repo):
    root, document, origin = asset_repo
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "baseline"],
        cwd=root, check=True, capture_output=True,
    )
    raw = b"Replacement bytes"
    (root / "sources/carrier.txt").write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    document["assets"][0].update(sha256=sha, bytes=len(raw))
    origin["sha256"] = sha
    write_catalog(root, document, [origin])
    catalog = AssetCatalog.from_repo(root)
    assert catalog.validate() == []
    assert catalog.compare_git_baseline("HEAD")
    with pytest.raises(AssetError, match="cannot read catalog"):
        catalog.compare_git_baseline("missing-baseline")


def test_case_colliding_paths_are_rejected(asset_repo):
    root, document, origin = asset_repo
    raw = b"A different carrier"
    (root / "sources/CARRIER.txt").write_bytes(raw)
    second = {**document["assets"][0], "id": "asset:test:second", "path": "sources/CARRIER.txt", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "origin_refs": ["origin:test:second"]}
    document["assets"].append(second)
    second_origin = {**origin, "id": "origin:test:second", "asset_ref": second["id"], "sha256": second["sha256"], "original_path": "CARRIER.txt"}
    write_catalog(root, document, [origin, second_origin])
    assert any("case-colliding" in e for e in AssetCatalog.from_repo(root).validate())


def source_repository(asset_repo, *, local=True):
    root, document, _ = asset_repo
    source = {
        "id": "src:test", "type": "NOVEL_TEXT", "witness": {"label": "test witness"},
        "text": "A fixed", "text_sha256": hashlib.sha256(b"A fixed").hexdigest(),
        "locator": {"lines": "1"},
    }
    if local:
        source["container"] = {"ref": document["assets"][0]["id"], "sha256": document["assets"][0]["sha256"]}
    else:
        source["bibliography"] = {"citation": "An external edition"}
    return ProvenanceRepository(ProvenanceGraph({source["id"]: source}, {}, {}, {}, {}), AssetCatalog.from_repo(root))


def test_bibliography_and_inline_excerpt_do_not_prove_content_closure(asset_repo):
    report = source_repository(asset_repo, local=False).check()
    assert report["status"] == "FAIL"
    assert report["unresolved_sources"] == 1
    assert "MISSING_LOCAL_CONTAINER" in report["sources"][0]["findings"][0]


def test_source_closure_cli_recognizes_repaired_carrier(asset_repo, monkeypatch, capsys):
    root, document, _ = asset_repo
    repository = source_repository(asset_repo, local=False)
    monkeypatch.setattr(ProvenanceRepository, "from_repo", classmethod(lambda cls, root: repository))
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), "self-contained", "check", "--profile", "source-content"])
    with pytest.raises(SystemExit) as failed:
        main()
    assert failed.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"
    asset = document["assets"][0]
    repository.graph.sources["src:test"]["container"] = {"ref": asset["id"], "sha256": asset["sha256"]}
    with pytest.raises(SystemExit) as repaired:
        main()
    assert repaired.value.code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_correct_file_hash_does_not_prove_locator_alignment(asset_repo):
    repo = source_repository(asset_repo)
    assert repo.check()["status"] == "PASS"
    assert repo.check(locators=True)["status"] == "FAIL"
    # Even a self-reported flag cannot bypass the missing alignment verifier.
    repo.graph.sources["src:test"]["locator_verification"] = {"status": "VERIFIED"}
    assert repo.check(locators=True)["status"] == "FAIL"


def test_empty_source_roots_cannot_produce_vacuous_pass(asset_repo):
    root, _, _ = asset_repo
    repo = ProvenanceRepository(ProvenanceGraph({}, {}, {}, {}, {}), AssetCatalog.from_repo(root))
    assert repo.check()["status"] == "FAIL"


def test_source_binding_hash_and_excerpt_changes_fail(asset_repo):
    repo = source_repository(asset_repo)
    repo.graph.sources["src:test"]["container"]["sha256"] = "0" * 64
    assert any("container SHA" in e for e in repo.validate_assets())
    repo.graph.sources["src:test"]["text"] = "Invented excerpt"
    assert any("excerpt hash" in e for e in repo.validate_assets())


def test_release_reads_actual_prose_bytes(asset_repo):
    root, document, _ = asset_repo
    manifest = {
        "schema_version": 1, "id": "release:test", "status": "IMPORTED_BASELINE",
        "text_asset_ref": document["assets"][0]["id"], "text_sha256": document["assets"][0]["sha256"],
        "related_asset_refs": [], "origin_batch": "test", "evidence_closure": "NOT_VERIFIED",
    }
    (root / "releases").mkdir()
    (root / "releases/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    release = ReleaseManifest.from_repo(root, "releases/manifest.json")
    assert release.validate_storage() == []
    (root / "sources/carrier.txt").write_bytes(b"Changed release")
    assert any("byte mismatch" in e for e in release.validate_storage())
