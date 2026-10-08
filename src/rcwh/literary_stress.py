from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .contracts import unique_index
from .literary_ecology import LiteraryEcologyRuntime
from .pareto import ParetoEvaluationRuntime
from .scenario_replay import CounterfactualReplayRuntime
from .scenarios import ScenarioRuntime
from .hypotheses import HypothesisRuntime
from .world import WorldRuntime


@dataclass
class ScenarioLiteraryStressRuntime:
    data: dict[str, Any]
    contracts: dict[str, dict[str, Any]]
    dimensions: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "ScenarioLiteraryStressRuntime":
        data = load_data(root / "data" / "literary_stress" / "v010.json") or {}
        return cls(
            data=data,
            contracts=unique_index(data.get('contracts', []), 'scenario_id'),
            dimensions=unique_index(data.get('dimensions', []), 'id'),
        )

    def _coverage(self, contract: dict[str, Any]) -> dict[str, Any]:
        probes = contract["probes"]
        dim_hits = {dim_id: 0 for dim_id in self.dimensions}
        focalizers: set[str] = set()
        actions: set[str] = set()
        side: set[str] = set()
        objects: set[str] = set()
        endings: set[str] = set()
        techniques: set[str] = set()
        indirect = 0
        culture = 0
        withheld = 0
        for probe in probes:
            for dim_id in probe["stress_dimensions"]:
                dim_hits[dim_id] += 1
            focalizers.update(probe["focalizers"])
            actions.update(probe["ordinary_actions"])
            side.update(probe["side_characters"])
            objects.update(probe["object_carriers"])
            endings.add(probe["ending_vector"])
            techniques.update(probe["technique_refs"])
            if probe["event_visibility"] != "DIRECT_SCENE":
                indirect += 1
            if probe["culture_in_action"]:
                culture += 1
            if probe["withheld_information"]:
                withheld += 1
        return {
            "dimension_hits": dim_hits,
            "unique_focalizers": len(focalizers),
            "unique_ordinary_actions": len(actions),
            "unique_side_characters": len(side),
            "unique_object_carriers": len(objects),
            "unique_ending_vectors": len(endings),
            "unique_techniques": len(techniques),
            "indirect_or_partial_probes": indirect,
            "culture_action_probes": culture,
            "withheld_info_probes": withheld,
        }

    def _window_coverage(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        rows = []
        for window in self.data["required_windows"]:
            hits = [
                p["id"] for p in contract["probes"]
                if p["window"][0] <= window["start"] and p["window"][1] >= window["end"]
            ]
            rows.append({
                "window_id": window["id"],
                "range": [window["start"], window["end"]],
                "probe_ids": hits,
                "covered": bool(hits),
            })
        return rows

    def evaluate(
        self,
        scenario_id: str,
        ecology: LiteraryEcologyRuntime,
    ) -> dict[str, Any]:
        if scenario_id not in self.contracts:
            raise KeyError(f"Unknown literary stress scenario: {scenario_id}")
        contract = self.contracts[scenario_id]
        coverage = self._coverage(contract)
        thresholds = self.data["thresholds"]
        blockers: list[dict[str, Any]] = []
        watches: list[dict[str, Any]] = []

        windows = self._window_coverage(contract)
        for row in windows:
            if not row["covered"]:
                blockers.append({
                    "kind": "MISSING_WINDOW",
                    "window": row["window_id"],
                    "message": f"No stress probe covers {row['range']}",
                })

        for dim_id, count in coverage["dimension_hits"].items():
            if count < thresholds["dimensions_min_hits"]:
                blockers.append({
                    "kind": "DIMENSION_UNDERCOVERED",
                    "dimension": dim_id,
                    "count": count,
                    "required": thresholds["dimensions_min_hits"],
                })

        metric_map = {
            "unique_focalizers": "unique_focalizers_min",
            "unique_ordinary_actions": "unique_ordinary_actions_min",
            "unique_side_characters": "unique_side_characters_min",
            "unique_object_carriers": "unique_object_carriers_min",
            "unique_ending_vectors": "unique_ending_vectors_min",
            "unique_techniques": "unique_techniques_min",
            "indirect_or_partial_probes": "indirect_or_partial_probe_min",
            "culture_action_probes": "culture_action_probe_min",
            "withheld_info_probes": "withheld_info_probe_min",
        }
        for metric, threshold_key in metric_map.items():
            if coverage[metric] < thresholds[threshold_key]:
                blockers.append({
                    "kind": "DIVERSITY_OR_LIFE_DENSITY_GAP",
                    "metric": metric,
                    "value": coverage[metric],
                    "required": thresholds[threshold_key],
                })

        probe_ids = {p["id"] for p in contract["probes"]}
        for item in contract["watch_items"]:
            missing = [x for x in item["addressed_by"] if x not in probe_ids]
            if missing:
                blockers.append({
                    "kind": "UNADDRESSED_SCENARIO_RISK",
                    "watch_id": item["id"],
                    "missing_probe_ids": missing,
                })
            else:
                watches.append({
                    "watch_id": item["id"],
                    "risk": item["risk"],
                    "must_show": item["must_show"],
                    "status": "ADDRESSED_IN_STRESS_CONTRACT_NOT_PROVEN_IN_PROSE",
                })

        known_voices = set(ecology.voices)
        known_techniques = set(ecology.techniques)
        known_basis = set(ecology.dimensions) | set(ecology.techniques)
        for probe in contract["probes"]:
            unknown_voice = sorted(set(probe["focalizers"]) - known_voices)
            if unknown_voice:
                blockers.append({
                    "kind": "UNKNOWN_FOCALIZER_PROFILE",
                    "probe_id": probe["id"],
                    "unknown": unknown_voice,
                })
            unknown_tech = sorted(set(probe["technique_refs"]) - known_techniques)
            if unknown_tech:
                blockers.append({
                    "kind": "UNKNOWN_TECHNIQUE",
                    "probe_id": probe["id"],
                    "unknown": unknown_tech,
                })
        for dimension in self.dimensions.values():
            unknown_basis = sorted(set(dimension["basis_refs"]) - known_basis)
            if unknown_basis:
                blockers.append({
                    "kind": "UNKNOWN_LITERARY_BASIS",
                    "dimension": dimension["id"],
                    "unknown": unknown_basis,
                })

        status = "STRESS_CONTRACT_READY" if not blockers else "STRESS_CONTRACT_NEEDS_REDESIGN"
        return {
            "scenario_id": scenario_id,
            "title": contract["title"],
            "status": status,
            "coverage": coverage,
            "window_coverage": windows,
            "blockers": blockers,
            "watch_items": watches,
            "probe_count": len(contract["probes"]),
            "automatic_prose_generation": False,
            "automatic_literary_pass": False,
            "automatic_winner": False,
            "promotion_eligible": False,
            "authority": "LITERARY_STRESS_ONLY",
            "note": (
                "A READY result proves only that the scenario has a sufficiently diverse "
                "scene-level stress contract. It does not prove that generated prose is "
                "literarily adequate or closer to the lost manuscript."
            ),
        }

    def evaluate_all(
        self,
        ecology: LiteraryEcologyRuntime,
    ) -> dict[str, Any]:
        rows = [
            self.evaluate(sid, ecology)
            for sid in sorted(self.contracts)
        ]
        return {
            "status": (
                "PASS" if all(x["status"] == "STRESS_CONTRACT_READY" for x in rows)
                else "NEEDS_REDESIGN"
            ),
            "scenarios": [
                {
                    "scenario_id": x["scenario_id"],
                    "status": x["status"],
                    "probe_count": x["probe_count"],
                    "blocker_count": len(x["blockers"]),
                }
                for x in rows
            ],
            "winner": None,
            "automatic_literary_pass": False,
            "automatic_winner": False,
            "next_gate": "P5_NARRATIVE_DISCOURSE_RUNTIME",
        }

    def compare(
        self,
        left_id: str,
        right_id: str,
        ecology: LiteraryEcologyRuntime,
    ) -> dict[str, Any]:
        left = self.evaluate(left_id, ecology)
        right = self.evaluate(right_id, ecology)
        keys = [
            "dimension_hits",
            "unique_focalizers",
            "unique_ordinary_actions",
            "unique_side_characters",
            "unique_object_carriers",
            "unique_ending_vectors",
            "unique_techniques",
            "indirect_or_partial_probes",
            "culture_action_probes",
            "withheld_info_probes",
        ]
        return {
            "left": left_id,
            "right": right_id,
            "structural_differences": [
                {
                    "metric": key,
                    "left": left["coverage"][key],
                    "right": right["coverage"][key],
                }
                for key in keys
            ],
            "ranking": None,
            "winner": None,
            "note": "Comparison exposes stress-contract shape only; it is not a literary ranking.",
        }

    def validate_integrity(
        self,
        pareto: ParetoEvaluationRuntime,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        replay: CounterfactualReplayRuntime,
        world: WorldRuntime,
        ecology: LiteraryEcologyRuntime,
    ) -> list[str]:
        errors: list[str] = []
        if self.data.get("authority") != "SHADOW_ONLY":
            errors.append("Literary stress must remain SHADOW_ONLY")
        if self.data.get("output_authority") != "LITERARY_STRESS_ONLY":
            errors.append("Literary stress output authority drift")
        for field, value in self.data.get("effects", {}).items():
            if value != "NONE":
                errors.append(f"Literary stress effect {field} must remain NONE")
        policy = self.data.get("policy", {})
        for field in (
            "automatic_prose_generation",
            "automatic_literary_pass",
            "automatic_winner",
            "scalar_score",
        ):
            if policy.get(field) is not False:
                errors.append(f"Literary stress policy {field} must remain false")

        frontier = pareto.frontier(hypotheses, scenarios, replay, world)
        required = set(self.data["source_basis"]["required_scenarios"])
        if required != set(frontier["robust_frontier_intersection"]):
            errors.append(
                "P4 scenario set must equal P3 robust frontier intersection"
            )
        if set(self.contracts) != required:
            errors.append("P4 contracts must cover exactly the P3 robust frontier")

        result = self.evaluate_all(ecology)
        if result["status"] != "PASS":
            errors.append(f"P4 stress contract coverage not ready: {result}")
        if result["winner"] is not None:
            errors.append("P4 may not select a winner")
        return errors
