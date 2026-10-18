"""New adverse scrutiny is preserved without editing frozen source/claim facts."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.io import load_data

ROOT = Path(__file__).resolve().parents[1]


def test_h05_support_range_adverse_record_binds_actual_unchanged_claim():
    report = json.loads((ROOT / "artifacts/agent_research/phase6/advancement/source-range-adverse-findings-v1.json").read_bytes())
    for ref in report["reports"]:
        bound_bytes(ROOT, ref)
    item = report["findings"][0]
    for key in ("source_file", "claim_file", "mechanism_file"):
        bound_bytes(ROOT, item[key])
    source = next(row for row in load_data(ROOT / item["source_file"]["path"])["sources"] if row["id"] == item["source_id"])
    claim = next(row for row in load_data(ROOT / item["claim_file"]["path"])["claims"] if row["id"] == item["subject_id"])
    assert source["text"] == item["actual_source_quote"]
    assert claim["statement"] == item["claim_statement"]
    assert claim["modality"] == item["stored_modality"] == "DIRECT_ASSERTION"
    assert claim["status"] == item["stored_status"] == "SUPPORTED"
    assert claim["support"][0]["relation"] == item["stored_relation"] == "DIRECT"
    assert item["automatic_runtime_gate_change"] is False
    assert report["old_records_changed"] is False
    assert report["source_admission_granted"] is False
    assert report["release_result_changed"] is False
    assert report["scope"]["literary_contexts_scrutinized"] + report["scope"]["historical_contexts_scrutinized"] == 25
    assert report["scope"]["facsimile_fidelity_newly_verified"] is False
    assert report["scope"]["candidate_drafts_audited"] == 0
