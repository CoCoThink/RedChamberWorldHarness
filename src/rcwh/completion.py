from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"


def _collect_doc_refs(item: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(item, dict):
        for value in item.values():
            refs |= _collect_doc_refs(value)
    elif isinstance(item, list):
        for value in item:
            refs |= _collect_doc_refs(value)
    elif isinstance(item, str) and item.startswith("doc:"):
        refs.add(item)
    return refs


@dataclass
class CompletionGateRuntime:
    root: Path
    state: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "CompletionGateRuntime":
        return cls(
            root=root,
            state=load_data(root / "data" / "project_state" / "m8.json") or {},
        )

    def _typed_doc_refs(self) -> set[str]:
        refs: set[str] = set()
        paths = [
            self.root / "data" / "reconstruction" / "m2.json",
            self.root / "data" / "objects" / "m4.json",
            self.root / "data" / "literary_ecology" / "m5.json",
            self.root / "data" / "implementation_alignment" / "m6.json",
        ]
        paths.extend(sorted((self.root / "data" / "world").glob("m3_*.json")))
        for path in paths:
            refs |= _collect_doc_refs(load_data(path) or {})
        return refs

    def traceability(self, registry: Any, coverage: Any, graph: Any) -> dict[str, Any]:
        registry_paths = [
            doc for doc in registry.documents.values()
            if doc.get("self_contained_path")
        ]
        typed_refs = self._typed_doc_refs()
        missing_refs = sorted(ref for ref in typed_refs if ref not in registry.documents)
        graph_errors = graph.validate_integrity()
        p0 = list(coverage.records.values())
        p0_bad_paths = [
            x["sha256"] for x in p0
            if not x.get("self_contained_path", "").startswith(
                ("01_PRIMARY_SOURCES/", "02_CURRENT_RUNTIME/", "03_VALID_HISTORY/")
            )
        ]
        return {
            "status": "PASS"
            if (
                len(registry_paths) == len(registry.documents)
                and not missing_refs
                and not graph_errors
                and len(p0) == 249
                and not p0_bad_paths
            )
            else "FAIL",
            "registry_documents_with_concrete_paths": len(registry_paths),
            "registry_documents_total": len(registry.documents),
            "typed_doc_refs": len(typed_refs),
            "missing_typed_doc_refs": missing_refs,
            "p0_concrete_paths": len(p0) - len(p0_bad_paths),
            "p0_total": len(p0),
            "p0_bad_paths": p0_bad_paths,
            "provenance_graph_errors": graph_errors,
            "graph_node_counts": {
                "sources": len(graph.sources),
                "claims": len(graph.claims),
                "decisions": len(graph.decisions),
                "implementations": len(graph.implementations),
                "title_axes": len(graph.title_axes),
            },
        }

    def evaluate(
        self,
        registry: Any,
        coverage: Any,
        reconstruction: Any,
        world: Any,
        objects: Any,
        literary: Any,
        implementation: Any,
        graph: Any,
        literals: Any,
        mechanisms: Any,
        opens: Any,
        plocks: Any,
        competitions: Any,
        promotions: Any,
        evidence_regression: dict[str, Any],
    ) -> dict[str, Any]:
        findings: list[str] = []
        checks: dict[str, bool] = {}

        def check(name: str, value: bool, finding: str) -> None:
            checks[name] = bool(value)
            if not value:
                findings.append(finding)

        cov = coverage.summary(registry)
        current = registry.current_summary()
        full_migration = coverage.regression(
            registry, reconstruction, world, objects, literary,
            implementation, evidence_regression
        )
        trace = self.traceability(registry, coverage, graph)

        check("M0_M7_PASS", all(
            self.state.get("milestone_status", {}).get(f"M{i}") == "PASS"
            for i in range(0, 8)
        ), "not all M0-M7 milestones are PASS")
        check("P0_249_FULL", cov["p0_total"] == 249 and cov["effective_coverage"] == {"FULL": 249} and cov["unresolved"] == 0,
              "P0 coverage is not 249/249 FULL")
        check("COVERAGE_SIGNOFF", self.state.get("coverage_signoff", {}).get("signed") is True,
              "M8 coverage signoff is missing")
        check("CURRENT_15_FULL", current.get("semantic_coverage_counts") == {"FULL": 15, "PARTIAL": 0, "MINIMAL": 0, "NONE": 0},
              "CURRENT runtime is not 15/15 FULL")
        check("CURRENT_MARKDOWN_ISLANDS_0", current.get("current_markdown_islands") == 0,
              "CURRENT Markdown-only islands remain")
        check("AUTHORITY_CONFLICTS_0", current.get("unresolved_authority_conflicts") == 0,
              "unresolved authority conflicts remain")
        check("EVIDENCE_CORE_REGRESSION", evidence_regression.get("overall") == "PASS",
              "R4 Evidence Core regression is not PASS")
        check("FULL_MIGRATION_REGRESSION", full_migration.get("overall") == "PASS",
              "M7 Full Migration regression is not PASS")
        check("RECONSTRUCTION_QUERY", reconstruction.summary().get("chapters") == 20,
              "Reconstruction chapter query surface incomplete")
        check("TIMELINE_QUERY", all(reconstruction.timeline_at(ch)["chapter"] == ch for ch in (81, 91, 95, 100)),
              "Timeline smoke query failed")
        check("WORLD_QUERY", world.summary().get("completion", {}).get("world_queryable") is True and len(world.presence) == 20,
              "World runtime is not queryable")
        try:
            character_ok = world.character_state("baoyu", 92)["chapter"] == 92
        except Exception:
            character_ok = False
        check("CHARACTER_QUERY", character_ok, "Character query smoke failed")
        check("OBJECT_QUERY", objects.continuity_report().get("status") == "PASS",
              "Object continuity/query gate failed")
        try:
            literary_ok = (
                literary.summary().get("completion", {}).get("literary_ecology_queryable") is True
                and literary.voice("daiyu")["id"] == "daiyu"
                and literary.chapter(92)["chapter"] == 92
            )
        except Exception:
            literary_ok = False
        check("LITERARY_ECOLOGY_QUERY", literary_ok, "Literary Ecology retrieval gate failed")
        check("IMPLEMENTATION_QUERY", implementation.summary().get("status") == "PASS" and len(implementation.chapters) == 20,
              "Implementation alignment gate failed")
        check("OPEN_28_OPEN_LOCKED", set(opens.interfaces) == {f"OL-{i:03d}" for i in range(1, 29)}
              and all(x.get("state") == "OPEN_LOCKED" for x in opens.interfaces.values()),
              "OPEN interface set/state drifted")
        check("H01_H06_FEASIBILITY_ONLY", set(mechanisms.mechanisms) == {f"H0{i}" for i in range(1, 7)}
              and all(x.get("effect") == "FEASIBILITY_ONLY" for x in mechanisms.mechanisms.values()),
              "historical mechanisms drifted or gained plot authority")
        check("PLOCK_LITERARY_ONLY", bool(plocks.locks)
              and all(x.get("state") == "P_LOCKED" and x.get("authority") == "LITERARY_PROTECTION_ONLY" for x in plocks.locks.values()),
              "P-Lock authority/state drifted")
        check("TRACEABILITY", trace["status"] == "PASS",
              "machine/source traceability gate failed")
        check("NEGATIVE_ARCHIVE_NON_RUNTIME", coverage.negative_archive.get("stable_active_effect") == "NONE"
              and all(registry.packages[x["id"]]["runtime_authority"] == "NO" for x in coverage.negative_archive.get("package_fixtures", [])),
              "negative archive regained runtime authority")
        check("STABLE_ACTIVE_UNCHANGED", current.get("stable_active_sha256") == STABLE_SHA
              and implementation.stable().get("sha256") == STABLE_SHA
              and evidence_regression.get("stable_active", {}).get("sha256") == STABLE_SHA,
              "stable ACTIVE SHA changed")
        gate_fixture_ok = (
            implementation.competitions[89]["state"] == "IN_REVIEW"
            and implementation.competitions[89]["progress"] == "PHASE1_ONLY"
            and implementation.competitions[92]["state"] == "BLOCKED_BY_PREDECESSOR"
            and implementation.competitions[97]["state"] == "BLOCKED_BY_PREDECESSOR"
        )
        check(
            "LITERARY_FREEZE_AT_GATE_SIGNOFF",
            gate_fixture_ok
            and self.state.get("literature", {}).get("migration_freeze_active") is True
            and self.state.get("literature", {}).get("resume_started") is False,
            "historical M8 gate-time literary freeze fixture drifted",
        )
        promo_ok = True
        for promotion_id in promotions.records:
            if promotions.evaluate(self.root, promotion_id).get("overall") != "PASS":
                promo_ok = False
        check("PROMOTION_REGRESSION", promo_ok, "promotion regression failed")

        overall = "PASS" if all(checks.values()) else "FAIL"
        return {
            "milestone": "M8",
            "overall": overall,
            "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
            "findings": findings,
            "coverage_signoff": "PASS" if self.state.get("coverage_signoff", {}).get("signed") else "FAIL",
            "stable_active_sha256": STABLE_SHA,
            "traceability": trace,
            "literature_resume_authorized": overall == "PASS",
            "literature_resume_started": False,
            "main_merge_state": self.state.get("migration_release", {}).get("main_merge_state"),
        }

    def validate_integrity(self, payload: dict[str, Any], registry: Any) -> list[str]:
        errors: list[str] = []
        status = self.state.get("status")
        if status not in {"PASS_CANDIDATE", "PASS"}:
            errors.append(f"M8 project state has invalid status: {status}")
        if payload.get("overall") != "PASS":
            errors.extend(f"M8 gate {k}: {v}" for k, v in payload.get("checks", {}).items() if v != "PASS")
        current = registry.current_summary()
        if status == "PASS":
            if self.state.get("completion_gate", {}).get("overall") != "PASS":
                errors.append("M8 PASS state must persist completion_gate.overall=PASS")
            if current.get("completion_gate_status") != "PASS":
                errors.append("M8 PASS state must publish completion_gate_status=PASS")
            if current.get("completion_gate_ready") is not True:
                errors.append("M8 PASS state must publish completion_gate_ready=true")
            if current.get("coverage_report_signed_off") is not True:
                errors.append("M8 PASS state must publish coverage_report_signed_off=true")
            if current.get("literature_resume_authorized") is not True:
                errors.append("M8 PASS state must authorize later literary resumption")
        return errors


def format_completion(kind: str, payload: Any) -> str:
    if kind == "gate":
        lines = [f"FULL MIGRATION COMPLETION GATE: {payload['overall']}"]
        lines.extend(f"- {k}: {v}" for k, v in payload["checks"].items())
        lines.extend([
            f"coverage_signoff: {payload['coverage_signoff']}",
            f"stable_active_sha256: {payload['stable_active_sha256']}",
            f"literature_resume_authorized: {str(payload['literature_resume_authorized']).lower()}",
            "literature_resume_started: false",
            f"main_merge_state: {payload['main_merge_state']}",
        ])
        return "\n".join(lines)
    if kind == "traceability":
        return "\n".join([
            f"TRACEABILITY: {payload['status']}",
            f"registry documents: {payload['registry_documents_with_concrete_paths']}/{payload['registry_documents_total']}",
            f"P0 concrete paths: {payload['p0_concrete_paths']}/{payload['p0_total']}",
            f"typed doc refs: {payload['typed_doc_refs']}",
            f"missing typed doc refs: {len(payload['missing_typed_doc_refs'])}",
            f"provenance graph errors: {len(payload['provenance_graph_errors'])}",
        ])
    if kind == "summary":
        return "\n".join([
            f"FULL MIGRATION M8: {payload['status']}",
            f"release: {payload['migration_release']['id']}",
            f"stable: {payload['migration_release']['stable_active_sha256']}",
            f"coverage signed: {str(payload['coverage_signoff']['signed']).lower()}",
            f"gate persisted: {payload['completion_gate']['overall']}",
            f"main merge: {payload['migration_release']['main_merge_state']}",
            f"literature resume started: {str(payload['literature']['resume_started']).lower()}",
        ])
    return str(payload)
