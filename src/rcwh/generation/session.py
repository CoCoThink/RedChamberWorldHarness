"""Offline session-authored imports, not provider execution attestations.

A prepared request is the exact draft/revise dry-run packet. Imports verify it
against a fresh renderer and retain its original bytes; model labels describe
session configuration only, never a served model or measured usage.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..io import load_data
from ..schema import validate_instance
from .records import append_bytes, binding, bound_bytes
from .render import PromptRenderer, request_for
from .runner import Budget, DEFAULT_MODEL

EXECUTION_BASIS = "SESSION_AUTHORED_NOT_PROVIDER_VERIFIED"
BUDGET_LIMITATION = "Prepared request ceilings only; session token usage and provider billing are not measured."


def _schema(root: Path) -> dict:
    return load_data(root / "schemas/session_author_run.schema.json")


def _validate(root: Path, value: dict, *, prepared: bool = False) -> None:
    schema = _schema(root)
    if prepared:
        schema = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/prepared"}
    errors = validate_instance(value, schema)
    if errors:
        raise ValueError("invalid session " + ("prepared request" if prepared else "author run") + ": " + "; ".join(errors))


def _writing_task(task: dict) -> dict:
    while "writing_task" in task:
        task = task["writing_task"]
    return task


def _parent_package(root: Path, draft: dict) -> dict:
    if draft.get("execution_basis") == EXECUTION_BASIS:
        return deepcopy(draft["package"])
    if draft["schema_version"] == 2 and draft["parent"] is not None:
        from .writing import load_draft
        return _parent_package(root, load_draft(root, draft["parent"]["path"])[0])
    package = _writing_task(draft["task"])["package"]
    from .lineage import snapshot_for_draft
    from ..io import parse_yaml
    snapshot = snapshot_for_draft(root, draft)
    def value(ref):
        if snapshot is None:
            return load_data(repository_path(root, ref["path"]))
        raw = snapshot.read(ref)
        return json.loads(raw) if Path(ref["path"]).suffix == ".json" else parse_yaml(raw)
    matches = [ref for ref in draft["inputs"]
               if Path(ref["path"]).suffix in {".json", ".yaml", ".yml"}
               and value(ref) == package]
    if len(matches) != 1:
        raise ValueError("revision parent must bind exactly one writing package")
    return deepcopy(matches[0])


def prepare_rendered(root: Path, rendered: dict, budget: Budget, model: str, context: dict) -> dict:
    """Attach reproducible selection context to an already rendered CLI preview."""
    request = request_for(rendered, budget, model)
    if len(canonical_bytes(request)) > budget.max_input_bytes:
        raise ValueError("request exceeds input byte budget; no truncation performed")
    parent = binding(root, context["parent_path"]) if context["parent_path"] else None
    feedback = binding(root, context["feedback_path"]) if context["feedback_path"] else None
    version = rendered.get("renderer_version", 1)
    if parent is not None and version == 2:
        from .writing import load_draft
        package = _parent_package(root, load_draft(root, parent["path"])[0])
    else:
        package = binding(root, context["package_path"])
    result = {"schema_version": version, "kind": "WRITING_PREPARED_REQUEST", "status": "PASS", "mode": "DRY_RUN",
            "context": deepcopy(context), "chapter": context["chapter"], "route": context["route"],
            "package": package, "parent": parent, "feedback": feedback,
            "task": deepcopy(rendered["task"]), "prompt_sha256": rendered["prompt_sha256"],
            "request_sha256": digest(canonical_bytes(request)), "request": request,
            "template": deepcopy(rendered["template"]), "inputs": deepcopy(rendered["inputs"]),
            "budget": budget.to_dict(), "budget_limitation": BUDGET_LIMITATION,
            "qualification": "RESEARCH_ONLY", "formal_eligibility": False, "human_qualification": False,
            "authority_effect": "NONE"}
    if version == 2:
        result.update(renderer_version=2, dependency_records=deepcopy(rendered["dependency_records"]),
                      readiness=deepcopy(rendered.get("readiness", {})))
    return result


def selection_context(root: Path, *, package_path: str | None = None, chapter: int | None = None,
                      route: str = "harness", characters: int = 6000, plan_path: str | None = None,
                      previous_path: str | None = None, parent_path: str | None = None,
                      feedback_path: str | None = None, notes_path: str | None = None,
                      revision_template: str = "revise-v1") -> dict:
    if revision_template not in {"revise-v1", "revise-v2"}:
        raise ValueError("unknown revision template")
    if not parent_path and revision_template != "revise-v1":
        raise ValueError("revision template requires a revision parent")
    if parent_path:
        from .writing import load_draft
        if not feedback_path or package_path or chapter is not None or plan_path or previous_path:
            raise ValueError("revision preparation requires parent and feedback, not draft selections")
        draft, _ = load_draft(root, parent_path)
        package_path = _parent_package(root, draft)["path"]
        chapter, route = draft["chapter"], draft["route"]
        characters = None
    elif not package_path or chapter is None or feedback_path or notes_path:
        raise ValueError("draft preparation requires package and chapter, without revision selections")
    context = {"operation": "revise" if parent_path else "draft", "package_path": package_path,
               "chapter": chapter, "route": route, "characters": characters,
               "plan_path": plan_path, "previous_path": previous_path,
               "parent_path": parent_path, "feedback_path": feedback_path, "notes_path": notes_path}
    # Preserve the exact legacy selection envelope for existing frozen requests.
    if revision_template != "revise-v1":
        context["revision_template"] = revision_template
    return context


def _render_context(root: Path, context: dict, *, version: int | None = None) -> dict:
    if context["operation"] == "draft":
        return PromptRenderer(root, version=version).draft(context["package_path"], context["chapter"], route=context["route"],
                                          characters=context["characters"], plan_path=context["plan_path"],
                                          previous_path=context["previous_path"])
    from .writing import revision_prompt
    return revision_prompt(root, context["parent_path"], context["feedback_path"], context["notes_path"],
                           revision_template=context.get("revision_template", "revise-v1"), renderer_version=version)


def prepare_request(root: Path, *, package_path: str | None = None, chapter: int | None = None,
                    route: str = "harness", characters: int = 6000, plan_path: str | None = None,
                    previous_path: str | None = None, parent_path: str | None = None,
                    feedback_path: str | None = None, notes_path: str | None = None,
                    budget: Budget | None = None, model: str = DEFAULT_MODEL,
                    revision_template: str = "revise-v1", renderer_version: int | None = None) -> dict:
    """Prepare a draft (package/chapter) or revision (parent/feedback) offline."""
    context = selection_context(root, package_path=package_path, chapter=chapter, route=route,
                                characters=characters, plan_path=plan_path, previous_path=previous_path,
                                parent_path=parent_path, feedback_path=feedback_path, notes_path=notes_path,
                                revision_template=revision_template)
    return prepare_rendered(root, _render_context(root, context, version=renderer_version), budget or Budget(), model, context)


def _saved_task_render(root: Path, prepared: dict, task: dict, *, read=None) -> dict:
    """Rebuild the frozen envelope, without consulting runtime observations."""
    read = read or (lambda ref: bound_bytes(root, ref))
    prompt = {"system": read(prepared["template"]).decode("utf-8"),
              "messages": [{"role": "user", "content": canonical_bytes(task).decode()}]}
    return {**prompt, "prompt_sha256": digest(canonical_bytes(prompt)), "task": task,
            "template": prepared["template"], "inputs": prepared["inputs"]}


# Only these two freshly observed leaves vary across the known CPython rebuilds.
# Registered toolchains, code/lock hashes, rebuild status and diff shape stay exact.
_RUNTIME_PYTHON_PATHS = (("current_toolchain", "extractor", "python"),
                         ("toolchain_diff", "extractor", "current", "python"))
_CPYTHON_VERSION = re.compile(r"CPython 3\.[0-9]+\.[0-9]+")


def _object_at(value: dict, keys: tuple[str, ...]) -> dict | None:
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value if isinstance(value, dict) else None


def _runtime_observations(saved_task: dict, fresh_task: dict) -> tuple[dict, list[dict]]:
    """Copy only named source observation leaves, including revision task nesting."""
    normalized = deepcopy(saved_task)
    saved, fresh, task_path = normalized, fresh_task, "task"
    variations = []
    while isinstance(saved, dict) and isinstance(fresh, dict):
        saved_sources, fresh_sources = saved.get("sources"), fresh.get("sources")
        if isinstance(saved_sources, list) and isinstance(fresh_sources, list) and len(saved_sources) == len(fresh_sources):
            for index, (old_source, new_source) in enumerate(zip(saved_sources, fresh_sources, strict=True)):
                prefix = ("verification", "verification_report", "rebuild")
                old_rebuild, new_rebuild = _object_at(old_source, prefix), _object_at(new_source, prefix)
                if (old_rebuild is None or new_rebuild is None
                        or old_rebuild.get("status") != "PASS" or new_rebuild.get("status") != "PASS"
                        or old_rebuild.get("scope") != "EXTRACTION_CONTENT_REBUILD"
                        or new_rebuild.get("scope") != "EXTRACTION_CONTENT_REBUILD"):
                    continue
                for keys in _RUNTIME_PYTHON_PATHS:
                    old_parent, new_parent = _object_at(old_rebuild, keys[:-1]), _object_at(new_rebuild, keys[:-1])
                    if old_parent is None or new_parent is None:
                        continue
                    old, new = old_parent.get(keys[-1]), new_parent.get(keys[-1])
                    if (isinstance(old, str) and isinstance(new, str) and old != new
                            and _CPYTHON_VERSION.fullmatch(old) and _CPYTHON_VERSION.fullmatch(new)):
                        old_parent[keys[-1]] = new
                        variations.append({"path": f"{task_path}.sources[{index}]." + ".".join(prefix + keys),
                                           "stored": old, "current": new})
        saved, fresh = saved.get("writing_task"), fresh.get("writing_task")
        task_path += ".writing_task"
    return normalized, variations


def verify_frozen_request(root: Path, prepared: dict, *, read=None) -> dict:
    """Check a saved request using its own inputs, without invoking today's renderer."""
    _validate(root, prepared, prepared=True)
    read = read or (lambda ref: bound_bytes(root, ref))
    for ref in prepared["inputs"] + [prepared["template"], prepared["package"], prepared["parent"], prepared["feedback"]]:
        if ref is not None:
            read(ref)
    budget = Budget(**prepared["budget"])
    budget.validate(prepared.get("samples", 1))
    frozen = _saved_task_render(root, prepared, prepared["task"], read=read)
    if prepared["prompt_sha256"] != frozen["prompt_sha256"]:
        raise ValueError("prepared request frozen prompt hash mismatch")
    if prepared["request_sha256"] != digest(canonical_bytes(prepared["request"])):
        raise ValueError("prepared request frozen request hash mismatch")
    if canonical_bytes(prepared["request"]) != canonical_bytes(request_for(frozen, budget, prepared["request"]["model"])):
        raise ValueError("prepared request differs from frozen task/template")
    if len(canonical_bytes(prepared["request"])) > budget.max_input_bytes:
        raise ValueError("prepared request exceeds input byte budget; no truncation performed")
    if prepared["chapter"] != prepared["context"]["chapter"] or prepared["route"] != prepared["context"]["route"]:
        raise ValueError("prepared request selection identity mismatch")
    for record in prepared.get("dependency_records", []):
        if digest(canonical_bytes(record["value"])) != record["sha256"] or record["value"]["id"] != record["id"]:
            raise ValueError("prepared request dependency record identity mismatch")
    return frozen


def _verify_prepared_request(root: Path, prepared: dict) -> tuple[dict, dict]:
    # Import preparation still checks fresh semantics. Historical draft loading
    # uses verify_frozen_request and a content-addressed snapshot instead.
    inherited = None
    if prepared.get("schema_version") == 2 and prepared.get("parent"):
        from .lineage import snapshot_for_draft
        from .writing import load_draft
        inherited = snapshot_for_draft(root, load_draft(root, prepared["parent"]["path"])[0])
    def read(ref):
        if inherited is not None and inherited.contains(ref):
            return inherited.read(ref)
        return bound_bytes(root, ref)
    verify_frozen_request(root, prepared, read=read)
    budget = Budget(**prepared["budget"])
    context = prepared["context"]
    if context["operation"] == "revise":
        expected_context = selection_context(root, parent_path=context["parent_path"],
                                             feedback_path=context["feedback_path"], notes_path=context["notes_path"],
                                             revision_template=context.get("revision_template", "revise-v1"))
    else:
        expected_context = selection_context(root, package_path=context["package_path"], chapter=context["chapter"],
                                             route=context["route"], characters=context["characters"],
                                             plan_path=context["plan_path"], previous_path=context["previous_path"])
    if canonical_bytes(context) != canonical_bytes(expected_context):
        raise ValueError("prepared request selection context mismatch")
    rendered = _render_context(root, context, version=prepared["schema_version"])
    current = prepare_rendered(root, rendered, budget, prepared["request"]["model"], context)
    if "samples" in prepared:
        current["samples"] = prepared["samples"]
    normalized_task, variations = _runtime_observations(prepared["task"], rendered["task"])
    semantic = deepcopy(prepared)
    semantic_render = _saved_task_render(root, prepared, normalized_task)
    semantic["task"], semantic["prompt_sha256"] = normalized_task, semantic_render["prompt_sha256"]
    semantic["request"] = request_for(semantic_render, budget, prepared["request"]["model"])
    semantic["request_sha256"] = digest(canonical_bytes(semantic["request"]))
    if prepared["schema_version"] == 2:
        # This is a historical observation, never an admission credential.
        current["readiness"] = semantic["readiness"]
    if canonical_bytes(current) != canonical_bytes(semantic):
        raise ValueError("prepared request differs from current renderer/context manifest")
    report = {"status": "PASS", "scope": "PREPARED_REQUEST_INTEGRITY",
              "stored_prompt_sha256": prepared["prompt_sha256"], "stored_request_sha256": prepared["request_sha256"],
              "fresh_prompt_sha256": current["prompt_sha256"], "fresh_request_sha256": current["request_sha256"],
              "runtime_observation_variations": variations}
    return rendered, report


def verify_prepared_request(root: Path, prepared: dict) -> dict:
    """Verify exact frozen custody, then fresh semantics with two Python leaves allowed."""
    return _verify_prepared_request(root, prepared)[0]


def prepared_request_integrity_report(root: Path, prepared: dict) -> dict:
    """Disclose allowed stored/current observations; not execution or consumption proof."""
    return _verify_prepared_request(root, prepared)[1]


def _publish(root: Path, directory: str, raw: bytes, suffix: str) -> dict:
    """Reuse identical content, but never replace an existing file or a link."""
    relative = f"{directory}/{digest(raw)}.{suffix}"
    ref = {"path": relative, "sha256": digest(raw)}
    path = repository_path(root, relative)
    try:
        return append_bytes(root, relative, raw)
    except FileExistsError:
        if not path.is_file() or bound_bytes(root, ref) != raw:
            raise ValueError("content-addressed session file conflicts with existing bytes")
        return ref


def import_draft(root: Path, text_path: str, request_path: str, *, session_id: str,
                 session_model_label: str, parent_path: str | None = None,
                 feedback_path: str | None = None) -> dict:
    """Import exact UTF-8 text plus a prepared manifest; no API/SDK is invoked."""
    imported_text, request_source = binding(root, text_path), binding(root, request_path)
    raw, prepared_raw = bound_bytes(root, imported_text), bound_bytes(root, request_source)
    text = raw.decode("utf-8")
    if not text.strip():
        raise ValueError("empty session-authored draft")
    from .prose_integrity import prose_integrity
    integrity = prose_integrity(text)
    if integrity["status"] == "FAIL":
        raise ValueError("session prose integrity failed: " + "; ".join(integrity["findings"]))
    prepared = json.loads(prepared_raw)
    verify_prepared_request(root, prepared)
    for path, field in ((parent_path, "parent"), (feedback_path, "feedback")):
        if path is not None and binding(root, path) != prepared[field]:
            raise ValueError(f"session import {field} differs from prepared request")
    chapter = prepared["chapter"]
    candidate = {"path": f"artifacts/candidates/ch{chapter}/{digest(raw)}.txt", "sha256": digest(raw)}
    request_ref = {"path": f"artifacts/writing-requests/{digest(prepared_raw)}.json", "sha256": digest(prepared_raw)}
    run = {"schema_version": 1, "kind": "SESSION_AUTHOR_RUN", "execution_basis": EXECUTION_BASIS,
           "session_id": session_id, "session_configured_model": {"label": session_model_label, "basis": "UNVERIFIED_DECLARATION"},
           "request_source": request_source, "prepared_request": request_ref, "imported_text": imported_text,
           "package": prepared["package"], "request_sha256": prepared["request_sha256"],
           "prompt_sha256": prepared["prompt_sha256"], "inputs": prepared["inputs"], "template": prepared["template"],
           "candidate": candidate, "output": text, "output_sha256": digest(raw),
           "parent": prepared["parent"], "feedback": prepared["feedback"], "qualification": "RESEARCH_ONLY",
           "formal_eligibility": False, "human_qualification": False, "authority_effect": "NONE"}
    if prepared["schema_version"] == 2:
        run["schema_version"] = 2
        # Validate declarations before publishing any snapshot assets.
        run["input_snapshot"] = {"path": "pending-snapshot.json", "sha256": "0" * 64}
    _validate(root, run)
    if prepared["schema_version"] == 2:
        from .lineage import session_refs, snapshot_for_draft
        from .snapshots import freeze_inputs
        from .writing import load_draft
        inherited = snapshot_for_draft(root, load_draft(root, prepared["parent"]["path"])[0]) if prepared["parent"] else None
        run["input_snapshot"] = freeze_inputs(root, session_refs(prepared, run), inherited=inherited,
                                               records=prepared["dependency_records"])
    _publish(root, f"artifacts/candidates/ch{chapter}", raw, "txt")
    _publish(root, "artifacts/writing-requests", prepared_raw, "json")
    author_run = _publish(root, "artifacts/author-runs", canonical_bytes(run), "json")
    source_id = "session-author:" + author_run["sha256"]
    draft = {"schema_version": 1, "kind": "WRITING_DRAFT", "execution_basis": EXECUTION_BASIS,
             "chapter": chapter, "route": prepared["route"], "candidate": candidate, "run": author_run,
             "authors": [{"principal_id": "session:" + session_id, "source_id": source_id, "kind": "MODEL", "run": author_run}],
             "prepared_request": request_ref, "package": prepared["package"], "inputs": prepared["inputs"],
             "template": prepared["template"], "task": prepared["task"], "prompt_sha256": prepared["prompt_sha256"],
             "parent": prepared["parent"], "feedback": prepared["feedback"], "qualification": "RESEARCH_ONLY",
             "formal_eligibility": False, "human_qualification": False, "authority_effect": "NONE"}
    if run["schema_version"] == 2:
        draft.update(schema_version=2, input_snapshot=run["input_snapshot"])
    verify_session_draft(root, draft, raw)
    draft_ref = _publish(root, f"data/writing/drafts/ch{chapter}", canonical_bytes(draft), "json")
    result = {"status": "PASS", "draft": draft_ref, "candidate": candidate, "run": author_run,
            "prepared_request": request_ref, "execution_basis": EXECUTION_BASIS,
            "session_configured_model": run["session_configured_model"], "qualification": "RESEARCH_ONLY",
            "formal_eligibility": False, "human_qualification": False, "authority_effect": "NONE"}
    if run["schema_version"] == 2:
        result["input_snapshot"] = run["input_snapshot"]
    return result


def verify_session_draft(root: Path, draft: dict, candidate_raw: bytes) -> None:
    """Strict alternative to raw-run validation, without claiming provider proof."""
    errors = validate_instance(draft, root / "schemas/draft_registry.schema.json")
    if errors:
        raise ValueError("invalid session draft record: " + "; ".join(errors))
    run = json.loads(bound_bytes(root, draft["run"]))
    _validate(root, run)
    from .lineage import session_refs, snapshot_for_draft
    snapshot = snapshot_for_draft(root, draft)
    if draft["schema_version"] != run["schema_version"] or draft.get("input_snapshot") != run.get("input_snapshot"):
        raise ValueError("session draft/run snapshot binding mismatch")
    read = snapshot.read if snapshot is not None else lambda ref: bound_bytes(root, ref)
    if run["output"].encode("utf-8") != candidate_raw or digest(candidate_raw) != run["output_sha256"]:
        raise ValueError("session output differs from authored candidate")
    if read(run["imported_text"]) != candidate_raw:
        raise ValueError("session import text identity mismatch")
    prepared_raw = bound_bytes(root, run["prepared_request"])
    if read(run["request_source"]) != prepared_raw:
        raise ValueError("session prepared request source identity mismatch")
    prepared = json.loads(prepared_raw)
    if snapshot is not None:
        snapshot.verify(session_refs(prepared, run))
        if snapshot.document["records"] != prepared.get("dependency_records", []):
            raise ValueError("session snapshot dependency records mismatch")
        verify_frozen_request(root, prepared, read=read)
        if prepared["parent"] is not None:
            _verify_revision_history(root, prepared, read)
    else:
        verify_prepared_request(root, prepared)
    for field in ("candidate", "prepared_request", "package", "inputs", "template", "prompt_sha256", "parent", "feedback"):
        if canonical_bytes(draft[field]) != canonical_bytes(run[field]):
            raise ValueError(f"session draft/run {field} binding mismatch")
    for field in ("package", "inputs", "template", "prompt_sha256", "request_sha256", "parent", "feedback"):
        if canonical_bytes(run[field]) != canonical_bytes(prepared[field]):
            raise ValueError(f"session run/prepared request {field} binding mismatch")
    if (draft["chapter"] != prepared["chapter"] or draft["route"] != prepared["route"]
            or canonical_bytes(draft["task"]) != canonical_bytes(prepared["task"])):
        raise ValueError("session draft task/chapter/route differs from prepared request")
    source_id = "session-author:" + draft["run"]["sha256"]
    expected = [{"principal_id": "session:" + run["session_id"], "source_id": source_id,
                 "kind": "MODEL", "run": draft["run"]}]
    if draft["authors"] != expected:
        raise ValueError("session draft author identity mismatch")


def _verify_revision_history(root: Path, prepared: dict, read) -> None:
    from .writing import load_draft

    parent, text = load_draft(root, prepared["parent"]["path"])
    if read(prepared["parent"]) != repository_path(root, prepared["parent"]["path"]).read_bytes():
        raise ValueError("historical revision parent identity mismatch")
    feedback = json.loads(read(prepared["feedback"]))
    if (feedback["draft"] != prepared["parent"] or feedback["candidate"] != parent["candidate"]
            or feedback["inputs"] != parent["inputs"] or prepared["package"] != _parent_package(root, parent)):
        raise ValueError("historical revision feedback/parent binding mismatch")
    task = prepared["task"]
    notes_path = prepared["context"]["notes_path"]
    notes = None
    if notes_path is not None:
        refs = [ref for ref in prepared["inputs"] if ref["path"] == notes_path]
        if len(refs) != 1:
            raise ValueError("historical revision notes binding mismatch")
        notes = read(refs[0]).decode("utf-8")
    if task != {"writing_task": parent["task"], "original": text, "feedback": feedback, "editorial_notes": notes}:
        raise ValueError("historical revision differs from frozen parent/context")
