"""Research draft → provisional feedback → revision; formal registries untouched."""
from __future__ import annotations

import difflib
from contextvars import ContextVar
import json
from pathlib import Path
import re

from ..candidate_reviews import canonical_bytes, digest
from ..evaluate import evaluate_scene_text
from ..evaluation.continuity import continuity_report
from ..evaluation.semantics import make_request
from ..evaluation.state import SceneStateAdapter
from ..evaluation.style import style_diagnostics
from ..evaluation.style_reference import reference_profile
from ..io import load_data
from ..knowledge import CharacterKnowledgeRuntime
from .records import append_bytes, binding, bound_bytes, legacy_run, run_task, store, verify_raw_run
from .render import PromptRenderer, request_for
from .runner import Budget, DEFAULT_MODEL, ModelRunner

_LOADING_DRAFTS = ContextVar("writing_lineage_loading", default=frozenset())


def load_draft(root: Path, relative: str) -> tuple[dict, str]:
    key = (str(root.resolve()), relative)
    loading = _LOADING_DRAFTS.get()
    if key in loading:
        raise ValueError("writing draft lineage cycle")
    token = _LOADING_DRAFTS.set(loading | {key})
    try:
        return _load_draft(root, relative)
    finally:
        _LOADING_DRAFTS.reset(token)


def _load_draft(root: Path, relative: str) -> tuple[dict, str]:
    """Commands take the immutable draft record, which binds prose and all inputs."""
    from ..assets.paths import repository_path
    from ..schema import validate_instance
    draft = load_data(repository_path(root, relative))
    errors = validate_instance(draft, root / "schemas/draft_registry.schema.json")
    if errors:
        raise ValueError("invalid draft record: " + "; ".join(errors))
    raw = bound_bytes(root, draft["candidate"])
    from .session import EXECUTION_BASIS, verify_session_draft
    if draft.get("execution_basis") == EXECUTION_BASIS:
        verify_session_draft(root, draft, raw)
        return draft, raw.decode("utf-8")
    run = json.loads(bound_bytes(root, draft["run"]))
    verify_raw_run(root, run, raw)
    trace = json.loads(bound_bytes(root, draft["raw_run"]))
    if (run.get("raw_run") != draft["raw_run"] or trace["inputs"] != draft["inputs"]
            or trace["template"] != draft["template"]
            or trace.get("input_snapshot") != draft.get("input_snapshot")
            or trace["request"]["messages"] != [{"role": "user", "content": canonical_bytes(draft["task"]).decode()}]):
        raise ValueError("draft task/input binding differs from executed request")
    prompt = {"system": trace["request"]["system"], "messages": trace["request"]["messages"]}
    if digest(canonical_bytes(prompt)) != draft["prompt_sha256"]:
        raise ValueError("draft prompt digest differs from executed request")
    expected_author = {"principal_id": "model:generation:" + draft["raw_run"]["sha256"],
                       "source_id": "generation:" + draft["raw_run"]["sha256"], "kind": "MODEL", "run": draft["run"]}
    if draft["authors"] != [expected_author] or run["source_id"] != expected_author["source_id"]:
        raise ValueError("draft author binding differs from execution")
    if draft["schema_version"] == 1:
        for ref in draft["inputs"]:
            bound_bytes(root, ref)
    else:
        from .snapshots import InputSnapshot
        snapshot = InputSnapshot(root, draft["input_snapshot"])
        if snapshot.document["records"] != draft.get("dependency_records", []):
            raise ValueError("provider draft snapshot dependency records mismatch")
        if draft["parent"] is not None:
            from .session import _parent_package, _verify_revision_history
            prepared = {"parent": draft["parent"], "feedback": draft["feedback"], "task": draft["task"],
                        "package": _parent_package(root, draft), "inputs": draft["inputs"],
                        "context": draft.get("selection_context", {"notes_path": None})}
            _verify_revision_history(root, prepared, snapshot.read)
    return draft, raw.decode("utf-8")


def generate(root: Path, runner: ModelRunner, rendered: dict, budget: Budget, *, chapter: int,
             model: str = DEFAULT_MODEL, route: str = "harness", parent: dict | None = None,
             feedback: dict | None = None, fallbacks: bool = False) -> dict:
    for field, supplied in (("parent", parent), ("feedback", feedback)):
        selected = rendered.get("revision_" + field)
        if selected is not None and supplied is not None and selected != supplied:
            raise ValueError(f"revision {field} differs from rendered selection")
    parent = parent or rendered.get("revision_parent")
    feedback = feedback or rendered.get("revision_feedback")
    result = run_task(root, runner, request_for(rendered, budget, model, fallbacks=fallbacks),
                      inputs=rendered["inputs"], template=rendered["template"], budget=budget,
                      dependency_records=rendered.get("dependency_records"))
    raw = result["output"].encode("utf-8")
    candidate = append_bytes(root, f"artifacts/candidates/ch{chapter}/{digest(raw)}.txt", raw)
    source_id = "generation:" + result["raw_run"]["sha256"]
    author_run = store(root, "artifacts/author-runs", legacy_run(result, source_id))
    record = {"schema_version": 2, "kind": "WRITING_DRAFT", "chapter": chapter, "route": route,
              "candidate": candidate, "run": author_run, "raw_run": result["raw_run"],
              "authors": [{"principal_id": "model:" + source_id, "source_id": source_id,
                           "kind": "MODEL", "run": author_run}],
              "inputs": rendered["inputs"], "template": rendered["template"],
              "input_snapshot": result["record"]["input_snapshot"],
              "task": rendered["task"], "prompt_sha256": rendered["prompt_sha256"],
              "parent": parent, "feedback": feedback, "authority_effect": "NONE"}
    if rendered.get("selection_context") is not None:
        record.update(selection_context=rendered["selection_context"], dependency_records=rendered["dependency_records"])
    ref = store(root, f"data/writing/drafts/ch{chapter}", record)
    return {"status": "PASS", "draft": ref, "candidate": candidate, "run": author_run,
            "raw_run": result["raw_run"], "usage": result["record"]["usage"],
            "qualification": "RESEARCH_ONLY", "authority_effect": "NONE"}


def feedback_report(root: Path, draft_path: str, *, runner: ModelRunner | None = None,
                    budget: Budget | None = None, model: str = DEFAULT_MODEL,
                    style_reference: bool = False, exclude_chapters: list[int] | None = None,
                    fallbacks: bool = False, audit_narrator: bool = False) -> dict:
    draft, text = load_draft(root, draft_path)
    task = draft["task"]
    # Revision tasks carry their original frozen writing task, never re-infer it.
    while "writing_task" in task:
        task = task["writing_task"]
    knowledge = CharacterKnowledgeRuntime.from_repo(root)
    checks, semantic_requests, semantic_runs = [], [], []
    budget = budget or Budget()
    scenes = task["scenes"]
    if runner is not None:
        budget.validate(len(scenes), fallback=fallbacks)
    for scene in scenes:
        contract = scene["contract"]
        if contract.get("kind") == "SCENE_SKELETON":
            checks.append({"evaluator": "scene_state", "scene": contract["id"], "status": "PENDING",
                           "qualification": "FEEDBACK_ONLY", "findings": ["DRAFT_SCENE_NO_EXECUTABLE_STATE_CONTRACT"]})
            continue
        entry = scene.get("entry") or SceneStateAdapter(root, contract).snapshot()
        semantic = make_request(contract, text, entry, draft["authors"])
        semantic_requests.append(semantic)
        reading = None
        if runner is not None:
            template = binding(root, "data/writing/prompts/feedback-v1.md")
            rendered = {"system": semantic["prompt"] + "\n" + bound_bytes(root, template).decode(),
                        "messages": [{"role": "user", "content": canonical_bytes({
                            "request": semantic, "response_schema": load_data(root / "schemas/semantic_reading.schema.json"),
                            "qualification": "FEEDBACK_ONLY"}).decode()}]}
            result = run_task(root, runner, request_for(rendered, budget, model, fallbacks=fallbacks),
                              inputs=[binding(root, draft_path), draft["candidate"]],
                              template=template, budget=budget)
            semantic_runs.append(result["raw_run"])
            try:
                reading = json.loads(result["output"])
            except ValueError:
                checks.append({"evaluator": "semantic_response", "status": "FAIL", "findings": ["model feedback is not JSON"]})
        # Supplying an empty reading prevents fallback to official scene registry.
        results = evaluate_scene_text(contract, text, knowledge_runtime=knowledge,
                                      semantic_reading=reading or {}, entry_state=entry,
                                      candidate_authors=draft["authors"], root=root)
        for result in results:
            item = result.to_dict()
            if runner is None and result.evaluator == "scene_semantics":
                item = {"evaluator": "scene_semantics", "status": "PENDING",
                        "findings": ["MODEL_SEMANTIC_FEEDBACK_NOT_REQUESTED"],
                        "details": {"reading_requested": False, "semantic_coverage": False}}
            checks.append({**item, "scene": contract["id"], "qualification": "FEEDBACK_ONLY"})
    from .prose_integrity import prose_integrity
    checks.append({"evaluator": "prose_integrity", "qualification": "FEEDBACK_ONLY",
                   **prose_integrity(text)})
    if audit_narrator:
        from .narrator_audit import narrator_audit
        checks.append({"evaluator": "narrator_audit", **narrator_audit(text)})
    reference = None
    if style_reference:
        reference = reference_profile(root, task.get("exemplar_dataset_ref") or draft_dataset(root, task),
                                      exclude_chapters=exclude_chapters or [])
    checks.append({"evaluator": "style", "qualification": "FEEDBACK_ONLY", "details": style_diagnostics(text, reference=reference)})
    checks.append({"evaluator": "declared_plan_continuity", "qualification": "FEEDBACK_ONLY",
                   "details": continuity_report(root, draft["chapter"]),
                   "limitation": "Declared state compatibility only; not actual-text exit verification"})
    return {"schema_version": 1, "kind": "WRITING_FEEDBACK", "qualification": "FEEDBACK_ONLY",
            "candidate": draft["candidate"], "draft": binding(root, draft_path),
            "inputs": draft["inputs"], "checks": checks, "semantic_requests": semantic_requests,
            "semantic_runs": semantic_runs, "formal_eligibility": False, "authority_effect": "NONE"}


def draft_dataset(root: Path, task: dict) -> str:
    ref = task["package"]["exemplar_set"]
    return json.loads(bound_bytes(root, ref))["dataset_ref"]


def revision_prompt(root: Path, draft_path: str, feedback_path: str, notes_path: str | None = None, *,
                    revision_template: str = "revise-v1", renderer_version: int | None = None) -> dict:
    if revision_template not in {"revise-v1", "revise-v2"}:
        raise ValueError("unknown revision template")
    draft, text = load_draft(root, draft_path)
    feedback_binding = binding(root, feedback_path)
    feedback = json.loads(bound_bytes(root, feedback_binding))
    from ..schema import validate_instance
    errors = validate_instance(feedback, root / "schemas/writing_feedback.schema.json")
    if errors:
        raise ValueError("invalid writing feedback: " + "; ".join(errors))
    if feedback["draft"] != binding(root, draft_path) or feedback["candidate"] != draft["candidate"] or feedback["inputs"] != draft["inputs"]:
        raise ValueError("feedback is stale or bound to a different candidate")
    from . import render
    version = render.DEFAULT_RENDERER_VERSION if renderer_version is None else renderer_version
    inputs = [draft["candidate"], binding(root, draft_path), feedback_binding]
    if version == 1:
        inputs = draft["inputs"] + [draft["template"]] + inputs
    for ref in inputs:
        bound_bytes(root, ref)
    notes = None
    if notes_path:
        ref = binding(root, notes_path)
        notes = bound_bytes(root, ref).decode("utf-8")
        inputs.append(ref)
    data = {"writing_task": draft["task"], "original": text, "feedback": feedback, "editorial_notes": notes}
    result = PromptRenderer(root, version=version).render(revision_template, data, inputs)
    result.update(revision_parent=binding(root, draft_path), revision_feedback=feedback_binding)
    if version == 2:
        from .session import selection_context
        result.update(renderer_version=2, dependency_records=[], readiness={"scope": "FROZEN_PARENT_REVISION"},
                      selection_context=selection_context(root, parent_path=draft_path, feedback_path=feedback_path,
                                                          notes_path=notes_path, revision_template=revision_template))
    return result


def diff_report(root: Path, left: str, right: str, *, context: int = 2) -> dict:
    a, old = load_draft(root, left)
    b, new = load_draft(root, right)
    if a["chapter"] != b["chapter"]:
        raise ValueError("diff requires drafts from the same chapter")
    before = re.split(r"\n\s*\n", old)
    after = re.split(r"\n\s*\n", new)
    groups = []
    for group in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_grouped_opcodes(context):
        groups.append([{ "operation": tag, "old_range": [i, j], "new_range": [k, l],
                         "old_paragraphs": before[i:j], "new_paragraphs": after[k:l]} for tag, i, j, k, l in group])
    return {"status": "PASS", "left": binding(root, left), "right": binding(root, right),
            "paragraph_change_reading_packet": groups,
            "unified_diff": "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile=left, tofile=right, lineterm="")),
            "qualification": "FEEDBACK_ONLY", "authority_effect": "NONE",
            "formal_review_requirement": "Independent qualification must bind readings to the entire revised candidate, not only changed passages."}
