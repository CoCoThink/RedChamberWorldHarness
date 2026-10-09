"""Constraint replay tests. Synthetic readers/programs are not a model benchmark."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
from test_candidate_reviews import reviewed_competition

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluate import evaluate_scene_text, overall_status
from rcwh.evaluation.semantics import make_request, check_reading, run_extractor
from rcwh.evaluation.state import SceneStateAdapter, canonical_target
from rcwh.io import load_data
from rcwh.knowledge import CharacterKnowledgeRuntime

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_data(ROOT / "data/scenes/ch86_last_night.yaml")
SCHEMA = load_data(ROOT / "schemas/semantic_reading.schema.json")
KNOWLEDGE = CharacterKnowledgeRuntime.from_repo(ROOT)
TEXT = '紫鹃搁下未饮完的药碗，挑了挑灯。黛玉的手松开，再也没有气息。宝玉说：“再温一温。”药已经冷了。'


def event(text, quote, name, order, actor="NARRATOR", **kwargs):
    start = text.index(quote)
    return dict(id=name, order=order, actor=actor, mode="NARRATION", scope="ACTUAL",
                spans=[dict(start=start, end=start+len(quote), quote=quote)], beats=[],
                violations=[], effects=[], knowledge=[], observations=[], observers=[], **kwargs)


def positive(text=TEXT):
    request = make_request(CONTRACT, text, SceneStateAdapter(ROOT, CONTRACT).snapshot(),
                           [{"principal_id": "test:author", "source_id": "test:author-origin", "kind": "HUMAN"}])
    targets = [b["id"] for b in CONTRACT["required_beats"] + CONTRACT["forbidden_beats"]]
    targets += [canonical_target(c["equals"]) for c in CONTRACT["exit_state"]]
    targets += [g["id"] for g in CONTRACT["knowledge_guards"]]
    events = [event(text, "紫鹃搁下未饮完的药碗，挑了挑灯。", "housework", 10, "zijuan"),
              event(text, "黛玉的手松开，再也没有气息。", "death", 20),
              event(text, "再温一温", "warming", 30, "baoyu"),
              event(text, "药已经冷了。", "cold", 40)]
    events[0].update(mode="ACTION", beats=["medicine_not_finished", "ordinary_domestic_labor_continues"])
    events[1]["effects"] = [{"target": "character.daiyu.life_state", "value": "dead"}]
    events[2].update(mode="DIALOGUE", beats=["baoyu_mundane_reaction"])
    events[3]["effects"] = [{"target": "object.medicine_bowl_86.temperature", "value": "cold"}]
    reading = {"schema_version": 1, "report_kind": "REVIEW_OPINION",
               **{k: request[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")},
               "producer": {"principal_id": "test:reader", "source_id": "test:reader-origin", "kind": "INDEPENDENT_HUMAN"},
               "coverage": targets, "unresolved": [], "events": events,
               "notes": "Synthetic attributed reading for replay tests; no actual human review."}
    return request, reading


def check(request, reading):
    return check_reading(request, reading, SCHEMA, KNOWLEDGE, ROOT)


@pytest.mark.parametrize("case", load_data(ROOT / "data/evaluation/semantic_challenges.json")["cases"])
def test_archived_editor_challenges_fail_through_actual_scene_evaluator(case):
    text = (ROOT / case["text_path"]).read_bytes().decode()
    results = evaluate_scene_text(CONTRACT, text, knowledge_runtime=KNOWLEDGE, root=ROOT)
    assert overall_status(results) == case["expected"] == "FAIL"
    semantic = next(r.details for r in results if r.evaluator == "scene_semantics")
    assert semantic["automatic_literary_pass"] is False
    if case["id"] == "negated-poem":
        assert next(c for c in semantic["checks"] if c["id"] == "complete_death_poem")["status"] == "PASS"


def test_no_reading_and_paraphrase_variants_cannot_pass():
    results = evaluate_scene_text(CONTRACT, "药碗 再温一温 灯。\n", root=ROOT)
    assert overall_status(results) == "PENDING"
    request, _ = positive()
    assert check(request, None)["status"] == "PENDING"


def test_indirect_death_and_cold_are_established_from_exact_text():
    request, reading = positive()
    report = check(request, reading)
    assert report["status"] == "PASS"
    assert {e["value"] for e in report["state_changes"]} == {"dead", "cold"}
    assert report["evidence_effect"] == "NONE"


@pytest.mark.parametrize("scope", ["NEGATED", "DREAM", "HYPOTHETICAL", "METAPHOR", "QUOTED"])
def test_nonactual_forbidden_event_does_not_count_as_violation(scope):
    request, reading = positive()
    reading["events"][0].update(scope=scope, violations=["supernatural_resolution"])
    report = check(request, reading)
    assert next(c for c in report["checks"] if c["id"] == "supernatural_resolution")["status"] == "PASS"
    assert report["status"] == "FAIL"  # actual required housework absent


def test_exit_uses_last_actual_change_and_rejects_recovery():
    request, reading = positive()
    recovered = deepcopy(reading["events"][1])
    recovered.update(id="recovery", order=50)
    recovered["effects"][0]["value"] = "active"
    reading["events"].append(recovered)
    assert check(request, reading)["status"] == "FAIL"
    recovered["scope"] = "DREAM"
    assert check(request, reading)["status"] == "PASS"


@pytest.mark.parametrize("fault", ["stale", "span", "scope", "speech", "coverage"])
def test_unbound_or_incomplete_state_table_cannot_qualify(fault):
    request, reading = positive()
    if fault == "stale": reading["candidate_sha256"] = "0"*64
    if fault == "span": reading["events"][1]["spans"][0]["quote"] = "伪造的引文"
    if fault == "scope": reading["events"][1]["scope"] = "HYPOTHETICAL"
    if fault == "speech": reading["events"][1]["mode"] = "DIALOGUE"
    if fault == "coverage": reading["coverage"].pop()
    assert check(request, reading)["status"] in {"FAIL", "PENDING"}


def test_self_annotation_and_internal_agent_cannot_issue_positive_qualification():
    request, reading = positive()
    reading["producer"]["source_id"] = request["authors"][0]["source_id"]
    assert check(request, reading)["status"] == "PENDING"
    reading["producer"].update(source_id="different", kind="INTERNAL_AGENT")
    assert check(request, reading)["status"] == "PENDING"


def test_knowledge_assertion_before_observation_fails_after_observation_passes():
    request, reading = positive()
    fact = "daiyu_death_exact_moment"
    assertion = {"actor": "baoyu", "fact": fact, "operation": "ASSERT", "status": "knows", "source_event": None}
    reading["events"][2]["knowledge"] = [assertion]
    assert check(request, reading)["status"] == "FAIL"
    reading["events"][1].update(observations=[fact], observers=["baoyu"])
    reading["events"][2]["knowledge"].insert(0, {**assertion, "operation": "ACQUIRE", "source_event": "death"})
    assert check(request, reading)["status"] == "PASS"
    reading["events"][1]["observers"] = ["zijuan"]
    assert check(request, reading)["status"] == "FAIL"


def test_inner_character_knowledge_is_guarded_and_duplicate_exits_rejected():
    request, reading = positive()
    reading["events"][2].update(mode="THOUGHT", knowledge=[{"actor": "baoyu", "fact": "daiyu_death_exact_moment", "operation": "ASSERT", "status": "knows", "source_event": None}])
    assert check(request, reading)["status"] == "FAIL"
    contract = deepcopy(CONTRACT)
    contract["exit_state"].append({"equals": "object.medicine_bowl_86.temperature", "value": "warm"})
    with pytest.raises(ValueError, match="duplicate"): make_request(contract, TEXT)


def test_frozen_knowledge_replay_does_not_read_later_world_entry():
    request, reading = positive()
    fact = "daiyu_death_exact_moment"
    reading["events"][2]["knowledge"] = [{"actor": "baoyu", "fact": fact, "operation": "ASSERT", "status": "knows", "source_event": None}]
    changed = deepcopy(KNOWLEDGE)
    buckets = changed.scenes[CONTRACT["id"]]["entry"]["baoyu"]
    for facts in buckets.values():
        if fact in facts: facts.remove(fact)
    buckets["knows"].append(fact)
    assert changed.status(CONTRACT["id"], "baoyu", fact) == "knows"
    assert check_reading(request, reading, SCHEMA, changed, ROOT)["status"] == "FAIL"
    assert check_reading(request, reading, SCHEMA, None, ROOT)["status"] == "FAIL"
    reading["events"][1].update(observations=[fact], observers=["baoyu"])
    reading["events"][2]["knowledge"].insert(0, {"actor": "baoyu", "fact": fact, "operation": "ACQUIRE", "status": "knows", "source_event": "death"})
    assert check_reading(request, reading, SCHEMA, None, ROOT)["status"] == "PASS"


def test_narrator_and_suspicion_do_not_assert_character_knowledge():
    request, reading = positive()
    update = {"actor": "baoyu", "fact": "daiyu_death_exact_moment", "operation": "ASSERT", "status": "suspects", "source_event": None}
    reading["events"][2]["knowledge"] = [update]
    assert check(request, reading)["status"] == "PASS"
    update["status"] = "knows"
    reading["events"][2]["mode"] = "NARRATION"
    assert check(request, reading)["status"] == "PASS"


def test_knowledge_exit_requires_observed_acquisition_not_a_filled_state_flag():
    request, reading = positive()
    fact = "daiyu_death_exact_moment"
    contract = deepcopy(CONTRACT)
    target = "character.baoyu.knowledge." + fact
    contract["exit_state"].append({"equals": target, "value": "knows"})
    request = make_request(contract, request["text"], request["entry"], request["authors"])
    reading.update({k: request[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")})
    reading["coverage"].append(target)
    assert check(request, reading)["status"] == "FAIL"
    reading["events"][1].update(observations=[fact], observers=["baoyu"])
    reading["events"][2]["knowledge"] = [{"actor": "baoyu", "fact": fact, "operation": "ACQUIRE", "status": "knows", "source_event": "death"}]
    assert check(request, reading)["status"] == "PASS"
    reading["events"][1]["mode"] = "THOUGHT"
    assert check(request, reading)["status"] == "FAIL"


def test_model_program_cannot_relabel_its_response_as_human_opinion():
    request, reading = positive()
    producer = {"principal_id": "fixture:model", "source_id": "fixture:model", "kind": "MODEL"}
    program = "import sys;sys.stdin.read();print(" + repr(json.dumps(reading)) + ")"
    assert run_extractor(request, [sys.executable, "-c", program], producer, SCHEMA)["status"] == "FAIL"


@pytest.mark.parametrize("program", ["raise SystemExit(3)", "print('not JSON')", "print('{}')"])
def test_extractor_failure_records_actual_io_and_never_falls_back(program):
    request, reading = positive()
    trace = run_extractor(request, [sys.executable, "-c", program], reading["producer"], SCHEMA)
    assert trace["status"] == "FAIL"
    assert digest(trace["input"].encode()) == trace["input_sha256"]
    assert json.loads(trace["input"])["request"] == request


def test_actual_model_trace_replay_and_tamper_detection(tmp_path):
    request, reading = positive()
    producer = dict(principal_id="test:model-reader", source_id="test:model-origin", kind="MODEL",
                    model=dict(provider="synthetic", name="fixture", version="1", family="fixture"))
    reading["producer"] = producer
    # This is a program fixture, explicitly not a real model capability result.
    program = "import sys;sys.stdin.read();print(" + repr(json.dumps(reading)) + ")"
    trace = run_extractor(request, [sys.executable, "-c", program], producer, SCHEMA)
    raw = canonical_bytes(trace); (tmp_path / "trace.json").write_bytes(raw)
    reading["producer"] = {**producer, "trace": dict(path="trace.json", sha256=digest(raw))}
    assert check_reading(request, reading, SCHEMA, KNOWLEDGE, tmp_path)["status"] == "PASS"
    reading["notes"] = "Altered after actual execution"
    assert check_reading(request, reading, SCHEMA, KNOWLEDGE, tmp_path)["status"] == "FAIL"


def test_model_family_independence_uses_bound_author_execution(tmp_path):
    import shutil
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    request, reading = positive()
    run = {"schema_version": 1, "source_id": "fixture:author-model",
           "model": dict(provider="fixture", name="fixture", version="1", family="same-family", session="test"),
           "prompt": "fixture", "prompt_sha256": digest(b"fixture"), "prompt_summary": "Synthetic only",
           "input": "fixture", "input_sha256": digest(b"fixture"), "output": TEXT, "output_sha256": digest(TEXT.encode())}
    raw = canonical_bytes(run); (tmp_path / "author.json").write_bytes(raw)
    authors = [dict(principal_id="fixture:author", source_id=run["source_id"], kind="MODEL", run=dict(path="author.json", sha256=digest(raw)))]
    request = make_request(CONTRACT, TEXT, request["entry"], authors)
    reading.update({k: request[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")})
    reading["producer"] = dict(principal_id="fixture:reader-model", source_id="fixture:different-session",
                               kind="MODEL", model=dict(provider="fixture", name="fixture", version="2", family="same-family"),
                               trace=dict(path="not-used-for-same-family.json", sha256="0"*64))
    report = check_reading(request, reading, SCHEMA, KNOWLEDGE, tmp_path)
    assert report["status"] == "PENDING"
    assert "AUTHOR_AND_EXTRACTOR_SHARE_MODEL_FAMILY" in report["pending"]


def test_extractor_timeout_cannot_produce_a_semantic_pass():
    request, reading = positive()
    trace = run_extractor(request, [sys.executable, "-c", "import time;time.sleep(1)"], reading["producer"], SCHEMA, timeout=0.05)
    assert trace["status"] == "FAIL" and trace["returncode"] is None
    assert trace["findings"] == ["EXTRACTOR_TIMEOUT"]


def test_good_readers_do_not_override_missing_semantic_qualification(reviewed_competition, monkeypatch):
    from rcwh.competition import CompetitionRegistry
    root, record, _ = reviewed_competition
    monkeypatch.setattr("rcwh.competition.run_r4_evidence_regression", lambda _: {"overall": "PASS"})
    monkeypatch.setattr("rcwh.competition.evaluate_literary_candidate", lambda *a, **k: {"machine_status": "READY_FOR_BLIND_READ"})
    monkeypatch.setattr("rcwh.competition.candidate_semantics", lambda *a: {"status": "PENDING", "reports": []})
    record["adjudication"].update(outcome="PENDING", winner_candidate_id=None, promotion_state="NOT_ELIGIBLE")
    report = CompetitionRegistry({}).evaluate_record(root, record)
    assert all(c["review_qualification"]["status"] == "PASS" for c in report["candidate_results"])
    assert not any(c["adjudication_eligible"] for c in report["candidate_results"])
