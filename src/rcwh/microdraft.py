from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
from .io import load_data
from .contracts import unique_index, record_sha256
from .literary_suite import LiteraryEvaluatorSuite
from .literary_stress import ScenarioLiteraryStressRuntime
from .narrative_discourse import NarrativeDiscourseRuntime

@dataclass
class ControlledMicrodraftRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "ControlledMicrodraftRuntime":
        return cls(root, load_data(root / "data" / "microdraft" / "v012.json") or {})

    @property
    def drafts(self) -> dict[str, dict[str, Any]]:
        return unique_index(self.data.get('drafts', []), 'token')

    def snapshot_sha256(self) -> str:
        """Bind draft identities, experimental controls, and original prose bytes."""
        return record_sha256({
            "record": self.data,
            "artifacts": {token: hashlib.sha256((self.root / spec["artifact"]).read_bytes()).hexdigest()
                          for token, spec in self.drafts.items()},
        })

    def require_snapshot(self, record_id: str, sha256: str) -> None:
        if record_id != self.data["id"] or sha256 != self.snapshot_sha256():
            raise ValueError("microdraft snapshot binding drift; review requires its original inputs")

    def text(self, token: str) -> str:
        if token not in self.drafts:
            raise KeyError(f"Unknown microdraft token: {token}")
        path = self.root / self.drafts[token]["artifact"]
        if not path.exists():
            raise FileNotFoundError(path)
        return path.read_text(encoding="utf-8").strip()

    def screen(self, token: str, discourse: NarrativeDiscourseRuntime, stress: ScenarioLiteraryStressRuntime, suite: LiteraryEvaluatorSuite) -> dict[str, Any]:
        spec=self.drafts[token]; text=self.text(token); card=discourse.card(spec["scenario_id"],spec["probe_id"],stress)
        blockers=[]; flags=[]; n=len(text)
        if not (self.data["thresholds"]["min_chars"] <= n <= self.data["thresholds"]["max_chars"]):
            blockers.append({"kind":"LENGTH_OUT_OF_RANGE","chars":n})
        anchor_hits=[x for x in spec["required_anchors"] if x in text]
        if len(anchor_hits) < self.data["thresholds"]["required_anchor_hits_min"]:
            blockers.append({"kind":"REQUIRED_ANCHOR_GAP","hits":anchor_hits,"required":self.data["thresholds"]["required_anchor_hits_min"]})
        forbidden_hits=[x for x in spec["forbidden_terms"] if x in text]
        if forbidden_hits: blockers.append({"kind":"DRAFT_SPEC_FORBIDDEN_TERM","hits":forbidden_hits})
        metadata_hits=[x for x in self.data["forbidden_metadata_terms"] if x in text]
        if metadata_hits: blockers.append({"kind":"BLIND_METADATA_CONTAMINATION","hits":metadata_hits})
        literary=suite.legacy_prose_screen(text,token)
        if literary["status"]=="REJECT_BEFORE_BLIND_READ":
            blockers.append({"kind":"LITERARY_SUITE_BLOCKER","blockers":literary["blockers"]})
        flags.extend(literary.get("human_flags",[]))
        if spec["primary_focalizer"] != card["sjuzet_plan"]["primary_focalizer"]:
            blockers.append({"kind":"FOCALIZER_BINDING_DRIFT","expected":card["sjuzet_plan"]["primary_focalizer"],"manifest":spec["primary_focalizer"]})
        return {"token":token,"cell_id":spec["cell_id"],"chars":n,"sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),"anchor_hits":anchor_hits,"blockers":blockers,"human_flags":sorted(set(flags)),"status":"READY_FOR_BLIND_MICRODRAFT_REVIEW" if not blockers else "BLOCKED","automatic_literary_pass":False,"automatic_winner":False,"canonical_effect":"NONE"}

    def blind_packet_violations(self, packet: dict[str, Any]) -> list[str]:
        forbidden=list(self.data["forbidden_metadata_terms"])+["scenario_id","probe_id","primary_focalizer","SCN-CURRENT-C","SCN-LATE-MARRIAGE","SCN-JADE-MULTILAYER","SCN-MINIMAL-CAUSE-OPEN"]
        raw=repr(packet)
        return [x for x in forbidden if x in raw]

    def cell_packet(self, cell_id: str) -> dict[str, Any]:
        specs=[x for x in self.data["drafts"] if x["cell_id"]==cell_id]
        if not specs: raise KeyError(f"Unknown microdraft cell: {cell_id}")
        candidates=[]
        for spec in sorted(specs,key=lambda x:x["token"]):
            text=self.text(spec["token"])
            candidates.append({"token":spec["token"],"artifact":spec["artifact"],"sha256":hashlib.sha256(text.encode("utf-8")).hexdigest()})
        packet={"kind":"P6_MICRODRAFT_BLIND_CELL","sealed":True,"cell_id":cell_id,"candidates":candidates,"questions":self.data["blind_review"]["questions"],"ranking_rule":"只按匿名token判断；不得猜测路线、假说或probe身份。"}
        leaks=self.blind_packet_violations(packet)
        if leaks: raise ValueError(f"Blind packet metadata leak: {leaks}")
        return packet

    def evaluate_all(self, discourse: NarrativeDiscourseRuntime, stress: ScenarioLiteraryStressRuntime, suite: LiteraryEvaluatorSuite) -> dict[str, Any]:
        rows=[self.screen(token,discourse,stress,suite) for token in sorted(self.drafts)]
        packets=[self.cell_packet(cell["id"]) for cell in self.data["design"]["cells"]]
        return {"status":"PASS" if all(x["status"]=="READY_FOR_BLIND_MICRODRAFT_REVIEW" for x in rows) else "BLOCKED","draft_count":len(rows),"ready_count":sum(x["status"]=="READY_FOR_BLIND_MICRODRAFT_REVIEW" for x in rows),"blocker_count":sum(len(x["blockers"]) for x in rows),"human_flag_count":sum(len(x["human_flags"]) for x in rows),"cells":[{"cell_id":p["cell_id"],"candidate_count":len(p["candidates"])} for p in packets],"winner":None,"automatic_literary_pass":False,"automatic_winner":False,"independent_human_review_required":True,"next_gate":"P7_BLIND_MICRODRAFT_REVIEW"}

    def validate_integrity(self, discourse: NarrativeDiscourseRuntime, stress: ScenarioLiteraryStressRuntime, suite: LiteraryEvaluatorSuite) -> list[str]:
        errors=[]
        if self.data.get("authority")!="SHADOW_ONLY": errors.append("Microdraft lab must remain SHADOW_ONLY")
        if self.data.get("output_authority")!="EXPERIMENTAL_PROSE_ONLY": errors.append("Microdraft output authority drift")
        policy=self.data.get("policy",{})
        for key in ("canonical_prose_effect","evidence_effect","open_interface_effect","stable_active_effect","competition_effect"):
            if policy.get(key)!="NONE": errors.append(f"P6 authority effect {key} must remain NONE")
        for key in ("automatic_literary_pass","automatic_winner","route_elimination_by_machine"):
            if policy.get(key) is not False: errors.append(f"P6 policy {key} must remain false")
        required=set(self.data["source_basis"]["required_scenarios"])
        if required != set(stress.contracts): errors.append("P6 scenarios must equal P4/P5 frontier scenarios")
        cards={(sid,p["id"]) for sid,contract in stress.contracts.items() for p in contract["probes"]}
        draft_cards=[(x["scenario_id"],x["probe_id"]) for x in self.data["drafts"]]
        if len(draft_cards) != len(set(draft_cards)) or set(draft_cards) != cards:
            errors.append("P6 must provide one unique microdraft for every upstream card")
        cells = unique_index(self.data["design"]["cells"])
        actual_cells = {(x["scenario_id"], x["cell_id"]) for x in self.data["drafts"]}
        expected_cells = {(sid, cell) for sid in required for cell in cells}
        if actual_cells != expected_cells or len(actual_cells) != len(self.data["drafts"]):
            errors.append("microdraft design cells must have one variant per required scenario")
        result=self.evaluate_all(discourse,stress,suite)
        if result["status"]!="PASS": errors.append(f"P6 microdraft screen failed: {result}")
        if result["winner"] is not None: errors.append("P6 may not select a winner")
        return errors
