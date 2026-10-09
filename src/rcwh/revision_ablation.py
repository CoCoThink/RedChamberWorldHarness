from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
from .contracts import unique_index, record_sha256
from .microdraft import ControlledMicrodraftRuntime
from .blind_microdraft_review import BlindMicrodraftReviewRuntime
from .narrative_discourse import NarrativeDiscourseRuntime
from .literary_stress import ScenarioLiteraryStressRuntime
from .literary_suite import LiteraryEvaluatorSuite

@dataclass
class CrossRouteRevisionAblationRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "CrossRouteRevisionAblationRuntime":
        from .workflow import ProjectState
        return cls(root, ProjectState.from_repo(root).experiment())

    @property
    def pairs(self) -> dict[str, dict[str, Any]]:
        return unique_index(self.data.get('pairs', []), 'baseline_token')

    def _text(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8").strip()

    def require_inputs(self, p6: ControlledMicrodraftRuntime, p7: BlindMicrodraftReviewRuntime) -> None:
        basis = self.data["source_basis"]
        p6.require_snapshot(basis["p6_ref"], basis["p6_snapshot_sha256"])
        if basis["p7_ref"] != p7.data["id"] or basis["p7_snapshot_sha256"] != record_sha256(p7.data):
            raise ValueError("blind review snapshot binding drift; revision requires its original review")
        p7.mapping(p6)

    def anti_patterns(self, text: str) -> dict[str, Any]:
        hits={}
        for key,terms in self.data["anti_pattern_rules"].items():
            found=[term for term in terms if term in text]
            hits[key]={"terms":found,"count":len(found)}
        return {"by_rule":hits,"total":sum(x["count"] for x in hits.values())}

    def pair(
        self,
        baseline_token: str,
        p6: ControlledMicrodraftRuntime,
        p7: BlindMicrodraftReviewRuntime,
        discourse: NarrativeDiscourseRuntime,
        stress: ScenarioLiteraryStressRuntime,
        suite: LiteraryEvaluatorSuite,
    ) -> dict[str, Any]:
        if baseline_token not in self.pairs:
            raise KeyError(f"Unknown P8 baseline token: {baseline_token}")
        self.require_inputs(p6, p7)
        spec=self.pairs[baseline_token]
        baseline=p6.text(baseline_token)
        revised=self._text(spec["revised_artifact"])
        base_spec=p6.drafts[baseline_token]
        blockers=[]
        card=discourse.card(base_spec["scenario_id"],base_spec["probe_id"],stress)
        if base_spec["primary_focalizer"] != card["sjuzet_plan"]["primary_focalizer"]:
            blockers.append({"kind":"BASELINE_FOCALIZER_DRIFT"})
        n=len(revised)
        if not (self.data["thresholds"]["min_chars"] <= n <= self.data["thresholds"]["max_chars"]):
            blockers.append({"kind":"REVISED_LENGTH_OUT_OF_RANGE","chars":n})

        for anchor in base_spec["required_anchors"]:
            if anchor in revised:
                continue
            aliases=self.data.get("lexical_equivalence",{}).get(baseline_token,{}).get(anchor,[])
            if not any(x in revised for x in aliases):
                blockers.append({"kind":"FABULA_ANCHOR_LOSS","anchor":anchor,"aliases":aliases})

        forbidden=[x for x in base_spec["forbidden_terms"] if x in revised]
        if forbidden:
            blockers.append({"kind":"FORBIDDEN_TERM","hits":forbidden})

        literary=suite.legacy_prose_screen(revised,spec["revised_token"])
        if literary["status"]=="REJECT_BEFORE_BLIND_READ":
            blockers.append({"kind":"LITERARY_SUITE_REJECT","details":literary["blockers"]})

        before=self.anti_patterns(baseline)
        after=self.anti_patterns(revised)
        if after["total"] > before["total"] + self.data["thresholds"]["regression_in_anti_pattern_count_allowed"]:
            blockers.append({"kind":"ANTI_PATTERN_REGRESSION","before":before["total"],"after":after["total"]})
        if baseline_token in self.data["strict_reduction_tokens"] and not after["total"] < before["total"]:
            blockers.append({"kind":"STRICT_REDUCTION_NOT_MET","before":before["total"],"after":after["total"]})

        return {
          "baseline_token":baseline_token,"revised_token":spec["revised_token"],
          "scenario_id":base_spec["scenario_id"],"probe_id":base_spec["probe_id"],"cell_id":base_spec["cell_id"],
          "applied_targets":spec["applied_targets"],
          "baseline_sha256":hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
          "revised_sha256":hashlib.sha256(revised.encode("utf-8")).hexdigest(),
          "baseline_chars":len(baseline),"revised_chars":len(revised),
          "anti_patterns_before":before,"anti_patterns_after":after,
          "p7_baseline":p7.token(baseline_token),
          "blockers":blockers,
          "status":"ABLATION_READY" if not blockers else "BLOCKED",
          "literary_status":literary["status"],
          "superiority_claim":None,
          "canonical_effect":"NONE"
        }

    def evaluate_all(self,p6,p7,discourse,stress,suite) -> dict[str, Any]:
        rows=[self.pair(token,p6,p7,discourse,stress,suite) for token in sorted(self.pairs)]
        before=sum(x["anti_patterns_before"]["total"] for x in rows)
        after=sum(x["anti_patterns_after"]["total"] for x in rows)
        return {
          "status":"PASS" if all(x["status"]=="ABLATION_READY" for x in rows) else "BLOCKED",
          "pair_count":len(rows),
          "ready_count":sum(x["status"]=="ABLATION_READY" for x in rows),
          "blocker_count":sum(len(x["blockers"]) for x in rows),
          "anti_pattern_total_before":before,
          "anti_pattern_total_after":after,
          "anti_pattern_delta":after-before,
          "strict_reduction_tokens":self.data["strict_reduction_tokens"],
          "winner":None,"route_eliminated":False,"literary_superiority_claim":None,
          "next_gate":self.data["next_gate"]
        }

    def validate_integrity(self,p6,p7,discourse,stress,suite) -> list[str]:
        errors=[]
        try:
            self.require_inputs(p6, p7)
        except (ValueError, KeyError, OSError) as exc:
            return [str(exc)]
        if self.data.get("authority")!="SHADOW_ONLY": errors.append("P8 must remain SHADOW_ONLY")
        if self.data.get("output_authority")!="EXPERIMENTAL_REVISION_ONLY": errors.append("P8 output authority drift")
        policy=self.data.get("policy",{})
        for key in ("baseline_artifacts_mutable","fabula_mutation_allowed","probe_rebinding_allowed","focalizer_rebinding_allowed","automatic_winner","automatic_route_elimination","automatic_literary_superiority_claim"):
            if policy.get(key) is not False: errors.append(f"P8 policy {key} must remain false")
        for key in ("evidence_effect","open_interface_effect","stable_active_effect","canonical_prose_effect","competition_effect"):
            if policy.get(key)!="NONE": errors.append(f"P8 authority effect {key} must remain NONE")
        if set(self.pairs)!=set(p6.drafts): errors.append("P8 pairs must cover exactly all P6 drafts")
        targets = set(unique_index(p7.data["revision_targets"]))
        unique_index(list(self.pairs.values()), "revised_token")
        if not targets:
            errors.append("revision requires declared review targets")
        for pair in self.pairs.values():
            if not set(pair["applied_targets"]) <= targets:
                errors.append(f"{pair['baseline_token']}: unknown revision target")
        if not set(self.data["strict_reduction_tokens"]) <= set(self.pairs):
            errors.append("strict reduction token missing revision pair")
        result=self.evaluate_all(p6,p7,discourse,stress,suite)
        if result["status"]!="PASS": errors.append(f"P8 ablation screen failed: {result}")
        if result["winner"] is not None or result["route_eliminated"]:
            errors.append("P8 may not select or eliminate a route")
        return errors
