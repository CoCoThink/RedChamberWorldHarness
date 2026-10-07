from pathlib import Path

from rcwh.competition import CompetitionRegistry
from rcwh.completion import CompletionGateRuntime
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA


ROOT = Path(__file__).resolve().parents[1]


def runtime() -> LiteraryProductionRuntime:
    return LiteraryProductionRuntime.from_repo(ROOT)


def competitions() -> CompetitionRegistry:
    return CompetitionRegistry.from_repo(ROOT)


def test_post_m8_literary_production_runtime_is_canonical_and_active():
    summary = runtime().summary()
    assert summary["phase"] == "43-0-resume"
    assert summary["status"] == "ACTIVE"
    assert summary["stable_sha256"] == STABLE_SHA
    assert summary["stable_changed"] is False
    assert summary["migration_freeze_released"] is True
    assert summary["literary_resume_started"] is True
    assert summary["active_chapter"] == 89


def test_ch89_is_not_adjudicated_before_manual_plock_and_real_blind_read():
    summary = runtime().summary()
    assert summary["ch89_gates"] == {
        "six_field": "PASS",
        "machine_literary_evaluation": "PASS",
        "manual_plock": "PENDING",
        "blind_read": "PENDING",
        "adjudication": "PENDING",
    }
    record = competitions().records["comp:43-0:ch89:pressure-test"]
    assert record["state"] == "IN_REVIEW"
    assert record["adjudication"]["outcome"] == "PENDING"
    assert record["adjudication"]["winner_candidate_id"] is None
    assert record["adjudication"]["promotion_state"] == "NOT_ELIGIBLE"


def test_ch92_and_ch97_remain_blocked_by_predecessor():
    summary = runtime().summary()
    assert summary["chapter_states"][92] == "BLOCKED_BY_PREDECESSOR"
    assert summary["chapter_states"][97] == "BLOCKED_BY_PREDECESSOR"
    assert competitions().records["comp:43-0:ch92:pressure-test"]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert competitions().records["comp:43-0:ch97:pressure-test"]["state"] == "BLOCKED_BY_PREDECESSOR"


def test_divergent_ch89_phase2_branch_is_quarantined_non_runtime():
    q = runtime().quarantine()
    assert q["status"] == "PASS"
    assert q["canonical_literary_branch"] == "literary/43-0-resume"
    fork = next(
        x for x in q["quarantined_forks"]
        if x["branch"] == "literary/43-0-ch89-phase2"
    )
    assert fork["head_sha"] == "69d406034960fc656ec1184425ae788ff18b6182"
    assert fork["state"] == "QUARANTINED_NON_RUNTIME"
    assert fork["merge_policy"] == "DO_NOT_MERGE"
    assert "artifacts/43-0/ch89/ADJUDICATION.md" in fork["reject_as_authority"]
    assert "any automatic transition of Chapter 92 to READY_FOR_CANDIDATES" in fork["reject_as_authority"]


def test_five_obsolete_work_branches_are_explicitly_safe_to_delete():
    branches = {
        x["branch"] for x in runtime().governance["safe_delete_when_tool_available"]
    }
    assert branches == {
        "feature/provenance-kernel-v0.2",
        "feature/r4-evidence-core-v0.2-beta",
        "feature/literary-plock-v0.3-alpha",
        "migration/full-v3",
        "release/post-merge-signoff-v3",
    }


def test_issue_audit_closes_completed_items_and_preserves_real_residuals():
    audit = runtime().governance["issue_audit"]
    assert audit["closed_completed"] == [1, 2, 3, 4, 5]
    assert audit["open_partial"] == [6]


def test_literary_production_runtime_integrity_passes():
    assert runtime().validate_integrity(
        CompletionGateRuntime.from_repo(ROOT),
        competitions(),
    ) == []


def test_stable_active_remains_unchanged_while_branch_governance_is_cleaned():
    assert runtime().data["stable_active"]["sha256"] == STABLE_SHA
    assert runtime().data["stable_active"]["changed"] is False
    for record in competitions().records.values():
        assert record["baseline"]["sha256"] == STABLE_SHA
        assert record["stable_active_effect"] == "SEPARATE_PROMOTION_ONLY"
