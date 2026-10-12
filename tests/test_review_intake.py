"""Receive only synthetic opinions in tiny temporary repositories.

The source/corpus/p9 fixtures exercise real schema, receipt and lane checks.
Scene production discovery is patched only where explicitly marked below.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from rcwh.application import reviews as review_command
from rcwh.assets import AssetCatalog
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluation.semantics import make_request
from rcwh.workflow import review_intake as intake
from test_source_audit import extraction_repo, audit_source_repo  # noqa: F401
from test_corpus_audit import corpus_repo, audit_repo  # noqa: F401
from test_corpus_dataset import DATASET
from test_paired_review import paired_repo  # noqa: F401
from test_pilot_review_selection import pilot, opinion as pilot_opinion, selection as pilot_selection  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_LANES = ("source", "corpus-pilot", "corpus-full", "p9")
ORIGIN = "test:synthetic-intake-only"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return path


def owner_files(root):
    """Snapshot owned files, not rebuildable caches or the intake lock."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()
            and ".rcwh-cache" not in path.relative_to(root).parts}


def selected_record(root, lane):
    selected = json.loads((root / intake.selection_path(lane)).read_bytes())
    binding = selected["readings" if lane == "scene-reading" else "reviews"][-1]
    raw = (root / binding["path"]).read_bytes()
    assert digest(raw) == binding["sha256"]
    return binding, json.loads(raw)


def assert_received(root, report, submitted):
    raw = AssetCatalog.from_repo(root).resolve(report["raw_review"]["asset_ref"])
    assert raw.sha256 == report["raw_review"]["sha256"] == digest(submitted.read_bytes())
    assert raw.path.read_bytes() == submitted.read_bytes()
    assert AssetCatalog.from_repo(root).assets[raw.id]["kind"] == "REVIEW_RECORD"


def add_closure(root, lane, *, stale=False):
    relative = intake.selection_path(lane)
    closure = {"records": [{"path": relative,
                            "sha256": "0" * 64 if stale else digest((root / relative).read_bytes())},
                           {"path": "untouched.json", "sha256": "a" * 64}]}
    save(root / intake.CLOSURE, closure)
    return closure


@pytest.fixture(params=PROTOCOL_LANES)
def intake_lane(request, monkeypatch):
    lane = request.param
    if lane == "source":
        root, source, _, selected = request.getfixturevalue("audit_source_repo")
        original = {"protocol_sha256": selected["protocol"]["sha256"],
                    "reviewer": {"id": "fixture:reader", "kind": "INDEPENDENT_HUMAN",
                                 "independent_of_corrections": True},
                    "results": [{"source_ref": source["id"], "carrier_edition_confirmed": True,
                                 "excerpt_valid": True, "witness_tier_unchanged": True,
                                 "claim_impact_reviewed": True, "notes": "Synthetic fixture only"}]}
    elif lane in ("corpus-pilot", "corpus-full"):
        root, protocol, selected, _ = request.getfixturevalue("audit_repo")
        # The shared fixture has two chapters, not the production front-80 corpus.
        monkeypatch.setitem(intake.DATASETS, lane, DATASET)
        original = {"dataset_ref": DATASET, "manifest_sha256": protocol["manifest_sha256"],
                    "protocol_sha256": selected["protocol"]["sha256"],
                    "reviewer": {"id": "fixture:reader", "kind": "INDEPENDENT_HUMAN",
                                 "independent_of_builder": True},
                    "main_boundaries_confirmed": True, "unknown_witnesses_acknowledged": True,
                    "unaligned_segments_acknowledged": True,
                    "checks": [{"segment_id": row["segment_id"], "layer_valid": True,
                                "locator_valid": True, "context_valid": True,
                                "notes": "Synthetic fixture only"} for row in protocol["samples"]]}
    else:
        root, selected, mapping = request.getfixturevalue("paired_repo")
        original = {"protocol_sha256": selected["protocol"]["sha256"],
                    "packet_sha256": selected["packet"]["sha256"],
                    "reviewer": {"id": "fixture:reader", "kind": "INDEPENDENT_HUMAN",
                                 "independent_of_authors": True, "mapping_unseen_during_review": True},
                    "pairs": [{"pair_id": row["pair_id"], "preference": "A",
                               "scores": {"voice": {"A": 4, "B": 3}},
                               "reason": "Synthetic fixture only"} for row in mapping["pairs"]]}
    return SimpleNamespace(root=root, lane=lane, original=original)


def submit(lane, tmp_path, *, identity="fixture:opinion", dry_run=False):
    path = save(tmp_path / "submitted.json", lane.original)
    return path, intake.register(lane.root, lane.lane, path, origin=ORIGIN,
                                 identity=identity, dry_run=dry_run)


def test_register_positive_opinion_binds_raw_and_does_not_grant_authority(intake_lane, tmp_path):
    lane = intake_lane
    path, report = submit(lane, tmp_path)
    assert report["registered"] is True
    assert report["status"] == ("PENDING" if lane.lane == "p9" else "PASS")
    assert report["authority_effect"] == report["evidence_effect"] == "NONE"
    assert report["automatic_literary_pass"] is False
    assert report["lane_report"]["review_count"] == 1
    binding, record = selected_record(lane.root, lane.lane)
    assert record["id"] == "fixture:opinion" and record["schema_version"] == 1
    assert record["raw_review"] == report["raw_review"]
    assert {k: v for k, v in record.items()
            if k not in {"schema_version", "id", "raw_review", "authority_effect"}} == lane.original
    assert binding["path"] in report["written_files"]
    assert_received(lane.root, report, path)


@pytest.mark.parametrize("intake_lane", ["source", "corpus-pilot", "corpus-full"], indirect=True)
def test_false_checks_are_received_retained_and_reported_fail(intake_lane, tmp_path):
    lane = intake_lane
    if lane.lane == "source":
        lane.original["results"][0]["excerpt_valid"] = False
    else:
        lane.original["checks"][0]["context_valid"] = False
        lane.original["main_boundaries_confirmed"] = False
    path, report = submit(lane, tmp_path)
    assert report["status"] == "FAIL" and report["registered"] is True
    assert report["lane_report"]["review_count"] == 1
    assert report["lane_report"]["findings"]
    _, record = selected_record(lane.root, lane.lane)
    if lane.lane == "source":
        assert record["results"][0]["excerpt_valid"] is False
    else:
        assert record["checks"][0]["context_valid"] is False
        assert record["main_boundaries_confirmed"] is False
    assert_received(lane.root, report, path)


@pytest.mark.parametrize("fault", ["null", "unknown", "metadata", "stale", "duplicate-key"])
def test_invalid_original_does_not_mutate_owner_files(intake_lane, tmp_path, fault):
    lane = intake_lane
    original = deepcopy(lane.original)
    if fault == "null":
        original["reviewer"]["id"] = None
    elif fault == "unknown":
        original["unapproved"] = True
    elif fault == "metadata":
        original["authority_effect"] = "NONE"
    elif fault == "stale":
        original["protocol_sha256"] = "0" * 64
    path = save(tmp_path / "invalid.json", original)
    if fault == "duplicate-key":
        raw = path.read_bytes()
        path.write_bytes(b'{"protocol_sha256":"' + original["protocol_sha256"].encode() + b'",' + raw[1:])
    before = owner_files(lane.root)
    with pytest.raises(ValueError):
        intake.register(lane.root, lane.lane, path, origin=ORIGIN)
    assert owner_files(lane.root) == before


@pytest.mark.parametrize("fault", ["scope", "duplicate-row", "lane-binding"])
def test_protocol_scope_and_lane_bindings_fail_before_raw_intake(intake_lane, tmp_path, fault):
    lane = intake_lane
    row_key, identity_key = {"source": ("results", "source_ref"),
                             "corpus-pilot": ("checks", "segment_id"),
                             "corpus-full": ("checks", "segment_id"),
                             "p9": ("pairs", "pair_id")}[lane.lane]
    if fault == "scope":
        lane.original[row_key][0][identity_key] = "unknown:synthetic-object"
    elif fault == "duplicate-row":
        lane.original[row_key].append(deepcopy(lane.original[row_key][0]))
    elif lane.lane == "p9":
        lane.original["packet_sha256"] = "0" * 64
    elif lane.lane == "source":
        lane.original["protocol_sha256"] = "0" * 64
    else:
        lane.original["manifest_sha256"] = "0" * 64
    path = save(tmp_path / "invalid-binding.json", lane.original)
    before = owner_files(lane.root)
    with pytest.raises(ValueError):
        intake.register(lane.root, lane.lane, path, origin=ORIGIN)
    assert owner_files(lane.root) == before


@pytest.mark.parametrize("fault", ["blank-origin", "blank-id", "symlink"])
def test_intake_rejects_missing_custody_or_symlink_original(intake_lane, tmp_path, fault):
    lane = intake_lane
    path = save(tmp_path / "submitted.json", lane.original)
    if fault == "symlink":
        link = tmp_path / "linked.json"
        link.symlink_to(path)
        path = link
    before = owner_files(lane.root)
    with pytest.raises(ValueError):
        intake.register(lane.root, lane.lane, path,
                        origin="  " if fault == "blank-origin" else ORIGIN,
                        identity="  " if fault == "blank-id" else None)
    assert owner_files(lane.root) == before


@pytest.mark.parametrize("duplicate", ["id", "reviewer", "original"])
def test_duplicate_opinion_does_not_mutate_owner_files(intake_lane, tmp_path, duplicate):
    lane = intake_lane
    submit(lane, tmp_path)
    if duplicate != "original":
        row_key = {"source": "results", "corpus-pilot": "checks", "corpus-full": "checks", "p9": "pairs"}[lane.lane]
        note_key = "reason" if lane.lane == "p9" else "notes"
        lane.original[row_key][0][note_key] = "A distinct synthetic original"
        if duplicate == "id":
            lane.original["reviewer"]["id"] = "fixture:another-reader"
    path = save(tmp_path / "second.json", lane.original)
    before = owner_files(lane.root)
    with pytest.raises(ValueError, match="重复|已有"):
        intake.register(lane.root, lane.lane, path, origin=ORIGIN,
                        identity="fixture:opinion" if duplicate == "id" else "fixture:other-opinion")
    assert owner_files(lane.root) == before


def test_dry_run_has_no_owner_mutations_or_raw_intake(intake_lane, tmp_path):
    lane = intake_lane
    add_closure(lane.root, lane.lane)
    before = owner_files(lane.root)
    _, report = submit(lane, tmp_path, dry_run=True)
    assert report["status"] == "PASS" and report["dry_run"] is True
    assert report["written_files"] == []
    assert report["authority_effect"] == "NONE"
    assert owner_files(lane.root) == before


def test_registration_updates_only_selected_closure_binding(intake_lane, tmp_path):
    lane = intake_lane
    closure = add_closure(lane.root, lane.lane)
    _, report = submit(lane, tmp_path)
    updated = json.loads((lane.root / intake.CLOSURE).read_bytes())
    assert updated["records"][0]["sha256"] == digest((lane.root / intake.selection_path(lane.lane)).read_bytes())
    assert updated["records"][0]["sha256"] != closure["records"][0]["sha256"]
    assert updated["records"][1] == closure["records"][1]
    assert intake.CLOSURE in report["written_files"]


def test_registration_does_not_rewrite_unrelated_closure_bytes(intake_lane, tmp_path):
    lane = intake_lane
    closure_path = lane.root / intake.CLOSURE
    closure_path.parent.mkdir(parents=True, exist_ok=True)
    # Deliberately noncanonical whitespace: equality of parsed objects is insufficient.
    raw = b'{\n  "records" : [ { "path" : "unrelated.json", "sha256" : "' + b"a" * 64 + b'" } ]\n}\n'
    closure_path.write_bytes(raw)
    _, report = submit(lane, tmp_path)
    assert closure_path.read_bytes() == raw
    assert intake.CLOSURE not in report["written_files"]


def test_stale_closure_binding_is_not_refreshed_by_intake(intake_lane, tmp_path):
    lane = intake_lane
    add_closure(lane.root, lane.lane, stale=True)
    path = save(tmp_path / "submitted.json", lane.original)
    before = owner_files(lane.root)
    with pytest.raises(ValueError, match="闭包绑定已过期"):
        intake.register(lane.root, lane.lane, path, origin=ORIGIN)
    assert owner_files(lane.root) == before


def test_postwrite_failure_restores_selection_and_closure_but_retains_raw(intake_lane, tmp_path, monkeypatch):
    lane = intake_lane
    add_closure(lane.root, lane.lane)
    selection = lane.root / intake.selection_path(lane.lane)
    closure = lane.root / intake.CLOSURE
    before_selection, before_closure = selection.read_bytes(), closure.read_bytes()
    path = save(tmp_path / "submitted.json", lane.original)
    sha = digest(path.read_bytes())
    expected_record = lane.root / intake.DIRECTORIES[lane.lane] / f"{sha}.json"
    real_summary = intake.lane_summary
    calls = []

    def fail_postwrite(root, lane_name):
        calls.append((root, lane_name))
        if len(calls) == 2:
            assert expected_record.is_file()
            assert selection.read_bytes() != before_selection
            assert closure.read_bytes() != before_closure
            raise ValueError("synthetic postwrite check failed")
        return real_summary(root, lane_name)

    monkeypatch.setattr(intake, "lane_summary", fail_postwrite)
    with pytest.raises(ValueError, match="登记失败并回滚.*synthetic postwrite"):
        intake.register(lane.root, lane.lane, path, origin=ORIGIN)
    assert len(calls) == 2
    assert selection.read_bytes() == before_selection
    assert closure.read_bytes() == before_closure
    assert not expected_record.exists()
    raw = AssetCatalog.from_repo(lane.root).resolve(f"asset:sha256:{sha}")
    assert raw.path.read_bytes() == path.read_bytes()
    assert real_summary(lane.root, lane.lane)["review_count"] == 0


@pytest.fixture
def pilot_intake(pilot):
    pilot_selection(pilot)
    return pilot


def test_pilot_registration_preserves_raw_id_and_does_not_add_schema_version(pilot_intake, tmp_path):
    study = pilot_intake
    original = pilot_opinion(study, 0)
    path = save(tmp_path / "pilot-opinion.json", original)
    study_before = owner_files(study.root)
    report = intake.register(study.root, "pilot", path, origin=ORIGIN)
    assert report["status"] == "PENDING" and report["registered"] is True
    assert report["id"] == original["id"] and report["lane_report"]["review_count"] == 1
    _, record = selected_record(study.root, "pilot")
    assert "schema_version" not in record
    assert {k: v for k, v in record.items() if k not in {"raw_review", "authority_effect"}} == original
    assert (study.root / record["raw_review"]["path"]).read_bytes() == path.read_bytes()
    assert record["raw_review"]["sha256"] == digest(path.read_bytes())
    assert record["authority_effect"] == report["authority_effect"] == "NONE"
    for relative, raw in study_before.items():
        if relative != intake.PILOT_SELECTION:
            assert (study.root / relative).read_bytes() == raw


@pytest.mark.parametrize("fault", ["null", "stale", "id", "unknown", "duplicate-key", "raw-metadata"])
def test_invalid_pilot_original_has_no_owner_mutations(pilot_intake, tmp_path, fault):
    study = pilot_intake
    original = pilot_opinion(study, 0)
    identity = None
    if fault == "null":
        original["reviewer"]["principal_id"] = None
    elif fault == "stale":
        original["context_sha256"] = "0" * 64
    elif fault == "id":
        identity = "fixture:not-the-raw-id"
    elif fault == "unknown":
        original["unapproved"] = True
    elif fault == "raw-metadata":
        original["raw_review"] = {"path": "injected.json", "sha256": "0" * 64}
    path = save(tmp_path / "pilot-invalid.json", original)
    if fault == "duplicate-key":
        path.write_bytes(b'{"id":"fixture:0",' + path.read_bytes()[1:])
    before = owner_files(study.root)
    with pytest.raises(ValueError):
        intake.register(study.root, "pilot", path, origin=ORIGIN, identity=identity)
    assert owner_files(study.root) == before


@pytest.mark.parametrize("field", ["id", "principal_id", "source_id"])
def test_duplicate_pilot_identity_or_source_is_rejected(pilot_intake, tmp_path, field):
    study = pilot_intake
    first = pilot_opinion(study, 0)
    intake.register(study.root, "pilot", save(tmp_path / "first.json", first), origin=ORIGIN)
    second = pilot_opinion(study, 1)
    if field == "id":
        second["id"] = first["id"]
    else:
        second["reviewer"][field] = first["reviewer"][field]
    path = save(tmp_path / "second.json", second)
    before = owner_files(study.root)
    with pytest.raises(ValueError, match="重复"):
        intake.register(study.root, "pilot", path, origin=ORIGIN)
    assert owner_files(study.root) == before


def test_pilot_dry_run_does_not_write_raw_or_structured_records(pilot_intake, tmp_path):
    study = pilot_intake
    path = save(tmp_path / "pilot-opinion.json", pilot_opinion(study, 0))
    before = owner_files(study.root)
    report = intake.register(study.root, "pilot", path, origin=ORIGIN, dry_run=True)
    assert report["dry_run"] is True and report["written_files"] == []
    assert owner_files(study.root) == before


def test_pilot_failed_postwrite_summary_restores_owners_and_retains_raw(pilot_intake, tmp_path, monkeypatch):
    study = pilot_intake
    add_closure(study.root, "pilot")
    selection = study.root / intake.PILOT_SELECTION
    closure = study.root / intake.CLOSURE
    before_selection, before_closure = selection.read_bytes(), closure.read_bytes()
    original = pilot_opinion(study, 0)
    path = save(tmp_path / "pilot-opinion.json", original)
    sha = digest(path.read_bytes())
    structured = study.root / intake.DIRECTORIES["pilot"] / f"{sha}.json"
    raw = study.root / intake.DIRECTORIES["pilot"] / "raw" / f"{sha}.json"

    def reject(root, lane):
        assert root == study.root and lane == "pilot"
        assert structured.exists() and raw.read_bytes() == path.read_bytes()
        assert selection.read_bytes() != before_selection
        assert closure.read_bytes() != before_closure
        return {"status": "FAIL", "findings": ["synthetic pilot postwrite rejection"]}

    # Pilot preflight calls selected_reviews directly; lane_summary is postwrite only.
    monkeypatch.setattr(intake, "lane_summary", reject)
    with pytest.raises(ValueError, match="登记失败并回滚.*synthetic pilot"):
        intake.register(study.root, "pilot", path, origin=ORIGIN)
    assert selection.read_bytes() == before_selection and closure.read_bytes() == before_closure
    assert not structured.exists() and raw.read_bytes() == path.read_bytes()


@pytest.fixture
def scene_intake(extraction_repo, tmp_path):
    root = extraction_repo
    for name in ("semantic_reading", "semantic_reading_index"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    contract = {"id": "scene:synthetic", "chapter": 1,
                "required_beats": [{"id": "domestic-labor"}], "forbidden_beats": [{"id": "miracle"}],
                "knowledge_guards": [{"id": "knowledge-guard"}],
                "exit_state": [{"equals": "object.bowl.temperature", "value": "cold"}]}
    request = make_request(contract, "人物放下药碗。", {},
                           [{"principal_id": "fixture:author", "source_id": "fixture:author-source"}])
    request_path = save(tmp_path / "request.json", request)
    original = {"schema_version": 1, "report_kind": "REVIEW_OPINION",
                **{k: request[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")},
                "producer": {"principal_id": "fixture:reader", "source_id": "fixture:reader-source",
                             "kind": "INDEPENDENT_HUMAN"},
                "coverage": [], "unresolved": [], "events": [], "notes": "Synthetic reading only"}
    save(root / intake.selection_path("scene-reading"),
         {"schema_version": 1, "readings": [], "authority_effect": "NONE"})
    return SimpleNamespace(root=root, request=request, request_path=request_path, original=original)


@pytest.fixture
def current_scene(scene_intake, monkeypatch):
    from rcwh.competition import CompetitionRegistry, git_blob_sha
    from rcwh.evaluation.state import SceneStateAdapter

    scene = scene_intake
    save(scene.root / "data/scenes/synthetic.yaml", scene.request["contract"])
    candidate_path = scene.root / "artifacts/candidate.txt"
    candidate_path.parent.mkdir()
    raw = scene.request["text"].encode()
    candidate_path.write_bytes(raw)
    candidate = {"artifact": {"kind": "REPO_FILE", "path": "artifacts/candidate.txt",
                              "git_blob_sha": git_blob_sha(raw)}, "authors": scene.request["authors"]}
    registry = SimpleNamespace(records={"synthetic": {"chapter": 1, "candidates": [candidate]}})
    monkeypatch.setattr(CompetitionRegistry, "from_repo", lambda _: registry)
    monkeypatch.setattr(SceneStateAdapter, "__init__", lambda self, *args, **kwargs: None)
    monkeypatch.setattr(SceneStateAdapter, "snapshot", lambda self, **kwargs:
                        {"fact_registry": ["fixture:changed-fact"]} if kwargs.get("request_version") == 2 else {})
    return scene


@pytest.mark.parametrize("fault", ["reading-binding", "request-binding", "contract", "candidate", "self", "nonhuman", "authors", "stale-v2"])
def test_scene_real_preflight_rejects_stale_or_nonindependent_inputs(current_scene, tmp_path, fault):
    scene = current_scene
    if fault == "reading-binding":
        scene.original["context_sha256"] = "0" * 64
    elif fault == "request-binding":
        request = deepcopy(scene.request)
        request["context_sha256"] = "0" * 64
        save(scene.request_path, request)
    elif fault == "contract":
        contract = deepcopy(scene.request["contract"])
        contract["chapter"] = 2
        save(scene.root / "data/scenes/synthetic.yaml", contract)
    elif fault == "candidate":
        (scene.root / "artifacts/candidate.txt").write_text("changed synthetic candidate", encoding="utf-8")
    elif fault == "self":
        scene.original["producer"]["source_id"] = scene.request["authors"][0]["source_id"]
    elif fault in {"authors", "stale-v2"}:
        if fault == "authors":
            request = make_request(scene.request["contract"], scene.request["text"], {},
                                   [{"principal_id": "fixture:forged-author", "source_id": "fixture:forged-source"}])
        else:
            request = make_request(scene.request["contract"], scene.request["text"],
                                   {"fact_registry": []}, scene.request["authors"], request_version=2)
        save(scene.request_path, request)
        scene.original.update({k: request[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")})
    else:
        scene.original["producer"]["kind"] = "INTERNAL_AGENT"
    path = save(tmp_path / "reading.json", scene.original)
    before = owner_files(scene.root)
    with pytest.raises(ValueError):
        intake.register(scene.root, "scene-reading", path, origin=ORIGIN, request_path=scene.request_path)
    assert owner_files(scene.root) == before


@pytest.mark.parametrize("field", ["principal_id", "source_id"])
def test_scene_real_preflight_rejects_whitespace_producer_identity(current_scene, tmp_path, field):
    scene = current_scene
    scene.original["producer"][field] = " \t\n "
    path = save(tmp_path / "reading.json", scene.original)
    before = owner_files(scene.root)
    with pytest.raises(ValueError):
        intake.register(scene.root, "scene-reading", path, origin=ORIGIN, request_path=scene.request_path)
    assert owner_files(scene.root) == before


def test_scene_real_preflight_registers_bound_reading_without_auto_acceptance(current_scene, tmp_path):
    scene = current_scene
    path = save(tmp_path / "reading.json", scene.original)
    result = intake.register(scene.root, "scene-reading", path, origin=ORIGIN, request_path=scene.request_path)
    assert result["status"] == "PENDING" and result["registered"] is True
    assert result["lane_report"]["checks"] and result["automatic_literary_pass"] is False
    assert selected_record(scene.root, "scene-reading")[1] == scene.original
    assert_received(scene.root, result, path)


def test_scene_template_declares_no_coverage_or_events(scene_intake, tmp_path):
    scene = scene_intake
    output = tmp_path / "template.json"
    report = intake.scene_template(scene.request_path, output)
    template = json.loads(output.read_bytes())
    assert template["report_kind"] == "TEMPLATE"
    assert template["coverage"] == template["unresolved"] == template["events"] == []
    assert template["producer"]["principal_id"] == template["producer"]["source_id"] == ""
    assert report["constraints_to_examine"] == ["domestic-labor", "miracle", "knowledge-guard", "object.bowl.temperature"]
    assert report["reading_status"] == "NOT_SUBMITTED" and report["authority_effect"] == "NONE"
    with pytest.raises(FileExistsError):
        intake.scene_template(scene.request_path, output)
    assert json.loads(output.read_bytes()) == template


def test_scene_reading_requires_frozen_request_before_any_owner_mutation(scene_intake, tmp_path):
    scene = scene_intake
    path = save(tmp_path / "reading.json", scene.original)
    before = owner_files(scene.root)
    with pytest.raises(ValueError, match="需要 --request"):
        intake.register(scene.root, "scene-reading", path, origin=ORIGIN)
    assert owner_files(scene.root) == before


def test_scene_schema_is_enforced_before_patched_production_preflight(scene_intake, tmp_path, monkeypatch):
    scene = scene_intake
    scene.original["unapproved"] = True
    path = save(tmp_path / "reading.json", scene.original)

    def unexpected(*args):
        pytest.fail("invalid reading must not reach production preflight")

    monkeypatch.setattr(intake, "_scene_preflight", unexpected)
    before = owner_files(scene.root)
    with pytest.raises(ValueError, match="评审字段无效"):
        intake.register(scene.root, "scene-reading", path, origin=ORIGIN, request_path=scene.request_path)
    assert owner_files(scene.root) == before


def test_scene_reading_preserves_original_and_rejects_unused_duplicate_first_match(scene_intake, tmp_path, monkeypatch):
    scene = scene_intake
    # Real reading/index schemas and raw intake, but no full production world fixture.
    report = {"status": "PENDING", "checks": [], "findings": [], "automatic_literary_pass": False}
    monkeypatch.setattr(intake, "_scene_preflight", lambda *_: deepcopy(report))
    path = save(tmp_path / "reading.json", scene.original)
    before = owner_files(scene.root)
    dry = intake.register(scene.root, "scene-reading", path, origin=ORIGIN,
                          request_path=scene.request_path, dry_run=True)
    assert dry["dry_run"] is True and owner_files(scene.root) == before
    result = intake.register(scene.root, "scene-reading", path, origin=ORIGIN, request_path=scene.request_path)
    _, record = selected_record(scene.root, "scene-reading")
    assert record == scene.original and result["status"] == "PENDING"
    assert_received(scene.root, result, path)
    scene.original["producer"] = {"principal_id": "fixture:another-reader", "source_id": "fixture:another-source",
                                  "kind": "INDEPENDENT_HUMAN"}
    second = save(tmp_path / "second-reading.json", scene.original)
    before = owner_files(scene.root)
    with pytest.raises(ValueError, match="只读取首条"):
        intake.register(scene.root, "scene-reading", second, origin=ORIGIN, request_path=scene.request_path)
    assert owner_files(scene.root) == before


@pytest.mark.parametrize("quote,occurrence,expected", [("药", None, 2), ("甲", 2, 4)])
def test_resolve_spans_uses_unicode_offsets_and_explicit_occurrence(tmp_path, quote, occurrence, expected):
    text = "甲😀药碗甲。"
    texts = tmp_path / "text.txt"
    texts.write_bytes(text.encode())
    span = {"quote": quote}
    if occurrence is not None:
        span["occurrence"] = occurrence
    original = {"nested": [{"spans": [span]}]}
    submitted = save(tmp_path / "original.json", original)
    raw = submitted.read_bytes()
    output = tmp_path / "resolved.json"
    report = intake.resolve_spans(submitted, texts, output)
    assert report["resolved_spans"] == 1 and report["authority_effect"] == "NONE"
    assert json.loads(output.read_bytes())["nested"][0]["spans"] == [{"quote": quote, "start": expected, "end": expected + len(quote)}]
    assert submitted.read_bytes() == raw


@pytest.mark.parametrize("span", [{"quote": "不存在"}, {"quote": "甲"}, {"quote": "甲", "occurrence": 0},
                                 {"quote": "甲", "occurrence": 3}, {"quote": "甲", "occurrence": True},
                                 {"quote": "药", "unknown": True}, {"quote": "药", "start": 0, "end": 1}])
def test_unresolved_or_invalid_spans_do_not_create_output(tmp_path, span):
    text = tmp_path / "text.txt"
    text.write_text("甲😀药碗甲。", encoding="utf-8")
    submitted = save(tmp_path / "original.json", {"spans": [span]})
    output = tmp_path / "resolved.json"
    with pytest.raises(ValueError):
        intake.resolve_spans(submitted, text, output)
    assert not output.exists()


def test_resolve_spans_preserves_valid_offsets_and_never_overwrites(tmp_path):
    text = tmp_path / "text.txt"
    text.write_text("甲😀药碗甲。", encoding="utf-8")
    original = {"spans": [{"quote": "药", "start": 2, "end": 3}]}
    submitted = save(tmp_path / "original.json", original)
    output = tmp_path / "resolved.json"
    assert intake.resolve_spans(submitted, text, output)["resolved_spans"] == 0
    assert json.loads(output.read_bytes()) == original
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        intake.resolve_spans(submitted, text, output)
    assert output.read_bytes() == before


def test_resolve_anonymous_directory_spans_uses_each_tokens_own_text(tmp_path):
    texts = tmp_path / "public"
    texts.mkdir()
    first, second = "read-aaaaaaaaaaaa", "read-bbbbbbbbbbbb"
    (texts / f"{first}.txt").write_text("甲药。", encoding="utf-8")
    (texts / f"{second}.txt").write_text("乙😀药。", encoding="utf-8")
    submitted = save(tmp_path / "original.json", {"observations": {
        first: {"spans": [{"quote": "药"}]}, second: {"spans": [{"quote": "药"}]}}})
    output = tmp_path / "resolved.json"
    assert intake.resolve_spans(submitted, texts, output)["resolved_spans"] == 2
    observations = json.loads(output.read_bytes())["observations"]
    assert observations[first]["spans"][0]["start"] == 1
    assert observations[second]["spans"][0]["start"] == 2


@pytest.mark.parametrize("status,exit_code", [("PASS", 0), ("FAIL", 1), ("PENDING", 2)])
def test_review_command_preserves_registration_status_and_exit_code(tmp_path, monkeypatch, capsys, status, exit_code):
    captured = []

    def register(*args, **kwargs):
        captured.append((args, kwargs))
        return {"status": status, "registered": True, "authority_effect": "NONE"}

    monkeypatch.setattr(review_command, "register", register)
    args = SimpleNamespace(root=str(tmp_path), review_action="register", lane="source",
                           file=str(tmp_path / "opinion.json"), origin=ORIGIN, id="fixture:id",
                           dry_run=True, request=str(tmp_path / "request.json"))
    assert review_command.command(args) == exit_code
    assert json.loads(capsys.readouterr().out)["status"] == status
    positional, keywords = captured[0]
    assert positional == (tmp_path.resolve(), "source", tmp_path / "opinion.json")
    assert keywords == {"origin": ORIGIN, "identity": "fixture:id", "dry_run": True,
                        "request_path": tmp_path / "request.json"}


def test_review_command_reports_preflight_errors_without_claiming_registration(tmp_path, monkeypatch, capsys):
    def reject(*args, **kwargs):
        raise ValueError("synthetic invalid opinion")

    monkeypatch.setattr(review_command, "register", reject)
    args = SimpleNamespace(root=str(tmp_path), review_action="register", lane="source",
                           file="synthetic.json", origin=ORIGIN, id=None, dry_run=False, request=None)
    assert review_command.command(args) == 1
    assert json.loads(capsys.readouterr().out) == {"status": "FAIL", "findings": ["synthetic invalid opinion"],
                                               "authority_effect": "NONE"}
