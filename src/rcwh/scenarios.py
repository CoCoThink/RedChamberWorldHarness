from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hypotheses import HypothesisRuntime
from .io import load_data
from .open_interfaces import OpenInterfaceRegistry


@dataclass
class ScenarioRuntime:
    scenarios: dict[str, dict[str, Any]]
    compatibility: dict[str, Any]
    replay_available: bool = False

    @classmethod
    def from_repo(cls, root: Path) -> "ScenarioRuntime":
        scenarios: dict[str, dict[str, Any]] = {}
        path = root / "data" / "research"
        if path.exists():
            for file in sorted(path.glob("scenarios.json")):
                doc = load_data(file) or {}
                for item in doc.get("scenarios", []):
                    item_id = item["id"]
                    if item_id in scenarios:
                        raise ValueError(f"Duplicate scenario id: {item_id}")
                    scenarios[item_id] = item
        cpath = root / "data" / "research" / "hypothesis_compatibility.json"
        compatibility = load_data(cpath) if cpath.exists() else {}
        return cls(
            scenarios=scenarios,
            compatibility=compatibility,
            replay_available=(root / "data" / "research" / "scenario_replay.json").exists(),
        )

    def validate_bundle(
        self,
        scenario: dict[str, Any],
        hypotheses: HypothesisRuntime,
        open_interfaces: OpenInterfaceRegistry,
    ) -> list[str]:
        errors: list[str] = []
        sid = scenario.get("id", "<unknown>")
        if scenario.get("authority") != "SCENARIO_ONLY":
            errors.append(f"{sid}: authority must be SCENARIO_ONLY")
        if scenario.get("evidence_effect") != "NONE":
            errors.append(f"{sid}: evidence_effect must be NONE")
        if scenario.get("stable_active_effect") != "NONE":
            errors.append(f"{sid}: stable_active_effect must be NONE")
        if scenario.get("open_interfaces", {}).get("policy") != "PRESERVE_OPEN":
            errors.append(f"{sid}: OPEN policy must be PRESERVE_OPEN")
        if scenario.get("open_interfaces", {}).get("closed_by_scenario"):
            errors.append(f"{sid}: scenario may not close OPEN interfaces")

        refs = scenario.get("hypotheses", [])
        unknown = [x for x in refs if x not in hypotheses.hypotheses]
        if unknown:
            errors.append(f"{sid}: unknown hypotheses {unknown}")
            return errors

        seen_questions: dict[str, str] = {}
        for hid in refs:
            item = hypotheses.hypotheses[hid]
            qref = item["question_ref"]
            if qref in seen_questions:
                errors.append(
                    f"{sid}: multiple hypotheses for {qref}: "
                    f"{seen_questions[qref]}, {hid}"
                )
            else:
                seen_questions[qref] = hid
            interface = open_interfaces.interfaces.get(qref)
            if interface is None or interface.get("state") != "OPEN_LOCKED":
                errors.append(f"{sid}: hypothesis {hid} does not preserve OPEN {qref}")

        present = set(refs)
        for group in self.compatibility.get("mutually_exclusive_groups", []):
            overlap = sorted(present.intersection(group))
            if len(overlap) > 1:
                errors.append(f"{sid}: mutually exclusive hypotheses co-occur {overlap}")

        policy = scenario.get("search_policy", {})
        if policy.get("evidence_bonus") != "NONE":
            errors.append(f"{sid}: evidence bonus forbidden")
        if policy.get("baseline_convenience_bonus") != "NONE":
            errors.append(f"{sid}: baseline convenience bonus forbidden")
        if scenario.get("current_c_relation") == "CURRENT_C_REFERENCE":
            if policy.get("search_priority") != "NONE":
                errors.append(f"{sid}: current-C may not receive search priority")
        return errors

    def validate_integrity(
        self,
        hypotheses: HypothesisRuntime,
        open_interfaces: OpenInterfaceRegistry,
    ) -> list[str]:
        errors: list[str] = []
        if self.compatibility:
            if self.compatibility.get("authority") != "SHADOW_ONLY":
                errors.append("compatibility graph must remain SHADOW_ONLY")
            if self.compatibility.get("evidence_effect") != "NONE":
                errors.append("compatibility graph may not affect Evidence")
            if self.compatibility.get("stable_active_effect") != "NONE":
                errors.append("compatibility graph may not affect stable ACTIVE")
        for scenario in self.scenarios.values():
            errors.extend(self.validate_bundle(scenario, hypotheses, open_interfaces))
        current = [
            x for x in self.scenarios.values()
            if x.get("current_c_relation") == "CURRENT_C_REFERENCE"
        ]
        if len(current) != 1:
            errors.append("exactly one scenario must be CURRENT_C_REFERENCE")
        admissible = [x for x in self.scenarios.values() if x.get("status") == "ADMISSIBLE"]
        if not admissible:
            errors.append("scenario search requires a nonempty admissible set")
        return errors

    def summary(self, hypotheses: HypothesisRuntime) -> dict[str, Any]:
        coverage = hypotheses.alternative_coverage()
        return {
            "status": "SHADOW_ONLY",
            "scenarios": len(self.scenarios),
            "admissible": sum(x.get("status") == "ADMISSIBLE" for x in self.scenarios.values()),
            "core_open_with_two_or_more_alternatives": len(
                [x for x in coverage.values() if x >= 2]
            ),
            "current_c_reference": next(
                (x["id"] for x in self.scenarios.values()
                 if x.get("current_c_relation") == "CURRENT_C_REFERENCE"),
                None,
            ),
            "automatic_winner": False,
            "world_replay": "AVAILABLE_V08" if self.replay_available else "PENDING_P2",
        }

    def get(self, scenario_id: str) -> dict[str, Any]:
        if scenario_id not in self.scenarios:
            raise KeyError(f"Unknown scenario: {scenario_id}")
        return self.scenarios[scenario_id]

    def generate(self) -> dict[str, Any]:
        return {
            "mode": "CURATED_SEED_BUNDLES",
            "automatic_plot_invention": False,
            "scenario_ids": sorted(self.scenarios),
            "count": len(self.scenarios),
        }

    def compare(self, scenario_ids: list[str], hypotheses: HypothesisRuntime) -> dict[str, Any]:
        selected = [self.get(x) for x in scenario_ids]
        all_h = set().union(*(set(x["hypotheses"]) for x in selected))
        rows = []
        for hid in sorted(all_h):
            rows.append({
                "hypothesis_id": hid,
                "title": hypotheses.hypotheses[hid]["title"],
                "present_in": [x["id"] for x in selected if hid in x["hypotheses"]],
            })
        return {
            "scenarios": scenario_ids,
            "differences": rows,
            "ranking": None,
            "note": "P1 comparison is structural only; Pareto axes remain UNASSESSED until later gates.",
        }

    def frontier(self) -> dict[str, Any]:
        return {
            "status": (
                "REPLAY_AVAILABLE_NOT_RANKED"
                if self.replay_available
                else "NOT_RANKED_BEFORE_P2_REPLAY"
            ),
            "scenario_ids": sorted(
                x["id"] for x in self.scenarios.values()
                if x.get("status") == "ADMISSIBLE"
            ),
            "single_total_score": False,
        }
