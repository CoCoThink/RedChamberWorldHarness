"""Prepared research-edition packets bind live inputs and validate (read-only)."""
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetError
from rcwh.workflow.agent_panel import verify_packet
from rcwh.workflow.release_packets import _write_immutable

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / "data/agent_release/research-81-100-v1"
SELECTION = ROOT / "data/agent_release/selection-81-100-v2.json"


def test_edition_request_binds_verified_packets_for_all_twenty_chapters():
    request = json.loads((EDITION / "request.json").read_bytes())
    assert [row["chapter"] for row in request["chapters"]] == list(range(81, 101))
    assert all(row["mode"] == "AGENT_CANDIDATE" for row in request["chapters"])
    for row in request["chapters"]:
        assert row["rebind_receipt"]["path"] == f"data/agent_release/rebind-v4/receipts/ch{row['chapter']}.json"
        for ref in [row["panel"], *row["source_reviews"], *row["corpus_reviews"]]:
            packet = verify_packet(ROOT, ref["packet"])
            assert ref["subject_id"] in {s["id"] for s in packet["subjects"]}
    assert "archive/" not in (EDITION / "request.json").read_text()
    book = verify_packet(ROOT, request["book_review"]["packet"])
    assert book["subjects"][0]["scope"] == "BOOK"
    assert book["subjects"][0]["review_policy"] == "ADVISORY"


def test_rebound_selection_uses_v4_packages_with_disclosure_receipts():
    selection = json.loads(SELECTION.read_bytes())
    assert selection["id"] == "selection:81-100:v2"
    for row in selection["chapters"]:
        chapter = row["chapter"]
        assert row["writing_package"]["path"] == f"data/writing/packages/ch{chapter}-agent-research-v4.json"
        draft = json.loads((ROOT / row["draft"]["path"]).read_bytes())
        assert draft["package"] == row["writing_package"] and draft["parent"] is None
        assert draft["candidate"] == row["candidate"]
        receipt = json.loads((ROOT / f"data/agent_release/rebind-v4/receipts/ch{chapter}.json").read_bytes())
        assert receipt["current"]["draft"] == row["draft"]
        assert receipt["prose_identical_to_previous"] == (chapter != 86)
        package = json.loads((ROOT / row["writing_package"]["path"]).read_bytes())
        assert package["exemplar_set"]["path"] == "data/writing/exemplars/ch89-research-v3.json"
        assert not any(s["source_ref"].startswith("src:history:cao:1728:") and not s["source_ref"].endswith(":npm005664")
                       for s in package["sources"])
    ch86 = next(r for r in selection["chapters"] if r["chapter"] == 86)
    assert "叫了声二叔" not in (ROOT / ch86["candidate"]["path"]).read_text(encoding="utf-8")


def test_cao_archive_sources_are_disclosed_as_agent_transcription():
    from rcwh.graph import ProvenanceGraph
    from rcwh.history import HistoricalMechanismRegistry
    graph = ProvenanceGraph.from_repo(ROOT)
    for key in ("inventory-seal", "pawn-tickets", "family-housing"):
        source = graph.sources[f"src:history:cao:1728:{key}:npm005664"]
        assert "代理目读校录" in source["bibliography"]["citation"] and "二百八十六" not in source["bibliography"]["citation"]
    claim = graph.claims["claim:history:h05:pawn-as-cashflow"]
    assert claim["modality"] == "INFERENCE"
    assert claim["support"][0]["source"].endswith(":npm005664")
    registry = HistoricalMechanismRegistry.from_repo(ROOT)
    assert registry.mechanisms["H05"]["verdict"] == "PASS-WITH-CAUTION"
    assert registry.validate_integrity(graph) == []


def test_packets_are_immutable_once_written(tmp_path):
    _write_immutable(tmp_path, "p.json", {"a": 1})
    _write_immutable(tmp_path, "p.json", {"a": 1})  # identical bytes: no-op
    with pytest.raises(AssetError, match="different bytes"):
        _write_immutable(tmp_path, "p.json", {"a": 2})


def test_full_edition_has_no_failures_and_only_missing_reviews_pending():
    from rcwh.workflow.agent_release import AgentRelease
    report = AgentRelease(ROOT).evaluate("data/agent_release/research-81-100-v1/request.json")
    assert report["findings"] == [] and report["status"] in {"PENDING", "PASS"}
    assert all(not c["findings"] for c in report["chapters"])
    allowed = {"CANDIDATE_PEERS", "COORDINATOR_DECISION", "CHAPTER_SAFETY_POLICY", "CONTRACT_PEERS",
               "SOURCE_PEERS", "CORPUS_PEERS"}
    assert all(set(c["pending"]) <= allowed for c in report["chapters"])
