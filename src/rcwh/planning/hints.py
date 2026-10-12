"""Citation-bound hint seeds, never automatic editorial propagation."""
from __future__ import annotations
from pathlib import Path
from ..io import load_data
from ..assets.paths import repository_path
from ..schema import validate_instance
from .chapters import ChapterPlans
from .references import BOUNDARY, record, verify_record, write_new

SEEDS = [("data/literary_ecology/m5.json", "evidence_nodes", "m5", "POETIC_HINT"),
         ("data/world/m3_knowledge.json", "longlines", "m3", "LONG_LINE"),
         ("data/implementation_alignment/m6.json", "cross_chapter_protections", "m6", "OBJECT"),
         ("data/provenance/claims/r4_w2.yaml", "claims", "r4_w2", "COMMENTARY")]


def build_hint_ledger(root: Path, *, output: str | None = None) -> dict:
    hints = []
    for path, key, prefix, kind in SEEDS:
        for index, value in enumerate(load_data(repository_path(root, path))[key]):
            if prefix == "m5" and value["id"] not in {f"C{i:02}" for i in range(1, 7)}:
                continue
            hints.append({"id": f"{prefix}:{value['id']}", "kind": kind,
                          "label": value.get("name", value.get("statement", value["id"])),
                          "source_record": record(root, path, f"/{key}/{index}", value),
                          "evidence_level": "EXISTING_CLAIM_SUPPORT" if prefix == "r4_w2" else "EDITORIAL_INTERPRETATION_DRAFT",
                          "claim_ref": value["id"] if prefix == "r4_w2" else None,
                          "target_refs": [], "planned_responses": [], "status": "DRAFT_IMPORTED",
                          "unresolved": ["target_refs", "response_chapter", "response_scene", "response_mode"]})
    ledger = {**BOUNDARY, "schema_version": 1, "status": "DRAFT_IMPORTED", "hints": hints,
              "rules": [{"id": "C05_NO_NEW_VERDICTS", "source_hint": "m5:C05", "rule": "作为命运总谱，不在后20再造一套新判词。", "status": "DRAFT_IMPORTED"}],
              "candidate_policy": "ZHIPI_SEARCH_MATCHES_ARE_CANDIDATE_ONLY; NO_AUTOMATIC_ADOPTION"}
    if output:
        write_new(repository_path(root, output), ledger)
    return ledger


def threads_report(root: Path, *, ledger: dict | None = None, directory: str | None = None) -> dict:
    ledger = ledger if ledger is not None else load_data(root / "data/planning/hints.json")
    checks = []
    def add(status, code, ref, detail):
        checks.append({"status": status, "code": code, "ref": ref, "detail": detail})
    errors = validate_instance(ledger, root / "schemas/hint_ledger.schema.json")
    for error in errors:
        add("FAIL", "INVALID_HINT_LEDGER", "hints", error)
    if errors:
        return {**BOUNDARY, "status": "FAIL", "checks": checks, "semantic_verified_response": "NOT_CHECKED"}
    seen = set()
    for hint in ledger.get("hints", []):
        identity = hint["id"]
        if identity in seen:
            add("FAIL", "DUPLICATE_HINT", identity, "duplicate hint id")
        seen.add(identity)
        for error in verify_record(root, hint["source_record"]):
            add("FAIL", error, identity, "hint text/hash/citation changed")
        if hint.get("claim_ref") and hint["claim_ref"] != hint["source_record"]["value"].get("id"):
            add("FAIL", "CLAIM_BINDING_MISMATCH", identity, "claim id differs from checked source")
        responses = hint.get("planned_responses", [])
        if not responses:
            add("PENDING", "HINT_RESPONSE_UNPLANNED", identity, "unknown links are not propagated")
        for response in responses:
            chapter, scene_id = response.get("chapter"), response.get("scene")
            if response.get("mode") not in {"DIRECT", "ECHO", "DEFERRED", "OPEN_UNANSWERED"}:
                add("FAIL", "INVALID_RESPONSE_MODE", identity, str(response.get("mode")))
            if identity == "m5:C05" and response.get("creates_new_verdicts"):
                add("FAIL", "C05_NEW_VERDICTS_FORBIDDEN", identity, "do not recreate a verdict system")
            if chapter is None or scene_id is None:
                add("PENDING", "HINT_LINK_UNRESOLVED", identity, "explicit chapter and scene required for coverage")
                continue
            if type(chapter) is not int or chapter < 1:
                add("FAIL", "INVALID_RESPONSE_CHAPTER", identity, str(chapter))
                continue
            if chapter > 100:
                add("PENDING", "HINT_RESPONSE_BEYOND_CURRENT_MODEL", identity, str(chapter))
            try:
                plan = ChapterPlans(root, directory).get(chapter)
                covered = {x["id"] for x in plan["scenes"]}
                if scene_id not in covered:
                    add("PENDING", "HINT_RESPONSE_SCENE_UNCOVERED", identity, f"ch{chapter}:{scene_id}")
                else:
                    add("PASS", "HINT_RESPONSE_DECLARED", identity, f"ch{chapter}:{scene_id}; not text verification")
            except (OSError, KeyError, ValueError, TypeError) as exc:
                add("PENDING", "HINT_RESPONSE_PLAN_MISSING", identity, str(exc))
    checks.sort(key=lambda row: (row["ref"], row["code"], row["detail"]))
    states = {row["status"] for row in checks}
    return {**BOUNDARY, "status": "FAIL" if "FAIL" in states else "PENDING" if "PENDING" in states else "PASS",
            "checks": checks, "hints": len(ledger.get("hints", [])), "semantic_verified_response": "NOT_CHECKED"}
