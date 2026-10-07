import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_m0_baseline_freezes_stable_active_until_completion_gate():
    baseline = load_json("data/migration/m0_baseline.json")
    regression = load_yaml("data/regression/r4_evidence_core.yaml")["regression_manifests"][0]

    assert baseline["milestone"] == "M0"
    assert baseline["status"] == "PASS"
    assert baseline["stable_active"]["frozen"] is True
    assert baseline["migration_freeze"]["completion_gate_reached"] is False
    assert baseline["stable_active"]["actual_sha256"] == STABLE_SHA
    assert regression["stable_active"]["sha256"] == STABLE_SHA


def test_literary_pressure_queue_freeze_is_preserved_in_m6_historical_fixture():
    m6 = load_json("data/implementation_alignment/m6.json")
    by_chapter = {
        item["chapter"]: item for item in m6["competition_fixtures"]
    }

    assert by_chapter[89]["state"] == "IN_REVIEW"
    assert by_chapter[89]["progress"] == "PHASE1_ONLY"
    assert by_chapter[89]["freeze_effect"] == "DO_NOT_CONTINUE_PHASE2"
    assert by_chapter[92]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert by_chapter[92]["freeze_effect"] == "DO_NOT_START"
    assert by_chapter[97]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert by_chapter[97]["freeze_effect"] == "DO_NOT_START"


def test_deferred_ch86_candidate_cannot_mutate_stable_active():
    promotion = load_yaml("data/promotions/ch86.yaml")["promotions"][0]

    assert promotion["baseline"]["sha256"] == STABLE_SHA
    assert promotion["stable_active_effect"] == "NONE"
    assert promotion["release_action"] == "SEPARATE_EXPLICIT_PROMOTION_REQUIRED"
