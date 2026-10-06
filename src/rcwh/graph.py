from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .io import load_data


@dataclass
class ProvenanceGraph:
    sources: dict[str, dict[str, Any]]
    claims: dict[str, dict[str, Any]]
    decisions: dict[str, dict[str, Any]]
    implementations: dict[str, dict[str, Any]]
    title_axes: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ProvenanceGraph":
        def load_dir(dirname: str, wrapper: str) -> dict[str, dict[str, Any]]:
            result: dict[str, dict[str, Any]] = {}
            path = root / "data" / dirname
            if not path.exists():
                return result
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get(wrapper, []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate {wrapper[:-1]} id: {item_id}")
                    result[item_id] = item
            return result

        return cls(
            sources=load_dir("sources", "sources"),
            claims=load_dir("claims", "claims"),
            decisions=load_dir("decisions", "decisions"),
            implementations=load_dir("implementations", "implementations"),
            title_axes=load_dir("axes", "title_axes"),
        )

    @staticmethod
    def _source_fingerprint(source: dict[str, Any]) -> str:
        witness = source.get("witness", {})
        locator = json.dumps(source.get("locator", {}), ensure_ascii=False, sort_keys=True)
        return "|".join([
            str(witness.get("siglum") or witness.get("label")),
            locator,
            source.get("text_sha256", ""),
        ])

    def decision_fully_source_backed(self, decision_id: str) -> bool:
        decision = self.decisions[decision_id]
        based_on = decision.get("based_on", [])
        if not based_on:
            return False
        return all(
            claim_id in self.claims
            and self.claims[claim_id].get("status") == "SUPPORTED"
            and bool(self.claims[claim_id].get("support"))
            for claim_id in based_on
        )

    def claim_source_tiers(self, claim_id: str) -> list[str]:
        claim = self.claims[claim_id]
        tiers: list[str] = []
        for edge in claim.get("support", []):
            source = self.sources.get(edge["source"])
            if source is None:
                continue
            tier = source.get("tier")
            if tier and tier not in tiers:
                tiers.append(tier)
        return tiers

    def claim_is_w2_only(self, claim_id: str) -> bool:
        if claim_id not in self.claims:
            return False
        claim = self.claims[claim_id]
        support = claim.get("support", [])
        if not support:
            return False
        tiers = self.claim_source_tiers(claim_id)
        return bool(tiers) and set(tiers) == {"W2_TRANSCRIPT"}

    def decision_lock_eligible(self, decision_id: str) -> bool:
        if not self.decision_fully_source_backed(decision_id):
            return False
        decision = self.decisions[decision_id]
        return not any(self.claim_is_w2_only(c) for c in decision.get("based_on", []))

    def validate_integrity(self) -> list[str]:
        errors: list[str] = []

        seen_fingerprints: dict[str, str] = {}
        for source_id, source in self.sources.items():
            tier = source.get("tier")
            source_type = source.get("type")
            if tier == "W2_TRANSCRIPT" and source_type != "EARLY_TRANSCRIPT":
                errors.append(
                    f"{source_id}: W2_TRANSCRIPT source must use EARLY_TRANSCRIPT type"
                )
            if source_type == "EARLY_TRANSCRIPT" and tier != "W2_TRANSCRIPT":
                errors.append(
                    f"{source_id}: EARLY_TRANSCRIPT source must use W2_TRANSCRIPT tier"
                )

            fingerprint = self._source_fingerprint(source)
            if fingerprint in seen_fingerprints:
                errors.append(
                    f"{source_id}: duplicate source witness/locator/text of "
                    f"{seen_fingerprints[fingerprint]}"
                )
            else:
                seen_fingerprints[fingerprint] = source_id

        for claim_id, claim in self.claims.items():
            support = claim.get("support", [])
            if claim.get("status") == "SUPPORTED" and not support:
                errors.append(f"{claim_id}: SUPPORTED claim has no source support")
            for edge in support:
                source_id = edge["source"]
                if source_id not in self.sources:
                    errors.append(f"{claim_id}: unknown source {source_id}")

            if self.claim_is_w2_only(claim_id):
                if claim.get("modality") != "TRANSCRIPT_WEAK":
                    errors.append(
                        f"{claim_id}: W2-only claim must use TRANSCRIPT_WEAK modality"
                    )
            if claim.get("modality") == "TRANSCRIPT_WEAK" and support:
                non_w2 = [
                    edge["source"] for edge in support
                    if edge["source"] in self.sources
                    and self.sources[edge["source"]].get("tier") != "W2_TRANSCRIPT"
                ]
                if non_w2:
                    errors.append(
                        f"{claim_id}: TRANSCRIPT_WEAK claim has non-W2 sources {non_w2}"
                    )

        compatibility = {
            "LOCKED": {"MUST", "MUST_NOT"},
            "CURRENT": {"MAY"},
            "OPEN": {"OPEN"},
            "REJECTED": {"NONE"},
        }

        for decision_id, decision in self.decisions.items():
            based_on = decision.get("based_on", [])
            for claim_id in based_on:
                if claim_id not in self.claims:
                    errors.append(f"{decision_id}: unknown claim {claim_id}")

            status = decision.get("status")
            constraint = decision.get("constraint")
            domain = decision.get("domain", "NARRATIVE_RECONSTRUCTION")
            historical_basis = [
                c for c in based_on
                if c in self.claims
                and self.claims[c].get("authority_scope") == "HISTORICAL_FEASIBILITY"
            ]
            if historical_basis and domain != "HISTORICAL_BOUNDARY":
                errors.append(
                    f"{decision_id}: historical-feasibility claims cannot silently "
                    f"support narrative decisions {historical_basis}"
                )
            if domain == "HISTORICAL_BOUNDARY":
                non_historical = [
                    c for c in based_on
                    if c in self.claims
                    and self.claims[c].get("authority_scope") != "HISTORICAL_FEASIBILITY"
                ]
                if non_historical:
                    errors.append(
                        f"{decision_id}: HISTORICAL_BOUNDARY has non-historical basis "
                        f"{non_historical}"
                    )
                if status == "LOCKED" and constraint != "MUST_NOT":
                    errors.append(
                        f"{decision_id}: locked historical boundary may only compile "
                        f"to MUST_NOT, never positive plot MUST"
                    )

            if constraint not in compatibility.get(status, set()):
                errors.append(
                    f"{decision_id}: incompatible status/constraint {status}/{constraint}"
                )

            if status == "LOCKED":
                if decision.get("reversible") is not False:
                    errors.append(f"{decision_id}: LOCKED decision must be irreversible")
                unsupported = [
                    c for c in based_on
                    if c not in self.claims
                    or self.claims[c].get("status") != "SUPPORTED"
                    or not self.claims[c].get("support")
                ]
                if unsupported:
                    errors.append(
                        f"{decision_id}: LOCKED decision has non-supported basis {unsupported}"
                    )
                w2_only = [c for c in based_on if self.claim_is_w2_only(c)]
                if w2_only:
                    errors.append(
                        f"{decision_id}: LOCKED decision cannot rely on W2-only claims {w2_only}"
                    )

            for impl_id in decision.get("implementation_refs", []):
                if impl_id not in self.implementations:
                    errors.append(f"{decision_id}: unknown implementation {impl_id}")

        for impl_id, implementation in self.implementations.items():
            for decision_id in implementation.get("decision_refs", []):
                if decision_id not in self.decisions:
                    errors.append(f"{impl_id}: unknown decision {decision_id}")
                    continue
                if impl_id not in self.decisions[decision_id].get("implementation_refs", []):
                    if self.decisions[decision_id].get("status") != "LOCKED":
                        errors.append(
                            f"{impl_id}: decision {decision_id} does not point back to implementation"
                        )

        expected_roles = {
            "T0": {"TITLE_FULL"},
            "T1": {"TITLE_PART"},
            "T2": {"DRAFT_LABEL", "CHAPTER_CALL"},
            "T2_W2": {"W2_HINT", "DRAFT_LABEL", "CHAPTER_CALL"},
            "T3": {"EVENT", "SCENE_DESCRIPTION"},
        }
        for axis_id, axis in self.title_axes.items():
            axis_class = axis["class"]
            claim_refs = axis.get("claim_refs", [])
            generated = axis["generated"]

            if axis_class == "TG":
                if not generated:
                    errors.append(f"{axis_id}: TG must be generated")
                if claim_refs:
                    errors.append(f"{axis_id}: TG must not claim evidence authority")
            else:
                if generated:
                    errors.append(f"{axis_id}: evidence-side T-axis record cannot be generated")
                if not claim_refs:
                    errors.append(f"{axis_id}: {axis_class} requires evidence claims")
                for claim_id in claim_refs:
                    if claim_id not in self.claims:
                        errors.append(f"{axis_id}: unknown claim {claim_id}")
                        continue
                    claim = self.claims[claim_id]
                    if claim.get("status") != "SUPPORTED":
                        errors.append(f"{axis_id}: claim {claim_id} is not SUPPORTED")
                    if claim.get("t_axis") != axis_class:
                        errors.append(
                            f"{axis_id}: claim {claim_id} t_axis {claim.get('t_axis')} != {axis_class}"
                        )
                    if claim.get("role") not in expected_roles.get(axis_class, set()):
                        errors.append(
                            f"{axis_id}: claim {claim_id} role {claim.get('role')} incompatible with {axis_class}"
                        )
                    if axis_class == "T2_W2" and not self.claim_is_w2_only(claim_id):
                        errors.append(
                            f"{axis_id}: T2_W2 claim {claim_id} must be W2-only"
                        )

            for key in ("placement_decision_ref", "formal_title_decision_ref"):
                decision_id = axis.get(key)
                if decision_id and decision_id not in self.decisions:
                    errors.append(f"{axis_id}: unknown {key} {decision_id}")

            formal_id = axis.get("formal_title_decision_ref")
            if formal_id and formal_id in self.decisions and axis_class in {"T2", "T2_W2", "T3"}:
                if self.decisions[formal_id].get("constraint") in {"MUST", "MUST_NOT"}:
                    errors.append(
                        f"{axis_id}: {axis_class} cannot hard-lock formal-title identity"
                    )

            for impl_id in axis.get("implementation_refs", []):
                if impl_id not in self.implementations:
                    errors.append(f"{axis_id}: unknown implementation {impl_id}")

            for embedded in axis.get("embedded_axes", []):
                if embedded not in self.title_axes:
                    errors.append(f"{axis_id}: unknown embedded axis {embedded}")

        return errors

    def permission(self, decision_id: str) -> str:
        return self.decisions[decision_id]["constraint"]

    def _sources_for_claims(self, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
        source_ids: list[str] = []
        for claim in claims:
            for edge in claim.get("support", []):
                if edge["source"] not in source_ids:
                    source_ids.append(edge["source"])
        return [self.sources[s] for s in source_ids if s in self.sources]

    def trace(self, node_id: str) -> dict[str, Any]:
        if node_id in self.sources:
            source = self.sources[node_id]
            claims = [
                c for c in self.claims.values()
                if any(edge["source"] == node_id for edge in c.get("support", []))
            ]
            claim_ids = {c["id"] for c in claims}
            decisions = [
                d for d in self.decisions.values()
                if claim_ids.intersection(d.get("based_on", []))
            ]
            decision_ids = {d["id"] for d in decisions}
            implementations = [
                i for i in self.implementations.values()
                if decision_ids.intersection(i.get("decision_refs", []))
            ]
            axes = [
                a for a in self.title_axes.values()
                if claim_ids.intersection(a.get("claim_refs", []))
            ]
            return {
                "type": "source",
                "source": source,
                "claims": claims,
                "decisions": decisions,
                "implementations": implementations,
                "title_axes": axes,
            }

        if node_id in self.claims:
            claim = self.claims[node_id]
            sources = [
                self.sources[edge["source"]]
                for edge in claim.get("support", [])
                if edge["source"] in self.sources
            ]
            decisions = [
                d for d in self.decisions.values()
                if node_id in d.get("based_on", [])
            ]
            decision_ids = {d["id"] for d in decisions}
            implementations = [
                i for i in self.implementations.values()
                if decision_ids.intersection(i.get("decision_refs", []))
            ]
            axes = [
                a for a in self.title_axes.values()
                if node_id in a.get("claim_refs", [])
            ]
            return {
                "type": "claim",
                "claim": claim,
                "support_tiers": self.claim_source_tiers(node_id),
                "w2_only": self.claim_is_w2_only(node_id),
                "sources": sources,
                "decisions": decisions,
                "implementations": implementations,
                "title_axes": axes,
            }

        if node_id in self.decisions:
            decision = self.decisions[node_id]
            claims = [
                self.claims[c]
                for c in decision.get("based_on", [])
                if c in self.claims
            ]
            sources = self._sources_for_claims(claims)
            implementations = [
                self.implementations[i]
                for i in decision.get("implementation_refs", [])
                if i in self.implementations
            ]
            axes = [
                a for a in self.title_axes.values()
                if node_id in {a.get("placement_decision_ref"), a.get("formal_title_decision_ref")}
            ]
            return {
                "type": "decision",
                "decision": decision,
                "permission": self.permission(node_id),
                "fully_source_backed": self.decision_fully_source_backed(node_id),
                "lock_eligible": self.decision_lock_eligible(node_id),
                "claims": claims,
                "sources": sources,
                "implementations": implementations,
                "title_axes": axes,
            }

        if node_id in self.implementations:
            implementation = self.implementations[node_id]
            decisions = [
                self.decisions[d]
                for d in implementation.get("decision_refs", [])
                if d in self.decisions
            ]
            claim_ids: list[str] = []
            for decision in decisions:
                for claim_id in decision.get("based_on", []):
                    if claim_id not in claim_ids:
                        claim_ids.append(claim_id)
            claims = [self.claims[c] for c in claim_ids if c in self.claims]
            sources = self._sources_for_claims(claims)
            axes = [
                a for a in self.title_axes.values()
                if node_id in a.get("implementation_refs", [])
            ]
            return {
                "type": "implementation",
                "implementation": implementation,
                "decisions": decisions,
                "claims": claims,
                "sources": sources,
                "title_axes": axes,
            }

        if node_id in self.title_axes:
            axis = self.title_axes[node_id]
            claims = [
                self.claims[c] for c in axis.get("claim_refs", []) if c in self.claims
            ]
            decisions = [
                self.decisions[d]
                for d in [axis.get("placement_decision_ref"), axis.get("formal_title_decision_ref")]
                if d and d in self.decisions
            ]
            implementations = [
                self.implementations[i]
                for i in axis.get("implementation_refs", [])
                if i in self.implementations
            ]
            return {
                "type": "title_axis",
                "title_axis": axis,
                "claims": claims,
                "sources": self._sources_for_claims(claims),
                "decisions": decisions,
                "implementations": implementations,
            }

        raise KeyError(f"Unknown provenance node: {node_id}")
