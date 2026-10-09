import json
from types import SimpleNamespace

import pytest

from rcwh.acceptance import ProjectAcceptance
from rcwh.assets import AssetError


@pytest.fixture
def acceptance_inputs(tmp_path, monkeypatch):
    """Synthetic runtime results; no fixture reviews enter the real catalog."""
    scope = {"id": "closure:fixture", "datasets": ["corpus:fixture"],
             "records": [{"schema": "writing_package", "path": "writing.json", "sha256": "a"*64}]}
    state = {"source_review": "PENDING", "corpus_review": "PENDING", "paired": "PENDING", "integrity": []}
    monkeypatch.setattr("rcwh.acceptance.AssetCatalog.from_repo", lambda _: SimpleNamespace(root=tmp_path))
    monkeypatch.setattr("rcwh.acceptance.ProjectState.from_repo", lambda _: SimpleNamespace(owner=lambda _: scope))
    def closure(*args, **kwargs):
        return {"status": "PASS" if state["source_review"] == "PASS" and not state["integrity"] else "FAIL",
                "sources": {"status": "PASS"}, "source_evidence_audit": {"status": state["source_review"]},
                "datasets": [{"dataset_ref": "corpus:fixture", "status": "PASS"}],
                "findings": state["integrity"], "input_digest": "b"*64, "root_set_digest": "c"*64}
    monkeypatch.setattr("rcwh.acceptance.InputClosure.verify", closure)
    monkeypatch.setattr("rcwh.acceptance.CorpusAudit.summary", lambda *args, **kwargs: {"status": state["corpus_review"]})
    monkeypatch.setattr("rcwh.acceptance.PairedReview.selected_summary", lambda _: {"status": state["paired"]})
    monkeypatch.setattr("rcwh.acceptance.LiteraryInputs.record", lambda *args: {})
    def package(*args, production=False, **kwargs):
        blockers = []
        if state["source_review"] != "PASS": blockers.append("DECLARED_INPUT_CLOSURE_INCOMPLETE")
        if state["corpus_review"] != "PASS":
            blockers.append("CORPUS_HUMAN_LAYER_AUDIT_FAILED" if state["corpus_review"] == "FAIL" else "CORPUS_HUMAN_LAYER_AUDIT_PENDING")
        if state["paired"] != "PASS": blockers.append("P9_PAIRED_REVIEW_PENDING")
        return {"status": "FAIL" if production and blockers else "PASS", "findings": [], "production_blockers": blockers}
    monkeypatch.setattr("rcwh.acceptance.LiteraryInputs.package", package)
    return tmp_path, state, scope


def test_pending_submissions_are_not_engineering_failures_or_acceptance_passes(acceptance_inputs):
    root, _, _ = acceptance_inputs
    result = ProjectAcceptance(root).summary()
    assert result["status"] == "PENDING" and result["engineering_status"] == "PASS"
    assert result["failed_checks"] == []
    assert result["checks"]["production_admission:writing.json"]["strict_status"] == "FAIL"
    assert result["checks"]["declared_input_closure"]["status"] == "BLOCKED"


def test_current_admissions_can_pass_without_claiming_literary_adoption(acceptance_inputs):
    root, state, _ = acceptance_inputs
    state.update(source_review="PASS", corpus_review="PASS", paired="PASS")
    result = ProjectAcceptance(root).summary()
    assert result["status"] == "PASS" and not result["pending_checks"]
    assert result["full_design_acceptance"] == "NOT_ASSESSED"
    assert result["automatic_literary_pass"] is False and result["authority_effect"] == "NONE"


@pytest.mark.parametrize("gate", ["source_review", "corpus_review", "paired"])
def test_a_real_rejection_cannot_be_hidden_by_pending_other_gates(acceptance_inputs, gate):
    root, state, _ = acceptance_inputs
    state[gate] = "FAIL"
    result = ProjectAcceptance(root).summary()
    assert result["status"] == "FAIL" and result["failed_checks"]


def test_stale_package_and_untracked_inputs_fail_engineering_acceptance(acceptance_inputs, monkeypatch):
    root, state, _ = acceptance_inputs
    state["integrity"] = ["UNTRACKED_CLOSURE_INPUT: required.json"]
    def stale(*args): raise AssetError("STALE_WRITING_INPUT")
    monkeypatch.setattr("rcwh.acceptance.LiteraryInputs.record", stale)
    result = ProjectAcceptance(root).summary(require_tracked=True)
    assert result["status"] == "FAIL" and result["engineering_status"] == "FAIL"
    assert result["checks"]["writing_inputs:writing.json"]["findings"] == ["STALE_WRITING_INPUT"]


def test_empty_declared_writing_scope_is_not_an_acceptance_pass(acceptance_inputs):
    root, _, scope = acceptance_inputs
    scope["records"] = []
    result = ProjectAcceptance(root).summary()
    assert result["status"] == "FAIL" and "writing_inputs" in result["failed_checks"]


@pytest.mark.parametrize("strict,code", [(False, 0), (True, 1)])
def test_cli_inspection_and_strict_acceptance_have_distinct_exit_codes(acceptance_inputs, monkeypatch, capsys, strict, code):
    root, _, _ = acceptance_inputs
    from rcwh.cli import main
    monkeypatch.setattr("sys.argv", ["rcwh", "--root", str(root), "project", "acceptance", *(["--require-complete"] if strict else [])])
    with pytest.raises(SystemExit) as result: main()
    assert result.value.code == code
    assert json.loads(capsys.readouterr().out)["status"] == "PENDING"
