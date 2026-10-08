from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .io import load_data
from .contracts import unique_index, project_chapters, coverage_errors, validate_plan_constraints


@dataclass
class ReconstructionRegistry:
    chapter_scope: tuple[int, ...]
    data: dict[str, Any]
    chapters: dict[int, dict[str, Any]]
    r_nodes: dict[str, dict[str, Any]]
    p_edges: dict[str, dict[str, Any]]
    timeline: dict[int, dict[str, Any]]
    states: dict[int, dict[str, Any]]
    legacy_open: dict[str, dict[str, Any]]
    cross_locks: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ReconstructionRegistry":
        data = load_data(root / "data" / "reconstruction" / "m2.json") or {}
        return cls(
            chapter_scope=project_chapters(root),
            data=data,
            chapters=unique_index(data.get('chapters', []), 'chapter'),
            r_nodes=unique_index(data.get('r_nodes', []), 'id'),
            p_edges=unique_index(data.get('p_edges', []), 'id'),
            timeline=unique_index(data.get('timeline', []), 'chapter'),
            states=unique_index(data.get('current_states_84_96', []), 'chapter'),
            legacy_open=unique_index(data.get('legacy_open_mapping', []), 'id'),
            cross_locks=unique_index(data.get('cross_chapter_locks', []), 'id'),
        )

    def validate_integrity(self, catalog: Any, open_interfaces: Any) -> list[str]:
        errors: list[str] = []

        expected_chapters = set(self.chapter_scope)
        errors.extend(coverage_errors(self.chapters, expected_chapters, "reconstruction chapters"))
        errors.extend(coverage_errors(self.timeline, expected_chapters, "reconstruction timeline"))
        if not self.r_nodes or not self.p_edges:
            errors.append("reconstruction evidence graph and ordering edges must be nonempty")
        if not set(self.states) <= expected_chapters:
            errors.append("reconstruction state lies outside the declared chapter scope")
        chain = unique_index(self.data.get("central_state_chain", []), "chapter")
        errors.extend(coverage_errors(chain, self.states, "central state chain"))
        if not self.data.get("economic_stages"):
            errors.append("economic stages must be declared")

        from .workflow import ProjectState
        pressure = {c for c, item in self.chapters.items() if item.get("pressure_test")}
        if pressure != set(ProjectState.from_repo(catalog.root).owner("literary")["sequence"]):
            errors.append(f"pressure-test set drifted: {sorted(pressure)}")

        ch90 = self.chapters.get(90, {})
        if ch90.get("title") != "薛宝钗借词含讽谏　王熙凤知命强英雄":
            errors.append("Chapter 90 T0 wording drifted")
        if ch90.get("title_status") != "T0_WORDING_PLACEMENT_PC":
            errors.append("Chapter 90 must preserve T0 wording / PC placement distinction")

        ch100 = self.chapters.get(100, {})
        if ch100.get("title_status") != "TG_FINAL_LIST_FUNCTION_HARD_NAME_OPEN":
            errors.append("Chapter 100 working title must preserve formal-list-name OPEN boundary")

        for source_name, source in self.data.get("sources", {}).items():
            doc_ref = source.get("asset_ref")
            doc = catalog.assets.get(doc_ref)
            if doc is None:
                errors.append(f"M2 source {source_name}: unknown DocumentRegistry ref {doc_ref}")
                continue
            if doc.get("sha256") != source.get("sha256"):
                errors.append(f"M2 source {source_name}: SHA256 disagrees with DocumentRegistry")

        for node in self.r_nodes.values():
            if node.get("placement_epistemic") != "PROJECT_PLACEMENT_ONLY":
                errors.append(f"{node['id']}: current placement may not masquerade as source proof")
        for edge in self.p_edges.values():
            if edge.get("sequence_epistemic") != "PROJECT_IMPLEMENTATION_ONLY":
                errors.append(f"{edge['id']}: current sequence may not masquerade as source proof")
            refs = set(re.findall(r"R\d+", edge.get("basis", "")))
            unknown = refs - set(self.r_nodes)
            if unknown:
                errors.append(f"{edge['id']}: unknown R refs {sorted(unknown)}")

        available_open = set(open_interfaces.interfaces)
        for item in self.legacy_open.values():
            refs = set(item.get("current_open_refs", []))
            unknown = refs - available_open
            if unknown:
                errors.append(f"{item['id']}: unknown current OPEN refs {sorted(unknown)}")
        o03 = self.legacy_open.get("O03", {})
        if o03.get("mapping_relation") != "REVISED_OLD_U1_DOWNGRADED":
            errors.append("O03 must record the old two-loss U1 model as revised/downgraded")
        if self.data.get("jade_logistics", {}).get("old_u1_status") != "DOWNGRADED":
            errors.append("Old jade U1 model must remain downgraded")
        forbidden = set(self.data.get("prison_case", {}).get("forbidden", []))
        for phrase in ("男丁自动连坐", "权贵救出", "劫狱"):
            if phrase not in forbidden:
                errors.append(f"Prison model lost hard prohibition: {phrase}")

        errors.extend(validate_plan_constraints(catalog, "reconstruction", {**self.data, "timeline": self.timeline}))
        return errors

    def chapter(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.chapters:
            raise KeyError(f"Unknown chapter: {chapter}")
        return self.chapters[chapter]

    def r(self, node_id: str) -> dict[str, Any]:
        if node_id not in self.r_nodes:
            raise KeyError(f"Unknown R node: {node_id}")
        return self.r_nodes[node_id]

    def p(self, edge_id: str) -> dict[str, Any]:
        if edge_id not in self.p_edges:
            raise KeyError(f"Unknown P edge: {edge_id}")
        return self.p_edges[edge_id]

    def timeline_at(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.timeline:
            raise KeyError(f"Unknown timeline chapter: {chapter}")
        return self.timeline[chapter]

    def state_at(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.states:
            raise KeyError(f"No M2 state snapshot for chapter: {chapter}")
        return self.states[chapter]

    def legacy(self, old_id: str) -> dict[str, Any]:
        if old_id not in self.legacy_open:
            raise KeyError(f"Unknown legacy OPEN interface: {old_id}")
        return self.legacy_open[old_id]

    def cross(self, lock_id: str) -> dict[str, Any]:
        if lock_id not in self.cross_locks:
            raise KeyError(f"Unknown cross-chapter lock: {lock_id}")
        return self.cross_locks[lock_id]

    def summary(self) -> dict[str, Any]:
        return {
            "chapters": len(self.chapters),
            "r_nodes": len(self.r_nodes),
            "p_edges": len(self.p_edges),
            "timeline_chapters": len(self.timeline),
            "state_chapters": len(self.states),
            "economic_stages": len(self.data["economic_stages"]),
            "legacy_open_mappings": len(self.legacy_open),
            "cross_chapter_locks": len(self.cross_locks),
            "jade_model": self.data["jade_logistics"]["current_model"],
            "prison_model": self.data["prison_case"]["model_id"],
            "coverage_limitations": self.data["coverage_limitations"],
        }


def format_reconstruction(kind: str, payload: dict[str, Any]) -> str:
    if kind == "summary":
        return "\n".join([
            "RECONSTRUCTION M2",
            f"chapters: {payload['chapters']}",
            f"R/P: {payload['r_nodes']}/{payload['p_edges']}",
            f"timeline: {payload['timeline_chapters']}",
            f"states: {payload['state_chapters']} chapters",
            f"legacy O mapping: {payload['legacy_open_mappings']}",
            f"cross locks: {payload['cross_chapter_locks']}",
            f"jade: {payload['jade_model']}",
            f"prison: {payload['prison_model']}",
        ])
    return "\n".join(f"{k}: {v}" for k, v in payload.items())
