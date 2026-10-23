"""Research-only synthetic releases: no real prose editions are created."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rcwh.assets import AssetError
from rcwh.assets.transactions import digest
from rcwh.candidate_reviews import canonical_bytes
from rcwh.workflow.agent_panel import AgentPanel, register
from rcwh.workflow.agent_release import AgentRelease, _split


ROOT = Path(__file__).resolve().parents[1]


def write(root, path, value):
    raw = value.encode() if isinstance(value, str) else canonical_bytes(value)
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(raw)
    return {"path": path, "sha256": digest(raw)}


def packet(root, name, subjects):
    return write(root, f"research/{name}-packet.json", {
        "schema_version": 1, "packet_kind": "AGENT_REVIEW_PACKET", "id": name,
        "coordinator_session_id": "coordinator", "subjects": subjects,
        "authority_effect": "NONE", "usage": "RESEARCH_ONLY"})


def peers(root, binding, count=2, verdict="PASS", session_prefix="reader", severity=None):
    document = json.loads((root / binding["path"]).read_bytes())
    refs = []
    for i in range(count):
        opinion = {
            "schema_version": 1, "report_kind": "AGENT_REVIEW_OPINION", "packet": binding,
            "reviewer": {"id": f"{session_prefix}-{i}", "kind": "MODEL_SUBAGENT", "session_id": f"{session_prefix}-session-{i}",
                "model": {"label": "synthetic model", "verification": "DECLARED_NOT_VERIFIED"},
                "context_isolation": {"asserted": True, "verification": "NOT_PROVEN"}},
            "results": [{"subject_id": s["id"], "subject_sha256": s["binding"]["sha256"], "verdict": verdict,
                         "notes": "Synthetic recorded opinion", "sample_checks": [
                             {"sample_id": x["id"], "sha256": x["binding"]["sha256"], "verdict": verdict, "notes": "Synthetic sample opinion"}
                             for x in s.get("samples", [])]} for s in document["subjects"]],
            "authority_effect": "NONE", "usage": "RESEARCH_ONLY", "independent_human_admission": False}
        if severity is not None:
            for result in opinion["results"]:
                result["severity"] = severity
        original = write(root, f"research/{binding['sha256']}-{session_prefix}-{i}.json", opinion)
        refs.append(register(root, root / original["path"], origin="synthetic test session"))
    return refs


@pytest.fixture
def edition(tmp_path, monkeypatch):
    for name in ("agent_release_manifest", "promotion_policy", "project_scope", "agent_packet", "agent_review"):
        write(tmp_path, f"schemas/{name}.schema.json", json.loads((ROOT / f"schemas/{name}.schema.json").read_bytes()))
    write(tmp_path, "data/project/scope.json", {"schema_version": 1, "chapters": [86, 87]})
    write(tmp_path, "data/project/current.json", {"stable": "DO_NOT_CHANGE"})
    write(tmp_path, "releases/stable/ACTIVE.json", {"stable": "DO_NOT_CHANGE"})
    baseline_text = "Research fixture\n\n# 第八十六回 原题\n\n" + "原文" * 500 + "\n\n# 第八十七回 后题\n\n" + "旧文" * 500 + "\n\n"
    baseline = write(tmp_path, "releases/stable/baseline.md", baseline_text)
    candidate = write(tmp_path, "artifacts/candidate.md", "# 第八十六回 新题\n\n" + "新文" * 500 + "\n\n")
    package = write(tmp_path, "data/packages/ch86.json", {"chapter": 86})
    contract = write(tmp_path, "data/scenes/ch86.json", {"chapter": 86, "id": "synthetic-contract"})
    candidate_packet = packet(tmp_path, "candidate", [
        {"id": "candidate", "scope": "CANDIDATE", "binding": candidate},
        {"id": "package", "scope": "PACKAGE", "binding": package},
        {"id": "contract", "scope": "CONTRACT", "binding": contract}])
    resolved = SimpleNamespace(id="asset:baseline", sha256=baseline["sha256"], size=len(baseline_text.encode()),
                               relative_path=baseline["path"], path=tmp_path / baseline["path"])
    catalog = SimpleNamespace(assets={"asset:baseline": {"immutable": True}}, resolve=lambda ref: resolved)
    monkeypatch.setattr("rcwh.workflow.agent_release.AssetCatalog.from_repo", lambda root: catalog)
    request = {"schema_version": 1, "id": "synthetic-edition", "baseline": {"asset_ref": "asset:baseline", "sha256": baseline["sha256"]},
               "chapters": [{"chapter": 86, "mode": "AGENT_CANDIDATE", "candidate": candidate,
                             "plock_ref": "plock:ch86:cold-medicine", "minimum_body_characters": 800,
                             "minimum_baseline_ratio": 0.8, "writing_package": package,
                             "panel": {"packet": candidate_packet, "subject_id": "candidate"}},
                            {"chapter": 87, "mode": "NOT_NEW_AUTHORED"}]}
    runtime = AgentRelease(tmp_path)
    return SimpleNamespace(root=tmp_path, runtime=runtime, request=request, candidate=candidate,
                           packet=candidate_packet, baseline=baseline, package=package, contract=contract, catalog=catalog)


def decide(e, outcome="ADOPT"):
    subject = AgentPanel(e.root).summary(e.packet)["panels"][0]["subjects"][0]
    decision = {"schema_version": 1, "decision_kind": "AGENT_RELEASE_COORDINATOR_DECISION", "chapter": 86,
                "candidate": e.candidate, "outcome": outcome, "coordinator_session_id": "coordinator",
                "rationale": "Explicit synthetic coordinator rationale, not a score winner",
                "considered_opinions": [o["record"] for o in subject["opinions"]],
                "rejected_opinions": [{"record": o["record"], "rationale": "Dissent retained; cannot override FAIL"}
                                      for o in subject["opinions"] if o["verdict"] in {"FAIL", "REJECT"}],
                "authority_effect": "NONE"}
    e.request["chapters"][0]["decision"] = write(e.root, "research/decision.json", decision)
    return decision


def positive_gates(e, monkeypatch):
    """Isolate publication I/O; actual packet registration/count/decision remain real."""
    peers(e.root, e.packet)
    decide(e)
    monkeypatch.setattr(e.runtime, "_policy", lambda *args: "PASS")
    monkeypatch.setattr(e.runtime, "_authors", lambda *args: ("PASS", [{"principal_id": "session:author"}]))
    monkeypatch.setattr(e.runtime, "_compatibility", lambda *args: ("PASS", {"compatibility": "CURRENT"}))
    monkeypatch.setattr(e.runtime, "_inputs", lambda row, **kwargs: ({"WRITING_PACKAGE": "PASS", "CONTRACT_PEERS": "PASS", "SOURCE_PEERS": "PASS", "CORPUS_PEERS": "PASS"}, {}))


@pytest.mark.parametrize("segmented", [False, True])
def test_two_whole_book_negatives_remain_advisory_and_do_not_change_gates(edition, monkeypatch, segmented):
    e = edition
    positive_gates(e, monkeypatch)
    before, book = e.runtime._evaluate(e.request)
    _, prose = _split(book.decode(), (86, 87))
    binding = write(e.root, "research/book.md", "".join(prose.values()) if segmented else book.decode())
    ref = packet(e.root, "book", [{"id": "continuity", "scope": "BOOK", "binding": binding,
                                   **({"chapters": [86, 87]} if segmented else {}),
                                   "review_policy": "ADVISORY"}])
    e.request["book_review"] = {"packet": ref, **({"subject_ids": ["continuity"]} if segmented else {"subject_id": "continuity"})}
    peers(e.root, ref, verdict="FAIL", session_prefix="book-reader")
    report = e.runtime.evaluate(e.request)
    assert report["status"] == before["status"] == "PASS"
    assert report["gates"] == before["gates"]
    advisory = report["advisories"]["book_continuity"]
    assert advisory["status"] == "PASS" and advisory["gate_effect"] == "NONE"
    subject = advisory["panels"][0]["subjects"][0]
    assert subject["distinct_reviewer_count"] == 2
    assert len(subject["advisories"]) == 2 and not subject["findings"]
    # A stale book packet is visible as invalid, never called reviewed or gated.
    (e.root / binding["path"]).write_text("stale")
    changed = e.runtime.evaluate(e.request)
    assert changed["status"] == "PASS"
    assert changed["advisories"]["book_continuity"]["status"] == "INVALID"


def test_no_reviews_are_pending_not_adopted_and_only_manifest_can_stage(edition):
    e = edition
    # Missing inputs stay pending; a missing writing-package proof is not PASS.
    e.request["chapters"][0].pop("writing_package")
    report = e.runtime.evaluate(e.request)
    assert report["status"] == "PENDING"
    changed = report["chapters"][0]
    assert changed["gates"]["CANDIDATE_PEERS"] == "PENDING"
    assert changed["gates"]["AUTHOR_PROVENANCE"] == "PENDING"
    assert changed["gates"]["CHAPTER_SAFETY_POLICY"] == "PENDING"
    assert report["output"]["text"] is None
    assert report["provenance"] == "RESEARCH_AGENT_PENDING"
    with pytest.raises(AssetError, match="PENDING"):
        e.runtime.build(e.request)
    built = e.runtime.build(e.request, allow_pending=True)
    directory = e.root / built["output"]["directory"]
    assert sorted(p.name for p in directory.iterdir()) == ["manifest.json"]
    assert json.loads((directory / "manifest.json").read_bytes()) == built
    assert built["chapters"][1]["provenance"] == "NOT_NEW_AUTHORED"


def test_reviewed_build_exact_full_scope_and_stable_storage_unchanged(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    snapshot = e.runtime._stable_snapshot()
    report = e.runtime.build(e.request)
    assert report["status"] == "PASS"
    assert report["provenance"] == "RESEARCH_AGENT_REVIEWED"
    assert report["independent_human_admission"] is False
    assert report["automatic_winner"] is False
    assert report["scope"] == [86, 87]
    assert report["changed_chapters"] == [86]
    text = (e.root / report["output"]["text"]["path"]).read_bytes()
    before = _split((e.root / e.baseline["path"]).read_text(), (86, 87))[1]
    after = _split(text.decode(), (86, 87))[1]
    assert after[86].encode() == (e.root / e.candidate["path"]).read_bytes()
    assert after[87] == before[87]
    assert report["chapters"][1]["integrity"] == report["chapters"][1]["baseline"]
    assert e.runtime._stable_snapshot() == snapshot
    assert digest(text) == report["output"]["text"]["sha256"]


def test_current_input_failure_does_not_become_an_author_provenance_failure(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    monkeypatch.setattr(e.runtime, '_compatibility', lambda row: ('FAIL', {
        'compatibility': 'STALE', 'findings': ['selected writing inputs changed']}))
    report = e.runtime.evaluate(e.request)
    chapter = report['chapters'][0]
    assert chapter['gates']['AUTHOR_PROVENANCE'] == 'PASS'
    assert chapter['gates']['CURRENT_WRITING_INPUTS'] == 'FAIL'
    assert report['status'] == 'FAIL' and report['output']['text'] is None


def test_length_cannot_hide_repeated_numbered_padding(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    text = "# 第八十六回 新题\n\n" + "\n\n".join(
        f"平儿将钥匙重新系紧，绳结太短，拆开一次便要重新打。这是第{i}次清点后的细小阻滞，仍需下一只手来接。"
        for i in range(40))
    e.request['chapters'][0]['candidate'] = write(e.root, e.candidate['path'], text)
    report = e.runtime.evaluate(e.request)
    assert report['status'] == 'FAIL'
    assert report['chapters'][0]['gates']['FULL_CHAPTER_LENGTH'] == 'PASS'
    assert report['chapters'][0]['gates']['PROSE_INTEGRITY'] == 'FAIL'
    assert report['output']['text'] is None


def test_no_overwrite_even_empty_output_directory(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    report = e.runtime.build(e.request)
    before = (e.root / report["output"]["manifest_path"]).read_bytes()
    with pytest.raises(AssetError, match="refusing overwrite"):
        e.runtime.build(e.request)
    assert (e.root / report["output"]["manifest_path"]).read_bytes() == before
    e.request["id"] = "empty-existing"
    (e.root / "releases/agent/empty-existing").mkdir()
    with pytest.raises(AssetError, match="refusing overwrite"):
        e.runtime.build(e.request)


def test_smoke_preserves_completed_edition_and_checks_exact_rebuilt_book(edition, monkeypatch):
    from tools.verify_agent_release import preserve_existing_release, compare_release_manifests
    e = edition
    positive_gates(e, monkeypatch)
    write(e.root, "research/request.json", e.request)
    original = e.runtime.build(e.request)
    snapshot = e.runtime._stable_snapshot()
    quarantine = e.root.parent / "preserved-edition"
    stored = preserve_existing_release(e.root, "research/request.json", quarantine)
    assert stored == original and (quarantine / "manifest.json").exists()
    rebuilt = e.runtime.build(e.request)
    assert compare_release_manifests(stored, rebuilt) == []
    assert (quarantine / "book.md").read_bytes() == (e.root / rebuilt["output"]["text"]["path"]).read_bytes()
    assert e.runtime._stable_snapshot() == snapshot
    # Corruption must fail before moving the existing artifact.
    (e.root / rebuilt["output"]["text"]["path"]).write_text("corrupt")
    with pytest.raises(ValueError, match="mismatch"):
        preserve_existing_release(e.root, "research/request.json", e.root.parent / "bad-copy")
    assert (e.root / rebuilt["output"]["manifest_path"]).exists()


def test_smoke_manifest_comparison_allows_only_named_runtime_observations():
    from tools.verify_agent_release import compare_release_manifests
    from rcwh.corpus.extraction import toolchain_diff
    registered = {"extractor": {"python": "CPython 3.12.13", "code_sha256": "a" * 64}}
    old = {"status": "PASS", "scope": "EXTRACTION_CONTENT_REBUILD", "output_sha256": "b" * 64,
           "registered_toolchain": registered, "current_toolchain": deepcopy(registered), "toolchain_diff": {}}
    new = deepcopy(old)
    new["current_toolchain"]["extractor"]["python"] = "CPython 3.12.3"
    new["toolchain_diff"] = toolchain_diff(registered, new["current_toolchain"])
    def manifest(rebuild):
        return {"chapters": [{"reviews": {"source_reviews": [{"source_proof": {
            "verification_report": {"rebuild": rebuild}}}]}}]}
    before, after = manifest(old), manifest(new)
    assert len(compare_release_manifests(before, after)) == 1
    for field in ("output_sha256", "status"):
        changed = deepcopy(after)
        changed["chapters"][0]["reviews"]["source_reviews"][0]["source_proof"]["verification_report"]["rebuild"][field] = "WRONG"
        with pytest.raises(ValueError, match="differs"):
            compare_release_manifests(before, changed)
    forged = deepcopy(after)
    forged["chapters"][0]["reviews"]["source_reviews"][0]["source_proof"]["verification_report"]["rebuild"]["toolchain_diff"] = {}
    with pytest.raises(ValueError, match="differs"):
        compare_release_manifests(before, forged)
    changed = deepcopy(after)
    changed["chapters"][0]["reviews"]["source_reviews"][0]["source_proof"]["verification_report"]["rebuild"]["current_toolchain"]["extractor"]["code_sha256"] = "c" * 64
    changed_rebuild = changed["chapters"][0]["reviews"]["source_reviews"][0]["source_proof"]["verification_report"]["rebuild"]
    changed_rebuild["toolchain_diff"] = toolchain_diff(registered, changed_rebuild["current_toolchain"])
    with pytest.raises(ValueError, match="differs"):
        compare_release_manifests(before, changed)


def test_publish_failure_rolls_back_both_files_without_marker(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    real_link = __import__("os").link
    def fail_marker(source, target):
        if target.name == "manifest.json":
            raise OSError("synthetic publish interruption")
        real_link(source, target)
    monkeypatch.setattr("rcwh.workflow.agent_release.os.link", fail_marker)
    with pytest.raises(OSError, match="interruption"):
        e.runtime.build(e.request)
    assert not (e.root / "releases/agent/synthetic-edition").exists()
    assert not list((e.root / "releases/agent").glob(".staging-*"))


def test_last_minute_input_change_prevents_any_publish(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    real = e.runtime._evaluate
    calls = []
    def mutate(request):
        result = real(request)
        calls.append(True)
        if len(calls) == 1:
            (e.root / "data/project/current.json").write_text('{"stable":"CHANGED_ELSEWHERE"}')
        return result
    monkeypatch.setattr(e.runtime, "_evaluate", mutate)
    with pytest.raises(AssetError, match="stable storage changed"):
        e.runtime.build(e.request)
    assert not (e.root / "releases/agent/synthetic-edition").exists()


@pytest.mark.parametrize("count", [0, 1])
def test_at_least_two_real_registered_reviews_required(edition, monkeypatch, count):
    e = edition
    peers(e.root, e.packet, count=count)
    decide(e)
    monkeypatch.setattr(e.runtime, "_inputs", lambda row, **kwargs: ({}, {}))
    report = e.runtime.evaluate(e.request)
    assert report["chapters"][0]["gates"]["CANDIDATE_PEERS"] == "PENDING"
    assert report["status"] == "PENDING"


@pytest.mark.parametrize("outcome", ["PENDING", "TIE", "NEUTRAL"])
def test_coordinator_neutral_tie_cannot_auto_select_from_scores(edition, monkeypatch, outcome):
    e = edition
    positive_gates(e, monkeypatch)
    decide(e, outcome)
    report = e.runtime.evaluate(e.request)
    assert report["status"] == "PENDING"
    assert report["chapters"][0]["gates"]["COORDINATOR_DECISION"] == "PENDING"
    assert report["output"]["text"] is None


def test_blocking_negative_review_prevails_over_positive_and_coordinator_adopt(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    peers(e.root, e.packet, count=1, verdict="REJECT", session_prefix="dissent")
    decide(e)
    report = e.runtime.evaluate(e.request)
    assert report["status"] == "FAIL"
    # An undeclared-severity rejection is BLOCKING: the coordinator may record
    # a reasoned ruling, but cannot lift the failed peer gate.
    assert report["chapters"][0]["gates"]["CANDIDATE_PEERS"] == "FAIL"
    assert report["chapters"][0]["gates"]["COORDINATOR_DECISION"] == "PASS"
    with pytest.raises(AssetError, match="FAIL"):
        e.runtime.build(e.request, allow_pending=True)


def test_advisory_dissent_overruled_by_coordinator_still_builds_research_edition(edition, monkeypatch):
    """E.g. a plan-card detail differing from the prose: reported, not a gate."""
    e = edition
    positive_gates(e, monkeypatch)
    peers(e.root, e.packet, count=1, verdict="FAIL", session_prefix="dissent", severity="ADVISORY")
    decision = decide(e)
    assert len(decision["rejected_opinions"]) == 1
    report = e.runtime.build(e.request)
    chapter = report["chapters"][0]
    assert report["status"] == chapter["gates"]["CANDIDATE_PEERS"] == chapter["gates"]["COORDINATOR_DECISION"] == "PASS"
    assert [a["severity"] for a in chapter["reviews"]["candidate"]["advisories"]] == ["ADVISORY"]
    assert (e.root / report["output"]["text"]["path"]).is_file()
    assert report["independent_human_admission"] is False and report["stable_active_effect"] == "NONE"


def test_new_opinion_requires_new_bound_coordinator_decision(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    peers(e.root, e.packet, count=1, session_prefix="third")
    report = e.runtime.evaluate(e.request)
    assert report["chapters"][0]["gates"]["CANDIDATE_PEERS"] == "PASS"
    assert report["chapters"][0]["gates"]["COORDINATOR_DECISION"] == "PENDING"


def test_split_contract_dissent_requires_consideration_and_reasoned_disposition(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    raw = json.loads((e.root / f"research/{e.packet['sha256']}-reader-0.json").read_bytes())
    raw["reviewer"]["id"] = "contract-only-reader"
    raw["reviewer"]["session_id"] = "contract-only-session"
    raw["results"] = [{**r, "verdict": "FAIL", "severity": "ADVISORY"} for r in raw["results"] if r["subject_id"] == "contract"]
    opinion = write(e.root, "research/contract-dissent.json", raw)
    dissent = register(e.root, e.root / opinion["path"], origin="synthetic contract-only dissent")
    contract = next(s for s in AgentPanel(e.root).summary(e.packet)["panels"][0]["subjects"] if s["scope"] == "CONTRACT")
    monkeypatch.setattr(e.runtime, "_inputs", lambda *a, **k: ({k: "PASS" for k in
        ("WRITING_PACKAGE", "CONTRACT_PEERS", "SOURCE_PEERS", "CORPUS_PEERS")}, {"contract_reviews": [contract]}))
    assert e.runtime.evaluate(e.request)["chapters"][0]["gates"]["COORDINATOR_DECISION"] == "PENDING"
    decision = json.loads((e.root / e.request["chapters"][0]["decision"]["path"]).read_bytes())
    decision["considered_opinions"].append(dissent["record"])
    e.request["chapters"][0]["decision"] = write(e.root, "research/decision-considered.json", decision)
    assert e.runtime.evaluate(e.request)["chapters"][0]["gates"]["COORDINATOR_DECISION"] == "PENDING"
    decision["rejected_opinions"].append({"record": dissent["record"], "rationale": "Synthetic explicit disposition of this contract objection"})
    e.request["chapters"][0]["decision"] = write(e.root, "research/decision-resolved.json", decision)
    assert e.runtime.evaluate(e.request)["status"] == "PASS"


def test_pending_stage_does_not_reserve_final_edition_id(edition, monkeypatch):
    e = edition
    pending = e.runtime.build(e.request, allow_pending=True)
    assert "/.pending/" in pending["output"]["directory"]
    assert e.runtime.build(e.request, allow_pending=True) == pending
    positive_gates(e, monkeypatch)
    final = e.runtime.build(e.request)
    assert final["status"] == "PASS" and final["output"]["directory"] == "releases/agent/synthetic-edition"
    assert (e.root / pending["output"]["manifest_path"]).exists()


def test_new_book_opinion_produces_new_pending_snapshot_without_overwriting(edition):
    e = edition
    _, book = e.runtime._evaluate(e.request)
    binding = write(e.root, "research/book.md", book.decode())
    ref = packet(e.root, "book", [{"id": "continuity", "scope": "BOOK", "binding": binding, "review_policy": "ADVISORY"}])
    e.request["book_review"] = {"packet": ref, "subject_id": "continuity"}
    before = e.runtime.build(e.request, allow_pending=True)
    peers(e.root, ref, count=1, session_prefix="book-reader")
    after = e.runtime.build(e.request, allow_pending=True)
    assert before["status"] == after["status"] == "PENDING"
    assert before["output"]["directory"] != after["output"]["directory"]
    assert all((e.root / m["output"]["manifest_path"]).exists() for m in (before, after))


@pytest.mark.parametrize("text", ["# 第八十七回 错回\n\n" + "文" * 1000,
    "# 第八十六回 空回\n\n", "# 第八十六回 第一\n正文\n# 第八十六回 第二\n正文\n",
    "# 第八十六回 短摘\n\n" + "文" * 10])
def test_chapter_heading_body_and_minimum_length_fail_precedence(edition, monkeypatch, text):
    e = edition
    positive_gates(e, monkeypatch)
    e.request["chapters"][0]["candidate"] = write(e.root, "artifacts/wrong.md", text)
    report = e.runtime.evaluate(e.request)
    assert report["status"] == "FAIL"
    assert report["output"]["text"] is None
    assert report["chapters"][0]["status"] == "FAIL"


def test_cannot_lower_minimum_ratio_to_replace_full_chapter_with_excerpt(edition):
    e = edition
    e.request["chapters"][0]["minimum_baseline_ratio"] = 0.01
    with pytest.raises(AssetError, match="request"):
        e.runtime.evaluate(e.request)


@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate"])
def test_full_scope_dispositions_are_mandatory(edition, fault):
    e = edition
    if fault == "missing":
        e.request["chapters"].pop()
    elif fault == "extra":
        e.request["chapters"].append({"chapter": 88, "mode": "NOT_NEW_AUTHORED"})
    else:
        e.request["chapters"].append(deepcopy(e.request["chapters"][0]))
    with pytest.raises(AssetError):
        e.runtime.evaluate(e.request)


@pytest.mark.parametrize("name", ["../stable", "/tmp/escape", "ACTIVE", "stable/ACTIVE"])
def test_release_id_cannot_control_output_path(edition, name):
    edition.request["id"] = name
    with pytest.raises(AssetError):
        edition.runtime.evaluate(edition.request)


@pytest.mark.parametrize("path", ["../escape.md", "/tmp/escape.md", "artifacts/../candidate.md", "artifacts\\candidate.md"])
def test_candidate_path_safety(edition, monkeypatch, path):
    e = edition
    positive_gates(e, monkeypatch)
    e.request["chapters"][0]["candidate"]["path"] = path
    assert e.runtime.evaluate(e.request)["status"] == "FAIL"


def test_symlink_output_and_candidate_are_refused(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    symlink = e.root / "artifacts/link.md"
    symlink.symlink_to(e.root / e.candidate["path"])
    e.request["chapters"][0]["candidate"] = {**e.candidate, "path": "artifacts/link.md"}
    assert e.runtime.evaluate(e.request)["status"] == "FAIL"
    e.request["chapters"][0]["candidate"] = e.candidate
    (e.root / "releases/agent").symlink_to(e.root / "releases/stable", target_is_directory=True)
    with pytest.raises(AssetError, match="symlink"):
        e.runtime.build(e.request)


def test_declared_agent_pass_field_cannot_bypass_gates(edition):
    edition.request["AGENT"] = "PASS"
    with pytest.raises(AssetError, match="request"):
        edition.runtime.evaluate(edition.request)


@pytest.mark.parametrize("status,evaluator", [("UNKNOWN", "LITERARY_PLOCK_V1"), ("SUPPORTED", "DECLARED_PASS")])
def test_unknown_or_unsupported_safety_policy_pending(edition, monkeypatch, status, evaluator):
    e = edition
    positive_gates(e, monkeypatch)
    # Restore actual policy code; all other gates independently pass.
    monkeypatch.setattr(e.runtime, "_policy", AgentRelease._policy.__get__(e.runtime))
    policy = json.loads((ROOT / "data/promotion/policies/ch86.json").read_bytes())
    policy.update(status=status, evaluator=evaluator)
    e.request["chapters"][0]["policy"] = write(e.root, "data/promotion/policies/ch86.json", policy)
    report = e.runtime.evaluate(e.request)
    assert report["status"] == "PENDING"
    assert report["chapters"][0]["gates"]["CHAPTER_SAFETY_POLICY"] == "PENDING"


def test_missing_policy_pending_even_other_gates_pass(edition, monkeypatch):
    e = edition
    positive_gates(e, monkeypatch)
    monkeypatch.setattr(e.runtime, "_policy", AgentRelease._policy.__get__(e.runtime))
    report = e.runtime.evaluate(e.request)
    assert report["status"] == "PENDING"
    assert report["chapters"][0]["gates"]["CHAPTER_SAFETY_POLICY"] == "PENDING"


def test_author_or_any_reviser_session_cannot_review_own_candidate(edition, monkeypatch):
    e = edition
    peers(e.root, e.packet)
    run = write(e.root, "research/run.json", {"session_id": "reader-session-0"})
    draft = write(e.root, "research/draft.json", {})
    row = e.request["chapters"][0]
    row["draft"] = draft
    monkeypatch.setattr("rcwh.generation.writing.load_draft", lambda root, path: ({
        "execution_basis": "SESSION_AUTHORED_NOT_PROVIDER_VERIFIED", "candidate": e.candidate,
        "chapter": 86, "package": e.package, "run": run, "authors": [{"principal_id": "session:reader-session-0"}], "parent": None},
        (e.root / e.candidate["path"]).read_text()))
    subject = AgentPanel(e.root).summary(e.packet)["panels"][0]["subjects"][0]
    with pytest.raises(AssetError, match="author/reviser"):
        e.runtime._authors(row, subject)


@pytest.mark.parametrize("missing_contracts", [False, True])
def test_input_scope_source_corpus_and_contracts_are_separate_gates(edition, monkeypatch, missing_contracts):
    e = edition
    # Missing required sources/corpus cannot be repaired by candidate reviews.
    exemplar = write(e.root, "data/exemplars/ch86.json", {"dataset_ref": "synthetic-dataset", "segments": []})
    e.request["chapters"][0]["writing_package"] = write(e.root, "data/packages/ch86-new.json", {"chapter": 86, "exemplar_set": exemplar})
    # New package bytes require a new packet rather than hidden normalization.
    e.packet = packet(e.root, "updated", [
        {"id": "candidate", "scope": "CANDIDATE", "binding": e.candidate},
        {"id": "package", "scope": "PACKAGE", "binding": e.request["chapters"][0]["writing_package"]},
        {"id": "contract", "scope": "CONTRACT", "binding": e.contract}])
    e.request["chapters"][0]["panel"]["packet"] = e.packet
    peers(e.root, e.packet)
    monkeypatch.setattr("rcwh.workflow.admission.chapter_scope", lambda root, path, **kwargs: {
        "chapter": 86, "paths": [e.package["path"], e.contract["path"]], "used_source_ids": ["source:needed"],
        "dataset_refs": ["synthetic-dataset"], "findings": ["CHAPTER_SCENE_SCOPE_MISSING"] if missing_contracts else []})
    gates, _ = e.runtime._inputs(e.request["chapters"][0])
    assert gates == {"WRITING_PACKAGE": "PASS", "CONTRACT_PEERS": "PENDING" if missing_contracts else "PASS", "SOURCE_PEERS": "PENDING", "CORPUS_PEERS": "PENDING"}


def test_missing_review_packet_is_pending_input_not_failure(edition):
    e = edition
    (e.root / e.packet["path"]).unlink()
    report = e.runtime.evaluate(e.request)
    gates = report["chapters"][0]["gates"]
    assert gates["CANDIDATE_PEERS"] == "PENDING"
    assert report["status"] == "PENDING"
    assert any("packet not found" in p for p in report["chapters"][0]["pending"])


def test_chapter_without_dependent_sources_or_corpus_needs_no_such_reviews(edition, monkeypatch):
    e = edition
    exemplar = write(e.root, "data/exemplars/ch86.json", {"dataset_ref": "synthetic-dataset", "segments": []})
    e.request["chapters"][0]["writing_package"] = write(e.root, "data/packages/ch86-new.json", {"chapter": 86, "exemplar_set": exemplar})
    e.packet = packet(e.root, "no-sources", [
        {"id": "candidate", "scope": "CANDIDATE", "binding": e.candidate},
        {"id": "package", "scope": "PACKAGE", "binding": e.request["chapters"][0]["writing_package"]},
        {"id": "contract", "scope": "CONTRACT", "binding": e.contract}])
    e.request["chapters"][0]["panel"]["packet"] = e.packet
    peers(e.root, e.packet)
    monkeypatch.setattr("rcwh.workflow.admission.chapter_scope", lambda root, path, **kwargs: {
        "chapter": 86, "paths": [e.package["path"], e.contract["path"]], "used_source_ids": [],
        "dataset_refs": [], "findings": []})
    gates, reports = e.runtime._inputs(e.request["chapters"][0])
    assert gates["SOURCE_PEERS"] == gates["CORPUS_PEERS"] == "PASS"
    assert "SOURCE_PEERS: NO_DEPENDENT_SOURCES" in reports["info"]
