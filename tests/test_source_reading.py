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
