"""Read-only policy coverage and quote checks, never semantic qualification.

The request preserves projected roots and structural components without turning
metadata into prose requirements. A complete submitted checklist is a declaration,
not proof of reading or entailment. No intake, aggregation or release consumer is
provided here; all valid submissions retain semantic/identity PENDING.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re

from ..agent_policies import evaluate_agent_policy, validate_agent_policy
from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..generation.records import bound_bytes
from ..io import load_data
from ..schema import validate_instance

SCHEMA = Path(__file__).resolve().parents[3] / "schemas/policy_evidence_reading.schema.json"


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite JSON value: {value}")

    def floating(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"nonfinite JSON number: {value}")
        return result

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=constant, parse_float=floating)


def _bound(root: Path, ref: dict) -> bytes:
    if (not isinstance(ref, dict) or set(ref) != {"path", "sha256"}
            or not isinstance(ref["path"], str) or not isinstance(ref["sha256"], str)
            or re.fullmatch(r"[a-f0-9]{64}", ref["sha256"]) is None):
        raise ValueError("invalid exact file binding")
    return bound_bytes(root, ref)


def _value(root: Path, ref: dict, pointer: str):
    raw = _bound(root, {key: ref[key] for key in ("path", "sha256")})
    path = repository_path(root, ref["path"])
    value = strict_json(raw) if path.suffix == ".json" else load_data(path)
    if not isinstance(pointer, str) or re.fullmatch(r"(?:/(?:[^~/]|~[01])*)*", pointer) is None:
        raise ValueError("invalid JSON pointer")
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if re.fullmatch(r"0|[1-9][0-9]*", token) is None:
                raise ValueError("invalid array pointer")
            value = value[int(token)]
        else:
            value = value[token]
    return value


def _components(value, pointer):
    if isinstance(value, dict) and value:
        for key in sorted(value):
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from _components(value[key], f"{pointer}/{escaped}")
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from _components(item, f"{pointer}/{index}")
    else:
        yield pointer, value


def _identity(ref: dict, pointer: str) -> str:
    return f"{ref['path']}@{ref['sha256']}#{pointer}"


def _manifest(root: Path, ref: dict, policy: dict) -> list[dict]:
    rows = []

    def add(pointer, value, role, parent=None, basis=None):
        row = {"key": _identity(ref, pointer), "pointer": pointer, "role": role,
               "value": deepcopy(value), "value_sha256": digest(canonical_bytes(value)),
               "parent": parent, "basis": deepcopy(basis or []), "crosswalk": []}
        rows.append(row)
        return row

    for index, item in enumerate(policy["semantic_obligations"]):
        pointer = f"/semantic_obligations/{index}"
        for basis in item["basis"]:
            _value(root, basis, basis["pointer"])
        parent = add(pointer, item, "PROJECTED_ROOT", basis=item["basis"])
        for child_pointer, value in _components(item["rule"], pointer + "/rule"):
            add(child_pointer, value, "STRUCTURAL_VALUE_NOT_AUTOMATIC_REQUIREMENT", parent["key"])
        if item["kind"] == "PLOCK_REVIEW":
            for feature_index, feature in enumerate(item["rule"]["required_features"]):
                add(f"{pointer}/rule/required_features/{feature_index}", feature,
                    "PLOCK_FEATURE", parent["key"], [
                        {**basis, "pointer": f"{basis['pointer']}/required_features/{feature_index}"}
                        for basis in item["basis"]])
    roots = [row for row in rows if row["role"] == "PROJECTED_ROOT"]
    for index, item in enumerate(policy["anchors"]):
        for basis in item["basis"]:
            _value(root, basis, basis["pointer"])
        add(f"/anchors/{index}", item, "ANCHOR_OBSERVATION", basis=item["basis"])
    for index, item in enumerate(policy["forbidden"]):
        aliases = [row["key"] for row in roots
                   if row["value"]["kind"] == "FORBIDDEN_DRIFT"
                   and row["value"]["rule"] == item["rule"] and row["basis"] == item["basis"]]
        if not aliases:
            raise ValueError("forbidden row lacks a projected-root crosswalk")
        add(f"/forbidden/{index}", item, "FORBIDDEN_ALIAS", basis=item["basis"])["crosswalk"] = aliases
    keys = [row["key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate policy manifest key")
    return rows


def build_policy_evidence_request(root: Path, selection: dict, chapter: int) -> dict:
    """Bind the explicitly selected policy/candidate; no latest-version discovery."""
    if type(chapter) is not int:
        raise ValueError("chapter must be an integer")
    selected = strict_json(_bound(root, selection))
    chapters = selected["chapters"]
    ids = [row["chapter"] for row in chapters]
    if any(type(value) is not int for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("duplicate or invalid selected chapter")
    matches = [row for row in chapters if row["chapter"] == chapter]
    if len(matches) != 1:
        raise ValueError("selected chapter missing")
    row = matches[0]
    refs = {key: deepcopy(row[key]) for key in ("candidate", "policy", "draft", "writing_package")}
    for ref in refs.values():
        _bound(root, ref)
    policy = strict_json(_bound(root, refs["policy"]))
    errors = validate_agent_policy(root, policy, chapter)
    if errors:
        raise ValueError("invalid selected policy: " + "; ".join(errors))
    # Projection dependencies and book reading scope are separate. Neither alone
    # establishes complete semantic context, author lineage or source authority.
    context = {"selection": selection, "selected": refs,
               "projection_inputs": policy["inputs"],
               "book_candidates": [{"chapter": item["chapter"], "candidate": item["candidate"]}
                                   for item in chapters]}
    for item in context["book_candidates"]:
        _bound(root, item["candidate"]).decode("utf-8")
    manifest = _manifest(root, refs["policy"], policy)
    payload = {"schema_version": 1, "kind": "POLICY_EVIDENCE_REQUEST", "chapter": chapter,
               "context": context, "context_sha256": digest(canonical_bytes(context)),
               "manifest": manifest, "manifest_sha256": digest(canonical_bytes(manifest)),
               "validator": {"path": "src/rcwh/evaluation/policy_evidence.py",
                             "sha256": digest(Path(__file__).read_bytes())},
               "reading_schema_sha256": digest(SCHEMA.read_bytes()),
               "qualification": "MODEL", "authority_effect": "NONE", "evidence_effect": "NONE",
               "semantic_expansion_status": "PENDING_ATTRIBUTED_CLAUSE_REVIEW",
               "identity_eligibility": "PENDING_NOT_IMPLEMENTED"}
    return {**payload, "request_sha256": digest(canonical_bytes(payload))}


def _interval(value: dict, text: str) -> tuple[int, int]:
    start, end = value["start"], value["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise ValueError("invalid Unicode evidence interval")
    return start, end


def _covered(intervals: list[tuple[int, int]], start: int, stop: int) -> bool:
    end = start
    for left, right in sorted(intervals):
        if right <= end:
            continue
        if left > end:
            return False
        end = right
        if end >= stop:
            return True
    return False


def _full_coverage(intervals: list[tuple[int, int]], length: int) -> bool:
    return length > 0 and _covered(intervals, 0, length)


def check_policy_evidence(root: Path, request: dict, raw_reading: dict) -> dict:
    """Validate a detached raw submission binding, not its semantic entailment.

    Submitted findings are returned as attributed data. Even complete SUPPORTED
    declarations cannot satisfy policy semantics or any release gate.
    """
    context = request["context"]
    rebuilt = build_policy_evidence_request(root, context["selection"], request["chapter"])
    if canonical_bytes(request) != canonical_bytes(rebuilt):
        raise ValueError("stale or altered policy evidence request")
    submitted = strict_json(_bound(root, raw_reading))
    errors = validate_instance(submitted, SCHEMA)
    if errors:
        raise ValueError("invalid policy evidence reading: " + "; ".join(errors))
    for field in ("request_sha256", "context_sha256", "manifest_sha256"):
        if submitted[field] != request[field]:
            raise ValueError(f"stale reading: {field}")
    candidate = context["selected"]["candidate"]
    if submitted["candidate_sha256"] != candidate["sha256"]:
        raise ValueError("stale candidate reading")
    allowed = {ref["path"]: ref for ref in context["projection_inputs"]}
    for ref in [*context["selected"].values(), *(item["candidate"] for item in context["book_candidates"])]:
        if ref["path"] in allowed and allowed[ref["path"]] != ref:
            raise ValueError("conflicting evidence file binding")
        allowed[ref["path"]] = ref
    texts = {}

    def text_for(ref):
        if allowed.get(ref["path"]) != ref:
            raise ValueError("evidence file outside frozen context")
        if ref["path"] not in texts:
            texts[ref["path"]] = _bound(root, ref).decode("utf-8")
        return texts[ref["path"]]

    declared_ranges = {}
    for scope in submitted["read_scope"]:
        text = text_for(scope["file"])
        interval = _interval(scope, text)
        declared_ranges.setdefault(scope["file"]["path"], []).append(interval)
    keys = [item["key"] for item in submitted["checks"]]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate submitted check key")
    expected = {row["key"] for row in request["manifest"]}
    if set(keys) - expected:
        raise ValueError("unknown submitted check key")
    for check in submitted["checks"]:
        for evidence in check["support"] + check["counterevidence"]:
            text = text_for(evidence["file"])
            start, end = _interval(evidence, text)
            if text[start:end] != evidence["quote"]:
                raise ValueError("evidence quote differs from exact file text")
            if not _covered(declared_ranges.get(evidence["file"]["path"], []), start, end):
                raise ValueError("evidence outside declared read scope")
    text = text_for(candidate)
    complete = _full_coverage(declared_ranges.get(candidate["path"], []), len(text))
    missing = sorted(expected - set(keys))
    machine = evaluate_agent_policy(root, strict_json(_bound(root, context["selected"]["policy"])), request["chapter"], text)
    unsupported = [item["key"] for item in submitted["checks"]
                   if item["finding"] != "UNKNOWN" and not (item["support"] or item["counterevidence"])]
    return {"kind": "POLICY_EVIDENCE_CHECK", "raw_reading": deepcopy(raw_reading),
            "request_sha256": request["request_sha256"], "integrity_status": "PASS",
            "declared_structural_coverage": "PENDING" if missing or not complete or unsupported else "PASS",
            "missing_checks": missing, "unsupported_declarations": unsupported,
            "candidate_declared_read_scope_complete": complete,
            "attributed_checks": deepcopy(submitted["checks"]), "machine": machine,
            "status": "FAIL" if machine["status"] == "FAIL" else "PENDING",
            "semantic_status": "PENDING", "identity_eligibility": "PENDING_NOT_IMPLEMENTED",
            "semantic_expansion_status": request["semantic_expansion_status"],
            "authority_effect": "NONE", "evidence_effect": "NONE", "qualification": "MODEL",
            "independent_human_admission": False, "release_gate_eligibility": "PENDING",
            "limitations": ["Exact quotes do not prove entailment or actual reading.",
                            "No author eligibility, negative aggregation, clause qualification or release integration.",
                            "All submitted findings, including negatives, retained as attributed data."]}
