"""Additive chapter-policy projections graded by evidence severity.

The frozen rules supply locators, not new Evidence. Exact checks concern only
literal anchors, and each anchor is graded by its basis (rcwh.findings): a
literal/title backed by an eligible A-W1 LOCKED decision blocks; a P-Lock
anchor copied from stable prose is a replaceable ADVISORY regression signal.
Free text and literary locks remain semantic obligations; their dedicated
reading is not implemented and is reported as INFO, never as a holding gate.
This module neither writes policies nor changes legacy exact changed-set gates.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .assets.paths import repository_path
from .contracts import project_chapters
from .evaluation.style_reference import CHAPTER_HEADING, _chapter_number
from .io import parse_yaml
from .schema import validate_instance


MANDATORY_PLOCKS = {
    86: "plock:ch86:cold-medicine",
    89: "plock:ch89:small-life-after-confiscation",
    92: "plock:ch92:procedure-density",
    97: "plock:ch97:miaoyu-object-progression",
    100: "plock:ch100:record-keeper-ending",
}
_SCHEMA = Path(__file__).resolve().parents[2] / "schemas/agent_chapter_policy.schema.json"
_PROJECTION = ("inputs", "anchors", "forbidden", "semantic_obligations", "plock")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _in_scope(scope: Any, chapter: int) -> bool:
    # Only structured chapter identifiers/ranges are interpreted, never prose.
    if type(scope) is int:
        return scope == chapter
    if isinstance(scope, str) and scope.count("-") == 1:
        start, end = scope.split("-")
        return start.isdecimal() and end.isdecimal() and int(start) <= chapter <= int(end)
    return False


def derive_agent_anchors(root: Path, chapter: int) -> dict[str, Any]:
    """Return an in-memory MODEL/NONE draft, bound to actual rule-file bytes."""
    return _derive(root, chapter)[0]


def _derive(root: Path, chapter: int) -> tuple[dict[str, Any], dict[str, str]]:
    """Projection plus each anchor's evidence severity (kept out of the stored file).

    Chapter placement via an implementation ref is CURRENT implementation scope,
    not historical authority. Baseline prose is never searched to invent anchors.
    Missing mandatory P-Locks or ambiguous local identities fail closed.
    """
    root = Path(root).resolve()
    if type(chapter) is not int or chapter not in project_chapters(root):
        raise ValueError("agent policy chapter outside configured scope")
    inputs: dict[str, dict] = {}

    def read(path: str) -> Any:
        raw = repository_path(root, path).read_bytes()
        inputs[path] = {"path": path, "sha256": _digest(raw)}
        return parse_yaml(raw) if path.endswith(".yaml") else json.loads(raw)

    def basis(path: str, pointer: str) -> dict:
        return {**inputs[path], "pointer": pointer, "chapter": chapter}

    anchors, forbidden, obligations = [], [], []
    severities: dict[str, str] = {}
    from .findings import ADVISORY, severity_for_decision, strongest
    from .graph import ProvenanceGraph
    graph = ProvenanceGraph.from_repo(root)

    def obligation(path: str, pointer: str, rule: Any, kind: str = "SEMANTIC") -> None:
        obligations.append({"id": f"{path}#{pointer}", "kind": kind, "rule": rule,
                            "status": "PENDING", "basis": [basis(path, pointer)]})

    def anchor(path: str, pointer: str, texts: list[str], mode: str, extra: list[dict] | None = None,
               decision_refs: Any = ()) -> None:
        if not texts or any(not isinstance(text, str) or not text for text in texts):
            raise ValueError(f"invalid exact anchor: {path}#{pointer}")
        if any(text.strip().upper() in {"UNKNOWN", "UNSPECIFIED", "PENDING"} for text in texts):
            obligation(path, pointer, texts, "UNKNOWN")
            return
        anchors.append({"id": f"{path}#{pointer}", "mode": mode, "texts": texts,
                        "basis": [basis(path, pointer), *(extra or [])]})
        severities[f"{path}#{pointer}"] = strongest((severity_for_decision(graph, ref) for ref in decision_refs), ADVISORY)

    def ban(path: str, pointer: str, rule: Any) -> None:
        # Prohibitions stated in natural language are not substring bans.
        forbidden.append({"id": f"{path}#{pointer}", "mode": "SEMANTIC",
                          "rule": rule, "basis": [basis(path, pointer)]})
        obligation(path, pointer, rule, "FORBIDDEN_DRIFT")

    read("data/project/scope.json")
    m6_path = "data/implementation_alignment/m6.json"
    m6 = read(m6_path)
    local_rows: dict[str, tuple[int, dict]] = {}
    matches = [(i, row) for i, row in enumerate(m6["stable_release"]["chapters"]) if row["chapter"] == chapter]
    if len(matches) != 1:
        raise ValueError("missing/ambiguous stable chapter locator")
    local_rows["chapters"] = matches[0]
    for collection in ("chapter_plans", "chapter_protections"):
        matches = [(i, row) for i, row in enumerate(m6[collection]) if row["chapter"] == chapter]
        if len(matches) != 1:
            raise ValueError(f"missing/ambiguous {collection} chapter")
        i, row = matches[0]
        obligation(m6_path, f"/{collection}/{i}", row, "CURRENT_IMPLEMENTATION")
        if collection == "chapter_protections":
            ban(m6_path, f"/{collection}/{i}/forbidden_drift", row["forbidden_drift"])
    for i, row in enumerate(m6["implementation_facts"]):
        if _in_scope(row["chapter_scope"], chapter):
            obligation(m6_path, f"/implementation_facts/{i}", row, "CURRENT_IMPLEMENTATION")
    # Cross-chapter trajectories are free text: retain all as context instead of
    # guessing their chapter scope or converting object names to required words.
    for i, row in enumerate(m6.get("cross_chapter_protections", [])):
        obligation(m6_path, f"/cross_chapter_protections/{i}", row, "CROSS_CHAPTER_CONTEXT")

    def registry(directory: str, key: str) -> dict[str, tuple[str, str, dict]]:
        result = {}
        files = sorted((root / directory).glob("*.yaml"))
        if not files:
            raise ValueError(f"frozen rule registry missing: {directory}")
        for file in files:
            path = file.relative_to(root).as_posix()
            doc = read(path)
            for i, row in enumerate(doc.get(key, [])):
                if row["id"] in result:
                    raise ValueError(f"duplicate {key}: {row['id']}")
                result[row["id"]] = (path, f"/{key}/{i}", row)
        return result

    implementations = registry("data/provenance/implementations", "implementations")
    literals = registry("data/literals", "literal_constraints")
    locks = registry("data/plocks", "literary_locks")
    decisions = registry("data/provenance/decisions", "decisions")
    axes = registry("data/provenance/axes", "title_axes")
    local_locks = [(path, pointer, row) for path, pointer, row in locks.values() if row["chapter"] == chapter]
    if len(local_locks) > 1:
        raise ValueError("ambiguous chapter P-Lock")
    expected_lock = MANDATORY_PLOCKS.get(chapter)
    if expected_lock and (not local_locks or local_locks[0][2]["id"] != expected_lock):
        raise ValueError("mandatory P-Lock missing or mismatched")
    declared_locks = [row["id"] for row in m6["specialized_plocks"] if row["chapter"] == chapter]
    if declared_locks != [row["id"] for _, _, row in local_locks]:
        raise ValueError("M6 specialized P-Lock mismatch")
    plock = {"required": bool(local_locks), "ref": None, "basis": []}
    literal_context, decision_context = set(), set()
    for path, pointer, row in local_locks:
        if (row["state"] != "P_LOCKED" or row["authority"] != "LITERARY_PROTECTION_ONLY"
                or row["generation_effect"] != "PROTECT_AGAINST_REGRESSION"
                or row["replacement_rule"] != "COMPETITION_PLUS_SIX_FIELD_PLUS_PLOCK_PLUS_BLIND_READ"):
            raise ValueError("invalid mandatory P-Lock protection metadata")
        plock = {"required": True, "ref": row["id"], "basis": [basis(path, pointer)]}
        obligation(path, pointer, row, "PLOCK_REVIEW")
        literal_context.update(row.get("upstream_context", {}).get("literal_refs", []))
        decision_context.update(row.get("upstream_context", {}).get("decision_refs", []))
        for i, item in enumerate(row.get("exact_anchors", [])):
            ap = f"{pointer}/exact_anchors/{i}"
            if item["mode"] in {"P1_DIALOGUE", "P1_TERMINAL"}:
                anchor(path, ap, [item["text"]], "CONTAINS")
                if item["mode"] == "P1_TERMINAL":
                    # The mode alone does not specify character-level no-tail.
                    # Even ch100's explicit ban concerns explanatory codas,
                    # verses/theme translations: judging a tail's function is
                    # semantic, not a universal substring/suffix condition.
                    obligation(path, ap, item, "TERMINAL_PLACEMENT")
            else:
                obligation(path, ap, item, "UNKNOWN")
        for i, item in enumerate(row.get("forbidden_drift", [])):
            ban(path, f"{pointer}/forbidden_drift/{i}", item)

    for path, pointer, row in literals.values():
        refs = row.get("implementation_refs", [])
        if any(ref not in implementations for ref in refs):
            raise ValueError(f"literal implementation ref missing: {row['id']}")
        local_refs = [implementations[ref] for ref in refs if implementations[ref][2]["chapter"] == chapter]
        if not local_refs and row["id"] not in literal_context:
            continue
        decision_context.update(row.get("decision_refs", []))
        obligation(path, pointer, row, "SOURCE_ONLY" if row["scope"] == "SOURCE_ONLY" else "SEMANTIC")
        targets = set(row["targets"])
        # SOURCE_ONLY is neither a required insertion nor an automatic ban.
        if (local_refs and row["scope"] != "SOURCE_ONLY" and row["required_in_active_prose"]
                and targets.intersection({"NOVEL_EXACT", "NAME_EXACT"})):
            anchor(path, pointer + "/text", [row["text"]], "CONTAINS",
                   [basis(p, ptr) for p, ptr, _ in local_refs], row.get("decision_refs", []))
        if "NEG" in targets:
            ban(path, pointer, row)

    for path, pointer, row in axes.values():
        if row.get("current_chapter") != chapter:
            continue
        obligation(path, pointer, row, "TITLE_BOUNDARY")
        for field in ("placement_decision_ref", "formal_title_decision_ref"):
            if row.get(field):
                decision_context.add(row[field])
        if row["class"] not in {"T0", "T1"} or row.get("generated"):
            continue  # TG/T2/T3 cannot acquire exact-title authority.
        related = {row[field] for field in ("placement_decision_ref", "formal_title_decision_ref") if row.get(field)}
        # T1's MUST ref is named on its implementation, not the axis itself.
        for ref in row.get("implementation_refs", []):
            if ref not in implementations or implementations[ref][2]["chapter"] != chapter:
                raise ValueError("title implementation ref missing or cross-chapter")
            related.update(implementations[ref][2].get("decision_refs", []))
        decision_context.update(related)
        supporting = [decisions[ref] for ref in sorted(related) if ref in decisions
                      and row["text"] in decisions[ref][2].get("statement", "")
                      and decisions[ref][2].get("constraint") == "MUST"
                      and decisions[ref][2].get("status") == "LOCKED"]
        if not supporting:
            obligation(path, pointer, row, "UNKNOWN")
            continue
        extra = [basis(p, ptr) for p, ptr, _ in supporting]
        supporting_ids = [r["id"] for _, _, r in supporting]
        if row["class"] == "T1":
            anchor(path, pointer + "/text", [row["text"]], "HEADING_CONTAINS", extra, supporting_ids)
        else:
            # Preserve source punctuation AND the frozen rule's typographic
            # rendering; do not choose the baseline as the only permitted title.
            i, stable = local_rows["chapters"]
            variants = [row["text"]]
            if stable["title"].replace("　", "，") == row["text"] and stable["title"] not in variants:
                variants.append(stable["title"])
                extra.append(basis(m6_path, f"/stable_release/chapters/{i}/title"))
            anchor(path, pointer + "/text", variants, "HEADING_EXACT", extra, supporting_ids)

    for ref in sorted(decision_context):
        if ref not in decisions:
            raise ValueError(f"local decision ref missing: {ref}")
        path, pointer, row = decisions[ref]
        obligation(path, pointer, row, "DECISION_BOUNDARY")
    legacy_path = f"data/promotion/policies/ch{chapter}.json"
    if repository_path(root, legacy_path).is_file():
        legacy = read(legacy_path)
        if legacy["chapter"] != chapter:
            raise ValueError("legacy policy chapter mismatch")
        # Its book-level checks/exact changed set are not chapter-local rules.
        obligation(legacy_path, "", legacy, "LEGACY_BOOK_SCOPE_NOT_PROJECTED")
    return ({"schema_version": 1, "id": f"agent-policy:ch{chapter}:anchors:v1", "chapter": chapter,
             "status": "DRAFT_GENERATED", "qualification": "MODEL", "authority_effect": "NONE",
             "inputs": [inputs[path] for path in sorted(inputs)], "anchors": anchors,
             "forbidden": forbidden, "semantic_obligations": obligations, "plock": plock,
             "review_refs": []}, severities)


def validate_agent_policy(root: Path, policy: Any, chapter: int) -> list[str]:
    """Return structural/binding findings; an empty list is NOT a safety PASS.

    Re-derivation verifies full input hashes, pointers, local scope and mandatory
    rule coverage. Removing an obligation/lock or adding baseline-invented rules
    cannot pass validation. Review refs are byte checked, not treated as verdicts.
    """
    errors = validate_instance(policy, _SCHEMA)
    if errors:
        return errors
    if type(chapter) is not int or policy["chapter"] != chapter:
        return ["agent policy chapter mismatch"]
    try:
        expected = derive_agent_anchors(root, chapter)
        for key in _PROJECTION:
            if policy[key] != expected[key]:
                errors.append(f"agent policy {key}: stale, altered, or cross-chapter projection")
        for ref in policy["review_refs"]:
            raw = repository_path(Path(root), ref["path"]).read_bytes()
            if _digest(raw) != ref["sha256"]:
                errors.append("agent policy review ref stale")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"agent policy inputs: {exc}")
    return errors


def evaluate_agent_policy(root: Path, policy: Any, chapter: int, candidate_text: str | bytes,
                          replacement_reason: str | None = None) -> dict[str, Any]:
    """Evaluate one actual chapter's machine anchors, graded by evidence severity.

    Integrity/binding errors and a lost BLOCKING anchor FAIL. A lost P-Lock or
    other ADVISORY anchor is reported as a replaceable finding; with a recorded
    replacement reason it is an accepted replacement. Semantic reading of the
    free-text obligations is not implemented and is reported as INFO only.
    """
    from .findings import BLOCKING, NOT_IMPLEMENTED, Finding, gate_status
    errors = validate_agent_policy(root, policy, chapter)
    severities: dict[str, str] = {}
    if not errors:
        try:
            severities = _derive(root, chapter)[1]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"agent policy inputs: {exc}")
    raw = candidate_text.encode("utf-8") if isinstance(candidate_text, str) else candidate_text
    results, findings = [], []
    try:
        text = raw.decode("utf-8")
        headings = list(CHAPTER_HEADING.finditer(text))
        if (len(headings) != 1 or _chapter_number(headings[0]["number"]) != chapter
                or text[:headings[0].start()].strip()):
            errors.append("candidate chapter heading mismatch")
        elif not text[headings[0].end():].strip():
            errors.append("candidate has no chapter body")
        elif not errors:
            heading = headings[0]["title"].strip()
            body = text[headings[0].end():]
            for item in policy["anchors"]:
                mode, texts = item["mode"], item["texts"]
                if mode == "HEADING_EXACT":
                    preserved = heading in texts
                elif mode == "HEADING_CONTAINS":
                    preserved = any(value in heading for value in texts)
                else:
                    preserved = any(value in body for value in texts)
                severity = severities.get(item["id"], BLOCKING)
                results.append({"id": item["id"], "preserved": preserved, "severity": severity})
                if not preserved:
                    findings.append(Finding(f"ANCHOR_MISSING:{item['id']}", severity, item["id"],
                                            replacement_reason if severity != BLOCKING else None,
                                            replaceable=severity != BLOCKING))
    except (UnicodeError, ValueError) as exc:
        errors.append(f"candidate bytes: {exc}")
    findings += [Finding("POLICY_INTEGRITY", BLOCKING, error) for error in errors]
    status = gate_status(findings, [NOT_IMPLEMENTED])
    soft_losses = [f for f in findings if f.replaceable]
    return {"chapter": chapter, "candidate_sha256": _digest(raw), "status": status,
            "anchor_status": "FAIL" if status == "FAIL" else "REPLACEMENT_CASE" if soft_losses else "PASS",
            "replacement_reason": replacement_reason if soft_losses else None,
            "semantic_status": NOT_IMPLEMENTED, "qualification": "MODEL", "authority_effect": "NONE",
            "chapter_safety_status": status, "automatic_policy_pass": False, "anchor_results": results,
            "findings": errors + [f"anchor missing: {f.basis}" for f in findings if f.code.startswith("ANCHOR_MISSING")],
            "graded_findings": [f.to_dict() for f in findings],
            "pending_reasons": [], "info": ["DEDICATED_CANDIDATE_POLICY_SEMANTIC_READING_NOT_IMPLEMENTED"],
            "review_refs_verified_as_readings": False}
