from copy import deepcopy
import json
import shutil

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.assets.transactions import digest
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import canonical_bytes
from rcwh.literary_inputs import LiteraryInputs
from test_corpus_dataset import ROOT, DATASET, BUILD, corpus_repo, rows
from test_source_extraction import extraction_repo


@pytest.fixture
def writing_repo(corpus_repo):
    root, _, inputs = corpus_repo
    for name in ("exemplar_set", "writing_package"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    built = CorpusRepository(AssetCatalog.from_repo(root)).build(BUILD, "corpus/front80/test-v1")
    corpus = CorpusRepository(AssetCatalog.from_repo(root)); _, products = corpus.load(DATASET)
    main = next(s for s in rows(products["segments.jsonl"]) if s["kind"] == "MAIN_TEXT")
    examples = {"schema_version": 1, "id": "exemplars:test:v1", "dataset_ref": DATASET, "manifest_ref": built["manifest_ref"],
                "manifest_sha256": built["manifest_sha256"], "segments": [{"segment_id": main["segment_id"], "text_sha256": main["text_sha256"], "reason": "Actual text"}], "authority_effect": "NONE"}
    path = "data/writing/exemplars/test.json"; (root/path).parent.mkdir(parents=True); (root/path).write_bytes(canonical_bytes(examples))
    for filename in ("data/world/version.json", "data/project/plan.json"):
        (root/filename).parent.mkdir(parents=True, exist_ok=True); (root/filename).write_bytes(b'{"id":"version:1"}\n')
    package = {"schema_version": 1, "id": "writing-package:test:v1", "purpose": "Research only", "chapter": 89,
               "exemplar_set": {"path": path, "sha256": digest((root/path).read_bytes())},
               "assets": [{"asset_ref": inputs["pdf"]["asset_ref"], "sha256": inputs["pdf"]["sha256"]}], "sources": [],
               "world": [{"path": "data/world/version.json", "sha256": digest((root/"data/world/version.json").read_bytes())}],
               "plan": [{"path": "data/project/plan.json", "sha256": digest((root/"data/project/plan.json").read_bytes())}], "authority_effect": "NONE"}
    package_path = "data/writing/packages/test.json"; (root/package_path).parent.mkdir(parents=True); (root/package_path).write_bytes(canonical_bytes(package))
    return root, path, package_path, examples, package


def test_frozen_examples_include_locator_context_and_blocker(writing_repo):
    root, examples, package, _, _ = writing_repo
    result = LiteraryInputs(AssetCatalog.from_repo(root)).package(package)
    assert result["status"] == "PASS" and result["scope"] == "FROZEN_RESEARCH_WRITING_INPUTS"
    assert result["exemplars"]["segments"][0]["locator"]["spans"]
    assert result["production_blockers"] == ["CORPUS_HUMAN_LAYER_AUDIT_PENDING"]


@pytest.mark.parametrize("target", ["world", "plan", "example-file", "segment", "commentary", "dataset"])
def test_writing_inputs_reject_stale_or_wrong_layers(writing_repo, target):
    root, path, package_path, examples, package = writing_repo
    if target in {"world", "plan"}:
        (root/package[target][0]["path"]).write_bytes(b'{"id":"version:2"}\n')
    elif target == "example-file":
        examples["segments"][0]["reason"] = "changed rationale"; (root/path).write_bytes(canonical_bytes(examples))
    else:
        if target == "segment": examples["segments"][0]["text_sha256"] = "0"*64
        elif target == "dataset": examples["manifest_sha256"] = "0"*64
        else:
            _, products = CorpusRepository(AssetCatalog.from_repo(root)).load(DATASET)
            zhipi = next(s for s in rows(products["segments.jsonl"]) if s["kind"] == "ZHIPI")
            examples["segments"][0].update(segment_id=zhipi["segment_id"], text_sha256=zhipi["text_sha256"])
        (root/path).write_bytes(canonical_bytes(examples)); package["exemplar_set"]["sha256"] = digest((root/path).read_bytes()); (root/package_path).write_bytes(canonical_bytes(package))
    with pytest.raises(AssetError): LiteraryInputs(AssetCatalog.from_repo(root)).package(package_path)


def test_receipt_binding_disappears_when_formal_writing_object_is_stale(writing_repo):
    root, _, path, _, package = writing_repo
    from rcwh.assets.receipts import ReceiptLedger
    record = package["assets"][0]
    assert package["id"] in ReceiptLedger(AssetCatalog.from_repo(root)).binding_refs(record)
    (root/package["world"][0]["path"]).write_bytes(b'{}\n')
    assert package["id"] not in ReceiptLedger(AssetCatalog.from_repo(root)).binding_refs(record)


def test_markdown_rows_preserve_raw_offsets_and_unresolved_interpretations(writing_repo):
    root, _, _, _, _ = writing_repo
    from rcwh.assets.ingest import AssetIntake
    for name in ("asset_collection", "asset_annotation"):
        shutil.copyfile(ROOT/f"schemas/{name}.schema.json", root/f"schemas/{name}.schema.json")
    raw = '| 类型 | 描述 |\r\n|---|---|\r\n\r\n| 引文 | “甲正文。” |\r\n\r\n| 理论 | 草蛇灰线有意回收 |\r\n'.encode()
    file = root.parent/"index.md"; file.write_bytes(raw)
    receipt = AssetIntake(root).ingest(file, origin="test:index", kind="PROJECT_REFERENCE")
    collection = {"schema_version": 1, "id": "collection:test:index", "title": "test", "purpose": "Interpretation only", "members": [receipt["asset_ref"]]}
    path = root/"data/catalog/collections/test.json"; path.parent.mkdir(parents=True); path.write_bytes(canonical_bytes(collection))
    result = LiteraryInputs(AssetCatalog.from_repo(root)).index_map(DATASET, collection["id"])
    assert len(result["rows"]) == 2 and result["unresolved_rows"] == 1
    for row in result["rows"]:
        span = row["raw_span"]; assert raw.decode()[span["start"]:span["end"]].startswith('|')
        assert row["interpretation_review"] == "PENDING"


def test_version_mapping_reports_splits_merges_and_unmapped_ranges(monkeypatch, tmp_path):
    def segment(identity, start, end):
        return {"segment_id": identity, "asset_ref": "asset:carrier", "text_sha256": str(start), "kind": "MAIN_TEXT",
                "locator": {"spans": [{"unit_ref": "pdf:page:1", "start": start, "end": end}]}}
    old = [segment("old-A",0,6), segment("old-B",6,10), segment("old-C",20,30)]
    new = [segment("new-A",0,3), segment("new-B",3,10), segment("new-C",40,50)]
    class FakeCorpus:
        def __init__(self, _): pass
        def load(self, ref, **kwargs):
            from rcwh.corpus.dataset import records_bytes
            return {}, {"segments.jsonl": records_bytes(ref,"SEGMENTS",old if ref=='old' else new)}
        def registry(self): return {"old":{"manifest_sha256":"a"*64},"new":{"manifest_sha256":"b"*64}}
    monkeypatch.setattr("rcwh.literary_inputs.CorpusRepository", FakeCorpus)
    result = LiteraryInputs(AssetCatalog(tmp_path,{},{})).dataset_map('old','new')
    assert [r["cardinality"] for r in result["rows"]] == ["MANY_TO_MANY", "MANY_TO_ONE", "UNMAPPED"]
    assert result["new_unmapped_segments"] == ["new-C"]
