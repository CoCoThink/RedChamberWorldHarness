"""Scoped positive/negative fixtures never register fabricated production audits."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from rcwh.assets.transactions import digest
from rcwh.graph import ProvenanceGraph
from rcwh.workflow.admission import ChapterAdmission, chapter_scope


@pytest.fixture
def admission_inputs(tmp_path, monkeypatch):
    world = [{"path": f"data/world/m3_{name}.json", "sha256": "a"*64} for name in
             ("core", "locations", "presence", "body", "resources", "knowledge")]
    spec = {"chapter": 89, "world": world, "plan": [{"path": "plan.json", "sha256": "a"*64}],
            "sources": [{"source_ref": "src:used", "record_sha256": "a"*64}],
            "exemplar_set": {"path": "exemplars.json", "sha256": "a"*64}}
    graph = ProvenanceGraph({"src:used": {"id": "src:used"}, "src:other": {"id": "src:other"}},
                            {}, {}, {}, {})
    state = {"audit": {"status": "PENDING", "required_source_ids": ["src:used", "src:other"],
                       "pending_source_ids": ["src:other"], "findings": []},
             "corpus": "PASS", "locator": "PASS", "rebuild": "PASS", "world": [], "findings": []}
    def write():
        (tmp_path / "package.json").write_text(json.dumps(spec))
        (tmp_path / "exemplars.json").write_text(json.dumps({"dataset_ref": "corpus:fixture"}))
    write()
    scene = tmp_path / "data/scenes/test.yaml"
    scene.parent.mkdir(parents=True)
    scene.write_text("id: scene:test\nchapter: 89\nhistorical_adapters: []\n")
    catalog = SimpleNamespace(root=tmp_path)
    repository = SimpleNamespace(graph=graph, catalog=catalog, source_report=lambda *args, **kwargs: {"status": state["locator"]})
    monkeypatch.setattr("rcwh.workflow.admission.ProvenanceGraph.from_repo", lambda _: graph)
    monkeypatch.setattr("rcwh.provenance.ProvenanceRepository.from_repo", lambda _: repository)
    monkeypatch.setattr("rcwh.provenance.audit.SourceAudit.summary", lambda _: deepcopy(state["audit"]))
    monkeypatch.setattr("rcwh.corpus.dataset.CorpusRepository.verify", lambda *args, **kwargs: {"status": state["rebuild"]})
    monkeypatch.setattr("rcwh.workflow.admission.project_chapters", lambda _: (86, 89))
    monkeypatch.setattr("rcwh.workflow.admission.validate", lambda *args: None)
    monkeypatch.setattr("rcwh.workflow.project.ProjectState.from_repo", lambda _: SimpleNamespace(data={"owners": {"plan_constraints": "plan.json"}}))
    monkeypatch.setattr("rcwh.world.WorldRuntime.from_repo", lambda _: SimpleNamespace(validate_integrity=lambda *args: state["world"]))
    monkeypatch.setattr("rcwh.reconstruction.ReconstructionRegistry.from_repo", lambda _: object())
    monkeypatch.setattr("rcwh.literary_inputs.LiteraryInputs.package", lambda *args, **kwargs: {
        "status": "PASS", "package": deepcopy(spec), "findings": state["findings"],
        "sources": [{"status": state["locator"]}], "exemplars": {"human_audit": {"status": state["corpus"]}}})
    return tmp_path, catalog, spec, state, graph, write


def test_scoped_sources_pass_despite_unrelated_pending_or_rejected_audit(admission_inputs):
    root, catalog, _, state, _, _ = admission_inputs
    for rejected in (False, True):
        if rejected:
            state["audit"].update(status="FAIL", findings=[{"source_ref": "src:other", "rejected_checks": ["excerpt_valid"]}])
        result = ChapterAdmission(catalog).summary(89, "package.json")
        assert result["status"] == "PASS"
        assert result["source_audit"]["covered_source_ids"] == ["src:used"]
        assert result["publication_preconditions"]["global_source_audit"]["status"] != "PASS"
        assert result["authority_effect"] == "NONE"


@pytest.mark.parametrize("fault,expected", [("pending", "PENDING"), ("unknown", "PENDING"),
    ("rejected-covered", "FAIL"), ("unscoped-failure", "FAIL"), ("corpus-pending", "PENDING"),
    ("corpus-fail", "FAIL"), ("locator", "FAIL"), ("rebuild", "FAIL"), ("world", "FAIL"),
    ("untracked-or-stale", "FAIL"), ("chapter", "FAIL"), ("research", "FAIL")])
def test_no_technical_or_human_gate_is_bypassed(admission_inputs, fault, expected):
    _, catalog, spec, state, _, write = admission_inputs
    if fault == "pending": state["audit"]["pending_source_ids"].append("src:used")
    elif fault == "unknown": state["audit"]["required_source_ids"].remove("src:used")
    elif fault == "rejected-covered": state["audit"].update(status="FAIL", findings=[{"source_ref": "src:used"}])
    elif fault == "unscoped-failure": state["audit"].update(status="FAIL", findings=[])
    elif fault == "corpus-pending": state["corpus"] = "PENDING"
    elif fault == "corpus-fail": state["corpus"] = "FAIL"
    elif fault == "locator": state["locator"] = "FAIL"
    elif fault == "rebuild": state["rebuild"] = "FAIL"
    elif fault == "world": state["world"] = ["WORLD_INTEGRITY_FAILED"]
    elif fault == "untracked-or-stale": state["findings"] = ["UNTRACKED_WRITING_INPUT"]
    elif fault == "chapter": spec["chapter"] = 86
    elif fault == "research": spec["operation_scope"] = "RESEARCH"
    write()
    assert ChapterAdmission(catalog).summary(89, "package.json")["status"] == expected


def test_mechanism_claim_and_reverse_implementation_dependencies_cannot_be_omitted(admission_inputs, monkeypatch):
    root, catalog, _, _, graph, _ = admission_inputs
    graph.sources["src:dependent"] = {"id": "src:dependent"}
    graph.claims["claim:dependent"] = {"id": "claim:dependent", "support": [{"source": "src:dependent"}]}
    graph.implementations["impl:chapter"] = {"id": "impl:chapter", "chapter": 89, "decision_refs": []}
    mechanisms = root / "data/mechanisms/test.yaml"
    mechanisms.parent.mkdir(parents=True)
    mechanisms.write_text("historical_mechanisms:\n  - id: H1\n    claim_refs: [claim:dependent]\n    implementation_refs: [impl:chapter]\n")
    scope = chapter_scope(root, "package.json")
    assert scope["used_source_ids"] == ["src:dependent", "src:used"]
    assert "PACKAGE_SOURCE_SCOPE_MISMATCH: src:dependent" in scope["findings"]
    assert ChapterAdmission(catalog).summary(89, "package.json")["status"] == "FAIL"
    graph.implementations.clear()
    (root / "data/scenes/test.yaml").write_text("id: scene:test\nchapter: 89\nhistorical_adapters: [adapter]\n")
    monkeypatch.setattr("rcwh.workflow.admission.HistoricalAdapterRuntime.from_repo", lambda _: SimpleNamespace(
        adapters={"adapter": {"mechanism_refs": ["H1"], "claim_refs": [], "source_refs": []}}))
    assert chapter_scope(root, "package.json")["used_source_ids"] == ["src:dependent", "src:used"]
    graph.claims.clear()
    assert "UNRESOLVED_DEPENDENT_CLAIM: claim:dependent" in chapter_scope(root, "package.json")["findings"]


def test_missing_production_package_pending_research_not_formal(admission_inputs):
    _, catalog, _, _, _, _ = admission_inputs
    service = ChapterAdmission(catalog)
    assert service.for_competition({"mode": "PRODUCTION_43_0"})["status"] == "PENDING"
    assert service.for_competition({"mode": "RESEARCH"})["status"] == "NOT_APPLICABLE"


def test_package_binding_is_raw_byte_bound_and_chapter_bound(admission_inputs):
    root, catalog, _, _, _, _ = admission_inputs
    binding = {"path": "package.json", "sha256": digest((root / "package.json").read_bytes())}
    record = {"mode": "PRODUCTION_43_0", "chapter": 89, "writing_package": binding}
    assert ChapterAdmission(catalog).for_competition(record)["status"] == "PASS"
    binding["sha256"] = "0"*64
    result = ChapterAdmission(catalog).for_competition(record)
    assert result["status"] == "FAIL"
    assert result["findings"] == ["STALE_COMPETITION_WRITING_PACKAGE"]


def test_actual_ch89_package_undeclared_sources_are_blockers():
    root = Path(__file__).resolve().parents[1]
    scope = chapter_scope(root, "data/writing/packages/ch89-research-v4.json")
    assert scope["dependent_source_ids"]
    assert all(f"PACKAGE_SOURCE_SCOPE_MISMATCH: {ref}" in scope["findings"]
               for ref in scope["dependent_source_ids"])


def test_current_competition_cannot_formally_qualify_with_missing_admission(monkeypatch):
    from rcwh.candidate_reviews import SIX_FIELDS
    from rcwh.competition import CompetitionRegistry
    root = Path(__file__).resolve().parents[1]
    record = CompetitionRegistry.from_repo(root).records["comp:43-0:ch86:pressure-test"]
    record["adjudication_basis"] = "CURRENT_SUBMISSIONS"
    monkeypatch.setattr("rcwh.competition.run_r4_evidence_regression", lambda _: {"overall": "PASS"})
    monkeypatch.setattr("rcwh.competition.evaluate_literary_candidate", lambda *args, **kwargs: {"machine_status": "READY_FOR_BLIND_READ"})
    monkeypatch.setattr("rcwh.competition.candidate_semantics", lambda *args: {"status": "PASS"})
    monkeypatch.setattr("rcwh.competition.CandidateReviewService", lambda *args: SimpleNamespace(evaluate=lambda *args: {
        "status": "PASS", "candidate_sha256": "a"*64, "findings": [],
        "check_statuses": {key: "PASS" for key in [*SIX_FIELDS, "HUMAN_PLOCK", "BLIND_READ"]}}))
    registry = CompetitionRegistry({})
    blocked = registry.evaluate_record(root, record)
    assert blocked["input_admission"]["status"] == "PENDING"
    assert not any(c["adjudication_eligible"] for c in blocked["candidate_results"])
    monkeypatch.setattr("rcwh.workflow.admission.ChapterAdmission.for_competition", lambda *args: {"status": "PASS"})
    allowed = registry.evaluate_record(root, record)
    assert all(c["adjudication_eligible"] for c in allowed["candidate_results"])
    assert allowed["adjudication_qualification"] == "PASS"


def test_status_derived_values_warn_without_mutating_declarations(monkeypatch):
    from rcwh.competition import CompetitionRegistry
    root = Path(__file__).resolve().parents[1]
    record = CompetitionRegistry.from_repo(root).records["comp:43-0:ch86:pressure-test"]
    before = deepcopy(record)
    monkeypatch.setattr("rcwh.competition.run_r4_evidence_regression", lambda _: {"overall": "PASS"})
    monkeypatch.setattr("rcwh.competition.evaluate_literary_candidate", lambda *args, **kwargs: {"machine_status": "READY_FOR_BLIND_READ"})
    monkeypatch.setattr("rcwh.competition.candidate_semantics", lambda *args: {"status": "PENDING"})
    result = CompetitionRegistry({}).evaluate_record(root, record)
    assert result["workflow_progress"]["SIX_FIELD_REGRESSION"] == "PENDING"
    assert result["declared_progress"]["SIX_FIELD_REGRESSION"] == "PASS"
    assert "DECLARED_PROGRESS_UNBACKED: SIX_FIELD_REGRESSION" in result["warnings"]
    assert result["adjudication"]["outcome"] == "PENDING"
    assert result["declared_adjudication"]["outcome"] == "WINNER"
    assert record == before


def test_runtime_gates_reuse_evaluation_and_summary_does_not_evaluate_twice(monkeypatch):
    from rcwh.competition import CompetitionRegistry, PIPELINE
    from rcwh.literary_production import LiteraryProductionRuntime
    root = Path(__file__).resolve().parents[1]
    record = next(record for record in CompetitionRegistry.from_repo(root).records.values()
                  if record["mode"] == "PRODUCTION_43_0" and record["chapter"] == 89)
    calls = []
    report = {"candidate_results": [], "adjudication": {"outcome": "PENDING"},
              "derived_progress": {stage: "PENDING" for stage in PIPELINE},
              "warnings": [], "input_admission": {"status": "PENDING"}}
    registry = SimpleNamespace(records={record["id"]: record}, evaluate_record=lambda *args: calls.append(1) or report)
    monkeypatch.setattr(CompetitionRegistry, "from_repo", lambda _: registry)
    runtime = LiteraryProductionRuntime(root, {"sequence": [89]})
    assert runtime.summary()["active_gates"]["six_field"] == "PENDING"
    assert len(calls) == 1
    runtime.gates(89, registry, evaluation=report)
    assert len(calls) == 1
