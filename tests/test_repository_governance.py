from copy import deepcopy
from pathlib import Path

from rcwh.competition import CompetitionRegistry, PIPELINE
from rcwh.literary_production import LiteraryProductionRuntime
from rcwh.schema import validate_instance
from rcwh.workflow import ProjectState


ROOT = Path(__file__).resolve().parents[1]


def runtime() -> LiteraryProductionRuntime:
    return LiteraryProductionRuntime.from_repo(ROOT)


def competitions() -> CompetitionRegistry:
    return CompetitionRegistry.from_repo(ROOT)


def test_literary_summary_uses_selected_owners_and_current_competitions():
    project = ProjectState.from_repo(ROOT)
    summary = runtime().summary()
    owner = project.owner("literary")
    assert summary["phase"] == owner["phase"]
    assert summary["stable_sha256"] == project.release().data["text_sha256"]
    records = {r["chapter"]: r for r in competitions().records.values() if r["mode"] == "PRODUCTION_43_0"}
    active = next((ch for ch in owner["sequence"] if records[ch]["state"] in {"IN_REVIEW", "READY_FOR_CANDIDATES"}), None)
    assert summary["active_chapter"] == active
    assert summary["chapter_states"] == {ch: records[ch]["state"] for ch in owner["sequence"]}


def test_missing_human_review_blocks_even_when_machine_stages_pass():
    registry = competitions()
    rec = registry.records["comp:43-0:ch89:pressure-test"]
    for candidate in rec["candidates"]:
        candidate["human_plock"]["status"] = "PENDING"
        candidate["blind_read"].update(status="PENDING", reviewer_blinded=False)
    rec["state"] = "IN_REVIEW"
    rec["workflow_progress"].update(PLOCK_REGRESSION="PENDING", BLIND_READ="PENDING")
    rec["adjudication"].update(outcome="PENDING", winner_candidate_id=None, promotion_state="NOT_ELIGIBLE")
    before = deepcopy(rec)
    payload = registry.evaluate_record(ROOT, rec)
    assert all(x["machine_status"] == "READY_FOR_BLIND_READ" for x in payload["candidate_results"])
    assert not any(x["adjudication_eligible"] for x in payload["candidate_results"])
    assert rec == before
    rec["state"] = "ADJUDICATED"
    rec["adjudication"].update(outcome="WINNER", winner_candidate_id=rec["candidates"][0]["id"], promotion_state="PROMOTION_CANDIDATE")
    assert any("not passed all promotion gates" in e for e in runtime().validate_integrity(registry))


def test_literary_workflow_name_is_not_bound_to_a_historical_branch():
    selected = runtime()
    selected.data["phase"] = "post-80-next-review-cycle"
    assert validate_instance(selected.data, ROOT / "schemas/literary_resume_state.schema.json") == []
    assert selected.validate_integrity(competitions()) == []


def test_literary_production_runtime_integrity_passes():
    assert runtime().validate_integrity(competitions()) == []


def test_stale_literary_release_binding_is_rejected():
    selected = runtime()
    selected.data["stable_active"]["sha256"] = "0" * 64
    assert any("may not mutate stable ACTIVE" in e for e in selected.validate_integrity(competitions()))


def test_competition_order_matches_explicit_selection_without_pinning_chapter_numbers():
    selected = runtime()
    registry = competitions()
    ordered = sorted((r for r in registry.records.values() if r["mode"] == "PRODUCTION_43_0"), key=lambda r: r["sequence"])
    assert selected.data["sequence"] == [r["chapter"] for r in ordered]
    assert all(r["pipeline"] == PIPELINE for r in ordered)
    selected.data["sequence"] = list(reversed(selected.data["sequence"]))
    assert any("must match production competition order" in e for e in selected.validate_integrity(registry))


def test_capability_rechecks_experiment_inputs(monkeypatch):
    project = ProjectState.from_repo(ROOT)
    experiment = project.experiment()
    experiment["thresholds"]["min_chars"] = 99999
    monkeypatch.setattr(project, "experiment", lambda: experiment)
    result = project.capability()
    assert result["status"] == "BLOCKED"
    assert any("ablation screen failed" in e for e in result["findings"])
    assert result["authority"] == "SHADOW_ONLY"


def test_each_selected_chapter_has_live_gates():
    selected = runtime()
    registry = competitions()
    for ch in selected.data["sequence"]:
        payload = selected.chapter(ch, registry)
        gates = payload["gates"]
        record = payload["competition"]
        assert gates["adjudication"] == "PENDING"
        assert gates["manual_plock"] == "PENDING"
        assert gates["declared_adjudication"] == record["adjudication"]
        assert gates["declared_workflow"] == record["workflow_progress"]
        if not record["candidates"]:
            assert gates["machine_literary_evaluation"] == "PENDING"
    summary = selected.summary()
    assert summary["active_gates"] == selected.gates(summary["active_chapter"], registry)
    assert summary["next_gate"] == "CH89_SIX_FIELD_REGRESSION"


def test_required_documents_follow_selected_owners_and_experiment(tmp_path):
    import json
    import shutil
    from rcwh.validate import REQUIRED_DOCUMENTS, validate_required_documents, validate_repository
    from rcwh.revision_ablation import CrossRouteRevisionAblationRuntime
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    project = ProjectState.from_repo(ROOT)
    selected = deepcopy(project.data)
    selected["owners"]["capability"] = "selected/capability.json"
    selected["owners"]["literary"] = "selected/literary.json"
    selected["owners"]["plan_constraints"] = "selected/plan.json"
    capability = project.owner("capability")
    capability["experiment_ref"] = "selected/experiment.json"
    experiment = project.experiment()
    experiment["next_gate"] = "P8_CI_THEN_P9_PAIRED_BLIND_REVISION_REVIEW"
    documents = {"data/project/current.json": selected,
                 "selected/capability.json": capability,
                 "selected/literary.json": project.owner("literary"),
                 "selected/plan.json": project.owner("plan_constraints"),
                 "selected/experiment.json": experiment}
    for relative, _ in REQUIRED_DOCUMENTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    for relative, value in documents.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")
    assert validate_required_documents(tmp_path) == []
    assert CrossRouteRevisionAblationRuntime.from_repo(tmp_path).data == experiment
    assert LiteraryProductionRuntime.from_repo(tmp_path).data == documents["selected/literary.json"]
    (tmp_path / "selected/experiment.json").write_text("{}", encoding="utf-8")
    assert any("selected/experiment.json" in e for e in validate_required_documents(tmp_path))
    (tmp_path / "selected/experiment.json").unlink()
    assert any("selected/experiment.json" in e for e in validate_required_documents(tmp_path))
    missing = REQUIRED_DOCUMENTS[0][0]
    (tmp_path / missing).unlink()
    assert any(missing in e for e in validate_repository(tmp_path))
