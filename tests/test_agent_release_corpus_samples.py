"""AgentRelease and AgentPanel share strict sample-container parsing."""
import hashlib
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.workflow.agent_panel import _check_sample, _sample_records
from rcwh.workflow.agent_release import AgentRelease

ROOT = Path(__file__).resolve().parents[1]


def record(identifier="segment-1", text="sample text"):
    return {"segment_id": identifier, "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest()}


@pytest.mark.parametrize("payload", [
    lambda row: [row],
    lambda row: {"segments": [row], "authority_effect": "NONE"},
    lambda row: {"samples": [row]},
    lambda row: {"sources": [row]},
    lambda row: row,
])
def test_sample_records_unwraps_supported_json_carriers(tmp_path, payload):
    row = record()
    path = tmp_path / "sample.json"
    path.write_bytes(canonical_bytes(payload(row)))
    binding = {"path": "sample.json", "sha256": digest(path.read_bytes())}
    rows = _sample_records(tmp_path, binding)
    assert rows == payload(row) if isinstance(payload(row), list) else rows == [row]
    _check_sample(rows, row["segment_id"])


def test_sample_records_rejects_ambiguous_or_non_list_envelopes(tmp_path):
    row = record()
    for payload in ({"segments": [row], "samples": [row]}, {"segments": row}):
        path = tmp_path / 'bad.json'
        path.write_bytes(canonical_bytes(payload))
        binding = {"path": "bad.json", "sha256": digest(path.read_bytes())}
        with pytest.raises(ValueError):
            _sample_records(tmp_path, binding)


def test_sample_records_preserves_jsonl_and_rejects_bad_text_digest(tmp_path):
    row = record()
    path = tmp_path / "sample.jsonl"
    path.write_bytes((json.dumps(row) + "\n\n").encode())
    binding = {"path": "sample.jsonl", "sha256": digest(path.read_bytes())}
    rows = _sample_records(tmp_path, binding)
    assert rows == [row]
    _check_sample(rows, row["segment_id"])
    bad = dict(row, text_sha256="0" * 64)
    with pytest.raises(ValueError, match="digest mismatch"):
        _check_sample([bad], row["segment_id"])


def test_sample_records_rejects_duplicate_or_missing_ids(tmp_path):
    first = record()
    path = tmp_path / "sample.json"
    path.write_bytes(canonical_bytes({"segments": [first, dict(first)]}))
    rows = _sample_records(tmp_path, {"path": "sample.json", "sha256": digest(path.read_bytes())})
    with pytest.raises(ValueError, match="not uniquely present"):
        _check_sample(rows, first["segment_id"])
    with pytest.raises(ValueError, match="not uniquely present"):
        _check_sample(rows, "missing")


def test_actual_phase6_corpus_samples_match_selected_exemplars_without_resetting_failures():
    packet = json.loads((ROOT / "artifacts/agent_research/phase6/corpus/review-packet-v1.json").read_bytes())
    exemplar = json.loads((ROOT / "data/writing/exemplars/ch89-research-v2.json").read_bytes())
    subject = packet["subjects"][0]
    samples = {sample["id"]: sample for sample in subject["samples"]}
    for segment in exemplar["segments"]:
        sample = samples[segment["segment_id"]]
        rows = _sample_records(ROOT, sample["binding"])
        _check_sample(rows, segment["segment_id"])
        actual = next(row for row in rows
                      if segment["segment_id"] in (row.get("segment_id"), row.get("id")))
        assert actual["text_sha256"] == segment["text_sha256"]
    assert len(exemplar["segments"]) == 5
    # The original model panel remains negative; parser alignment is not a review reset.
    report = json.loads((ROOT / "artifacts/agent_research/phase6/corpus/review-packet-v1.json").read_bytes())
    assert report["subjects"][0]["id"] == "corpus-v2"
    original_opinions = list((ROOT / "artifacts/agent_research/phase6/corpus").glob("reader*-opinion-v1.json"))
    assert original_opinions


def test_agent_release_module_uses_canonical_sample_reader():
    assert AgentRelease._inputs.__globals__["_sample_records"] is _sample_records
    assert AgentRelease._inputs.__globals__["_check_sample"] is _check_sample
