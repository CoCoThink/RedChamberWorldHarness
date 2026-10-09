from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hypotheses import HypothesisRuntime
from .io import load_data
from .contracts import unique_index
from .scenario_replay import CounterfactualReplayRuntime
from .scenarios import ScenarioRuntime
from .world import WorldRuntime


@dataclass
class ParetoEvaluationRuntime:
    root: Path
    data: dict[str, Any]
    burdens: dict[str, dict[str, Any]]
    expert_axes: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ParetoEvaluationRuntime":
        data = load_data(root / "data" / "research" / "pareto.json") or {}
        return cls(
            root=root,
            data=data,
            burdens=unique_index(data.get('hypothesis_burdens', []), 'hypothesis_id'),
            expert_axes=unique_index(data.get('scenario_expert_axes', []), 'scenario_id'),
        )

    def _historical_cost(
        self,
        scenario: dict[str, Any],
        hypotheses: HypothesisRuntime,
    ) -> tuple[int, list[dict[str, Any]]]:
        mapping = self.data["historical_cost_mapping"]
        total = 0
        detail = []
        for hid in scenario["hypotheses"]:
            cost = hypotheses.hypotheses[hid]["historical_cost"]
            value = mapping[cost]
            total += value
            if value:
                detail.append({"hypothesis_id": hid, "cost": cost, "burden": value})
        return total, detail

    def evaluate_scenario(
        self,
        scenario_id: str,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        scenario = scenarios.get(scenario_id)
        p2 = replay.evaluate(scenario_id, scenarios, world)
        if p2["blockers"]:
            return {
                "scenario_id": scenario_id,
                "status": "PARETO_INELIGIBLE_P2_BLOCKER",
                "blockers": p2["blockers"],
                "vector": None,
                "authority": "SHADOW_ONLY",
            }

        evidence_distance = 0
        open_consumption = 0
        chapter_economy = 0
        evidence_detail = []
        open_detail = []
        chapter_detail = []
        for hid in scenario["hypotheses"]:
            item = self.burdens[hid]
            evidence_distance += item["evidence_distance"]
            open_consumption += item["open_consumption"]
            chapter_economy += item["chapter_economy"]
            if item["evidence_distance"]:
                evidence_detail.append({
                    "hypothesis_id": hid,
                    "burden": item["evidence_distance"],
                    "reason": item["rationale"]["evidence_fit"],
                })
            if item["open_consumption"]:
                open_detail.append({
                    "hypothesis_id": hid,
                    "burden": item["open_consumption"],
                    "reason": item["rationale"]["open_consumption"],
                })
            if item["chapter_economy"]:
                chapter_detail.append({
                    "hypothesis_id": hid,
                    "burden": item["chapter_economy"],
                    "reason": item["rationale"]["chapter_economy"],
                })

        historical_cost, historical_detail = self._historical_cost(scenario, hypotheses)
        pressure_kinds = [x["kind"] for x in p2["pressures"]]
        world_kinds = set(self.data["world_pressure_kinds"])
        world_pressures = [x for x in p2["pressures"] if x["kind"] in world_kinds]

        expert = self.expert_axes[scenario_id]
        vector = {
            "evidence_fit": evidence_distance,
            "contradiction_risk": len(p2["pressures"]),
            "open_consumption": open_consumption,
            "historical_cost": historical_cost,
            "world_coherence": len(world_pressures),
            "chapter_economy": chapter_economy,
            "front80_structural_echo": expert["front80_structural_echo"],
            "literary_fertility": expert["literary_fertility"],
        }
        return {
            "scenario_id": scenario_id,
            "title": scenario["title"],
            "status": "PARETO_ELIGIBLE",
            "vector": vector,
            "directions": {k: self.data["axes"][k]["direction"] for k in self.data["full_axes"]},
            "details": {
                "evidence_fit": evidence_detail,
                "contradiction_risk": {
                    "pressure_count": len(p2["pressures"]),
                    "pressure_kinds": pressure_kinds,
                },
                "open_consumption": open_detail,
                "historical_cost": historical_detail,
                "world_coherence": {
                    "pressure_count": len(world_pressures),
                    "pressure_kinds": [x["kind"] for x in world_pressures],
                },
                "chapter_economy": chapter_detail,
                "front80_structural_echo": {
                    "grade": expert["front80_structural_echo"],
                    "rationale": expert["rationale"],
                    "basis_refs": expert["basis_refs"],
                    "authority": "HEURISTIC_NOT_EVIDENCE",
                },
                "literary_fertility": {
                    "grade": expert["literary_fertility"],
                    "rationale": expert["rationale"],
                    "basis_refs": expert["basis_refs"],
                    "authority": "HEURISTIC_NOT_EVIDENCE",
                },
            },
            "authority": "SHADOW_ONLY",
            "evidence_effect": "NONE",
            "open_interface_effect": "NONE",
            "stable_active_effect": "NONE",
            "automatic_winner": False,
            "single_total_score": False,
        }

    def _dominates(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        axes: list[str],
    ) -> bool:
        better_or_equal = True
        strictly_better = False
        for axis in axes:
            direction = self.data["axes"][axis]["direction"]
            lv = left["vector"][axis]
            rv = right["vector"][axis]
            if direction == "MINIMIZE":
                if lv > rv:
                    better_or_equal = False
                if lv < rv:
                    strictly_better = True
            else:
                if lv < rv:
                    better_or_equal = False
                if lv > rv:
                    strictly_better = True
        return better_or_equal and strictly_better

    def _evaluated(
        self,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
    ) -> dict[str, dict[str, Any]]:
        return {
            sid: self.evaluate_scenario(sid, hypotheses, scenarios, replay, world)
            for sid in sorted(scenarios.scenarios)
        }

    def _frontier_for(
        self,
        evaluated: dict[str, dict[str, Any]],
        axes: list[str],
    ) -> tuple[list[str], dict[str, list[str]]]:
        eligible = {k: v for k, v in evaluated.items() if v["status"] == "PARETO_ELIGIBLE"}
        dominated_by: dict[str, list[str]] = {sid: [] for sid in eligible}
        for right_id, right in eligible.items():
            for left_id, left in eligible.items():
                if left_id == right_id:
                    continue
                if self._dominates(left, right, axes):
                    dominated_by[right_id].append(left_id)
        frontier = sorted(sid for sid, dominators in dominated_by.items() if not dominators)
        for sid in dominated_by:
            dominated_by[sid].sort()
        return frontier, dominated_by

    def _tiers_for(
        self,
        evaluated: dict[str, dict[str, Any]],
        axes: list[str],
    ) -> list[list[str]]:
        remaining = {
            k: v for k, v in evaluated.items()
            if v["status"] == "PARETO_ELIGIBLE"
        }
        tiers: list[list[str]] = []
        while remaining:
            frontier, _ = self._frontier_for(remaining, axes)
            if not frontier:
                raise ValueError("Pareto tier construction stalled")
            tiers.append(frontier)
            for sid in frontier:
                remaining.pop(sid)
        return tiers

    def frontier(
        self,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        evaluated = self._evaluated(hypotheses, scenarios, replay, world)
        mechanism_frontier, mechanism_dominated = self._frontier_for(
            evaluated, self.data["mechanism_axes"]
        )
        full_frontier, full_dominated = self._frontier_for(
            evaluated, self.data["full_axes"]
        )
        return {
            "status": "PARETO_COMPLETE_NO_WINNER",
            "mechanism_frontier": mechanism_frontier,
            "full_frontier": full_frontier,
            "robust_frontier_intersection": sorted(
                set(mechanism_frontier).intersection(full_frontier)
            ),
            "mechanism_dominated_by": mechanism_dominated,
            "full_dominated_by": full_dominated,
            "full_tiers": self._tiers_for(evaluated, self.data["full_axes"]),
            "vectors": {sid: item["vector"] for sid, item in evaluated.items()},
            "axis_directions": {
                k: self.data["axes"][k]["direction"]
                for k in self.data["full_axes"]
            },
            "winner": None,
            "automatic_winner": False,
            "single_total_score": False,
            "authority": "SHADOW_ONLY",
            "next_gate": "P4_SCENARIO_LITERARY_STRESS_TEST",
        }

    def compare(
        self,
        left_id: str,
        right_id: str,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        left = self.evaluate_scenario(left_id, hypotheses, scenarios, replay, world)
        right = self.evaluate_scenario(right_id, hypotheses, scenarios, replay, world)
        rows = []
        for axis in self.data["full_axes"]:
            direction = self.data["axes"][axis]["direction"]
            lv = left["vector"][axis]
            rv = right["vector"][axis]
            if lv == rv:
                relation = "TIE"
            elif direction == "MINIMIZE":
                relation = "LEFT_BETTER" if lv < rv else "RIGHT_BETTER"
            else:
                relation = "LEFT_BETTER" if lv > rv else "RIGHT_BETTER"
            rows.append({
                "axis": axis,
                "direction": direction,
                "left": lv,
                "right": rv,
                "relation": relation,
            })
        return {
            "left": left_id,
            "right": right_id,
            "axes": rows,
            "left_dominates_right": self._dominates(left, right, self.data["full_axes"]),
            "right_dominates_left": self._dominates(right, left, self.data["full_axes"]),
            "winner": None,
            "single_total_score": False,
        }

    def summary(
        self,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        frontier = self.frontier(hypotheses, scenarios, replay, world)
        return {
            "authority": self.data["authority"],
            "axes": self.data["full_axes"],
            "scenario_count": len(scenarios.scenarios),
            "mechanism_frontier": frontier["mechanism_frontier"],
            "full_frontier": frontier["full_frontier"],
            "robust_frontier_intersection": frontier["robust_frontier_intersection"],
            "automatic_winner": False,
            "single_total_score": False,
            "next_gate": frontier["next_gate"],
        }

    def validate_integrity(
        self,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
    ) -> list[str]:
        errors: list[str] = []
        if self.data.get("authority") != "SHADOW_ONLY":
            errors.append("Pareto runtime must remain SHADOW_ONLY")
        if self.data.get("pareto_policy", {}).get("no_total_score") is not True:
            errors.append("Pareto runtime must forbid total score")
        if self.data.get("pareto_policy", {}).get("no_automatic_winner") is not True:
            errors.append("Pareto runtime must forbid automatic winner")
        axes = set(self.data.get("axes", {}))
        full = self.data.get("full_axes", [])
        mechanism = self.data.get("mechanism_axes", [])
        if not full or len(full) != len(set(full)) or not set(full) <= axes:
            errors.append("full Pareto axes must be nonempty, unique and declared")
        if not mechanism or len(mechanism) != len(set(mechanism)) or not set(mechanism) <= set(full):
            errors.append("mechanism axes must be nonempty, unique and included in full axes")
        for field, value in self.data.get("effects", {}).items():
            if value != "NONE":
                errors.append(f"Pareto effect {field} must remain NONE")

        used_hypotheses = set()
        for scenario in scenarios.scenarios.values():
            used_hypotheses.update(scenario["hypotheses"])
        missing = sorted(used_hypotheses.difference(self.burdens))
        if missing:
            errors.append(f"Missing Pareto hypothesis burdens: {missing}")
        missing_scenarios = sorted(set(scenarios.scenarios).difference(self.expert_axes))
        if missing_scenarios:
            errors.append(f"Missing Pareto expert axes: {missing_scenarios}")

        from .literary_ecology import LiteraryEcologyRuntime
        known_dimensions = set(LiteraryEcologyRuntime.from_repo(self.root).dimensions)
        for sid, item in self.expert_axes.items():
            if not (1 <= item["front80_structural_echo"] <= 5):
                errors.append(f"{sid}: front80 expert grade out of range")
            if not (1 <= item["literary_fertility"] <= 5):
                errors.append(f"{sid}: literary fertility grade out of range")
            unknown = sorted(set(item["basis_refs"]).difference(known_dimensions))
            if unknown:
                errors.append(f"{sid}: unknown literary-ecology basis refs {unknown}")

        p2 = replay.evaluate_all(scenarios, world)
        if p2["status"] != "PASS":
            errors.append("P3 requires P2 replay PASS")
        frontier = self.frontier(hypotheses, scenarios, replay, world)
        if not frontier["full_frontier"]:
            errors.append("P3 full frontier may not be empty")
        if frontier["winner"] is not None:
            errors.append("P3 may not select a winner")
        if frontier["single_total_score"] is not False:
            errors.append("P3 may not expose a single total score")
        return errors
