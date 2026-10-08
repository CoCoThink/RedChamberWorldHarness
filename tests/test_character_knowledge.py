from pathlib import Path

from rcwh.evaluate import evaluate_scene_text, overall_status
from rcwh.io import load_data
from rcwh.knowledge import CharacterKnowledgeRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.world import WorldRuntime


ROOT = Path(__file__).resolve().parents[1]
SLICE = {"baoyu", "daiyu", "zijuan", "baochai", "xiaohong", "qianxue"}


def runtime() -> CharacterKnowledgeRuntime:
    return CharacterKnowledgeRuntime.from_repo(ROOT)


def test_knowledge_preserves_supported_characters_and_four_buckets():
    summary = runtime().summary()
    assert SLICE <= set(summary["character_ids"])
    assert summary["characters"] == len(runtime().characters)
    assert summary["automatic_voice_identity"] is False
    for scene_id in runtime().scenes:
        payload = runtime().scene(scene_id, "ENTRY")
        for state in payload["states"].values():
            assert set(state) == {"knows", "believes", "suspects", "does_not_know"}


def test_event_driven_knowledge_update_moves_xiaohong_from_unknown_to_known():
    rt = runtime()
    assert rt.status(
        "ch92_delivery_gate", "xiaohong", "detention_delivery_rules", "ENTRY"
    ) == "does_not_know"
    assert rt.status(
        "ch92_delivery_gate",
        "xiaohong",
        "detention_delivery_rules",
        "K92-XIAOHONG-ASKS-GATE-RULES",
    ) == "knows"
    assert rt.status(
        "ch92_delivery_gate", "xiaohong", "baoyu_detention_whole_case", None
    ) == "does_not_know"


def test_event_driven_knowledge_update_preserves_zijuan_uncertainty_until_event():
    rt = runtime()
    assert rt.status(
        "ch86_last_night", "zijuan", "daiyu_death_exact_moment", "ENTRY"
    ) == "does_not_know"
    assert rt.status(
        "ch86_last_night",
        "zijuan",
        "daiyu_may_die_tonight",
        "K86-ZIJUAN-SEES-RAPID-DECLINE",
    ) == "suspects"
    assert rt.status(
        "ch86_last_night",
        "zijuan",
        "daiyu_death_exact_moment",
        "K86-DEATH-OCCURS",
    ) == "knows"


def test_scene_validator_catches_omniscient_dialogue_and_action():
    rt = runtime()
    contract = load_data(ROOT / "data/scenes/ch92_delivery_gate.yaml")
    dialogue = '小红道：“案情从头到尾我都知道。”'
    action = "小红已把宝玉的全案打听明白，回来便逐件说与众人。"
    for text in (dialogue, action):
        results = evaluate_scene_text(contract, text, knowledge_runtime=rt)
        knowledge = next(x for x in results if x.evaluator == "knowledge_omniscience")
        assert knowledge.status == "FAIL"
        assert knowledge.findings
        assert overall_status(results) == "FAIL"


def test_scene_validator_allows_rule_knowledge_after_learning_event():
    rt = runtime()
    contract = load_data(ROOT / "data/scenes/ch92_delivery_gate.yaml")
    contract = dict(contract)
    contract["knowledge_checkpoint"] = "K92-XIAOHONG-ASKS-GATE-RULES"
    contract["knowledge_guards"] = [
        {
            "id": "rules_after_asking",
            "actor": "xiaohong",
            "fact": "detention_delivery_rules",
            "modes": ["DIALOGUE"],
            "allowed_status": ["knows"],
            "any_text": ["这送东西的规矩我如今问明白了"],
        }
    ]
    payload = rt.text_guard(
        "ch92_delivery_gate",
        contract,
        '小红道：“这送东西的规矩我如今问明白了。”',
    )
    assert payload["status"] == "PASS"
    assert payload["checks"][0]["epistemic_status"] == "knows"


def test_voice_hooks_are_source_backed_for_five_and_abstain_for_qianxue():
    rt = runtime()
    for cid in SLICE - {"qianxue"}:
        profile = rt.voice(cid)
        assert profile["voice_profile"]["support"] == "SOURCE_BACKED"
        assert profile["voice_profile"]["source_ref"] == "asset:sha256:3a6c54bfac7be45f913a8f43d4869efe87a618a4161738f1424c20668ca24d9a"
        probe = rt.mask(cid, "寻常一句话。")
        assert probe["status"] == "READY_FOR_HUMAN_MASKING"
        assert probe["automatic_identity_pass"] is False
    qianxue = rt.voice("qianxue")
    assert qianxue["voice_profile"]["support"] == "SPARSE_ABSTAIN"
    assert qianxue["voice_profile"]["source_ref"] is None
    assert rt.mask("qianxue", "寻常一句话。")["status"] == "ABSTAIN_SPARSE_CORPUS"


def test_voice_mask_rejects_explicit_forbidden_modernized_or_omniscient_voice():
    rt = runtime()
    assert rt.mask("baochai", "作为管理者，这要讲绩效。")["status"] == "FAIL_FORBIDDEN_VOICE"
    assert rt.mask("xiaohong", "我什么都知道，案情我都清楚。")["status"] == "FAIL_FORBIDDEN_VOICE"
    assert rt.mask("qianxue", "案情从头到尾我都知道。")["status"] == "FAIL_FORBIDDEN_VOICE"


def test_scene_contracts_bind_knowledge_guards_and_voice_hooks():
    expected = {
        "ch86_last_night": {"baoyu", "daiyu", "zijuan"},
        "ch89_confiscation_message": {"baochai", "xiaohong", "qianxue"},
        "ch92_delivery_gate": {"baochai", "xiaohong", "qianxue", "baoyu"},
    }
    for scene_id, participants in expected.items():
        contract = load_data(ROOT / f"data/scenes/{scene_id}.yaml")
        assert contract["knowledge_guards"]
        assert set(contract["voice_profile_hooks"]).issubset(participants)
        assert set(contract["voice_profile_hooks"]).issubset(SLICE)


def test_character_knowledge_integrity_passes_world_and_literary_layers():
    assert runtime().validate_integrity(
        WorldRuntime.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT),
    ) == []
