from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .io import load_data


@dataclass
class ReconstructionRegistry:
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
            data=data,
            chapters={x["chapter"]: x for x in data.get("chapters", [])},
            r_nodes={x["id"]: x for x in data.get("r_nodes", [])},
            p_edges={x["id"]: x for x in data.get("p_edges", [])},
            timeline={x["chapter"]: x for x in data.get("timeline", [])},
            states={x["chapter"]: x for x in data.get("current_states_84_96", [])},
            legacy_open={x["id"]: x for x in data.get("legacy_open_mapping", [])},
            cross_locks={x["id"]: x for x in data.get("cross_chapter_locks", [])},
        )

    def validate_integrity(self, migration_registry: Any, open_interfaces: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("milestone") != "M2":
            errors.append("Reconstruction registry milestone must be M2")

        expected_chapters = set(range(81, 101))
        if set(self.chapters) != expected_chapters:
            errors.append(
                f"Reconstruction chapters must be 81..100 exactly; missing={sorted(expected_chapters-set(self.chapters))} "
                f"extra={sorted(set(self.chapters)-expected_chapters)}"
            )
        expected_r = {f"R{i:02d}" for i in range(1, 44)}
        if set(self.r_nodes) != expected_r:
            errors.append("R graph must contain R01..R43 exactly")
        expected_p = {f"P{i:02d}" for i in range(1, 12)}
        if set(self.p_edges) != expected_p:
            errors.append("P graph must contain P01..P11 exactly")
        if set(self.timeline) != expected_chapters:
            errors.append("M2 timeline must contain chapters 81..100 exactly")
        if set(self.states) != set(range(84, 97)):
            errors.append("M2 current state chain must contain chapters 84..96 exactly")
        if len(self.data.get("central_state_chain", [])) != 13:
            errors.append("M2 central state chain must contain 84..96 exactly")
        if len(self.data.get("economic_stages", [])) != 6:
            errors.append("M2 economic stages must contain E0..E5")
        if set(self.legacy_open) != {f"O{i:02d}" for i in range(1, 11)}:
            errors.append("Legacy mapping must contain O01..O10 exactly")
        if set(self.cross_locks) != {f"XLOCK-{i:02d}" for i in range(1, 17)}:
            errors.append("Cross-chapter locks must contain XLOCK-01..XLOCK-16 exactly")

        pressure = {c for c, item in self.chapters.items() if item.get("pressure_test")}
        if pressure != {86, 89, 92, 97}:
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
            doc_ref = source.get("document_ref")
            doc = migration_registry.documents.get(doc_ref)
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
            refs = set(re.findall(r"R\d{2}", edge.get("basis", "")))
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
        if self.data.get("jade_logistics", {}).get("current_model") != "U3P_PARTIAL_CONVERGENCE":
            errors.append("Current jade model must remain U3P partial convergence")
        if self.data.get("jade_logistics", {}).get("old_u1_status") != "DOWNGRADED":
            errors.append("Old jade U1 model must remain downgraded")
        if self.data.get("prison_case", {}).get("model_id") != "J1":
            errors.append("Current prison model must remain J1 家案牵连待质")
        forbidden = set(self.data.get("prison_case", {}).get("forbidden", []))
        for phrase in ("男丁自动连坐", "权贵救出", "劫狱"):
            if phrase not in forbidden:
                errors.append(f"Prison model lost hard prohibition: {phrase}")

        if self.timeline.get(91, {}).get("time_window") != "家败后的第一冬":
            errors.append("Chapter 91 must remain the first post-collapse winter")
        if self.timeline.get(95, {}).get("time_window") != "家败后的第二冬":
            errors.append("Chapter 95 must remain the second post-collapse winter")
        if self.data.get("completion", {}).get("current_markdown_islands") != 0:
            errors.append("M2 must eliminate the CURRENT Markdown-only island")
        if self.data.get("completion", {}).get("completion_gate_ready"):
            errors.append("M2 may not mark the overall Completion Gate ready")
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
            "milestone": self.data["milestone"],
            "status": self.data["status"],
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
            "completion": self.data["completion"],
        }


def format_reconstruction(kind: str, payload: dict[str, Any]) -> str:
    if kind == "summary":
        c = payload["completion"]
        return "\n".join([
            "RECONSTRUCTION M2",
            f"status: {payload['status']}",
            f"chapters: {payload['chapters']}/20",
            f"R/P: {payload['r_nodes']}/{payload['p_edges']}",
            f"timeline: {payload['timeline_chapters']}/20",
            f"states: {payload['state_chapters']} chapters",
            f"legacy O mapping: {payload['legacy_open_mappings']}/10",
            f"cross locks: {payload['cross_chapter_locks']}/16",
            f"jade: {payload['jade_model']}",
            f"prison: {payload['prison_model']}",
            f"CURRENT markdown islands: {c['current_markdown_islands']}",
            f"Completion Gate ready: {str(c['completion_gate_ready']).lower()}",
        ])
    return "\n".join(f"{k}: {v}" for k, v in payload.items())
