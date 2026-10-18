"""Pilot preparation is a genuine same-package revision, not literary acceptance."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/agent_research/phase6/advancement"


def test_actual_three_requests_were_published_after_no_drift_preparation():
    handoff = json.loads((BASE / "pilot-preparation-handoff-v2.json").read_bytes())
    report = json.loads(bound_bytes(ROOT, handoff["preparation_report"]))
    custody = json.loads((BASE / "pilot-requests-v2/snapshot-custody.json").read_bytes())
    freeze = json.loads((BASE / "m2-input-freeze-v3/freeze.json").read_bytes())
    assert report["status"] == custody["status"] == "PASS"
    assert custody["changed_original_inputs"] == []
    assert custody["input_files"] == len(custody["inputs"]) == 4517
    assert [row["chapter"] for row in report["chapters"]] == [86, 95, 99]
    assert custody["output_hashes"]["preparation-report.json"] == handoff["preparation_report"]["sha256"]
    for row, sent in zip(report["chapters"], handoff["chapters"], strict=True):
        chapter = row["chapter"]
        assert sent["request"] == row["request"]
        packet = json.loads(bound_bytes(ROOT, row["request"]))
        assert custody["output_hashes"][f"ch{chapter}.json"] == row["request"]["sha256"]
        assert packet["parent"] == row["draft"] == freeze["pilot_parents"][str(chapter)]["draft"]
        assert packet["feedback"] == row["feedback"]
        assert packet["package"] == freeze["chapters"][str(chapter)]["package"]
        assert packet["context"]["revision_template"] == "revise-v2"
        assert packet["context"]["notes_path"] == row["notes"]["path"]
        assert row["integrity"]["status"] == "PASS"
        assert row["integrity"]["runtime_observation_variations"] == []
        assert bound_bytes(ROOT, row["notes"]).decode() == packet["task"]["editorial_notes"]
        assert packet["task"]["feedback"] == json.loads(bound_bytes(ROOT, row["feedback"]))
    assert handoff["release_selection_changed"] is False
    assert handoff["literary_acceptance"] == "NOT_GRANTED"
    assert handoff["independent_human_admission"] is False
    assert "FAIL_INPUT_DRIFT_NO_COPYBACK" in handoff["old_failed_attempt"]
