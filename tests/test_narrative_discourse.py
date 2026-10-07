from pathlib import Path

from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.literary_production import LiteraryProductionRuntime, STABLE_SHA
from rcwh.literary_stress import ScenarioLiteraryStressRuntime
from rcwh.narrative_discourse import NarrativeDiscourseRuntime

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "SCN-CURRENT-C",
    "SCN-LATE-MARRIAGE",
    "SCN-JADE-MULTILAYER",
    "SCN-MINIMAL-CAUSE-OPEN",
}


def stress():
    return ScenarioLiteraryStressRuntime.from_repo(ROOT)


def discourse():
    return NarrativeDiscourseRuntime.from_repo(ROOT)


def ecology():
    return LiteraryEcologyRuntime.from_repo(ROOT)


def test_p5_compiles_exactly_twenty_discourse_cards():
    payload = discourse().evaluate_all(stress())
    assert payload["status"] == "PASS"
    assert payload["card_count"] == 20
    assert payload["winner"] is None
    assert payload["automatic_prose_generation"] is False


def test_p5_covers_exactly_the_four_p4_scenarios():
    assert set(discourse().data["source_basis"]["required_scenarios"]) == SCENARIOS
    assert set(discourse().data["scenario_overrides"]) == SCENARIOS
    assert set(stress().contracts) == SCENARIOS


def test_fabula_is_exact_passthrough_and_withheld_information_never_resolved():
    for scenario_id in SCENARIOS:
        payload = discourse().evaluate(scenario_id, stress())
        assert payload["status"] == "DISCOURSE_RUNTIME_READY"
        for card in payload["cards"]:
            probe = next(
                x for x in stress().contracts[scenario_id]["probes"]
                if x["id"] == card["probe_id"]
            )
            assert card["fabula_passthrough"]["ordinary_actions"] == probe["ordinary_actions"]
            assert card["fabula_passthrough"]["withheld_information"] == probe["withheld_information"]
            assert card["sjuzet_plan"]["resolved_withheld_information"] == []
            assert card["fabula_mutation"] == "NONE"


def test_all_cards_use_limited_narrator_and_forbid_authorial_explanation():
    for scenario_id in SCENARIOS:
        for card in discourse().evaluate(scenario_id, stress())["cards"]:
            p = card["sjuzet_plan"]
            assert p["narrator_access"] == "LIMITED"
            assert p["theme_statement_allowed"] is False
            assert p["narrator_motive_explanation_allowed"] is False
            assert p["institutional_exposition_allowed"] is False


def test_each_scenario_has_real_discourse_diversity():
    t = discourse().data["thresholds"]
    for scenario_id in SCENARIOS:
        c = discourse().evaluate(scenario_id, stress())["coverage"]
        assert len(c["temporal_modes"]) >= t["temporal_modes_min"]
        assert len(c["relay_channels"]) >= t["relay_channels_min"]
        assert len(c["opening_modes"]) >= t["opening_modes_min"]
        assert len(c["distance_curves"]) >= t["distance_curves_min"]
        assert len(c["exit_channels"]) >= t["exit_channels_min"]
        assert len(c["primary_focalizers"]) >= t["primary_focalizers_min"]
        assert c["indirect_cards"] >= t["indirect_cards_min"]


def test_current_c_direct_zhen_jia_encounter_is_not_allowed_to_become_philosophical_exposition():
    card = discourse().card("SCN-CURRENT-C", "C-P4", stress())
    p = card["sjuzet_plan"]
    assert p["primary_channel"] == "OBJECT_TRACE"
    assert p["reveal_policy"] == "CUSTODY_BEFORE_IDENTITY"
    assert "NO_TRUE_FALSE_PHILOSOPHICAL_DIALOGUE" in p["extra_restraints"]
    assert "NO_NARRATOR_JADE_IDENTITY_DECLARATION" in p["extra_restraints"]


def test_late_marriage_keeps_baochai_out_of_wife_pov_before_e2():
    card = discourse().card("SCN-LATE-MARRIAGE", "L-P1", stress())
    assert "BAOCHAI_NOT_WIFE_BEFORE_E2" in card["sjuzet_plan"]["extra_restraints"]
    assert "NO_FUTURE_WIFE_FREE_INDIRECT_LEAK" in card["sjuzet_plan"]["extra_restraints"]


def test_multilayer_jade_disambiguates_by_custody_not_narrator_labels():
    card = discourse().card("SCN-JADE-MULTILAYER", "J-P2", stress())
    p = card["sjuzet_plan"]
    assert p["reveal_policy"] == "CUSTODY_SPACE_PACKAGE_DISAMBIGUATION"
    assert "NO_OBJECT_IDENTITY_LABELS" in p["extra_restraints"]


def test_minimal_open_route_keeps_procedure_concrete_and_only_cause_open():
    card = discourse().card("SCN-MINIMAL-CAUSE-OPEN", "M-P2", stress())
    p = card["sjuzet_plan"]
    assert p["reveal_policy"] == "PROCEDURE_FULL_CAUSE_OPEN"
    assert "CAUSE_GAP_ONLY" in p["extra_restraints"]
    assert "NO_VAGUE_UNSPEAKABLE_CAUSE_ESCAPE" in p["extra_restraints"]


def test_p5_compare_never_ranks():
    payload = discourse().compare("SCN-CURRENT-C", "SCN-LATE-MARRIAGE", stress())
    assert payload["ranking"] is None
    assert payload["winner"] is None


def test_p5_integrity_and_canonical_literary_state_unchanged():
    assert discourse().validate_integrity(stress(), ecology()) == []
    literary = LiteraryProductionRuntime.from_repo(ROOT)
    assert literary.data["stable_active"]["sha256"] == STABLE_SHA
    assert literary.data["stable_active"]["changed"] is False
    assert literary.data["chapter89"]["plock_manual_review"] == "PENDING"
    assert literary.data["chapter89"]["blind_read"] == "PENDING"
