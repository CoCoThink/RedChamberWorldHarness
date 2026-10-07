from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


@dataclass
class ImplementationAlignmentRuntime:
    data: dict[str, Any]
    chapters: dict[int, dict[str, Any]]
    plans: dict[int, dict[str, Any]]
    facts: dict[str, dict[str, Any]]
    protections: dict[int, dict[str, Any]]
    competitions: dict[int, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ImplementationAlignmentRuntime":
        data = load_data(root / "data" / "implementation_alignment" / "m6.json") or {}
        return cls(
            data=data,
            chapters={
                x["chapter"]: x
                for x in data.get("stable_release", {}).get("chapters", [])
            },
            plans={x["chapter"]: x for x in data.get("chapter_plans", [])},
            facts={x["id"]: x for x in data.get("implementation_facts", [])},
            protections={x["chapter"]: x for x in data.get("chapter_protections", [])},
            competitions={x["chapter"]: x for x in data.get("competition_fixtures", [])},
        )

    def summary(self) -> dict[str, Any]:
        completion = self.data.get("completion", {})
        return {
            "milestone": self.data.get("milestone"),
            "status": self.data.get("status"),
            "stable_release": self.data.get("stable_release", {}).get("release_id"),
            "stable_sha256": self.data.get("stable_release", {}).get("sha256"),
            "chapters": len(self.chapters),
            "chapter_plans": len(self.plans),
            "implementation_facts": len(self.facts),
            "chapter_protections": len(self.protections),
            "cross_chapter_protections": len(self.data.get("cross_chapter_protections", [])),
            "competition_fixtures": len(self.competitions),
            "completion": completion,
        }

    def stable(self) -> dict[str, Any]:
        return self.data["stable_release"]

    def chapter(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.chapters:
            raise KeyError(f"M6 chapter query covers 81..100: {chapter}")
        fact_ids = self._fact_ids_for_chapter(chapter)
        return {
            "chapter": chapter,
            "stable_body": self.chapters[chapter],
            "plan": self.plans[chapter],
            "protection": self.protections[chapter],
            "implementation_facts": [self.facts[x] for x in fact_ids],
            "specialized_plocks": [
                x["id"]
                for x in self.data.get("specialized_plocks", [])
                if x["chapter"] == chapter
            ],
            "competition": self.competitions.get(chapter),
            "alignment": next(
                x for x in self.data["chapter_alignment"]
                if x["chapter"] == chapter
            ),
        }

    def fact(self, fact_id: str) -> dict[str, Any]:
        if fact_id not in self.facts:
            raise KeyError(f"Unknown implementation fact: {fact_id}")
        return self.facts[fact_id]

    def protection(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.protections:
            raise KeyError(f"Unknown chapter protection: {chapter}")
        return self.protections[chapter]

    def competition(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.competitions:
            raise KeyError(f"No frozen competition fixture for chapter {chapter}")
        return self.competitions[chapter]

    def trace(self, kind: str, key: str, registry: Any) -> dict[str, Any]:
        if kind == "source":
            ref = key if key.startswith("doc:") else f"doc:{key}"
            if ref not in registry.documents:
                raise KeyError(f"Unknown source document: {ref}")
            node: Any = {"source_ref": ref}
        elif kind == "fact":
            node = self.fact(key)
        elif kind == "chapter":
            node = self.chapter(int(key))
        elif kind == "protection":
            node = self.protection(int(key))
        else:
            raise KeyError(f"Unknown M6 trace kind: {kind}")

        refs = _collect_doc_refs(node)
        if kind == "source":
            refs = [node["source_ref"]]
        resolved = []
        for ref in refs:
            doc = registry.documents.get(ref)
            if doc is None:
                resolved.append({"ref": ref, "kind": "missing_document"})
                continue
            resolved.append({
                "ref": ref,
                "kind": "document",
                "filename": doc["filename"],
                "sha256": doc["sha256"],
                "self_contained_path": doc["self_contained_path"],
                "canonical_path": doc["canonical_path"],
                "authority": doc["authority"],
                "runtime_authority": doc["runtime_authority"],
                "semantic_coverage": doc["machine_representation"]["semantic_coverage"],
            })
        return {
            "kind": kind,
            "key": key,
            "node": node,
            "resolved_sources": resolved,
            "trace_complete": bool(resolved) and all(x["kind"] == "document" for x in resolved),
        }

    def validate_integrity(
        self,
        root: Path,
        registry: Any,
        reconstruction: Any,
        world: Any,
        object_network: Any,
        literary_ecology: Any,
        plocks: Any,
        competitions: Any,
        promotions: Any,
    ) -> list[str]:
        errors: list[str] = []
        if self.data.get("milestone") != "M6":
            errors.append("Implementation alignment milestone must be M6")

        expected = set(range(81, 101))
        if set(self.chapters) != expected:
            errors.append("M6 stable body must contain chapter locators 81..100 exactly")
        if set(self.plans) != expected:
            errors.append("M6 chapter plans must contain 81..100 exactly")
        if set(self.protections) != expected:
            errors.append("M6 chapter protections must contain 81..100 exactly")
        if len(self.facts) != 39:
            errors.append(f"M6 implementation register must contain 39 normalized facts; got {len(self.facts)}")

        stable = self.data.get("stable_release", {})
        stable_ref = stable.get("document_ref")
        stable_doc = registry.documents.get(stable_ref)
        if stable_doc is None:
            errors.append(f"M6 stable body document missing from registry: {stable_ref}")
        elif stable_doc.get("sha256") != stable.get("sha256"):
            errors.append("M6 stable body SHA does not match DocumentRegistry")

        sources = self.data.get("sources", {})
        for name, source in sources.items():
            doc = registry.documents.get(source["document_ref"])
            if doc is None:
                errors.append(f"M6 source {name}: unregistered document")
            elif doc["sha256"] != source["sha256"]:
                errors.append(f"M6 source {name}: SHA256 mismatch")

        # Stable chapter locators must be contiguous and cover the exact frozen body.
        ordered = [self.chapters[ch] for ch in range(81, 101)]
        expected_line = 1
        for item in ordered:
            if item["line_start"] != expected_line:
                errors.append(
                    f"chapter {item['chapter']}: stable locator gap/overlap, "
                    f"expected line {expected_line}, got {item['line_start']}"
                )
            if item["line_end"] < item["line_start"]:
                errors.append(f"chapter {item['chapter']}: invalid stable line range")
            expected_line = item["line_end"] + 1
        if expected_line - 1 != stable.get("line_count"):
            errors.append("M6 stable chapter locators do not cover the frozen body line count")

        # Reuse the reviewed promotion baseline as an independent chapter-hash fixture.
        promo = promotions.records.get("promotion:ch86:b:v1-5-candidate")
        if promo is None:
            errors.append("M6 cannot find the Chapter-86 promotion fixture")
        else:
            if promo["baseline"]["sha256"] != stable["sha256"]:
                errors.append("M6 stable SHA disagrees with promotion baseline")
            for ch, item in self.chapters.items():
                expected_hash = promo["baseline_chapter_sha256"].get(str(ch))
                if expected_hash != item["sha256"]:
                    errors.append(f"chapter {ch}: stable chapter SHA disagrees with promotion fixture")

        # Every aligned chapter must exist in the downstream runtimes.
        for ch in range(81, 101):
            if ch not in reconstruction.chapters:
                errors.append(f"chapter {ch}: missing Reconstruction node")
            if ch not in world.presence:
                errors.append(f"chapter {ch}: missing World chapter")
            if ch not in literary_ecology.post80_text:
                errors.append(f"chapter {ch}: missing Literary Ecology chapter")
            if ch not in self.plans or ch not in self.protections:
                continue
            if self.plans[ch]["source_ref"] != "doc:23861cce04ac":
                errors.append(f"chapter {ch}: plan source drift")
            if self.protections[ch]["source_ref"] != "doc:626917a3603d":
                errors.append(f"chapter {ch}: protection source drift")

        # Specialized PR9 P-Locks are a strict subset of the full 20-chapter protection table.
        expected_specialized = {
            "plock:ch86:cold-medicine",
            "plock:ch89:small-life-after-confiscation",
            "plock:ch92:procedure-density",
            "plock:ch97:miaoyu-object-progression",
            "plock:ch100:record-keeper-ending",
        }
        declared_specialized = {x["id"] for x in self.data.get("specialized_plocks", [])}
        if declared_specialized != expected_specialized:
            errors.append("M6 specialized P-Lock bridge must preserve the exact PR9 five-lock set")
        for lock_id in expected_specialized:
            lock = plocks.locks.get(lock_id)
            if lock is None:
                errors.append(f"M6 specialized P-Lock missing: {lock_id}")
            elif lock["active_prose_locator"]["file_sha256"] != stable["sha256"]:
                errors.append(f"{lock_id}: specialized P-Lock locator not on frozen stable body")

        # Freeze the production state exactly; do not silently resume literature.
        for ch, fixture in self.competitions.items():
            record = competitions.records.get(fixture["id"])
            if record is None:
                errors.append(f"chapter {ch}: missing competition fixture {fixture['id']}")
                continue
            if record["state"] != fixture["state"]:
                errors.append(
                    f"chapter {ch}: competition state drift {record['state']} != {fixture['state']}"
                )
        if self.competitions[89]["freeze_effect"] != "DO_NOT_CONTINUE_PHASE2":
            errors.append("Chapter 89 Phase 2 must remain frozen")
        if self.competitions[92]["freeze_effect"] != "DO_NOT_START":
            errors.append("Chapter 92 pressure work must remain frozen")
        if self.competitions[97]["freeze_effect"] != "DO_NOT_START":
            errors.append("Chapter 97 pressure work must remain frozen")

        # The object runtime should remain usable while M6 does not try to duplicate it.
        continuity = object_network.continuity_report()
        if continuity["status"] != "PASS":
            errors.append("M6 requires Object continuity PASS")

        forbidden_identity_prefixes = ("A-", "B-", "EVIDENCE_")
        for fact in self.facts.values():
            if fact.get("source_ref") != "doc:b90e41f44edb":
                errors.append(f"{fact['id']}: implementation fact source drift")
            if any(str(fact.get("identity", "")).startswith(x) for x in forbidden_identity_prefixes):
                errors.append(f"{fact['id']}: implementation identity illegally resembles Evidence authority")

        norm = self.data.get("source_normalization", {})
        if norm.get("effective_stable_body_sha256") != stable.get("sha256"):
            errors.append("M6 source-normalization effective stable pointer mismatch")
        if norm.get("stale_header_body_sha256") == stable.get("sha256"):
            errors.append("M6 failed to distinguish stale v1.3 header from effective v1.4 release")

        completion = self.data.get("completion", {})
        if completion.get("chapters_aligned") != 20:
            errors.append("M6 must align exactly 20 chapters")
        if not completion.get("literature_frozen"):
            errors.append("M6 must keep literature frozen")
        if completion.get("stable_active_changed"):
            errors.append("M6 may not change stable ACTIVE")
        if completion.get("p0_full_coverage"):
            errors.append("M6 may not claim P0 100% before M7")
        if completion.get("completion_gate_ready"):
            errors.append("M6 may not mark Completion Gate ready")
        return errors

    def _fact_ids_for_chapter(self, chapter: int) -> list[str]:
        result = []
        for fact in self.facts.values():
            scope = fact["chapter_scope"]
            if isinstance(scope, int) and scope == chapter:
                result.append(fact["id"])
            elif isinstance(scope, str) and "-" in scope:
                left, right = scope.split("-", 1)
                if left.isdigit() and right.isdigit() and int(left) <= chapter <= int(right):
                    result.append(fact["id"])
        return result


def _collect_doc_refs(item: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(item, dict):
        for key, value in item.items():
            if key in {"source_ref", "document_ref"} and isinstance(value, str) and value.startswith("doc:"):
                refs.append(value)
            elif isinstance(value, (dict, list)):
                refs.extend(_collect_doc_refs(value))
    elif isinstance(item, list):
        for value in item:
            refs.extend(_collect_doc_refs(value))
    return list(dict.fromkeys(refs))


def format_implementation_alignment(kind: str, payload: Any) -> str:
    if kind == "summary":
        c = payload["completion"]
        return "\n".join([
            "IMPLEMENTATION ALIGNMENT M6",
            f"status: {payload['status']}",
            f"stable_release: {payload['stable_release']}",
            f"stable_sha256: {payload['stable_sha256']}",
            f"chapters: {payload['chapters']}/20",
            f"chapter_plans: {payload['chapter_plans']}/20",
            f"implementation_facts: {payload['implementation_facts']}",
            f"chapter_protections: {payload['chapter_protections']}/20",
            f"literature_frozen: {str(c['literature_frozen']).lower()}",
            f"P0 full coverage: {str(c['p0_full_coverage']).lower()}",
            f"Completion Gate ready: {str(c['completion_gate_ready']).lower()}",
        ])
    if kind == "chapter":
        body = payload["stable_body"]
        plan = payload["plan"]
        lock = payload["protection"]
        return "\n".join([
            f"M6 CHAPTER {payload['chapter']} | {body['title']}",
            f"stable_lines: {body['line_start']}-{body['line_end']}",
            f"stable_chapter_sha256: {body['sha256']}",
            f"plan: {plan['plan_class']} / {plan['edit_level']}",
            f"title_source: {plan['title_source']}",
            f"protection: {lock['level']}",
            f"facts: {len(payload['implementation_facts'])}",
            f"specialized_plocks: {', '.join(payload['specialized_plocks']) or 'none'}",
        ])
    if kind == "stable":
        return "\n".join([
            f"STABLE RELEASE {payload['release_id']}",
            f"file: {payload['file_ref']}",
            f"sha256: {payload['sha256']}",
            f"lines: {payload['line_count']}",
            f"chapters: {payload['chapter_count']}",
            f"mutable_during_full_migration: {str(payload['mutable_during_full_migration']).lower()}",
        ])
    return str(payload)
