from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .contracts import project_chapters


@dataclass
class ObjectNetworkRuntime:
    chapter_scope: tuple[int, ...]
    data: dict[str, Any]
    objects: dict[str, dict[str, Any]]
    transitions: list[dict[str, Any]]
    by_object: dict[str, list[dict[str, Any]]]
    identity_edges: list[dict[str, Any]]
    containment_edges: list[dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ObjectNetworkRuntime":
        data = load_data(root / "data" / "objects" / "m4.json") or {}
        chapter_scope = project_chapters(root)
        baseline = data.get("baseline_chapter")
        if type(baseline) is not int or not 0 <= baseline < chapter_scope[0]:
            raise ValueError("object baseline_chapter must be a nonnegative integer before the project scope")
        objects = {x["id"]: x for x in data.get("objects", [])}
        transitions = sorted(
            data.get("transitions", []),
            key=lambda x: (x["chapter"], x["sequence"], x["id"]),
        )
        by_object: dict[str, list[dict[str, Any]]] = {key: [] for key in objects}
        for transition in transitions:
            by_object.setdefault(transition["object_id"], []).append(transition)
        return cls(
            chapter_scope=chapter_scope,
            data=data,
            objects=objects,
            transitions=transitions,
            by_object=by_object,
            identity_edges=data.get("identity_edges", []),
            containment_edges=data.get("containment_edges", []),
        )

    def _query_chapter(self, chapter: int | None) -> int:
        chapter = self.chapter_scope[-1] if chapter is None else chapter
        if chapter != self.data["baseline_chapter"] and chapter not in self.chapter_scope:
            raise KeyError(f"Chapter outside configured object scope: {chapter}")
        return chapter

    def snapshot(self, object_id: str, chapter: int | None = None) -> dict[str, Any]:
        if object_id not in self.objects:
            raise KeyError(f"Unknown object: {object_id}")
        chapter = self._query_chapter(chapter)
        state = deepcopy(self.objects[object_id]["baseline"])
        applied: list[str] = []
        for transition in self.by_object.get(object_id, []):
            if transition["chapter"] > chapter:
                break
            self._assert_from_matches(state, transition)
            state = deepcopy(transition["to"])
            applied.append(transition["id"])
        return {
            "object": deepcopy(self.objects[object_id]),
            "chapter": chapter,
            "state": state,
            "applied_transitions": applied,
        }

    def history(self, object_id: str) -> dict[str, Any]:
        if object_id not in self.objects:
            raise KeyError(f"Unknown object: {object_id}")
        return {
            "object": deepcopy(self.objects[object_id]),
            "transitions": deepcopy(self.by_object.get(object_id, [])),
            "identity_edges": [
                deepcopy(edge)
                for edge in self.identity_edges
                if object_id in {edge.get("from"), edge.get("to")}
            ],
            "containment_edges": [
                deepcopy(edge)
                for edge in self.containment_edges
                if object_id in {edge.get("container"), edge.get("contained")}
            ],
        }

    def jade(self, chapter: int | None = None) -> dict[str, Any]:
        chapter = self._query_chapter(chapter)
        ids = ["OBJ-TONGLING-JADE", "OBJ-SNOW-JADE-91"]
        return {
            "chapter": chapter,
            "objects": [self.snapshot(object_id, chapter) for object_id in ids],
            "identity_edges": deepcopy(self.identity_edges),
            "boundary": "The chapter-91 snow jade remains a distinct OPEN identity node and is never auto-merged with the Tongling jade.",
        }

    def at_location(self, location: str, chapter: int) -> dict[str, Any]:
        chapter = self._query_chapter(chapter)
        matches = []
        for object_id in self.objects:
            snap = self.snapshot(object_id, chapter)
            if snap["state"].get("location") == location:
                matches.append(snap)
        return {"location": location, "chapter": chapter, "objects": matches}

    def trace(self, object_id: str, catalog: Any, reconstruction: Any) -> dict[str, Any]:
        if object_id not in self.objects:
            raise KeyError(f"Unknown object: {object_id}")
        refs: list[str] = []
        for ref in self.objects[object_id].get("source_refs", []):
            if ref not in refs:
                refs.append(ref)
        for transition in self.by_object.get(object_id, []):
            for ref in transition.get("source_refs", []):
                if ref not in refs:
                    refs.append(ref)
        for edge in self.identity_edges:
            if object_id in {edge.get("from"), edge.get("to")}:
                for ref in edge.get("source_refs", []):
                    if ref not in refs:
                        refs.append(ref)
        for edge in self.containment_edges:
            if object_id in {edge.get("container"), edge.get("contained")}:
                for ref in edge.get("source_refs", []):
                    if ref not in refs:
                        refs.append(ref)

        r_index = {x["id"]: x for x in reconstruction.data.get("r_nodes", [])}
        resolved = []
        for ref in refs:
            if ref.startswith("asset:"):
                resolved.append({"ref": ref, "kind": "asset", **catalog.resolve(ref).summary()})
            elif ref.startswith("R"):
                node = r_index[ref]
                resolved.append({
                    "ref": ref,
                    "kind": "reconstruction_evidence",
                    "node": node["node"],
                    "internal_evidence": node["internal_evidence"],
                    "boundary": node["boundary"],
                    "source_ref": node["source_ref"],
                    "source_line": node.get("source_line"),
                })
        return {
            "object_id": object_id,
            "object": deepcopy(self.objects[object_id]),
            "resolved_sources": resolved,
            "transition_ids": [x["id"] for x in self.by_object.get(object_id, [])],
            "trace_complete": len(resolved) == len(refs),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "objects": len(self.objects),
            "transitions": len(self.transitions),
            "identity_edges": len(self.identity_edges),
            "containment_edges": len(self.containment_edges),
        }

    def continuity_report(self) -> dict[str, Any]:
        findings = self._continuity_findings()
        return {
            "status": "PASS" if not findings else "FAIL",
            "findings": findings,
            "objects_checked": len(self.objects),
            "transitions_checked": len(self.transitions),
        }

    def validate_integrity(
        self,
        root: Path,
        catalog: Any,
        reconstruction: Any,
    ) -> list[str]:
        errors: list[str] = []

        ids = [x["id"] for x in self.data.get("objects", [])]
        if len(ids) != len(set(ids)):
            errors.append("Object ids must be unique")
        transition_ids = [x["id"] for x in self.transitions]
        if len(transition_ids) != len(set(transition_ids)):
            errors.append("Object transition ids must be unique")

        r_ids = {x["id"] for x in reconstruction.data.get("r_nodes", [])}
        for object_item in self.objects.values():
            for ref in object_item.get("source_refs", []):
                errors.extend(self._validate_source_ref(ref, catalog, r_ids))
            legacy_ref = object_item.get("legacy_ref")
            if legacy_ref and not (root / legacy_ref).exists():
                errors.append(f"{object_item['id']}: missing legacy object ref {legacy_ref}")

        for transition in self.transitions:
            if transition["object_id"] not in self.objects:
                errors.append(f"{transition['id']}: unknown object {transition['object_id']}")
                continue
            if transition["chapter"] not in self.chapter_scope:
                errors.append(f"{transition['id']}: chapter {transition['chapter']} outside configured object scope")
            for ref in transition.get("source_refs", []):
                errors.extend(self._validate_source_ref(ref, catalog, r_ids))

        for edge in self.identity_edges:
            if edge.get("from") not in self.objects or edge.get("to") not in self.objects:
                errors.append(f"{edge.get('id')}: identity edge endpoint missing")
            for ref in edge.get("source_refs", []):
                errors.extend(self._validate_source_ref(ref, catalog, r_ids))

        for edge in self.containment_edges:
            if edge.get("container") not in self.objects:
                errors.append(f"{edge.get('id')}: containment container missing")
            contained = edge.get("contained")
            if contained and contained not in self.objects:
                errors.append(f"{edge.get('id')}: containment object missing")
            for ref in edge.get("source_refs", []):
                errors.extend(self._validate_source_ref(ref, catalog, r_ids))

        errors.extend(self._continuity_findings())

        snow_edges = [
            edge for edge in self.identity_edges
            if {edge.get("from"), edge.get("to")}
            == {"OBJ-SNOW-JADE-91", "OBJ-TONGLING-JADE"}
        ]
        if len(snow_edges) != 1:
            errors.append("M4 must have exactly one explicit snow-jade/Tongling identity edge")
        elif snow_edges[0].get("status") != "OPEN_LOCKED_NONMERGE":
            errors.append("Chapter-91 snow-jade identity edge must remain OPEN_LOCKED_NONMERGE")

        # These are protected checkpoints of the current model, not query limits.
        try:
            snow = self.snapshot("OBJ-SNOW-JADE-91", 100)
            terminal = self.snapshot("OBJ-TONGLING-JADE", 100)["state"]
            rice = self.snapshot("OBJ-RICE-JAR-95", 96)["state"]
        except (KeyError, ValueError) as exc:
            errors.append(f"protected object checkpoint unavailable: {exc}")
            return errors
        if snow["object"]["identity_status"] != "OPEN_MAY_OR_MAY_NOT_BE_TONGLING":
            errors.append("Chapter-91 snow jade identity must remain OPEN")
        if terminal.get("frame_status") != "RETURNED_TO_ESSENCE_QINGGENG_FRAME":
            errors.append("Tongling jade must reach the hard terminal outer-frame state by chapter 100")
        if terminal.get("location") != "UNKNOWN":
            errors.append("Tongling jade earthly physical route must remain unresolved at chapter 100")
        if rice.get("quantity_state") != "MEASURED_USE_HALF_AID":
            errors.append("Chapter-96 rice aid must remain measured/partial rather than restorative")
        return errors

    def _continuity_findings(self) -> list[str]:
        findings: list[str] = []
        for object_id, item in self.objects.items():
            state = deepcopy(item["baseline"])
            for transition in self.by_object.get(object_id, []):
                try:
                    self._assert_from_matches(state, transition)
                except ValueError as exc:
                    findings.append(str(exc))
                    state = deepcopy(transition["to"])
                    continue
                old_location = state.get("location")
                new_location = transition["to"].get("location")
                if old_location != new_location:
                    mode = transition.get("movement", "NONE")
                    if mode not in {"EXPLICIT", "OPEN_BOUNDARY", "DISCOVERY_FROM_UNKNOWN"}:
                        findings.append(
                            f"{transition['id']}: location changed {old_location!r}->{new_location!r} without explicit movement mode"
                        )
                state = deepcopy(transition["to"])
        return findings

    @staticmethod
    def _assert_from_matches(state: dict[str, Any], transition: dict[str, Any]) -> None:
        expected = transition.get("from", {})
        for key, value in expected.items():
            if state.get(key) != value:
                raise ValueError(
                    f"{transition['id']}: continuity mismatch for {transition['object_id']} field {key}: "
                    f"runtime={state.get(key)!r} expected={value!r}"
                )

    @staticmethod
    def _validate_source_ref(ref: str, catalog: Any, r_ids: set[str]) -> list[str]:
        if ref.startswith("asset:"):
            return [] if ref in catalog.assets else [f"unregistered object source document {ref}"]
        if ref.startswith("R"):
            return [] if ref in r_ids else [f"unknown Reconstruction evidence node {ref}"]
        return [f"unsupported object source ref {ref}"]


def format_object(kind: str, payload: dict[str, Any]) -> str:
    if kind == "summary":
        return "\n".join([
            "OBJECT NETWORK M4",
            f"objects: {payload['objects']}",
            f"transitions: {payload['transitions']}",
            f"identity_edges: {payload['identity_edges']}",
            f"containment_edges: {payload['containment_edges']}",
        ])
    if kind == "get":
        obj = payload["object"]
        state = payload["state"]
        return "\n".join([
            f"OBJECT {obj['id']} / {obj['name']} @ ch{payload['chapter']}",
            f"kind: {obj['kind']}",
            f"identity_status: {obj['identity_status']}",
            f"holder: {state.get('holder')}",
            f"location: {state.get('location')}",
            f"status: {state.get('status')}",
            f"frame_status: {state.get('frame_status')}",
            f"transitions: {len(payload['applied_transitions'])}",
        ])
    if kind == "continuity":
        return "\n".join([
            f"OBJECT CONTINUITY: {payload['status']}",
            f"objects_checked: {payload['objects_checked']}",
            f"transitions_checked: {payload['transitions_checked']}",
            *[f"- {x}" for x in payload["findings"]],
        ])
    return "\n".join(f"{key}: {value}" for key, value in payload.items())
