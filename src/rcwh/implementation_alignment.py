from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
import hashlib
from .contracts import unique_index, project_chapters, coverage_errors
from .competition import CompetitionRegistry
from .workflow import ProjectState


@dataclass
class ImplementationAlignmentRuntime:
    chapter_scope: tuple[int, ...]
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
            chapter_scope=project_chapters(root),
            data=data,
            chapters=unique_index(data.get('stable_release', {}).get('chapters', []), 'chapter'),
            plans=unique_index(data.get('chapter_plans', []), 'chapter'),
            facts=unique_index(data.get('implementation_facts', []), 'id'),
            protections=unique_index(data.get('chapter_protections', []), 'chapter'),
            competitions=unique_index([x for x in CompetitionRegistry.from_repo(root).records.values() if x["mode"] == "PRODUCTION_43_0"], "chapter"),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "stable_release": self.data.get("stable_release", {}).get("release_id"),
            "stable_sha256": self.data.get("stable_release", {}).get("sha256"),
            "chapters": len(self.chapters),
            "chapter_plans": len(self.plans),
            "implementation_facts": len(self.facts),
            "chapter_protections": len(self.protections),
            "cross_chapter_protections": len(self.data.get("cross_chapter_protections", [])),
            "competitions": len(self.competitions),
        }

    def stable(self) -> dict[str, Any]:
        return {**self.data["stable_release"], "chapter_count": len(self.chapters)}

    def alignment(self, chapter: int) -> dict[str, Any]:
        body = self.chapters[chapter]
        location = self.data["object_query_locations"].get(str(chapter))
        return {
            "chapter": chapter,
            "stable_body": {key: body[key] for key in ("line_start", "line_end", "sha256", "title")},
            "plan_ref": f"plan:{chapter}", "protection_ref": f"protection:{chapter}",
            "reconstruction_query": f"rcwh reconstruction chapter {chapter}",
            "world_query": f"rcwh world chapter {chapter}",
            "literary_ecology_query": f"rcwh literary-ecology chapter {chapter}",
            "object_query": f"rcwh object location {location} {chapter}" if location else None,
            "specialized_plock_refs": [x["id"] for x in self.data["specialized_plocks"] if x["chapter"] == chapter],
            "implementation_fact_ids": self._fact_ids_for_chapter(chapter),
        }

    def chapter(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.chapters:
            raise KeyError(f"Chapter outside configured implementation scope: {chapter}")
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
            "alignment": self.alignment(chapter),
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
            raise KeyError(f"No production competition for chapter {chapter}")
        return self.competitions[chapter]

    def trace(self, kind: str, key: str, catalog: Any) -> dict[str, Any]:
        if kind == "source":
            ref = key
            if ref not in catalog.assets:
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

        refs = _collect_asset_refs(node)
        if kind == "source":
            refs = [node["source_ref"]]
        resolved = []
        for ref in refs:
            doc = catalog.assets.get(ref)
            if doc is None:
                resolved.append({"ref": ref, "kind": "missing_asset"})
                continue
            resolved.append({"ref": ref, "kind": "asset", **catalog.resolve(ref).summary()})
        return {
            "kind": kind,
            "key": key,
            "node": node,
            "resolved_sources": resolved,
            "trace_complete": bool(resolved) and all(x["kind"] == "asset" for x in resolved),
        }

    def validate_integrity(
        self,
        root: Path,
        catalog: Any,
        reconstruction: Any,
        world: Any,
        object_network: Any,
        literary_ecology: Any,
        plocks: Any,
        competitions: Any,
    ) -> list[str]:
        errors: list[str] = []

        for label, view in [("stable locators", self.chapters), ("plans", self.plans), ("protections", self.protections)]:
            errors.extend(coverage_errors(view, self.chapter_scope, "alignment " + label))
        if not self.facts:
            errors.append("implementation facts must be nonempty")

        stable = self.data.get("stable_release", {})
        release = ProjectState.from_repo(root).release(catalog)
        errors.extend(release.validate_storage())
        if stable.get("release_id") != release.data["id"] or stable.get("sha256") != release.data["text_sha256"]:
            errors.append("implementation alignment differs from selected release")
        stable_ref = stable.get("asset_ref")
        stable_doc = catalog.assets.get(stable_ref)
        if stable_doc is None:
            errors.append(f"M6 stable body document missing from catalog: {stable_ref}")
        elif stable_doc.get("sha256") != stable.get("sha256"):
            errors.append("M6 stable body SHA does not match DocumentRegistry")
        if stable_doc and catalog.resolve(stable_ref).id != catalog.resolve(release.data["text_asset_ref"]).id:
            errors.append("implementation alignment text asset differs from selected release")

        sources = self.data.get("sources", {})
        for name, source in sources.items():
            doc = catalog.assets.get(source["asset_ref"])
            if doc is None:
                errors.append(f"M6 source {name}: unregistered document")
            elif doc["sha256"] != source["sha256"]:
                errors.append(f"M6 source {name}: SHA256 mismatch")

        # Stable chapter locators must be contiguous and cover the exact frozen body.
        ordered = [self.chapters[ch] for ch in self.chapter_scope if ch in self.chapters]
        body_lines = catalog.resolve(stable_ref).path.read_bytes().decode("utf-8").splitlines(keepends=True) if stable_doc else []
        if len(body_lines) != stable.get("line_count"):
            errors.append("stable body line count disagrees with actual asset bytes")
        expected_line = 1
        for item in ordered:
            if item["line_start"] != expected_line:
                errors.append(
                    f"chapter {item['chapter']}: stable locator gap/overlap, "
                    f"expected line {expected_line}, got {item['line_start']}"
                )
            if item["line_end"] < item["line_start"]:
                errors.append(f"chapter {item['chapter']}: invalid stable line range")
            fragment = "".join(body_lines[item["line_start"] - 1:item["line_end"]])
            if hashlib.sha256(fragment.encode("utf-8")).hexdigest() != item["sha256"]:
                errors.append(f"chapter {item['chapter']}: locator hash disagrees with actual stable bytes")
            expected_line = item["line_end"] + 1
        if expected_line - 1 != stable.get("line_count"):
            errors.append("M6 stable chapter locators do not cover the frozen body line count")

        # Every aligned chapter must exist in the downstream runtimes.
        for ch in self.chapter_scope:
            if ch not in reconstruction.chapters:
                errors.append(f"chapter {ch}: missing Reconstruction node")
            if ch not in world.presence:
                errors.append(f"chapter {ch}: missing World chapter")
            if ch not in literary_ecology.post80_text:
                errors.append(f"chapter {ch}: missing Literary Ecology chapter")
            if ch not in self.plans or ch not in self.protections:
                continue
            if self.plans[ch]["source_ref"] != self.data["sources"]["chapter_plan"]["asset_ref"]:
                errors.append(f"chapter {ch}: plan source drift")
            if self.protections[ch]["source_ref"] != self.data["sources"]["protection_table"]["asset_ref"]:
                errors.append(f"chapter {ch}: protection source drift")

        # Cover registered active protections in scope; the set can grow with the project.
        expected_specialized = {identity for identity, lock in plocks.locks.items()
                                if lock["state"] == "P_LOCKED" and lock["chapter"] in self.chapter_scope}
        declared_specialized = unique_index(self.data.get("specialized_plocks", []))
        errors.extend(coverage_errors(declared_specialized, expected_specialized, "specialized P-Lock coverage"))
        for lock_id, binding in declared_specialized.items():
            lock = plocks.locks.get(lock_id)
            if lock is None:
                errors.append(f"M6 specialized P-Lock missing: {lock_id}")
                continue
            if binding["chapter"] != lock["chapter"] or binding["chapter"] not in self.chapter_scope:
                errors.append(f"{lock_id}: specialized P-Lock chapter binding drift")
            if lock["active_prose_locator"]["file_sha256"] != stable["sha256"]:
                errors.append(f"{lock_id}: specialized P-Lock locator not on selected stable body")

        for chapter, location in self.data["object_query_locations"].items():
            if int(chapter) not in self.chapter_scope or location not in world.locations:
                errors.append(f"chapter {chapter}: unknown object-query chapter or location {location}")

        # Competition transitions are checked against actual review records by their owner.
        errors.extend(coverage_errors(self.competitions, [r["chapter"] for r in competitions.records.values() if r["mode"] == "PRODUCTION_43_0"], "competition references"))

        # The object runtime should remain usable while M6 does not try to duplicate it.
        continuity = object_network.continuity_report()
        if continuity["status"] != "PASS":
            errors.append("M6 requires Object continuity PASS")

        forbidden_identity_prefixes = ("A-", "B-", "EVIDENCE_")
        for fact in self.facts.values():
            if fact.get("source_ref") != "asset:sha256:b90e41f44edbf0f3f86bd34365d842ccb121baa6ff1d8c9d047a38d86d67a95d":
                errors.append(f"{fact['id']}: implementation fact source drift")
            if any(str(fact.get("identity", "")).startswith(x) for x in forbidden_identity_prefixes):
                errors.append(f"{fact['id']}: implementation identity illegally resembles Evidence authority")

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


def _collect_asset_refs(item: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(item, dict):
        for key, value in item.items():
            if key in {"source_ref", "asset_ref"} and isinstance(value, str) and value.startswith("asset:"):
                refs.append(value)
            elif isinstance(value, (dict, list)):
                refs.extend(_collect_asset_refs(value))
    elif isinstance(item, list):
        for value in item:
            refs.extend(_collect_asset_refs(value))
    return list(dict.fromkeys(refs))


def format_implementation_alignment(kind: str, payload: Any) -> str:
    if kind == "summary":
        return "\n".join([
            "IMPLEMENTATION ALIGNMENT M6",
            f"stable_release: {payload['stable_release']}",
            f"stable_sha256: {payload['stable_sha256']}",
            f"chapters: {payload['chapters']}",
            f"chapter_plans: {payload['chapter_plans']}",
            f"implementation_facts: {payload['implementation_facts']}",
            f"chapter_protections: {payload['chapter_protections']}",
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
            f"mutable: {str(payload['mutable']).lower()}",
        ])
    return str(payload)
