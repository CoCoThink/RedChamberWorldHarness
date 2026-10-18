"""Prepared research-edition packets bind live inputs and validate (read-only)."""
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetError
from rcwh.workflow.agent_panel import verify_packet
from rcwh.workflow.release_packets import _write_immutable

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data/agent_release/research-81-100-pilot-v1"


@pytest.mark.skipif(not PILOT.exists(), reason="pilot edition not prepared")
def test_pilot_request_binds_verified_packets_for_selected_chapters_only():
    request = json.loads((PILOT / "request.json").read_bytes())
    changed = [row for row in request["chapters"] if row["mode"] == "AGENT_CANDIDATE"]
    assert [row["chapter"] for row in changed] == [86, 95, 99]
    assert len(request["chapters"]) == 20
    for row in changed:
        for ref in [row["panel"], *row["source_reviews"], *row["corpus_reviews"]]:
            packet = verify_packet(ROOT, ref["packet"])
            assert ref["subject_id"] in {s["id"] for s in packet["subjects"]}
    assert "archive/" not in (PILOT / "request.json").read_text()


def test_packets_are_immutable_once_written(tmp_path):
    _write_immutable(tmp_path, "p.json", {"a": 1})
    _write_immutable(tmp_path, "p.json", {"a": 1})  # identical bytes: no-op
    with pytest.raises(AssetError, match="different bytes"):
        _write_immutable(tmp_path, "p.json", {"a": 2})


@pytest.mark.skipif(not PILOT.exists(), reason="pilot edition not prepared")
def test_pilot_registered_reviews_and_decisions_evaluate_to_research_pass():
    from rcwh.workflow.agent_release import AgentRelease
    report = AgentRelease(ROOT).evaluate("data/agent_release/research-81-100-pilot-v1/request.json")
    assert report["status"] == "PASS" and report["findings"] == [] and report["pending"] == []
    assert report["provenance"] == "RESEARCH_AGENT_REVIEWED"
    assert report["independent_human_admission"] is False and report["stable_active_effect"] == "NONE"
    changed = [c for c in report["chapters"] if c["provenance"] != "NOT_NEW_AUTHORED"]
    assert [c["chapter"] for c in changed] == [86, 95, 99]
    assert all(set(c["gates"].values()) == {"PASS"} for c in changed)
