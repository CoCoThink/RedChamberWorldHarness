from copy import deepcopy
from pathlib import Path

from rcwh.graph import ProvenanceGraph
from rcwh.history import HistoricalMechanismRegistry
from rcwh.literals import LiteralRegistry
from rcwh.open_interfaces import OpenInterfaceRegistry
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.regression import run_r4_evidence_regression


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def registries():
    graph = ProvenanceGraph.from_repo(root())
    literals = LiteralRegistry.from_repo(root())
    mechanisms = HistoricalMechanismRegistry.from_repo(root())
    opens = OpenInterfaceRegistry.from_repo(root())
    plocks = LiteraryProtectionRegistry.from_repo(root())
    regression = run_r4_evidence_regression(root())
    return graph, literals, mechanisms, opens, plocks, regression


def test_evidence_core_stays_frozen_under_plock_layer():
    result = run_r4_evidence_regression(root())
    assert result["overall"] == "PASS"


def test_first_literary_layer_has_five_high_risk_plocks():
    _, _, _, _, plocks, _ = registries()
    assert set(plocks.locks) == {
        "plock:ch86:cold-medicine",
        "plock:ch89:small-life-after-confiscation",
        "plock:ch92:procedure-density",
        "plock:ch97:miaoyu-object-progression",
        "plock:ch100:record-keeper-ending",
    }


def test_all_plocks_are_literary_only_and_on_stable_active():
    graph, literals, mechanisms, opens, plocks, regression = registries()
    assert plocks.validate_integrity(
        graph, literals, mechanisms, opens, regression["stable_active"]
    ) == []
    for item in plocks.locks.values():
        assert item["authority"] == "LITERARY_PROTECTION_ONLY"
        assert item["active_prose_locator"]["file_sha256"] == regression["stable_active"]["sha256"]


def test_plock_cannot_be_used_as_upstream_decision_evidence():
    graph, literals, mechanisms, opens, plocks, regression = registries()
    broken = deepcopy(graph)
    broken.decisions["decision:daiyu:death-direction"]["based_on"].append(
        "plock:ch86:cold-medicine"
    )
    errors = plocks.validate_integrity(
        broken, literals, mechanisms, opens, regression["stable_active"]
    )
    assert any("downstream P-Lock" in e for e in errors)


def test_ch86_keeps_cold_terminal_and_no_complete_death_poem():
    lock = LiteraryProtectionRegistry.from_repo(root()).locks[
        "plock:ch86:cold-medicine"
    ]
    anchors = {x["text"] for x in lock["exact_anchors"]}
    assert "那盏药早已冷透，再没有人去温。" in anchors
    assert any("绝命诗" in x for x in lock["forbidden_drift"])


def test_ch92_keeps_density_cap_and_two_character_functions():
    lock = LiteraryProtectionRegistry.from_repo(root()).locks[
        "plock:ch92:procedure-density"
    ]
    assert lock["legacy_ref"] == "G-P92-02"
    features = {x["id"]: x["mode"] for x in lock["required_features"]}
    assert features["procedure-cap"] == "DENSITY_CAP"
    assert "xiaohong-capability" in features
    assert "qianxue-socks" in features


def test_ch97_keeps_object_progression_and_xichun_ambiguity():
    lock = LiteraryProtectionRegistry.from_repo(root()).locks[
        "plock:ch97:miaoyu-object-progression"
    ]
    anchors = {x["text"] for x in lock["exact_anchors"]}
    assert "从前也有数。" in anchors
    assert "谁同你说我件件想得明白？" in anchors
    assert any(x["id"] == "basin-dedicated-to-shared" for x in lock["required_features"])


def test_ch100_keeps_record_keeper_and_terminal_line():
    lock = LiteraryProtectionRegistry.from_repo(root()).locks[
        "plock:ch100:record-keeper-ending"
    ]
    assert lock["legacy_ref"] == "G-P100-04"
    assert any(x["text"] == "石在，字在。" for x in lock["exact_anchors"])
    assert any(x["id"] == "record-not-interpret" for x in lock["required_features"])
