from copy import deepcopy
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from rcwh.assets import AssetError
from rcwh.closure import InputClosure
from rcwh.corpus.extraction import canonical_bytes
from rcwh.corpus.locators import source_digest
from rcwh.provenance import ProvenanceRepository
from test_source_extraction import ROOT, extraction_repo, setup_source, write_source


@pytest.fixture
def closure_repo(extraction_repo):
    root = extraction_repo
    for name in ("closure_roots", "source_gap_baseline"):
        shutil.copyfile(ROOT / f"schemas/{name}.schema.json", root / f"schemas/{name}.schema.json")
    _, source = setup_source(root)
    source["locator"] = {"legacy_lines": "unresolved"}
    write_source(root, source)
    repository = ProvenanceRepository.from_repo(root)
    report = repository.verify_all()
    baseline = {"schema_version": 1, "source_ids": [source["id"]], "gaps": [{"source_id": source["id"],
                "source_record_sha256": source_digest(source), "findings": sorted(set(report["sources"][0]["findings"]))}]}
    path = "data/project/source_gap_baseline.json"
    (root / path).parent.mkdir(parents=True); (root / path).write_bytes(canonical_bytes(baseline))
    return root, source, path


def test_known_failure_is_budgeted_but_not_a_closure_pass(closure_repo):
    root, _, path = closure_repo
    result = InputClosure(root).gap_check(path)
    assert result["status"] == "PASS" and result["closure_status"] == "FAIL"
    assert len(result["known_gaps_remaining"]) == 1


@pytest.mark.parametrize("change", ["changed-source", "changed-reason", "new-failure", "deleted-root"])
def test_gap_baseline_cannot_hide_regression_or_remove_roots(closure_repo, change):
    root, source, path = closure_repo
    if change == "changed-source":
        source["title"] = "changed witness context"; write_source(root, source)
    elif change == "changed-reason":
        source["container"]["sha256"] = "0" * 64; write_source(root, source)
    elif change == "new-failure":
        other = deepcopy(source); other["id"] = "src:test:new-gap"
        (root / "data/provenance/sources/test.yaml").write_text(__import__("yaml").safe_dump({"schema_version": 1, "sources": [source, other]}))
    else:
        other = deepcopy(source); other["id"] = "src:test:replacement"; write_source(root, other)
    assert InputClosure(root).gap_check(path)["status"] == "FAIL"


def test_repaired_gap_is_allowed_and_new_failure_after_repair_is_rejected(closure_repo):
    root, source, path = closure_repo
    _, repaired = setup_source(root)
    result = InputClosure(root).gap_check(path)
    assert result["status"] == "FAIL" and result["closure_status"] == "PASS"
    assert result["resolved_gap_ids"] == [source["id"]]
    # Remove the exemption once repaired: the same old failure is now a regression.
    baseline = json.loads((root / path).read_bytes()); baseline["gaps"] = []; (root / path).write_bytes(canonical_bytes(baseline))
    assert InputClosure(root).gap_check(path)["status"] == "PASS"
    write_source(root, source)
    assert InputClosure(root).gap_check(path)["status"] == "FAIL"


def test_declared_scope_checks_missing_untracked_and_cache_inputs(closure_repo, monkeypatch):
    root, _, _ = closure_repo
    config = {"schema_version": 1, "id": "closure:test", "source_selector": "ALL_LOADED", "collections": [], "assets": [],
              "records": [], "datasets": [], "build_configs": [], "required_paths": ["data/required.json"]}
    (root / "data/project/closure_roots.json").write_bytes(canonical_bytes(config))
    (root / "data/project/current.json").write_bytes(b"{}\n")
    project = SimpleNamespace(data={"owners": {"closure": "data/project/closure_roots.json"}}, owner=lambda _: config, validate=lambda _: [])
    monkeypatch.setattr("rcwh.closure.ProjectState.from_repo", lambda _: project)
    result = InputClosure(root).verify()
    assert "MISSING_CLOSURE_INPUT: data/required.json" in result["findings"]
    (root / "data/required.json").write_bytes(b"{}\n")
    assert any("UNTRACKED_CLOSURE_INPUT" in f for f in InputClosure(root).verify(require_tracked=True)["findings"])
    config["required_paths"] = [".rcwh-cache/hidden.json"]
    with pytest.raises(AssetError, match="CACHE_CANNOT_BE_FORMAL_INPUT"):
        InputClosure(root).verify()


def test_declared_source_selector_cannot_select_only_successes(closure_repo):
    root, _, _ = closure_repo
    from rcwh.schema import validate_instance
    config = {"schema_version": 1, "id": "closure:test", "source_selector": ["src:success-only"], "collections": [], "assets": [],
              "records": [], "datasets": [], "build_configs": [], "required_paths": []}
    assert validate_instance(config, root / "schemas/closure_roots.schema.json")


def test_git_baseline_allows_only_shrinking_waivers(closure_repo):
    root, source, path = closure_repo
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Freeze gap budget"], cwd=root, check=True)
    other = deepcopy(source); other["id"] = "src:test:new-failure"; other["witness"] = {"label": "new distinct witness"}
    import yaml
    (root/"data/provenance/sources/test.yaml").write_text(yaml.safe_dump({"schema_version": 1, "sources": [source, other]}))
    baseline = json.loads((root/path).read_bytes()); baseline["source_ids"].append(other["id"])
    baseline["gaps"].append({"source_id": other["id"], "source_record_sha256": source_digest(other), "findings": baseline["gaps"][0]["findings"]})
    (root/path).write_bytes(canonical_bytes(baseline))
    assert InputClosure(root).gap_check(path)["status"] == "PASS"
    result = InputClosure(root).gap_check(path, base_ref="HEAD")
    assert result["status"] == "FAIL" and f"SOURCE_GAP_WAIVER_EXPANDED: {other['id']}" in result["findings"]


@pytest.mark.parametrize("rejected", ["source", "corpus", None])
def test_regression_allows_pending_but_not_actual_rejections(closure_repo, monkeypatch, rejected):
    root, _, _ = closure_repo
    closure = InputClosure(root)
    monkeypatch.setattr(closure, "verify", lambda **_: {"status": "FAIL", "findings": [], "input_digest": "a"*64,
        "root_set_digest": "b"*64, "source_evidence_audit": {"status": "FAIL" if rejected == "source" else "PENDING"},
        "datasets": [{"dataset_ref": "corpus:fixture", "status": "PASS", "findings": []}]})
    monkeypatch.setattr(closure, "gap_check", lambda *args, **kwargs: {"status": "PASS", "findings": []})
    monkeypatch.setattr("rcwh.corpus.audit.CorpusAudit.summary", lambda *args, **kwargs: {"status": "FAIL" if rejected == "corpus" else "PENDING"})
    result = closure.regression()
    assert result["status"] == ("FAIL" if rejected else "PASS")
    assert result["closure_status"] == "FAIL"
