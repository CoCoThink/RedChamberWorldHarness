from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import ProvenanceGraph
from .history import HistoricalMechanismRegistry
from .io import load_data
from .literals import LiteralRegistry
from .open_interfaces import OpenInterfaceRegistry


@dataclass
class RegressionGate:
    name: str
    passed: bool
    findings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "findings": self.findings,
        }


def _load_manifest(root: Path) -> dict[str, Any]:
    path = root / "data" / "regression" / "r4_evidence_core.yaml"
    doc = load_data(path) or {}
    manifests = doc.get("regression_manifests", [])
    if len(manifests) != 1:
        raise ValueError("R4 regression manifest must contain exactly one manifest")
    return manifests[0]


def _gate(name: str, findings: list[str]) -> RegressionGate:
    return RegressionGate(name=name, passed=not findings, findings=findings)


def _legacy_hard_evidence_errors(root: Path, graph: ProvenanceGraph) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / "data" / "evidence").glob("*.yaml")):
        doc = load_data(path) or {}
        for claim in doc.get("claims", []):
            if claim.get("status") != "HARD":
                continue
            source_ref = claim.get("source_ref")
            if not source_ref:
                errors.append(
                    f"{path.relative_to(root)}:{claim.get('id')}: HARD evidence has no source_ref"
                )
            elif source_ref not in graph.sources:
                errors.append(
                    f"{path.relative_to(root)}:{claim.get('id')}: unknown source_ref {source_ref}"
                )
    return errors


def run_r4_evidence_regression(root: Path) -> dict[str, Any]:
    manifest = _load_manifest(root)
    graph = ProvenanceGraph.from_repo(root)
    literals = LiteralRegistry.from_repo(root)
    mechanisms = HistoricalMechanismRegistry.from_repo(root)
    opens = OpenInterfaceRegistry.from_repo(root)

    gates: list[RegressionGate] = []

    # 1. Provenance
    findings = list(graph.validate_integrity())
    findings.extend(_legacy_hard_evidence_errors(root, graph))
    for source_id, source in graph.sources.items():
        if source["type"] == "EARLY_COMMENT" and source.get("tier") not in {
            "W1_DIRECT", "W1_SEEN"
        }:
            findings.append(f"{source_id}: EARLY_COMMENT lacks W1 tier")
    gates.append(_gate("PROVENANCE", findings))

    # 2. Role / T-axis
    findings = []
    expected_axes = manifest["axis_expectations"]
    actual_axes = {k: v["class"] for k, v in graph.title_axes.items()}
    if actual_axes != expected_axes:
        findings.append(
            f"axis mismatch expected={expected_axes} actual={actual_axes}"
        )
    gates.append(_gate("ROLE_T_AXIS", findings))

    # 3. Modality / W2
    findings = []
    w2_sources = [
        s for s in graph.sources.values() if s.get("tier") == "W2_TRANSCRIPT"
    ]
    if len(w2_sources) != manifest["source_type_counts"]["EARLY_TRANSCRIPT"]:
        findings.append(
            f"W2 source count {len(w2_sources)} != "
            f"{manifest['source_type_counts']['EARLY_TRANSCRIPT']}"
        )
    for claim_id, claim in graph.claims.items():
        if graph.claim_is_w2_only(claim_id) and claim.get("modality") != "TRANSCRIPT_WEAK":
            findings.append(f"{claim_id}: W2-only claim modality is not TRANSCRIPT_WEAK")
    for decision_id, decision in graph.decisions.items():
        if decision["status"] == "LOCKED":
            w2_basis = [
                c for c in decision.get("based_on", []) if graph.claim_is_w2_only(c)
            ]
            if w2_basis:
                findings.append(f"{decision_id}: LOCKED on W2-only basis {w2_basis}")
    gates.append(_gate("MODALITY_W2", findings))

    # 4. Literal target identity
    findings = list(literals.validate_integrity(graph))
    actual_literal_targets = {
        literal_id: item["targets"] for literal_id, item in literals.constraints.items()
    }
    if actual_literal_targets != manifest["literal_expectations"]:
        findings.append(
            "literal target map differs from release manifest"
        )
    gates.append(_gate("LITERAL_TARGET", findings))

    # 5. Placement / current choices
    findings = []
    actual_current = {
        d_id for d_id, d in graph.decisions.items() if d["status"] == "CURRENT"
    }
    expected_current = set(manifest["current_decisions"])
    if actual_current != expected_current:
        findings.append(
            f"CURRENT decision set mismatch missing={sorted(expected_current-actual_current)} "
            f"extra={sorted(actual_current-expected_current)}"
        )
    for d_id in expected_current:
        decision = graph.decisions.get(d_id)
        if not decision or decision.get("constraint") != "MAY":
            findings.append(f"{d_id}: current placement/model is not CURRENT/MAY")
    gates.append(_gate("PLACEMENT_CURRENT", findings))

    # 6. Implementation / stable ACTIVE hash
    findings = []
    stable = manifest["stable_active"]
    for impl_id, impl in graph.implementations.items():
        if impl.get("status") != "ACTIVE":
            continue
        locator = impl.get("locator", {})
        if locator.get("file_ref") != stable["file_ref"]:
            findings.append(
                f"{impl_id}: ACTIVE implementation file_ref differs from stable ACTIVE"
            )
        if locator.get("file_sha256") != stable["sha256"]:
            findings.append(
                f"{impl_id}: ACTIVE implementation SHA differs from stable ACTIVE"
            )
    gates.append(_gate("IMPLEMENTATION_STABLE_ACTIVE", findings))

    # 7. Semantic hard anchors
    findings = []
    actual_locked = {
        d_id for d_id, d in graph.decisions.items() if d["status"] == "LOCKED"
    }
    expected_locked = set(manifest["locked_decisions"])
    if actual_locked != expected_locked:
        findings.append(
            f"LOCKED decision set mismatch missing={sorted(expected_locked-actual_locked)} "
            f"extra={sorted(actual_locked-expected_locked)}"
        )
    for d_id in expected_locked:
        decision = graph.decisions.get(d_id)
        if not decision:
            findings.append(f"{d_id}: missing")
            continue
        if decision.get("constraint") not in {"MUST", "MUST_NOT"}:
            findings.append(f"{d_id}: LOCKED without hard constraint")
        if not graph.decision_fully_source_backed(d_id):
            findings.append(f"{d_id}: not fully source-backed")
        if not graph.decision_lock_eligible(d_id):
            findings.append(f"{d_id}: not lock-eligible")
    gates.append(_gate("SEMANTIC_HARD_ANCHORS", findings))

    # 8. Boundary / OPEN-LOCK
    findings = list(opens.validate_integrity(graph, literals, mechanisms))
    actual_open = {
        d_id for d_id, d in graph.decisions.items() if d["status"] == "OPEN"
    }
    expected_open = set(manifest["open_decisions"])
    if actual_open != expected_open:
        findings.append(
            f"OPEN decision set mismatch missing={sorted(expected_open-actual_open)} "
            f"extra={sorted(actual_open-expected_open)}"
        )
    if len(opens.interfaces) != manifest["expected_counts"]["open_interfaces"]:
        findings.append(
            f"OPEN interface count {len(opens.interfaces)} != "
            f"{manifest['expected_counts']['open_interfaces']}"
        )
    gates.append(_gate("BOUNDARY_OPEN_LOCK", findings))

    # 9. Historical feasibility
    findings = list(mechanisms.validate_integrity(graph))
    actual_verdicts = {k: v["verdict"] for k, v in mechanisms.mechanisms.items()}
    if actual_verdicts != manifest["mechanism_verdicts"]:
        findings.append(
            f"historical verdict mismatch expected={manifest['mechanism_verdicts']} "
            f"actual={actual_verdicts}"
        )
    gates.append(_gate("HISTORICAL_H01_H06", findings))

    # 10. Release shape counts
    findings = []
    actual_counts = {
        "sources": len(graph.sources),
        "claims": len(graph.claims),
        "decisions": len(graph.decisions),
        "implementations": len(graph.implementations),
        "title_axes": len(graph.title_axes),
        "literals": len(literals.constraints),
        "mechanisms": len(mechanisms.mechanisms),
        "open_interfaces": len(opens.interfaces),
    }
    if actual_counts != manifest["expected_counts"]:
        findings.append(
            f"node counts differ expected={manifest['expected_counts']} actual={actual_counts}"
        )

    claim_statuses = Counter(c["status"] for c in graph.claims.values())
    actual_claim_statuses = {
        key: claim_statuses.get(key, 0)
        for key in ("SUPPORTED", "CONTESTED", "NOT_ESTABLISHED", "REFUTED")
    }
    if actual_claim_statuses != manifest["claim_status_counts"]:
        findings.append(
            f"claim status counts differ expected={manifest['claim_status_counts']} "
            f"actual={actual_claim_statuses}"
        )

    decision_statuses = Counter(d["status"] for d in graph.decisions.values())
    actual_decision_statuses = {
        key: decision_statuses.get(key, 0)
        for key in ("LOCKED", "CURRENT", "OPEN", "REJECTED")
    }
    if actual_decision_statuses != manifest["decision_status_counts"]:
        findings.append(
            f"decision status counts differ expected={manifest['decision_status_counts']} "
            f"actual={actual_decision_statuses}"
        )

    source_types = Counter(s["type"] for s in graph.sources.values())
    actual_source_types = dict(sorted(source_types.items()))
    if actual_source_types != manifest["source_type_counts"]:
        findings.append(
            f"source type counts differ expected={manifest['source_type_counts']} "
            f"actual={actual_source_types}"
        )
    gates.append(_gate("RELEASE_SHAPE", findings))

    overall = all(gate.passed for gate in gates)
    return {
        "id": manifest["id"],
        "overall": "PASS" if overall else "FAIL",
        "stable_active": manifest["stable_active"],
        "gates": [gate.to_dict() for gate in gates],
    }


def format_regression(payload: dict[str, Any]) -> str:
    out = [
        f"R4 EVIDENCE CORE REGRESSION: {payload['overall']}",
        f"manifest: {payload['id']}",
        f"stable_active: {payload['stable_active']['file_ref']}",
        f"stable_sha256: {payload['stable_active']['sha256']}",
        "",
        "GATES",
    ]
    for gate in payload["gates"]:
        out.append(f"- {gate['name']}: {gate['status']}")
        for finding in gate["findings"]:
            out.append(f"  - {finding}")
    return "\n".join(out)
