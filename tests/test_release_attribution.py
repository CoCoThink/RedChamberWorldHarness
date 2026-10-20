"""Rebinding is custody; retained records identify actual contributors."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.assets import AssetError
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.workflow.attribution import release_attribution

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def rebound(tmp_path):
    rows = json.loads((ROOT / "data/agent_release/selection-81-100-v2.json").read_bytes())["chapters"]
    row = deepcopy(next(r for r in rows if r["chapter"] == 86))
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    seen = set()

    def copy(ref):
        if not ref or ref["path"] in seen:
            return
        seen.add(ref["path"])
        target = tmp_path / ref["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref["path"], target)
        if target.suffix == ".json":
            value = json.loads(target.read_bytes())
            for field in ("current", "previous"):
                for binding in value.get(field, {}).values():
                    copy(binding)
            for field in ("candidate", "run", "prepared_request", "package", "parent", "feedback", "imported_text", "request_source"):
                if isinstance(value.get(field), dict) and "path" in value[field]:
                    copy(value[field])
    copy(row["rebind_receipt"])
    return tmp_path, row


def replace(root, row, update):
    value = json.loads((root / row["rebind_receipt"]["path"]).read_bytes())
    update(value)
    raw = canonical_bytes(value)
    (root / "receipt.json").write_bytes(raw)
    row["rebind_receipt"] = {"path": "receipt.json", "sha256": digest(raw)}


def test_original_author_revisers_and_coordinator_edit_are_explicit(rebound):
    root, row = rebound
    report = release_attribution(root, row)
    assert report["contributors"][0]["principal_id"] == "session:phase6-v3-author-ch86"
    assert report["contributors"][-1]["role"] == "COORDINATOR_EDITOR"
    assert report["custodians"][0]["principal_id"] == "session:rebind-v4:ch86"
    assert len(report["chain"]) == 4
    assert report["previous_writing_inputs_replay"] == "NOT_CHECKED"


def test_missing_disclosure_cannot_attribute_rebind_session_as_author(rebound):
    root, row = rebound
    del row["rebind_receipt"]
    with pytest.raises(AssetError, match="explicit rebind_receipt"):
        release_attribution(root, row)


@pytest.mark.parametrize("update,match", [
    (lambda r: r.update(chapter=87), "chapter/bindings"),
    (lambda r: r.update(prose_identical_to_previous=True), "identity declaration"),
    (lambda r: r.update(coordinator_edit=[]), "exact coordinator edit"),
    (lambda r: r["current"].update(draft=r["previous"]["draft"]), "chapter/bindings"),
])
def test_wrong_or_incomplete_disclosure_is_rejected(rebound, update, match):
    root, row = rebound
    replace(root, row, update)
    with pytest.raises(AssetError, match=match):
        release_attribution(root, row)


def test_unchanged_rebind_contributes_no_new_prose_author():
    row = json.loads((ROOT / "data/agent_release/selection-81-100-v2.json").read_bytes())["chapters"][0]
    report = release_attribution(ROOT, row)
    assert report["prose_identical_to_previous"]
    assert not any(a["principal_id"].startswith("session:rebind-") for a in report["contributors"])


def test_tampering_old_author_run_is_detected(rebound):
    root, row = rebound
    report = release_attribution(root, row)
    (root / report["chain"][-1]["run"]["path"]).write_text("{}")
    with pytest.raises(ValueError, match="digest|stale|mismatch"):
        release_attribution(root, row)


def test_later_revision_retains_original_authorship_and_rebind_receipt(rebound):
    root, row = rebound

    def store(name, value):
        raw = value if isinstance(value, bytes) else canonical_bytes(value)
        (root / name).write_bytes(raw)
        return {"path": name, "sha256": digest(raw)}

    draft = json.loads((root / row["draft"]["path"]).read_bytes())
    run = json.loads((root / draft["run"]["path"]).read_bytes())
    prepared = json.loads((root / draft["prepared_request"]["path"]).read_bytes())
    original = (root / row["candidate"]["path"]).read_bytes()
    feedback = {"draft": row["draft"], "candidate": row["candidate"], "inputs": draft["inputs"]}
    task = {"writing_task": draft["task"], "original": original.decode(), "feedback": feedback, "editorial_notes": None}
    parent, feedback_ref = row["draft"], store("new-feedback.json", feedback)
    prepared.update(parent=parent, feedback=feedback_ref, task=task)
    prepared["request"]["messages"] = [{"role": "user", "content": canonical_bytes(task).decode()}]
    prepared["request_sha256"] = digest(canonical_bytes(prepared["request"]))
    prepared["prompt_sha256"] = digest(canonical_bytes({k: prepared["request"][k] for k in ("system", "messages")}))
    request_ref = store("new-request.json", prepared)
    raw = original + "\n测试用后续修订。\n".encode()
    candidate = store("new-candidate.txt", raw)
    run.update(session_id="later-reviser", candidate=candidate, output=raw.decode(), output_sha256=candidate["sha256"],
               imported_text=candidate, prepared_request=request_ref, request_source=request_ref,
               parent=parent, feedback=feedback_ref, request_sha256=prepared["request_sha256"], prompt_sha256=prepared["prompt_sha256"])
    run_ref = store("new-run.json", run)
    draft.update(candidate=candidate, run=run_ref, prepared_request=request_ref, parent=parent,
        feedback=feedback_ref, task=task, prompt_sha256=prepared["prompt_sha256"], authors=[{
            "principal_id": "session:later-reviser", "source_id": "session-author:" + run_ref["sha256"], "kind": "MODEL", "run": run_ref}])
    row.update(draft=store("new-draft.json", draft), candidate=candidate)
    report = release_attribution(root, row)
    assert report["contributors"][0]["principal_id"] == "session:phase6-v3-author-ch86"
    assert report["contributors"][-1]["principal_id"] == "session:later-reviser"
    assert report["contributors"][-1]["role"] == "REVISER"
    assert len(report["subsequent_revisions"]) == 1
