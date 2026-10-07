from __future__ import annotations

import base64
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any
import zlib

from .io import load_data


P0_INVENTORY_SHA256 = "77b70c7785235d976fe1f42665be5aef6668b983170259e019454c0b02238247"

EXPECTED_OLD_COVERAGE = {
    "FULL": 9,
    "PARTIAL": 105,
    "MINIMAL": 1,
    "NONE": 134,
}
EXPECTED_LAYERS = {
    "EVIDENCE": 29,
    "EVIDENCE_LITERARY": 7,
    "GOVERNANCE": 5,
    "IMPLEMENTATION": 12,
    "LITERARY_ECOLOGY": 60,
    "LITERARY_EVIDENCE": 21,
    "LOCK": 18,
    "MECHANISM": 3,
    "PLANNING": 13,
    "RECONSTRUCTION": 49,
    "SOURCE": 2,
    "WORLD": 22,
    "WORLD_LITERARY": 8,
}
EXPECTED_AUTHORITY = {"REFERENCE": 233, "CURRENT": 14, "SOURCE_AUTHORITY": 2}
EXPECTED_RUNTIME_AUTHORITY = {"REFERENCE": 233, "YES": 16}


def _binding_for(layer: str, node: str) -> dict[str, Any]:
    if node == "evidence.title_axis":
        return {
            "surface": "EVIDENCE_CORE",
            "artifacts": ["data/axes/title_axis.yaml", "data/axes/title_axis_w2.yaml"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "evidence.claim_role_matrix":
        return {
            "surface": "EVIDENCE_CORE",
            "artifacts": ["data/sources", "data/claims", "data/decisions"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "evidence.literal_target":
        return {
            "surface": "EVIDENCE_CORE",
            "artifacts": ["data/literals/r4_literal_core.yaml"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "governance.evidence_policy":
        return {
            "surface": "GOVERNANCE",
            "artifacts": ["src/rcwh/graph.py", "src/rcwh/validate.py"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "governance.project_state":
        return {
            "surface": "GOVERNANCE",
            "artifacts": ["data/project_state/m7.json"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "implementation.register" or node == "implementation.body":
        return {
            "surface": "IMPLEMENTATION",
            "artifacts": ["data/implementation_alignment/m6.json"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "lock.open_interface":
        return {
            "surface": "OPEN_LOCK",
            "artifacts": ["data/open_interfaces/r4_open.yaml"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "lock.literary_plock":
        return {
            "surface": "P_LOCK",
            "artifacts": [
                "data/plocks/r4_literary.yaml",
                "data/implementation_alignment/m6.json",
            ],
            "query": f"rcwh coverage target {node}",
        }
    if node == "mechanism.h01_h06":
        return {
            "surface": "HISTORICAL_MECHANISM",
            "artifacts": ["data/mechanisms/r4_historical.yaml"],
            "query": f"rcwh coverage target {node}",
        }
    if node == "source.raw_corpus":
        return {
            "surface": "SOURCE_AUTHORITY",
            "artifacts": [
                "data/coverage/p0_inventory.part1.b64",
                "data/coverage/p0_inventory.part2.b64",
                "data/coverage/p0_inventory.part3.b64",
                "data/coverage/p0_inventory.part4.b64",
            ],
            "query": f"rcwh coverage target {node}",
        }
    if layer in {"EVIDENCE_LITERARY", "LITERARY_ECOLOGY", "LITERARY_EVIDENCE", "PLANNING"}:
        return {
            "surface": "LITERARY_ECOLOGY",
            "artifacts": ["data/literary_ecology/m5.json"],
            "query": f"rcwh coverage target {node}",
        }
    if layer == "RECONSTRUCTION":
        artifacts = ["data/reconstruction/m2.json"]
        if node in {"reconstruction.chapter_plan", "reconstruction.scene_seed"}:
            artifacts.append("data/implementation_alignment/m6.json")
        return {
            "surface": "RECONSTRUCTION",
            "artifacts": artifacts,
            "query": f"rcwh coverage target {node}",
        }
    if layer == "WORLD":
        artifacts = [
            "data/world/m3_core.json",
            "data/world/m3_locations.json",
            "data/world/m3_presence.json",
            "data/world/m3_resources.json",
        ]
        if node == "world.object_flow.jade":
            artifacts.append("data/objects/m4.json")
        return {
            "surface": "WORLD",
            "artifacts": artifacts,
            "query": f"rcwh coverage target {node}",
        }
    if layer == "WORLD_LITERARY":
        return {
            "surface": "WORLD_LITERARY",
            "artifacts": [
                "data/world/m3_body.json",
                "data/literary_ecology/m5.json",
                "data/objects/m4.json",
            ],
            "query": f"rcwh coverage target {node}",
        }
    raise KeyError(f"No M7 semantic binding for {layer}/{node}")


@dataclass
class CoverageAuditRuntime:
    root: Path
    records: dict[str, dict[str, Any]]
    project_state: dict[str, Any]
    negative_archive: dict[str, Any]
    inventory_sha256: str

    @classmethod
    def from_repo(cls, root: Path) -> "CoverageAuditRuntime":
        encoded = "".join(
            (root / "data" / "coverage" / f"p0_inventory.part{i}.b64")
            .read_text(encoding="utf-8")
            .strip()
            for i in range(1, 5)
        )
        raw = zlib.decompress(base64.b64decode(encoded))
        payload = json.loads(raw.decode("utf-8"))
        records: dict[str, dict[str, Any]] = {}
        for row in payload:
            sha, layer, node, old_coverage, authority, runtime_authority, path = row
            binding = _binding_for(layer, node)
            if authority == "CURRENT":
                mode = "DIRECT_CURRENT_RUNTIME"
            elif authority == "SOURCE_AUTHORITY":
                mode = "RAW_SOURCE_AUTHORITY"
            elif old_coverage == "FULL":
                mode = "DIRECT_PREEXISTING_RUNTIME"
            else:
                mode = "VERSIONED_REFERENCE_BOUND_TO_EFFECTIVE_RUNTIME"
            records[sha] = {
                "sha256": sha,
                "target_layer": layer,
                "target_node": node,
                "pre_migration_coverage": old_coverage,
                "authority": authority,
                "runtime_authority": runtime_authority,
                "self_contained_path": path,
                "coverage_mode": mode,
                "effective_coverage": "FULL",
                "binding": binding,
            }
        return cls(
            root=root,
            records=records,
            project_state=load_data(root / "data" / "project_state" / "m7.json") or {},
            negative_archive=load_data(root / "data" / "coverage" / "negative_archive.json") or {},
            inventory_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def summary(self, registry: Any | None = None) -> dict[str, Any]:
        layer_counts = Counter(x["target_layer"] for x in self.records.values())
        old = Counter(x["pre_migration_coverage"] for x in self.records.values())
        final = Counter(x["effective_coverage"] for x in self.records.values())
        authority = Counter(x["authority"] for x in self.records.values())
        registered = 0
        if registry is not None:
            shas = {x["sha256"] for x in registry.documents.values()}
            registered = sum(1 for x in self.records.values() if x["sha256"] in shas)
        return {
            "milestone": "M7",
            "status": self.project_state.get("status"),
            "p0_total": len(self.records),
            "pre_migration_coverage": dict(old),
            "effective_coverage": dict(final),
            "layers": dict(layer_counts),
            "authority": dict(authority),
            "document_registry_matches": registered if registry is not None else None,
            "concrete_source_paths": sum(bool(x["self_contained_path"]) for x in self.records.values()),
            "unresolved": len(self.gaps()),
            "current_markdown_islands": self.project_state.get("current_authority", {}).get("markdown_islands"),
            "unresolved_authority_conflicts": self.project_state.get("current_authority", {}).get("unresolved_authority_conflicts"),
            "coverage_report_signed_off": self.project_state.get("p0_coverage", {}).get("signed_off"),
            "completion_gate_ready": self.project_state.get("completion_gate_ready"),
        }

    def document(self, key: str, registry: Any | None = None) -> dict[str, Any]:
        if key in self.records:
            record = dict(self.records[key])
        else:
            matches = [
                x for x in self.records.values()
                if key in {x["self_contained_path"], x["target_node"]}
            ]
            if len(matches) != 1:
                raise KeyError(f"Coverage document key must resolve uniquely: {key}")
            record = dict(matches[0])
        if registry is not None:
            reg = next(
                (x for x in registry.documents.values() if x["sha256"] == record["sha256"]),
                None,
            )
            record["document_registry_ref"] = reg["id"] if reg else None
        return record

    def target(self, target_node: str) -> dict[str, Any]:
        items = [x for x in self.records.values() if x["target_node"] == target_node]
        if not items:
            raise KeyError(f"Unknown P0 target node: {target_node}")
        binding = items[0]["binding"]
        return {
            "target_node": target_node,
            "surface": binding["surface"],
            "artifacts": binding["artifacts"],
            "query": binding["query"],
            "documents": len(items),
            "effective_coverage": "FULL"
            if all(x["effective_coverage"] == "FULL" for x in items)
            else "INCOMPLETE",
            "source_sha256": [x["sha256"] for x in items],
        }

    def layer(self, layer: str) -> dict[str, Any]:
        items = [x for x in self.records.values() if x["target_layer"] == layer]
        if not items:
            raise KeyError(f"Unknown P0 layer: {layer}")
        nodes = sorted({x["target_node"] for x in items})
        return {
            "layer": layer,
            "documents": len(items),
            "targets": nodes,
            "full": sum(x["effective_coverage"] == "FULL" for x in items),
            "coverage": "FULL"
            if all(x["effective_coverage"] == "FULL" for x in items)
            else "INCOMPLETE",
        }

    def gaps(self) -> list[dict[str, Any]]:
        return [x for x in self.records.values() if x["effective_coverage"] != "FULL"]

    def regression(
        self,
        registry: Any,
        reconstruction: Any,
        world: Any,
        objects: Any,
        literary: Any,
        implementation: Any,
        evidence_regression: dict[str, Any],
    ) -> dict[str, Any]:
        checks = {
            "P0_249_FULL": len(self.records) == 249 and not self.gaps(),
            "CURRENT_15_FULL": registry.current_summary().get("semantic_coverage_counts")
            == {"FULL": 15, "PARTIAL": 0, "MINIMAL": 0, "NONE": 0},
            "CURRENT_MARKDOWN_ISLANDS_0": registry.current_summary().get("current_markdown_islands") == 0,
            "AUTHORITY_CONFLICTS_0": registry.current_summary().get("unresolved_authority_conflicts") == 0,
            "RECONSTRUCTION_QUERYABLE": reconstruction.summary().get("chapters") == 20,
            "WORLD_QUERYABLE": world.summary().get("completion", {}).get("world_queryable") is True,
            "OBJECT_CONTINUITY": objects.continuity_report().get("status") == "PASS",
            "LITERARY_ECOLOGY_QUERYABLE": literary.summary().get("completion", {}).get("literary_ecology_queryable") is True,
            "IMPLEMENTATION_ALIGNMENT": implementation.summary().get("status") == "PASS",
            "EVIDENCE_CORE": evidence_regression.get("overall") == "PASS",
            "STABLE_ACTIVE_UNCHANGED": registry.current_summary().get("stable_active_sha256")
            == "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320",
            "LITERATURE_FROZEN": self.project_state.get("literature_freeze", {}).get("active") is True,
            "NEGATIVE_ARCHIVE_NON_RUNTIME": self.negative_archive.get("stable_active_effect") == "NONE",
        }
        return {
            "milestone": "M7",
            "overall": "PASS" if all(checks.values()) else "FAIL",
            "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
            "coverage_signoff": "PENDING_M8",
            "completion_gate_ready": False,
        }

    def validate_integrity(
        self,
        registry: Any,
        reconstruction: Any,
        world: Any,
        objects: Any,
        literary: Any,
        implementation: Any,
        evidence_regression: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        if self.inventory_sha256 != P0_INVENTORY_SHA256:
            errors.append(
                f"P0 inventory digest mismatch: {self.inventory_sha256} != {P0_INVENTORY_SHA256}"
            )
        if len(self.records) != 249:
            errors.append(f"M7 P0 inventory must contain 249 unique records; got {len(self.records)}")

        old = Counter(x["pre_migration_coverage"] for x in self.records.values())
        if dict(old) != EXPECTED_OLD_COVERAGE:
            errors.append(f"M7 pre-migration coverage census drift: {dict(old)}")
        layers = Counter(x["target_layer"] for x in self.records.values())
        if dict(layers) != EXPECTED_LAYERS:
            errors.append(f"M7 P0 layer census drift: {dict(layers)}")
        authority = Counter(x["authority"] for x in self.records.values())
        if dict(authority) != EXPECTED_AUTHORITY:
            errors.append(f"M7 P0 authority census drift: {dict(authority)}")
        runtime_authority = Counter(x["runtime_authority"] for x in self.records.values())
        if dict(runtime_authority) != EXPECTED_RUNTIME_AUTHORITY:
            errors.append(f"M7 P0 runtime-authority census drift: {dict(runtime_authority)}")

        for sha, record in self.records.items():
            if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
                errors.append(f"M7 invalid SHA256: {sha}")
            path = record["self_contained_path"]
            if not path.startswith(("01_PRIMARY_SOURCES/", "02_CURRENT_RUNTIME/", "03_VALID_HISTORY/")):
                errors.append(f"{sha}: no concrete self-contained entity path")
            if record["effective_coverage"] != "FULL":
                errors.append(f"{sha}: P0 semantic coverage is not FULL")
            for artifact in record["binding"]["artifacts"]:
                if not (self.root / artifact).exists():
                    errors.append(f"{sha}: binding artifact missing: {artifact}")

        # All fourteen P0 CURRENT sources are already in DocumentRegistry and FULL after M7.
        current_p0 = [x for x in self.records.values() if x["authority"] == "CURRENT"]
        registry_by_sha = {x["sha256"]: x for x in registry.documents.values()}
        if len(current_p0) != 14:
            errors.append(f"M7 expected 14 P0 CURRENT documents; got {len(current_p0)}")
        for record in current_p0:
            doc = registry_by_sha.get(record["sha256"])
            if doc is None:
                errors.append(f"P0 CURRENT source absent from DocumentRegistry: {record['sha256']}")
            elif doc["machine_representation"]["semantic_coverage"] != "FULL":
                errors.append(f"P0 CURRENT source not FULL in DocumentRegistry: {doc['id']}")

        current = registry.current_summary()
        if current.get("semantic_coverage_counts") != {
            "FULL": 15, "PARTIAL": 0, "MINIMAL": 0, "NONE": 0
        }:
            errors.append("M7 must leave all 15 CURRENT runtime documents semantic FULL")
        if current.get("current_markdown_islands") != 0:
            errors.append("M7 CURRENT Markdown-only islands must be zero")
        if current.get("unresolved_authority_conflicts") != 0:
            errors.append("M7 unresolved authority conflicts must be zero")
        if current.get("completion_gate_ready"):
            m8 = load_data(self.root / "data" / "project_state" / "m8.json") or {}
            if (
                m8.get("status") != "PASS"
                or m8.get("completion_gate", {}).get("overall") != "PASS"
            ):
                errors.append("Completion Gate may be ready only after persisted M8 PASS")

        state = self.project_state
        if state.get("milestone") != "M7":
            errors.append("M7 project state milestone mismatch")
        if state.get("p0_coverage", {}).get("full") != 249:
            errors.append("M7 project state must record P0 FULL=249")
        if state.get("p0_coverage", {}).get("signed_off"):
            errors.append("M7 coverage signoff belongs to M8 and must remain false")
        if state.get("completion_gate_ready"):
            errors.append("M7 project state may not mark Completion Gate ready")
        if not state.get("literature_freeze", {}).get("active"):
            errors.append("M7 literature freeze must remain active")

        # Negative/archive fixtures may never re-enter runtime authority.
        for item in self.negative_archive.get("package_fixtures", []):
            package = registry.packages.get(item["id"])
            if package is None:
                errors.append(f"negative archive references unknown package {item['id']}")
            elif package["runtime_authority"] != "NO":
                errors.append(f"negative package regained runtime authority: {item['id']}")
        if self.negative_archive.get("stable_active_effect") != "NONE":
            errors.append("negative archive may not mutate stable ACTIVE")

        regression = self.regression(
            registry,
            reconstruction,
            world,
            objects,
            literary,
            implementation,
            evidence_regression,
        )
        if regression["overall"] != "PASS":
            errors.extend(
                f"M7 regression {name}: {status}"
                for name, status in regression["checks"].items()
                if status != "PASS"
            )
        return errors


def format_coverage(kind: str, payload: Any) -> str:
    if kind == "summary":
        before = payload["pre_migration_coverage"]
        after = payload["effective_coverage"]
        return "\n".join([
            "FULL MIGRATION COVERAGE M7",
            f"status: {payload['status']}",
            f"P0: {payload['p0_total']}",
            "before: "
            f"FULL={before.get('FULL', 0)} PARTIAL={before.get('PARTIAL', 0)} "
            f"MINIMAL={before.get('MINIMAL', 0)} NONE={before.get('NONE', 0)}",
            f"after: FULL={after.get('FULL', 0)}",
            f"concrete_source_paths: {payload['concrete_source_paths']}/249",
            f"unresolved: {payload['unresolved']}",
            f"CURRENT Markdown islands: {payload['current_markdown_islands']}",
            f"authority conflicts: {payload['unresolved_authority_conflicts']}",
            f"coverage signoff: {str(payload['coverage_report_signed_off']).lower()}",
            f"Completion Gate ready: {str(payload['completion_gate_ready']).lower()}",
        ])
    if kind == "regression":
        lines = [f"M7 FULL MIGRATION REGRESSION: {payload['overall']}"]
        lines.extend(f"- {k}: {v}" for k, v in payload["checks"].items())
        lines.extend([
            f"coverage_signoff: {payload['coverage_signoff']}",
            "completion_gate_ready: false",
        ])
        return "\n".join(lines)
    if kind in {"target", "layer"}:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if kind == "gaps":
        return "M7 P0 GAPS: 0" if not payload else json.dumps(payload, ensure_ascii=False, indent=2)
    return json.dumps(payload, ensure_ascii=False, indent=2)
