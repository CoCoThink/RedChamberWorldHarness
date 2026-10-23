"""Even freshly rehashed source packets cannot substitute context or page images."""
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.workflow.source_reading import verify

ROOT = Path(__file__).resolve().parents[1]


def source_case():
    request = json.loads((ROOT / "data/agent_release/research-81-100-v1/request.json").read_bytes())
    ref = next(ref for row in request["chapters"] for ref in row["source_reviews"])
    packet = json.loads((ROOT / ref["packet"]["path"]).read_bytes())
    subjects = [s for s in packet["subjects"] if json.loads((ROOT / s["evidence"]["path"]).read_bytes())["images"]]
    subject = subjects[0]
    source = json.loads((ROOT / subject["binding"]["path"]).read_bytes())["sources"][0]
    evidence = json.loads((ROOT / subject["evidence"]["path"]).read_bytes())
    assert evidence["images"][0]["page"] is not None
    return subjects, subject, source, evidence


@pytest.mark.parametrize("fault", ["context", "image", "omitted-page"])
def test_source_evidence_rejects_rehashed_context_or_image_substitution(fault):
    subjects, subject, source, evidence = source_case()
    if fault == "context":
        evidence["contexts"][0]["text"] = "Rehashed but invented context"
    elif fault == "image":
        other = next(json.loads((ROOT / s["evidence"]["path"]).read_bytes())["images"][0]["binding"]
                     for s in subjects[1:] if json.loads((ROOT / s["evidence"]["path"]).read_bytes())["images"][0]["binding"] != evidence["images"][0]["binding"])
        evidence["images"][0]["binding"] = other
    else:
        evidence["images"] = []
    raw = canonical_bytes(evidence)
    binding = {"path": "rehashed-proof.json", "sha256": digest(raw)}

    def read(ref):
        result = raw if ref == binding else (ROOT / ref["path"]).read_bytes()
        assert digest(result) == ref["sha256"]  # Every input digest is valid.
        return result
    with pytest.raises(ValueError, match="context differs|image differs|omits an original"):
        verify(source, binding, read)


def test_historical_source_custody_does_not_depend_on_future_image_codec(monkeypatch):
    _, subject, source, _ = source_case()
    def read(ref):
        raw = (ROOT / ref["path"]).read_bytes()
        assert digest(raw) == ref["sha256"]
        return raw
    def changed_codec(*args):
        raise RuntimeError("new renderer cannot reproduce the old JPEG encoding")
    monkeypatch.setattr("rcwh.workflow.source_reading.page_image", changed_codec)
    verify(source, subject["evidence"], read, rebuild_images=False)
    with pytest.raises(RuntimeError, match="new renderer"):
        verify(source, subject["evidence"], read)


def test_witness_context_requires_full_text_and_original_page_images():
    from copy import deepcopy
    from rcwh.assets import AssetCatalog
    from rcwh.corpus.extraction import ExtractionRepository
    from rcwh.workflow.source_reading import prepare
    _, _, source, _ = source_case()
    source = deepcopy(source)
    catalog = AssetCatalog.from_repo(ROOT)
    _, units = ExtractionRepository(catalog).load(source["locator"]["extraction_ref"], rebuild=False)
    locator_refs = {s["unit_ref"] for s in source["locator"]["spans"]}
    extra = next(ref for ref in units if ref not in locator_refs)
    source["witness"]["context_units"] = [extra]
    stored = {}

    def write(root, path, value):
        raw = value if isinstance(value, bytes) else canonical_bytes(value)
        stored[path] = raw
        return {"path": path, "sha256": digest(raw)}

    ref = prepare(catalog, source, "test-witness-context", write)
    def read(binding):
        raw = stored[binding["path"]] if binding["path"] in stored else (ROOT / binding["path"]).read_bytes()
        assert digest(raw) == binding["sha256"]
        return raw
    value = json.loads(read(ref))
    assert next(c for c in value["contexts"] if c["unit_ref"] == extra)["text"] == units[extra]["text"]
    assert {i["page"] for i in value["images"]} == {int(r.rsplit(":", 1)[1]) for r in locator_refs | {extra}}
    verify(source, ref, read)
    for fault in ("missing-context", "missing-image", "changed-context"):
        bad = deepcopy(value)
        if fault == "missing-context":
            bad["contexts"] = [c for c in bad["contexts"] if c["unit_ref"] != extra]
        elif fault == "missing-image":
            bad["images"] = [i for i in bad["images"] if i["page"] != int(extra.rsplit(":", 1)[1])]
        else:
            next(c for c in bad["contexts"] if c["unit_ref"] == extra)["text"] = "invented witness"
        bad_ref = write(ROOT, "test-witness-context/bad.json", bad)
        with pytest.raises(ValueError, match="context differs|omits an original"):
            verify(source, bad_ref, read)


@pytest.mark.parametrize("refs", ["pdf:page:1", ["missing"], [1], ["pdf:page:1", "pdf:page:1"]])
def test_invalid_witness_context_units_fail_closed(refs):
    from rcwh.workflow.source_reading import context_units
    with pytest.raises(ValueError, match="invalid witness context"):
        context_units({"witness": {"context_units": refs}}, {"pdf:page:1": {"text": "fixed"}})
