import hashlib
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetCatalog
from rcwh.cli import main
from rcwh.graph import ProvenanceGraph
from rcwh.provenance import ProvenanceRepository
from rcwh.workflow import ProjectState


ROOT = Path(__file__).resolve().parents[1]


def run_cli(monkeypatch, capsys, *arguments):
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(ROOT), *arguments])
    with pytest.raises(SystemExit) as result:
        main()
    return result.value.code, json.loads(capsys.readouterr().out)


def test_asset_and_release_native_commands(monkeypatch, capsys):
    code, payload = run_cli(monkeypatch, capsys, "assets", "resolve", "asset:primary:hlm:zhihui:v3.1416:pdf")
    assert code == 0
    assert payload["path"].startswith("sources/primary/")
    code, payload = run_cli(monkeypatch, capsys, "self-contained", "check", "--profile", "release-storage")
    assert code == 0 and payload["status"] == "PASS"
    assert payload["evidence_closure"] == "NOT_VERIFIED"
    assert payload["adoption_effect"] == "NONE"


def test_unknown_assets_fail_without_basename_fallback(monkeypatch, capsys):
    code, payload = run_cli(monkeypatch, capsys, "assets", "resolve", "original.pdf")
    assert code == 1
    assert "unknown asset" in payload["findings"][0]


def test_decision_trace_reaches_local_pdf_without_closing_open(monkeypatch, capsys):
    before = ProvenanceGraph.from_repo(ROOT)
    code, payload = run_cli(monkeypatch, capsys, "sources", "trace", "decision:cliff-release:function")
    assert code == 0 and payload["content_status"] == "PASS"
    assert payload["locator_status"] == "UNVERIFIED"
    assert all(s["asset"]["path"].startswith("sources/") for s in payload["source_assets"])
    after = ProvenanceGraph.from_repo(ROOT)
    assert after.decisions == before.decisions


def test_project_status_uses_owners_and_does_not_claim_implementation_complete(monkeypatch, capsys):
    code, payload = run_cli(monkeypatch, capsys, "project", "status")
    assert code == 0 and payload["integrity_status"] == "PASS"
    project = ProjectState.from_repo(ROOT)
    assert payload["status"] == project.owner("implementation")["status"]
    assert payload["chapters"] == {
        str(record["chapter"]): {key: record[key] for key in ("state", "workflow_progress", "adjudication")}
        for record in project.owner("competitions")["competition_records"]
    }
    assert project.validate() == []


def test_imported_excerpt_fingerprints_still_match_actual_text():
    graph = ProvenanceGraph.from_repo(ROOT)
    for source in graph.sources.values():
        assert hashlib.sha256(source["text"].encode("utf-8")).hexdigest() == source["text_sha256"]
    assert ProvenanceRepository.from_repo(ROOT).validate_assets() == []


@pytest.mark.parametrize("domain", ["reconstruction", "world", "object", "literary-ecology", "implementation",
                                   "knowledge", "historical-adapter", "literary-suite", "prewrite", "pareto"])
def test_domain_summary_does_not_report_an_unexecuted_integrity_pass(monkeypatch, capsys, domain):
    arguments = [domain, "summary"]
    if domain != "pareto":
        arguments.append("--json")
    code, payload = run_cli(monkeypatch, capsys, *arguments)
    assert code == 0
    assert "status" not in payload


def test_missing_world_chapter_is_reported_by_validation_without_a_summary_pass():
    from rcwh.world import WorldRuntime
    from rcwh.reconstruction import ReconstructionRegistry

    runtime = WorldRuntime.from_repo(ROOT)
    del runtime.presence[81]
    assert "status" not in runtime.summary()
    errors = runtime.validate_integrity(AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT))
    assert any("world presence: missing=[81]" in error for error in errors)
