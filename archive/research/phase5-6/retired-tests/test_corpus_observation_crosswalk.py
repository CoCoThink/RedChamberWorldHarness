"""Correct mapping metadata by source positions, without acquitting old FAILs."""
import importlib.util
import json
from pathlib import Path

import pytest

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("observation_crosswalk", ROOT / "tools/corpus_observation_crosswalk.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_actual_correction_is_recomputed_and_preserves_original_negative():
    saved = json.loads((ROOT / "artifacts/agent_research/phase6/advancement/reader2-old-kind-correction-v1.json").read_bytes())
    assert saved == MODULE.crosswalk(ROOT)
    assert saved["checked"] == 102
    assert saved["mismatches"] == 49
    assert saved["negative_samples_with_mapping_error"] == 8
    assert saved["original_fail_retained"] is True
    assert saved["original_opinion_changed"] is False
    assert saved["corpus_product_changed"] is False
    for ref in saved["bindings"].values():
        bound_bytes(ROOT, ref)
    opinion = json.loads(bound_bytes(ROOT, saved["bindings"]["opinion"]))
    assert opinion["results"][0]["verdict"] == "FAIL"
    assert sum(row["verdict"] == "FAIL" for row in opinion["results"][0]["sample_checks"]) == 31
    wrong = next(row for row in saved["rows"] if row["sample_id"] == "hlm80:chapter:67:p00072")
    assert wrong["claimed_old_kind"] is None
    assert wrong["actual_old_kinds"] == ["VARIANT"]
    assert wrong["old_segments"][0]["segment_id"] == "hlm80:chapter:67:p00064"


@pytest.mark.parametrize("fault", ["duplicate_segment", "text_hash", "verdict", "missing_prefix_map"])
def test_crosswalk_rejects_inconsistent_original_inputs(tmp_path, fault):
    names = {
        "old_segments": "corpus/front80/v1-candidate/segments.jsonl",
        "new_segments": "corpus/front80/v2-candidate/segments.jsonl",
        "observations": "artifacts/agent_research/phase6/corpus/reader2-observations-v1.json",
        "opinion": "artifacts/agent_research/phase6/corpus/reader2-opinion-v1.json",
        "samples": "artifacts/agent_research/phase6/corpus/review-samples-v1.json",
        "map": "artifacts/agent_research/phase6/corpus/dataset-map-v1-to-v2.json",
    }
    from rcwh.candidate_reviews import digest
    locator = {"extraction_ref": "x", "spans": [{"unit_ref": "u", "start": 0, "end": 2}], "transforms": []}
    row = {"record_type": "SEGMENT", "segment_id": "new", "kind": "EDITORIAL", "text": "中文", "text_sha256": digest("中文".encode()), "locator": locator}
    old = {**row, "segment_id": "old", "kind": "APPENDIX"}
    new_rows = [row, row] if fault == "duplicate_segment" else [row]
    if fault == "text_hash":
        row["text_sha256"] = "0" * 64
    values = {
        "old_segments": json.dumps(old) + "\n",
        "new_segments": "".join(json.dumps(item) + "\n" for item in new_rows),
        "observations": json.dumps({"observations": [{"sample_id": "new", "locator": locator, "verdict": "PASS" if fault == "verdict" else "FAIL", "evidence": {"old_kind": None}}]}),
        "opinion": json.dumps({"results": [{"subject_id": "corpus-v2", "verdict": "FAIL", "sample_checks": [{"sample_id": "new", "verdict": "FAIL"}]}]}),
        "samples": json.dumps({"segments": [row]}),
        "map": json.dumps({"rows": [] if fault == "missing_prefix_map" else [{"old_segment_ref": "old", "new_segment_refs": ["new"]}]}),
    }
    for key, name in names.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(values[key], encoding="utf-8")
    with pytest.raises(ValueError):
        MODULE.crosswalk(tmp_path)


def segment(start, end, *, unit="pdf:page:1", extraction="x", transforms=None):
    return {"locator": {"extraction_ref": extraction,
                        "spans": [{"unit_ref": unit, "start": start, "end": end}],
                        "transforms": transforms or []}}


def test_overlap_uses_carrier_and_spans_not_segment_number():
    assert MODULE.overlap(segment(0, 3), segment(1, 4))
    assert not MODULE.overlap(segment(0, 3), segment(3, 4))
    assert not MODULE.overlap(segment(0, 3), segment(0, 3, unit="pdf:page:2"))
    assert not MODULE.overlap(segment(0, 3), segment(0, 3, extraction="other"))
    assert not MODULE.overlap(segment(0, 3), segment(0, 3, transforms=["changed"]))
