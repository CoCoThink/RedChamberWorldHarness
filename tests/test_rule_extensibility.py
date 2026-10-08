"""Growth must preserve identities, scope and review boundaries, not old totals."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetCatalog
from rcwh.competition import CompetitionRegistry
from rcwh.contracts import project_chapters, unique_index
from rcwh.graph import ProvenanceGraph
from rcwh.knowledge import CharacterKnowledgeRuntime
from rcwh.literary_ecology import LiteraryEcologyRuntime
from rcwh.literary_production import LiteraryProductionRuntime
from rcwh.mechanism_adapters import HistoricalAdapterRuntime
from rcwh.microdraft import ControlledMicrodraftRuntime
from rcwh.plocks import LiteraryProtectionRegistry
from rcwh.prewrite import V5PrewriteRuntime
from rcwh.reconstruction import ReconstructionRegistry
from rcwh.regression import run_r4_evidence_regression
from rcwh.schema import validate_instance
from rcwh.world import WorldRuntime

ROOT = Path(__file__).resolve().parents[1]


def test_world_accepts_additional_character_with_baseline_and_rejects_missing_binding():
    world = WorldRuntime.from_repo(ROOT)
    character = deepcopy(world.characters["baoyu"])
    character["id"] = "extension-character"
    world.characters[character["id"]] = character
    world.data["baseline"]["characters"][character["id"]] = deepcopy(world.data["baseline"]["characters"]["baoyu"])
    dependencies = AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT)
    assert world.validate_integrity(*dependencies) == []
    del world.data["baseline"]["characters"][character["id"]]
    assert any("world baseline characters" in e for e in world.validate_integrity(*dependencies))


def test_duplicate_identity_fails_even_when_population_does_not_change():
    rows = [{"id": "A"}, {"id": "B"}]
    assert set(unique_index(rows)) == {"A", "B"}
    rows[1]["id"] = "A"
    with pytest.raises(ValueError, match="duplicate id"):
        unique_index(rows)


def test_missing_declared_chapter_is_a_failure():
    world = WorldRuntime.from_repo(ROOT)
    del world.presence[project_chapters(ROOT)[0]]
    assert any("world presence: missing=" in e for e in world.validate_integrity(
        AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT)
    ))


def test_project_scope_is_explicit_and_rejects_duplicates(tmp_path):
    (tmp_path / "data/project").mkdir(parents=True)
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas/project_scope.schema.json").write_bytes((ROOT / "schemas/project_scope.schema.json").read_bytes())
    path = tmp_path / "data/project/scope.json"
    path.write_text(json.dumps({"schema_version": 1, "chapters": [81, 82, 101]}))
    assert project_chapters(tmp_path) == (81, 82, 101)
    path.write_text(json.dumps({"schema_version": 1, "chapters": [81, 81]}))
    with pytest.raises(ValueError, match="invalid project scope"):
        project_chapters(tmp_path)


def test_new_scene_is_allowed_but_duplicate_or_unknown_dimension_fails():
    runtime = V5PrewriteRuntime.from_repo(ROOT)
    deps = (AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT),
            LiteraryEcologyRuntime.from_repo(ROOT), LiteraryProtectionRegistry.from_repo(ROOT),
            HistoricalAdapterRuntime.from_repo(ROOT))
    scenes = runtime.planners[89]["candidate_scenes"]
    added = {**scenes[0], "id": "89-EXTENSION"}
    scenes.append(added)
    assert validate_instance(runtime.data, ROOT / "schemas/v5_prewrite.schema.json") == []
    assert runtime.validate_integrity(*deps) == []
    runtime.gaps[89]["states"]["undeclared"] = "THIN"
    assert any("gap dimensions" in e for e in runtime.validate_integrity(*deps))
    scenes.append(deepcopy(added))
    with pytest.raises(ValueError, match="duplicate id"):
        runtime.validate_integrity(*deps)


def test_knowledge_can_add_supported_character_without_six_person_limit():
    runtime = CharacterKnowledgeRuntime.from_repo(ROOT)
    world = WorldRuntime.from_repo(ROOT)
    literary = LiteraryEcologyRuntime.from_repo(ROOT)
    identity = next(iter(set(world.characters) & set(literary.voices) - set(runtime.characters)))
    added = deepcopy(runtime.characters["baoyu"])
    added["id"] = identity
    runtime.data["characters"].append(added)
    assert validate_instance(runtime.data, ROOT / "schemas/character_knowledge_graph.schema.json") == []
    assert runtime.validate_integrity(world, literary) == []


def test_regression_accepts_valid_graph_growth_and_still_protects_anchor(monkeypatch):
    graph = ProvenanceGraph.from_repo(ROOT)
    old = next(x for x in graph.decisions.values() if x["status"] == "CURRENT")
    added = {**deepcopy(old), "id": "decision:extension:current-choice"}
    graph.decisions[added["id"]] = added
    assert graph.validate_integrity() == []
    monkeypatch.setattr(ProvenanceGraph, "from_repo", classmethod(lambda cls, root: graph))
    report = run_r4_evidence_regression(ROOT)
    assert report["overall"] == "PASS"
    assert "RELEASE_SHAPE" not in {g["name"] for g in report["gates"]}
    graph.decisions["decision:qingbang:formal-title"]["status"] = "CURRENT"
    graph.decisions["decision:qingbang:formal-title"]["constraint"] = "MAY"
    assert run_r4_evidence_regression(ROOT)["overall"] == "FAIL"


def test_declared_cell_growth_is_not_bound_to_five_windows():
    lab = ControlledMicrodraftRuntime.from_repo(ROOT)
    cell = deepcopy(lab.data["design"]["cells"][0])
    cell["id"] = "W-EXTENSION"
    lab.data["design"]["cells"].append(cell)
    from rcwh.literary_stress import ScenarioLiteraryStressRuntime
    from rcwh.literary_suite import LiteraryEvaluatorSuite
    from rcwh.narrative_discourse import NarrativeDiscourseRuntime
    stress = ScenarioLiteraryStressRuntime.from_repo(ROOT)
    discourse = NarrativeDiscourseRuntime.from_repo(ROOT)
    for sid, contract in stress.contracts.items():
        first = next(x for x in lab.data["drafts"] if x["scenario_id"] == sid)
        probe = deepcopy(next(x for x in contract["probes"] if x["id"] == first["probe_id"]))
        probe["id"] += "-EXTENSION"
        contract["probes"].append(probe)
        draft = {**deepcopy(first), "token": first["token"] + "-99", "cell_id": "W-EXTENSION", "probe_id": probe["id"]}
        draft["primary_focalizer"] = discourse.card(sid, probe["id"], stress)["sjuzet_plan"]["primary_focalizer"]
        lab.data["drafts"].append(draft)
    dependencies = (discourse, stress, LiteraryEvaluatorSuite.from_repo(ROOT))
    assert validate_instance(lab.data, ROOT / "schemas/controlled_microdraft.schema.json") == []
    result = lab.evaluate_all(*dependencies)
    assert "W-EXTENSION" in {c["cell_id"] for c in result["cells"]}
    assert lab.validate_integrity(*dependencies) == []
    lab.data["drafts"].pop()
    assert any("design cells" in e for e in lab.validate_integrity(*dependencies))


def test_real_human_results_can_advance_without_editing_literary_snapshot(monkeypatch):
    competitions = CompetitionRegistry.from_repo(ROOT)
    record = competitions.records["comp:43-0:ch89:pressure-test"]
    successors = sorted((r for r in competitions.records.values()
                         if r["mode"] == "PRODUCTION_43_0" and r["sequence"] > record["sequence"]),
                        key=lambda r: r["sequence"])
    # Construct this gate scenario explicitly, regardless of real project progress.
    for successor in successors:
        successor["state"] = "BLOCKED_BY_PREDECESSOR"
        successor["candidates"] = []
        successor["workflow_progress"] = {stage: "PENDING" for stage in successor["pipeline"]}
        successor["adjudication"].update(outcome="PENDING", winner_candidate_id=None, promotion_state="NOT_ELIGIBLE")
    record["state"] = "IN_REVIEW"
    record["adjudication"].update(outcome="PENDING", winner_candidate_id=None, promotion_state="NOT_ELIGIBLE")
    successors[0]["state"] = "READY_FOR_CANDIDATES"
    plocks = LiteraryProtectionRegistry.from_repo(ROOT)
    assert any("BLOCKED_BY_PREDECESSOR" in error
               for error in competitions.validate_integrity(ROOT, plocks, record["baseline"]))
    for candidate in record["candidates"]:
        candidate["human_plock"]["status"] = "PASS"
        candidate["blind_read"]["status"] = "PASS"
        candidate["blind_read"]["reviewer_blinded"] = True
    record["workflow_progress"] = {stage: "PASS" for stage in record["pipeline"]}
    record["state"] = "ADJUDICATED"
    record["adjudication"].update(outcome="WINNER", winner_candidate_id="ch89-A", promotion_state="PROMOTION_CANDIDATE")
    monkeypatch.setattr(CompetitionRegistry, "from_repo", classmethod(lambda cls, root: competitions))
    runtime = LiteraryProductionRuntime.from_repo(ROOT)
    assert runtime.validate_integrity(competitions) == []
    assert competitions.validate_integrity(ROOT, plocks, record["baseline"]) == []
    assert runtime.summary()["active_chapter"] == successors[0]["chapter"]
    assert runtime.gates(89, competitions)["adjudication"] == "WINNER"
    assert not any(k.startswith("chapter") for k in runtime.data)


def test_forced_winner_and_fabricated_review_stage_are_rejected():
    competitions = CompetitionRegistry.from_repo(ROOT)
    record = competitions.records["comp:43-0:ch89:pressure-test"]
    for candidate in record["candidates"]:
        candidate["human_plock"]["status"] = "PENDING"
        candidate["blind_read"].update(status="PENDING", reviewer_blinded=False)
    record["state"] = "ADJUDICATED"
    record["adjudication"].update(outcome="WINNER", winner_candidate_id="ch89-A", promotion_state="PROMOTION_CANDIDATE")
    record["workflow_progress"]["PLOCK_REGRESSION"] = "PASS"
    record["workflow_progress"]["BLIND_READ"] = "PASS"
    errors = LiteraryProductionRuntime.from_repo(ROOT).validate_integrity(competitions)
    assert any("not passed all promotion gates" in e for e in errors)
    assert any("completion lacks actual candidate reviews" in e for e in errors)


def test_retired_files_are_gone_and_all_asset_bytes_remain_unchanged():
    report = json.loads((ROOT / "artifacts/migration/handover-20261008/rules_cleanup_report.json").read_text())
    assert all(not (ROOT / item["path"]).exists() for item in report["retired_files"])
    catalog = AssetCatalog.from_repo(ROOT)
    for identity, item in catalog.assets.items():
        path = catalog.resolve(identity).path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_contiguous_but_wrong_chapter_boundaries_fail_against_actual_bytes():
    from rcwh.implementation_alignment import ImplementationAlignmentRuntime
    from rcwh.object_network import ObjectNetworkRuntime
    alignment = ImplementationAlignmentRuntime.from_repo(ROOT)
    first, second = alignment.chapter_scope[:2]
    alignment.chapters[first]["line_end"] += 1
    alignment.chapters[second]["line_start"] += 1
    errors = alignment.validate_integrity(
        ROOT, AssetCatalog.from_repo(ROOT), ReconstructionRegistry.from_repo(ROOT),
        WorldRuntime.from_repo(ROOT), ObjectNetworkRuntime.from_repo(ROOT),
        LiteraryEcologyRuntime.from_repo(ROOT), LiteraryProtectionRegistry.from_repo(ROOT),
        CompetitionRegistry.from_repo(ROOT)
    )
    assert any("locator hash disagrees with actual stable bytes" in e for e in errors)
    assert not any("gap/overlap" in e for e in errors)


@pytest.mark.parametrize("path,schema,container,field", [
    ("scenario_replay/v08", "scenario_replay", "effects", "competitions"),
    ("pareto/v09", "pareto_evaluation", "effects", "competitions"),
    ("literary_stress/v010", "scenario_literary_stress", "effects", "competitions"),
    ("microdraft/v012", "controlled_microdraft", "policy", "competition_effect"),
    ("blind_review/v013", "blind_microdraft_review", "policy", "competition_effect"),
    ("revision_ablation/v014", "revision_ablation", "policy", "competition_effect"),
])
def test_experiment_competition_noninterference_is_required_for_all_chapters(path, schema, container, field):
    from rcwh.schema import validate_instance
    data = json.loads((ROOT / f"data/{path}.json").read_text())
    schema_path = ROOT / f"schemas/{schema}.schema.json"
    assert validate_instance(data, schema_path) == []
    data[container][field] = "MUTATE"
    assert validate_instance(data, schema_path)
    del data[container][field]
    assert validate_instance(data, schema_path)


def _plan_selection(tmp_path, monkeypatch):
    """Use a separate selected plan while resolving unchanged real source assets."""
    from rcwh.workflow import ProjectState
    import shutil

    original = ProjectState.from_repo(ROOT)
    for relative in (original.data["owners"]["plan_constraints"],
                     original.data["owners"]["release"], original.data["owners"]["literary"]):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    project = ProjectState(tmp_path, deepcopy(original.data))
    monkeypatch.setattr(ProjectState, "from_repo", classmethod(lambda cls, root: project))
    return project


def _write_plan_selection(project, plan, rebind=True):
    from rcwh.contracts import record_sha256

    # A new version may be selected at another path; this is not an adoption action.
    project.data["owners"]["plan_constraints"] = "selected/constraints.json"
    path = project.root / project.data["owners"]["plan_constraints"]
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    if rebind:
        project.data["plan_constraints_binding"] = {"id": plan["id"], "sha256": record_sha256(plan)}


@pytest.mark.parametrize("domain", ["reconstruction", "world", "literary_ecology"])
def test_current_plan_rejects_unreviewed_choice_drift(domain):
    from rcwh.open_interfaces import OpenInterfaceRegistry

    catalog = AssetCatalog.from_repo(ROOT)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    if domain == "reconstruction":
        reconstruction.data["jade_logistics"]["current_model"] = "ALTERNATIVE_MODEL"
        errors = reconstruction.validate_integrity(catalog, OpenInterfaceRegistry.from_repo(ROOT))
    elif domain == "world":
        world = WorldRuntime.from_repo(ROOT)
        for event in world.data["events"]:
            if event["chapter"] == 87:
                for effect in event["effects"]:
                    if effect["set"] == "relations.rel:baoyu_baochai.status":
                        effect["value"] = "PROPOSED_ALTERNATIVE"
        errors = world.validate_integrity(catalog, reconstruction)
    else:
        literary = LiteraryEcologyRuntime.from_repo(ROOT)
        literary.author_rhyme[93]["winner"] = "B_PROPOSED_ALTERNATIVE"
        errors = literary.validate_integrity(catalog)
    assert any(f"{domain} plan " in e for e in errors)


def test_selected_alternative_plan_needs_no_runtime_code_change_and_grants_no_authority(tmp_path, monkeypatch):
    from rcwh.open_interfaces import OpenInterfaceRegistry

    project = _plan_selection(tmp_path, monkeypatch)
    catalog = AssetCatalog.from_repo(ROOT)
    plan = project.plan_constraints(catalog)
    plan["id"] = "plan-constraints:test-alternative:v2"
    plan["provenance"] = {"kind": "PROPOSED_REVISION", "note": "Test-only alternative; no review or adoption claim."}
    next(r for r in plan["rules"]["reconstruction"] if r["id"] == "jade-model")["equals"] = "ALTERNATIVE_MODEL"
    next(r for r in plan["rules"]["world"] if r["id"] == "checkpoint-2")["equals"] = "PROPOSED_ALTERNATIVE"
    next(r for r in plan["rules"]["literary_ecology"] if r["id"] == "rhyme-b-chapters")["equals"] = [92, 93]
    _write_plan_selection(project, plan)
    reconstruction = ReconstructionRegistry.from_repo(ROOT)
    reconstruction.data["jade_logistics"]["current_model"] = "ALTERNATIVE_MODEL"
    assert reconstruction.validate_integrity(catalog, OpenInterfaceRegistry.from_repo(ROOT)) == []
    world = WorldRuntime.from_repo(ROOT)
    for event in world.data["events"]:
        if event["chapter"] == 87:
            for effect in event["effects"]:
                if effect["set"] == "relations.rel:baoyu_baochai.status":
                    effect["value"] = "PROPOSED_ALTERNATIVE"
    assert world.validate_integrity(catalog, reconstruction) == []
    literary = LiteraryEcologyRuntime.from_repo(ROOT)
    literary.author_rhyme[93]["winner"] = "B_PROPOSED_ALTERNATIVE"
    assert literary.validate_integrity(catalog) == []
    # Selecting a plan cannot disable evidence uncertainty or human review gates.
    literary.data["qingbang"]["formal_title_status"] = "LOCKED"
    assert any("formal title must remain OPEN" in e for e in literary.validate_integrity(catalog))
    assert project.plan_constraints(catalog)["authority"] == "CURRENT_IMPLEMENTATION_ONLY"


@pytest.mark.parametrize("case, message", [
    ("digest", "version/hash mismatch"), ("identity", "version/hash mismatch"),
    ("baseline", "baseline disagrees"), ("duplicate_id", "duplicate id"),
    ("duplicate_path", "duplicate plan constraint path"), ("missing_basis", "unknown asset"),
    ("empty_domain", "invalid plan_constraints owner"), ("authority", "invalid plan_constraints owner"),
])
def test_plan_selection_rejects_broken_bindings(tmp_path, monkeypatch, case, message):
    from rcwh.assets import AssetError

    project = _plan_selection(tmp_path, monkeypatch)
    catalog = AssetCatalog.from_repo(ROOT)
    plan = project.plan_constraints(catalog)
    rules = plan["rules"]["reconstruction"]
    if case == "digest": rules[0]["equals"] = "UNSELECTED_CHANGE"
    elif case == "identity": plan["id"] += "-unselected"
    elif case == "baseline": plan["baseline"]["text_sha256"] = "0" * 64
    elif case == "duplicate_id": rules[1]["id"] = rules[0]["id"]
    elif case == "duplicate_path": rules[1]["path"] = rules[0]["path"]
    elif case == "missing_basis": rules[0]["basis_refs"] = ["asset:missing:source"]
    elif case == "empty_domain": plan["rules"]["world"] = []
    elif case == "authority": plan["authority"] = "EVIDENCE"
    _write_plan_selection(project, plan, rebind=case not in {"digest", "identity"})
    with pytest.raises((AssetError, ValueError), match=message):
        project.plan_constraints(catalog)


def test_plan_missing_target_is_reported_instead_of_silently_skipped(tmp_path, monkeypatch):
    project = _plan_selection(tmp_path, monkeypatch)
    catalog = AssetCatalog.from_repo(ROOT)
    plan = project.plan_constraints(catalog)
    plan["rules"]["world"][0]["path"][1] = 101
    _write_plan_selection(project, plan)
    errors = WorldRuntime.from_repo(ROOT).validate_integrity(catalog, ReconstructionRegistry.from_repo(ROOT))
    assert any("unresolved path" in e for e in errors)
