from pathlib import Path

from rcwh.evaluate import evaluate_scene_text, overall_status
from rcwh.history import HistoricalMechanismRegistry
from rcwh.io import load_data
from rcwh.mechanism_adapters import HistoricalAdapterRuntime
from rcwh.assets import AssetCatalog


ROOT = Path(__file__).resolve().parents[1]


def runtime() -> HistoricalAdapterRuntime:
    return HistoricalAdapterRuntime.from_repo(ROOT)


def mechanisms() -> HistoricalMechanismRegistry:
    return HistoricalMechanismRegistry.from_repo(ROOT)


def test_issue4_defines_all_required_adapters_without_plot_authority():
    rt = runtime()
    assert rt.adapters
    assert "confiscation" in rt.adapters
    assert rt.summary()["effect"] == "FEASIBILITY_ONLY"
    for adapter in rt.adapters.values():
        assert adapter["effect"] == "FEASIBILITY_ONLY"
        assert adapter["plot_authority"] == "NONE"
        assert adapter["may_create_events"] is False


def test_h_backed_adapters_preserve_all_open_and_cannot_prove_boundaries():
    rt = runtime()
    mech = mechanisms()
    for adapter_id, adapter in rt.adapters.items():
        payload = rt.describe(adapter_id, mech)
        for mechanism_id in adapter["mechanism_refs"]:
            mechanism = mech.mechanisms[mechanism_id]
            for item in mechanism["open"]:
                assert item in payload["effective_open_questions"]
            for item in mechanism["cannot_prove"]:
                assert item in payload["effective_cannot_prove"]


def test_transport_and_monastic_profiles_remain_open_research_not_fake_history():
    rt = runtime()
    for adapter_id in ("transport_letters", "monastic_economy"):
        adapter = rt.adapters[adapter_id]
        assert adapter["research_status"] == "OPEN_RESEARCH"
        assert adapter["mechanism_refs"] == []
        assert adapter["open_questions"]
        payload = rt.scene_status(
            {"id": "probe", "historical_adapters": [adapter_id]},
            "这里只写人物跑腿与日常生活，不宣称制度细节。",
            mechanisms(),
        )
        assert payload["status"] == "PASS"
        assert payload["findings"][0]["status"] == "PASS_WITH_OPEN"
        assert payload["findings"][0]["plot_authority"] == "NONE"


def test_ch86_medical_and_household_first_implementation_passes_candidate_b():
    rt = runtime()
    contract = load_data(ROOT / "data/scenes/ch86_last_night.yaml")
    text = (
        ROOT / "artifacts/43-0/ch86/candidates/ch86_B_light_full.md"
    ).read_text(encoding="utf-8")
    payload = rt.scene_status(contract, text, mechanisms())
    assert payload["status"] == "PASS"
    assert [x["adapter"] for x in payload["findings"]] == [
        "medical",
        "household_economy",
    ]
    assert all(x["status"] == "PASS" for x in payload["findings"])
    assert all(x["missing_required_groups"] == [] for x in payload["findings"])
    assert all(x["forbidden_hits"] == [] for x in payload["findings"])


def test_ch86_adapter_rejects_missing_process_signals_without_inventing_plot():
    contract = load_data(ROOT / "data/scenes/ch86_last_night.yaml")
    payload = runtime().scene_status(contract, "黛玉静静坐着。", mechanisms())
    assert payload["status"] == "FAIL"
    by_id = {x["adapter"]: x for x in payload["findings"]}
    assert by_id["medical"]["reason"] == "MISSING_FEASIBILITY_SIGNAL"
    assert by_id["household_economy"]["reason"] == "MISSING_FEASIBILITY_SIGNAL"
    assert all(x["plot_authority"] == "NONE" for x in payload["findings"])


def test_ch86_adapter_rejects_historical_overclaim():
    contract = load_data(ROOT / "data/scenes/ch86_last_night.yaml")
    text = (
        ROOT / "artifacts/43-0/ch86/candidates/ch86_B_light_full.md"
    ).read_text(encoding="utf-8")
    text += "\n史料已经证明黛玉必用此方。"
    payload = runtime().scene_status(contract, text, mechanisms())
    medical = next(x for x in payload["findings"] if x["adapter"] == "medical")
    assert payload["status"] == "FAIL"
    assert medical["reason"] == "HISTORICAL_OVERCLAIM"
    assert medical["forbidden_hits"] == ["史料已经证明黛玉必用此方"]


def test_scene_evaluator_exposes_structured_adapter_details():
    contract = load_data(ROOT / "data/scenes/ch86_last_night.yaml")
    text = (
        ROOT / "artifacts/43-0/ch86/candidates/ch86_B_light_full.md"
    ).read_text(encoding="utf-8")
    results = evaluate_scene_text(
        contract,
        text,
        mechanism_adapter_runtime=runtime(),
        historical_mechanisms=mechanisms(),
    )
    by_name = {x.evaluator: x for x in results}
    assert by_name["historical_adapter:medical"].status == "PASS"
    assert by_name["historical_adapter:medical"].details["plot_authority"] == "NONE"
    assert by_name["historical_adapter:household_economy"].details["open_questions"]
    assert overall_status(results) == "PASS"


def test_adapter_integrity_passes_registry_and_historical_core():
    assert runtime().validate_integrity(
        mechanisms(),
        AssetCatalog.from_repo(ROOT),
    ) == []
