from pathlib import Path

from rcwh.competition import CompetitionRegistry
from rcwh.completion import CompletionGateRuntime, STABLE_SHA
from rcwh.coverage import CoverageAuditRuntime
from rcwh.graph import ProvenanceGraph
from rcwh.history import HistoricalMechanismRegistry
from rcwh.implementation_alignment import ImplementationAlignmentRuntime
from rcwh.literals import LiteralRegistry
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.object_network import ObjectNetworkRuntime
from rcwh.open_interfaces import OpenInterfaceRegistry
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.promotion import PromotionRegistry
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.registry import MigrationRegistry
from rcwh.regression import run_r4_evidence_regression
from rcwh.world import WorldRuntime


ROOT = Path(__file__).resolve().parents[1]


def gate() -> CompletionGateRuntime:
    return CompletionGateRuntime.from_repo(ROOT)


def evaluate():
    registry = MigrationRegistry.from_repo(ROOT)
    coverage = CoverageAuditRuntime.from_repo(ROOT)
    graph = ProvenanceGraph.from_repo(ROOT)
    literals = LiteralRegistry.from_repo(ROOT)
    mechanisms = HistoricalMechanismRegistry.from_repo(ROOT)
    opens = OpenInterfaceRegistry.from_repo(ROOT)
    plocks = LiteraryProtectionRegistry.from_repo(ROOT)
    competitions = CompetitionRegistry.from_repo(ROOT)
    promotions = PromotionRegistry.from_repo(ROOT)
    return gate().evaluate(
        registry,
        coverage,
        ReconstructionRegistry.from_repo(ROOT),
        WorldRuntime.from_repo(ROOT),
        ObjectNetworkRuntime.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT),
        ImplementationAlignmentRuntime.from_repo(ROOT),
        graph,
        literals,
        mechanisms,
        opens,
        plocks,
        competitions,
        promotions,
        run_r4_evidence_regression(ROOT),
    )


def test_m8_state_is_persisted_pass_with_coverage_signoff():
    state = gate().state
    assert state["milestone"] == "M8"
    assert state["status"] == "PASS"
    assert all(state["milestone_status"][f"M{i}"] == "PASS" for i in range(9))
    assert state["coverage_signoff"] == {
        "signed": True,
        "p0_total": 249,
        "p0_full": 249,
        "p0_partial": 0,
        "p0_minimal": 0,
        "p0_none": 0,
        "current_documents": 15,
        "current_full": 15,
        "current_markdown_islands": 0,
        "unresolved_authority_conflicts": 0,
    }
    assert state["completion_gate"]["overall"] == "PASS"


def test_completion_gate_passes_all_checks():
    payload = evaluate()
    assert payload["overall"] == "PASS"
    assert payload["findings"] == []
    assert all(status == "PASS" for status in payload["checks"].values())


def test_completion_gate_preserves_stable_active_identity():
    payload = evaluate()
    assert payload["stable_active_sha256"] == STABLE_SHA
    assert payload["checks"]["STABLE_ACTIVE_UNCHANGED"] == "PASS"


def test_completion_gate_has_all_required_query_surfaces():
    payload = evaluate()
    for name in (
        "RECONSTRUCTION_QUERY",
        "TIMELINE_QUERY",
        "WORLD_QUERY",
        "CHARACTER_QUERY",
        "OBJECT_QUERY",
        "LITERARY_ECOLOGY_QUERY",
        "IMPLEMENTATION_QUERY",
    ):
        assert payload["checks"][name] == "PASS"


def test_completion_gate_keeps_evidence_open_history_and_plock_roles_non_conflicting():
    payload = evaluate()
    for name in (
        "EVIDENCE_CORE_REGRESSION",
        "OPEN_28_OPEN_LOCKED",
        "H01_H06_FEASIBILITY_ONLY",
        "PLOCK_LITERARY_ONLY",
        "NEGATIVE_ARCHIVE_NON_RUNTIME",
    ):
        assert payload["checks"][name] == "PASS"


def test_traceability_gate_has_all_registry_docs_and_all_p0_paths():
    registry = MigrationRegistry.from_repo(ROOT)
    coverage = CoverageAuditRuntime.from_repo(ROOT)
    graph = ProvenanceGraph.from_repo(ROOT)
    payload = gate().traceability(registry, coverage, graph)
    assert payload["status"] == "PASS"
    assert payload["registry_documents_with_concrete_paths"] == 65
    assert payload["registry_documents_total"] == 65
    assert payload["p0_concrete_paths"] == 249
    assert payload["p0_total"] == 249
    assert payload["missing_typed_doc_refs"] == []
    assert payload["provenance_graph_errors"] == []


def test_registry_publishes_final_gate_without_unfreezing_by_side_effect():
    current = MigrationRegistry.from_repo(ROOT).current_summary()
    assert current["migration_status"] == "COMPLETE"
    assert current["completion_gate_status"] == "PASS"
    assert current["completion_gate_ready"] is True
    assert current["coverage_report_signed_off"] is True
    assert current["literature_resume_authorized"] is True
    assert current["literature_frozen"] is True
    assert current["literature_resume_started"] is False


def test_gate_authorizes_later_literary_work_but_m8_does_not_start_it():
    payload = evaluate()
    assert payload["literature_resume_authorized"] is True
    assert payload["literature_resume_started"] is False
    assert gate().state["literature"]["migration_freeze_active"] is True
    assert gate().state["literature"]["resume_started"] is False


def test_pressure_queue_is_still_exactly_frozen_at_gate_pass():
    competitions = CompetitionRegistry.from_repo(ROOT).records
    assert competitions["comp:43-0:ch89:pressure-test"]["state"] == "IN_REVIEW"
    assert competitions["comp:43-0:ch92:pressure-test"]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert competitions["comp:43-0:ch97:pressure-test"]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert evaluate()["checks"]["LITERARY_FREEZE_PRESERVED_THROUGH_GATE"] == "PASS"


def test_m8_integrity_accepts_signed_gate():
    registry = MigrationRegistry.from_repo(ROOT)
    payload = evaluate()
    assert gate().validate_integrity(payload, registry) == []
