from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
from .io import load_data
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
        return cls(root, load_data(root / "data" / "revision_ablation" / "v014.json") or {})

    @property
    def pairs(self) -> dict[str, dict[str, Any]]:
        return {x["baseline_token"]: x for x in self.data.get("pairs", [])}

    def _text(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8").strip()

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
        spec=self.pairs[baseline_token]
        baseline=self._text(spec["baseline_artifact"])
        revised=self._text(spec["revised_artifact"])
        base_spec=p6.drafts[baseline_token]
        blockers=[]
        if (base_spec["scenario_id"],base_spec["probe_id"],base_spec["cell_id"]) != (spec["scenario_id"],spec["probe_id"],spec["cell_id"]):
            blockers.append({"kind":"PAIR_BINDING_DRIFT"})
        card=discourse.card(spec["scenario_id"],spec["probe_id"],stress)
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

        literary=suite.evaluate_prose(revised,spec["revised_token"])
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
          "scenario_id":spec["scenario_id"],"probe_id":spec["probe_id"],"cell_id":spec["cell_id"],
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
          "milestone":"P8",
          "status":"PASS" if all(x["status"]=="ABLATION_READY" for x in rows) else "BLOCKED",
          "pair_count":len(rows),
          "ready_count":sum(x["status"]=="ABLATION_READY" for x in rows),
          "blocker_count":sum(len(x["blockers"]) for x in rows),
          "anti_pattern_total_before":before,
          "anti_pattern_total_after":after,
          "anti_pattern_delta":after-before,
          "strict_reduction_tokens":self.data["strict_reduction_tokens"],
          "winner":None,"route_eliminated":False,"literary_superiority_claim":None,
          "next_gate":"P9_PAIRED_BLIND_REVISION_REVIEW"
        }

    def validate_integrity(self,p6,p7,discourse,stress,suite) -> list[str]:
        errors=[]
        if self.data.get("milestone")!="P8": errors.append("P8 milestone mismatch")
        if self.data.get("authority")!="SHADOW_ONLY": errors.append("P8 must remain SHADOW_ONLY")
        if self.data.get("output_authority")!="EXPERIMENTAL_REVISION_ONLY": errors.append("P8 output authority drift")
        policy=self.data.get("policy",{})
        for key in ("baseline_artifacts_mutable","fabula_mutation_allowed","probe_rebinding_allowed","focalizer_rebinding_allowed","automatic_winner","automatic_route_elimination","automatic_literary_superiority_claim"):
            if policy.get(key) is not False: errors.append(f"P8 policy {key} must remain false")
        for key in ("evidence_effect","open_interface_effect","stable_active_effect","canonical_prose_effect","chapter89_competition_effect"):
            if policy.get(key)!="NONE": errors.append(f"P8 authority effect {key} must remain NONE")
        if set(self.pairs)!=set(p6.drafts): errors.append("P8 pairs must cover exactly all P6 drafts")
        if len(self.pairs)!=20: errors.append(f"P8 requires 20 pairs; got {len(self.pairs)}")
        if {x["id"] for x in p7.data["revision_targets"]} != {f"RT-{i:02d}" for i in range(1,10)}:
            errors.append("P8 expects the complete P7 RT-01..RT-09 revision target set")
        result=self.evaluate_all(p6,p7,discourse,stress,suite)
        if result["status"]!="PASS": errors.append(f"P8 ablation screen failed: {result}")
        if result["winner"] is not None or result["route_eliminated"]:
            errors.append("P8 may not select or eliminate a route")
        return errors
