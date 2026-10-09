from copy import deepcopy
import json
import shutil
import subprocess

import pytest
import yaml

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.discovery import AssetDiscovery
from rcwh.assets.ingest import AssetIntake, ROLES
from rcwh.cli import main
from rcwh.graph import ProvenanceGraph
from test_source_extraction import ROOT, extraction_repo, setup_source


def metadata(root):
    for name in ("asset_annotation", "asset_collection"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    _, source = setup_source(root)
    annotation = {
        "schema_version": 1, "asset_ref": source["container"]["ref"], "title": "固定阅读材料",
        "version": "v1", "roles": ["MASTER_DRAFT"], "tags": ["pilot"], "chapters": [89],
    }
    collection = {"schema_version": 1, "id": "collection:test:reading", "title": "阅读集合",
                  "purpose": "Discovery only", "members": [annotation["asset_ref"]]}
    for dirname, document in (("annotations", annotation), ("collections", collection)):
        directory = root / "data/catalog" / dirname
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "test.yaml").write_text(yaml.safe_dump(document, allow_unicode=True))
    return source, annotation, collection


def test_discovery_filters_intersect_and_leave_assets_and_evidence_unchanged(extraction_repo):
    root = extraction_repo
    source, annotation, collection = metadata(root)
    catalog = AssetCatalog.from_repo(root)
    records = deepcopy(catalog.assets)
    graph = deepcopy(ProvenanceGraph.from_repo(root))
    discovery = AssetDiscovery(catalog)
    result = discovery.query(role="MASTER_DRAFT", collection=collection["id"], chapter=89, tag="pilot")
    assert result["authority_effect"] == "NONE" and result["count"] == 1
    item = result["assets"][0]
    assert item["asset_id"] == source["container"]["ref"]
    assert item["title"] == annotation["title"] and item["version"] == "v1"
    assert discovery.query(role="GOVERNANCE", collection=collection["id"])["count"] == 0
    assert discovery.query(chapter=90)["count"] == 0
    assert discovery.query()["count"] == len(catalog.assets)
    assert AssetCatalog.from_repo(root).assets == records
    assert ProvenanceGraph.from_repo(root) == graph
    assert catalog.validate() == []


@pytest.mark.parametrize("change", ["unknown-asset", "unknown-member", "duplicate-annotation", "duplicate-collection", "duplicate-member", "unknown-role", "authority-field"])
def test_invalid_discovery_metadata_blocks_queries_and_catalog_validation(extraction_repo, change):
    root = extraction_repo
    _, annotation, collection = metadata(root)
    if change == "unknown-asset":
        annotation["asset_ref"] = "asset:missing"
    elif change == "unknown-member":
        collection["members"] = ["asset:missing"]
    elif change == "duplicate-annotation":
        (root / "data/catalog/annotations/duplicate.yaml").write_text(yaml.safe_dump(annotation))
    elif change == "duplicate-collection":
        (root / "data/catalog/collections/duplicate.yaml").write_text(yaml.safe_dump(collection))
    elif change == "duplicate-member":
        collection["members"].append(collection["members"][0])
    elif change == "unknown-role":
        annotation["roles"] = ["W1_DIRECT"]
    else:
        annotation["adopted"] = True
    (root / "data/catalog/annotations/test.yaml").write_text(yaml.safe_dump(annotation))
    (root / "data/catalog/collections/test.yaml").write_text(yaml.safe_dump(collection))
    catalog = AssetCatalog.from_repo(root)
    assert catalog.validate()
    with pytest.raises(AssetError, match="invalid discovery metadata"):
        AssetDiscovery(catalog).query()


def test_duplicate_basenames_do_not_resolve_collection_members(extraction_repo):
    root = extraction_repo
    _, _, collection = metadata(root)
    collection["members"] = ["sample.txt"]
    (root / "data/catalog/collections/test.yaml").write_text(yaml.safe_dump(collection))
    assert AssetDiscovery(AssetCatalog.from_repo(root)).validate()


def test_unknown_collection_and_invalid_chapter_are_errors(extraction_repo):
    metadata(extraction_repo)
    discovery = AssetDiscovery(AssetCatalog.from_repo(extraction_repo))
    with pytest.raises(AssetError, match="unknown collection"):
        discovery.query(collection="collection:typo")
    with pytest.raises(AssetError, match="between 1 and 100"):
        discovery.query(chapter=101)


def test_classified_receipt_roles_are_hints_until_an_annotation_overrides_them(extraction_repo):
    root = extraction_repo
    metadata(root)
    path = root.parent / "draft.md"
    path.write_text("A new draft")
    receipt = AssetIntake(root).ingest(path, origin="test:new", kind="PROJECT_REFERENCE", role="MASTER_DRAFT")
    result = AssetDiscovery(AssetCatalog.from_repo(root)).query(role="MASTER_DRAFT")
    found = next(item for item in result["assets"] if item["asset_id"] == receipt["asset_ref"])
    assert found["role_origin"] == "RECEIPT_CLASSIFICATION" and found["version"] is None
    override = {"schema_version": 1, "asset_ref": receipt["asset_ref"], "title": "New role",
                "version": None, "roles": ["LITERARY_REVIEW"], "tags": [], "chapters": []}
    (root / "data/catalog/annotations/new.yaml").write_text(yaml.safe_dump(override))
    discovery = AssetDiscovery(AssetCatalog.from_repo(root))
    assert receipt["asset_ref"] not in {item["asset_id"] for item in discovery.query(role="MASTER_DRAFT")["assets"]}
    assert discovery.query(role="LITERARY_REVIEW")["count"] == 1


def test_tracked_gate_includes_discovery_metadata_and_schemas(extraction_repo):
    root = extraction_repo
    metadata(root)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "reset", "--quiet", "schemas/asset_collection.schema.json"], cwd=root, check=True)
    findings = AssetCatalog.from_repo(root).validate(require_tracked=True)
    assert any("schemas/asset_collection.schema.json" in finding for finding in findings)


def test_discovery_cli_and_role_vocabulary(extraction_repo, monkeypatch, capsys):
    root = extraction_repo
    _, _, collection = metadata(root)
    schema = json.loads((root / "schemas/asset_annotation.schema.json").read_bytes())
    assert set(schema["properties"]["roles"]["items"]["enum"]) == set(ROLES)
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), "assets", "list", "--chapter", "89", "--collection", collection["id"]])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    assert json.loads(capsys.readouterr().out)["count"] == 1
