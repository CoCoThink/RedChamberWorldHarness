from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections import Counter
from .io import load_data
from .microdraft import ControlledMicrodraftRuntime

@dataclass
class BlindMicrodraftReviewRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "BlindMicrodraftReviewRuntime":
        return cls(root, load_data(root / "data" / "blind_review" / "v013.json") or {})

    def mapping(self) -> dict[str, Any]:
        return load_data(self.root / self.data["source_basis"]["sealed_mapping_path"]) or {}

    def raw_review(self) -> str:
        return (self.root / self.data["source_basis"]["raw_review_path"]).read_text(encoding="utf-8")

    def token(self, token: str) -> dict[str, Any]:
        row=next((x for x in self.data["reviews"] if x["token"]==token),None)
        if row is None: raise KeyError(f"Unknown P7 token: {token}")
        mapped=self.mapping()[token]
        return {**row,"scenario_id":mapped["scenario_id"],"probe_id":mapped["probe_id"]}

    def scenario(self, scenario_id: str) -> dict[str, Any]:
        if scenario_id not in self.data["scenario_summary"]:
            raise KeyError(f"Unknown P7 scenario: {scenario_id}")
        rows=[self.token(x["token"]) for x in self.data["reviews"] if self.mapping()[x["token"]]["scenario_id"]==scenario_id]
        rows.sort(key=lambda x:x["cell_id"])
        return {"scenario_id":scenario_id,"summary":self.data["scenario_summary"][scenario_id],"cells":rows,"winner":None,"route_eliminated":False}

    def summary(self) -> dict[str, Any]:
        return {
          "milestone":"P7",
          "status":self.data["status"],
          "review_count":len(self.data["reviews"]),
          "cell_count":len(self.data["cell_rankings"]),
          "scenario_summary":self.data["scenario_summary"],
          "revision_targets":self.data["revision_targets"],
          "winner":None,
          "route_eliminated":False,
          "next_gate":self.data["next_gate"],
        }

    def validate_integrity(self, lab: ControlledMicrodraftRuntime) -> list[str]:
        errors=[]
        if self.data.get("milestone")!="P7": errors.append("Blind review milestone must be P7")
        if self.data.get("authority")!="SHADOW_ONLY": errors.append("P7 must remain SHADOW_ONLY")
        if self.data.get("output_authority")!="BLIND_REVIEW_SIGNAL_ONLY": errors.append("P7 output authority drift")
        if not self.data.get("source_basis",{}).get("mapping_unsealed_after_review"):
            errors.append("P7 mapping may only be unsealed after blind review")
        policy=self.data.get("policy",{})
        for key in ("evidence_effect","open_interface_effect","stable_active_effect","canonical_prose_effect","chapter89_competition_effect"):
            if policy.get(key)!="NONE": errors.append(f"P7 authority effect {key} must remain NONE")
        for key in ("automatic_winner","automatic_route_elimination"):
            if policy.get(key) is not False: errors.append(f"P7 policy {key} must remain false")

        review_tokens={x["token"] for x in self.data.get("reviews",[])}
        if review_tokens != set(lab.drafts): errors.append("P7 review tokens must exactly match P6 drafts")
        if len(review_tokens)!=20: errors.append(f"P7 requires 20 reviewed tokens; got {len(review_tokens)}")

        mapping=self.mapping()
        if set(mapping)!=review_tokens: errors.append("P7 unsealed mapping must exactly match reviewed tokens")
        for cid, ranking in self.data["cell_rankings"].items():
            if len(ranking)!=4 or len(set(ranking))!=4: errors.append(f"{cid}: invalid ranking")
            expected={x["token"] for x in self.data["reviews"] if x["cell_id"]==cid}
            if set(ranking)!=expected: errors.append(f"{cid}: ranking tokens do not match reviews")
            for i,token in enumerate(ranking,1):
                row=next(x for x in self.data["reviews"] if x["token"]==token)
                if row["rank"]!=i: errors.append(f"{token}: rank mismatch")
                if row["top2"] != (i<=2): errors.append(f"{token}: top2 mismatch")

        derived={}
        for scenario_id in self.data["scenario_summary"]:
            rows=[x for x in self.data["reviews"] if mapping[x["token"]]["scenario_id"]==scenario_id]
            rank_sum=sum(x["rank"] for x in rows)
            first=sum(x["rank"]==1 for x in rows)
            top2=sum(x["rank"]<=2 for x in rows)
            if rank_sum!=self.data["scenario_summary"][scenario_id]["rank_sum"]:
                errors.append(f"{scenario_id}: rank_sum mismatch")
            if first!=self.data["scenario_summary"][scenario_id]["first_place_count"]:
                errors.append(f"{scenario_id}: first_place_count mismatch")
            if top2!=self.data["scenario_summary"][scenario_id]["top2_count"]:
                errors.append(f"{scenario_id}: top2_count mismatch")

        raw=self.raw_review()
        for token in review_tokens:
            if token not in raw: errors.append(f"Raw review missing token {token}")
        if "各 cell 排序汇总" not in raw or "跨 cell 总体观察" not in raw:
            errors.append("Raw review missing required summary sections")
        return errors
