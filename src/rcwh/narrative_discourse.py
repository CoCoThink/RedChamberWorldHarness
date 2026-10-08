from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .literary_ecology import LiteraryEcologyRuntime
from .literary_stress import ScenarioLiteraryStressRuntime


@dataclass
class NarrativeDiscourseRuntime:
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "NarrativeDiscourseRuntime":
        return cls(load_data(root / "data" / "narrative_discourse" / "v011.json") or {})

    def _channels(self, probe: dict[str, Any], template: dict[str, Any], ending: dict[str, Any]) -> list[str]:
        channels = [template["primary_channel"]]
        if probe["ordinary_actions"]:
            channels.append(self.data["channel_rules"]["ordinary_actions_add"])
        if len(probe["focalizers"]) > 1:
            channels.append(self.data["channel_rules"]["multiple_focalizers_add"])
        if probe["culture_in_action"]:
            channels.append(self.data["channel_rules"]["culture_in_action_add"])
        if probe["object_carriers"]:
            channels.append(self.data["channel_rules"]["object_carriers_add"])
        if probe["event_visibility"] == "REPORTED":
            channels.append(self.data["channel_rules"]["reported_visibility_add"])
        if probe["ending_vector"] == "SOUND":
            channels.append(self.data["channel_rules"]["sound_ending_add"])
        if probe["ending_vector"] == "EMPTY_SPACE":
            channels.append(self.data["channel_rules"]["empty_space_ending_add"])
        channels.append(ending["exit_channel"])
        return list(dict.fromkeys(channels))

    def card(self, scenario_id: str, probe_id: str, stress: ScenarioLiteraryStressRuntime) -> dict[str, Any]:
        if scenario_id not in stress.contracts:
            raise KeyError(f"Unknown P4 scenario: {scenario_id}")
        contract = stress.contracts[scenario_id]
        try:
            probe = next(x for x in contract["probes"] if x["id"] == probe_id)
        except StopIteration as exc:
            raise KeyError(f"Unknown P4 probe {probe_id} for {scenario_id}") from exc

        template = dict(self.data["visibility_templates"][probe["event_visibility"]])
        ending = self.data["ending_templates"][probe["ending_vector"]]
        override = (
            self.data.get("scenario_overrides", {})
            .get(scenario_id, {})
            .get("probe_overrides", {})
            .get(probe_id, {})
        )
        template.update({
            k: v
            for k, v in override.items()
            if k in {"primary_channel", "reveal_policy", "opening_mode", "distance_curve"}
        })

        focalizers = list(probe["focalizers"])
        primary_focalizer = override.get("primary_focalizer", focalizers[0])
        if primary_focalizer not in focalizers:
            raise ValueError(
                f"{scenario_id}/{probe_id}: primary focalizer {primary_focalizer} "
                "must come from the P4 focalizer set"
            )
        secondary_focalizers = [x for x in focalizers if x != primary_focalizer]
        channels = self._channels(probe, template, ending)
        if override.get("primary_channel") and override["primary_channel"] not in channels:
            channels.insert(0, override["primary_channel"])

        return {
            "scenario_id": scenario_id,
            "probe_id": probe_id,
            "window": probe["window"],
            "label": probe["label"],
            "fabula_passthrough": {
                "ordinary_actions": list(probe["ordinary_actions"]),
                "side_characters": list(probe["side_characters"]),
                "object_carriers": list(probe["object_carriers"]),
                "culture_in_action": list(probe["culture_in_action"]),
                "withheld_information": list(probe["withheld_information"]),
                "event_visibility": probe["event_visibility"],
                "ending_vector": probe["ending_vector"],
            },
            "sjuzet_plan": {
                "primary_focalizer": primary_focalizer,
                "secondary_focalizers": secondary_focalizers,
                "opening_mode": template["opening_mode"],
                "temporal_order": template["temporal_order"],
                "event_presence": template["event_presence"],
                "primary_channel": template["primary_channel"],
                "relay_channels": channels,
                "distance_curve": template["distance_curve"],
                "reveal_policy": template["reveal_policy"],
                "narrator_access": template["narrator_access"],
                "direct_event_replay": template["direct_event_replay"],
                "exit_channel": ending["exit_channel"],
                "closure_mode": ending["closure_mode"],
                "resolved_withheld_information": [],
                "theme_statement_allowed": False,
                "narrator_motive_explanation_allowed": False,
                "institutional_exposition_allowed": False,
                "extra_restraints": list(override.get("extra_restraints", [])),
                "anti_exposition_rule": probe["anti_exposition_rule"],
            },
            "authority": "DISCOURSE_PLANNING_ONLY",
            "fabula_mutation": "NONE",
            "prose_generated": False,
        }

    def scenario(self, scenario_id: str, stress: ScenarioLiteraryStressRuntime) -> dict[str, Any]:
        if scenario_id not in stress.contracts:
            raise KeyError(f"Unknown P4 scenario: {scenario_id}")
        cards = [self.card(scenario_id, p["id"], stress) for p in stress.contracts[scenario_id]["probes"]]
        temporal = {x["sjuzet_plan"]["temporal_order"] for x in cards}
        relay = {c for x in cards for c in x["sjuzet_plan"]["relay_channels"]}
        openings = {x["sjuzet_plan"]["opening_mode"] for x in cards}
        curves = {tuple(x["sjuzet_plan"]["distance_curve"]) for x in cards}
        exits = {x["sjuzet_plan"]["exit_channel"] for x in cards}
        primary = {x["sjuzet_plan"]["primary_focalizer"] for x in cards}
        non_full_direct = sum(
            x["sjuzet_plan"]["event_presence"] != "DIRECT_EMBODIED"
            for x in cards
        )
        mediated = sum(
            bool({"DOCUMENT", "OBJECT_TRACE"}.intersection(x["sjuzet_plan"]["relay_channels"]))
            for x in cards
        )
        return {
            "scenario_id": scenario_id,
            "status": "DISCOURSE_RUNTIME_READY",
            "cards": cards,
            "coverage": {
                "card_count": len(cards),
                "temporal_modes": sorted(temporal),
                "relay_channels": sorted(relay),
                "opening_modes": sorted(openings),
                "distance_curves": [list(x) for x in sorted(curves)],
                "exit_channels": sorted(exits),
                "primary_focalizers": sorted(primary),
                "non_full_direct_cards": non_full_direct,
                "document_or_object_mediated_cards": mediated,
            },
            "watch": self.data["scenario_overrides"][scenario_id]["watch"],
            "winner": None,
            "automatic_literary_pass": False,
            "automatic_prose_generation": False,
        }

    def evaluate(self, scenario_id: str, stress: ScenarioLiteraryStressRuntime) -> dict[str, Any]:
        payload = self.scenario(scenario_id, stress)
        t = self.data["thresholds"]
        c = payload["coverage"]
        blockers: list[dict[str, Any]] = []
        metric_checks = [
            ("card_count", t["cards_per_scenario"]),
            ("temporal_modes", t["temporal_modes_min"]),
            ("relay_channels", t["relay_channels_min"]),
            ("opening_modes", t["opening_modes_min"]),
            ("distance_curves", t["distance_curves_min"]),
            ("exit_channels", t["exit_channels_min"]),
            ("primary_focalizers", t["primary_focalizers_min"]),
            ("non_full_direct_cards", t["non_full_direct_cards_min"]),
            ("document_or_object_mediated_cards", t["document_or_object_mediated_cards_min"]),
        ]
        for key, minimum in metric_checks:
            value = c[key]
            count = len(value) if isinstance(value, list) else value
            if count < minimum:
                blockers.append({"kind":"DISCOURSE_DIVERSITY_GAP","metric":key,"value":count,"required":minimum})

        for card in payload["cards"]:
            plan = card["sjuzet_plan"]
            if plan["narrator_access"] != t["narrator_access_must_be"]:
                blockers.append({"kind":"NARRATOR_ACCESS_DRIFT","probe_id":card["probe_id"]})
            if plan["resolved_withheld_information"]:
                blockers.append({"kind":"WITHHELD_INFO_LEAK","probe_id":card["probe_id"],"items":plan["resolved_withheld_information"]})
            if any([
                plan["theme_statement_allowed"],
                plan["narrator_motive_explanation_allowed"],
                plan["institutional_exposition_allowed"],
            ]):
                blockers.append({"kind":"AUTHORIAL_EXPOSITION_PERMISSION","probe_id":card["probe_id"]})

            probe = next(x for x in stress.contracts[scenario_id]["probes"] if x["id"] == card["probe_id"])
            fp = card["fabula_passthrough"]
            expected = {
                "ordinary_actions": list(probe["ordinary_actions"]),
                "side_characters": list(probe["side_characters"]),
                "object_carriers": list(probe["object_carriers"]),
                "culture_in_action": list(probe["culture_in_action"]),
                "withheld_information": list(probe["withheld_information"]),
                "event_visibility": probe["event_visibility"],
                "ending_vector": probe["ending_vector"],
            }
            if fp != expected:
                blockers.append({"kind":"FABULA_MUTATION","probe_id":card["probe_id"]})

        payload["blockers"] = blockers
        payload["status"] = "DISCOURSE_RUNTIME_READY" if not blockers else "DISCOURSE_RUNTIME_NEEDS_REDESIGN"
        return payload

    def evaluate_all(self, stress: ScenarioLiteraryStressRuntime) -> dict[str, Any]:
        rows = [self.evaluate(sid, stress) for sid in sorted(stress.contracts)]
        return {
            "status":"PASS" if all(x["status"] == "DISCOURSE_RUNTIME_READY" for x in rows) else "NEEDS_REDESIGN",
            "scenarios":[
                {
                    "scenario_id":x["scenario_id"],
                    "status":x["status"],
                    "card_count":x["coverage"]["card_count"],
                    "blocker_count":len(x["blockers"]),
                }
                for x in rows
            ],
            "card_count":sum(x["coverage"]["card_count"] for x in rows),
            "winner":None,
            "automatic_literary_pass":False,
            "automatic_prose_generation":False,
            "next_gate":"P6_CONTROLLED_MICRODRAFT_LAB",
        }

    def compare(self, left_id: str, right_id: str, stress: ScenarioLiteraryStressRuntime) -> dict[str, Any]:
        left = self.evaluate(left_id, stress)
        right = self.evaluate(right_id, stress)
        keys = [
            "temporal_modes","relay_channels","opening_modes","distance_curves",
            "exit_channels","primary_focalizers","non_full_direct_cards","document_or_object_mediated_cards"
        ]
        return {
            "left":left_id,
            "right":right_id,
            "differences":[
                {"metric":k,"left":left["coverage"][k],"right":right["coverage"][k]}
                for k in keys
            ],
            "ranking":None,
            "winner":None,
            "note":"P5 compares discourse shape only; no scenario ranking is authorized.",
        }

    def validate_integrity(
        self,
        stress: ScenarioLiteraryStressRuntime,
        ecology: LiteraryEcologyRuntime,
    ) -> list[str]:
        errors: list[str] = []
        if self.data.get("authority") != "SHADOW_ONLY":
            errors.append("Narrative discourse runtime must remain SHADOW_ONLY")
        if self.data.get("output_authority") != "DISCOURSE_PLANNING_ONLY":
            errors.append("Narrative discourse output authority drift")
        policy = self.data.get("policy", {})
        for key in ("fabula_mutation_allowed","automatic_prose_generation","automatic_literary_pass","automatic_winner","scalar_score"):
            if policy.get(key) is not False:
                errors.append(f"Narrative discourse policy {key} must remain false")
        for key in ("evidence_effect","open_interface_effect","stable_active_effect","canonical_competition_effect"):
            if policy.get(key) != "NONE":
                errors.append(f"Narrative discourse policy {key} must remain NONE")

        required = set(self.data["source_basis"]["required_scenarios"])
        if required != set(stress.contracts):
            errors.append("P5 scenario set must equal the P4 scenario set")
        if set(self.data.get("scenario_overrides", {})) != required:
            errors.append("P5 scenario overrides must cover exactly all P4 scenarios")

        known_basis = set(ecology.dimensions) | set(ecology.techniques)
        for dim in self.data.get("discourse_dimensions", []):
            unknown = sorted(set(dim["basis_refs"]) - known_basis)
            if unknown:
                errors.append(f"{dim['id']}: unknown literary basis refs {unknown}")

        p4 = stress.evaluate_all(ecology)
        if p4["status"] != "PASS":
            errors.append("P5 requires P4 literary stress PASS")

        result = self.evaluate_all(stress)
        if result["status"] != "PASS":
            errors.append(f"P5 discourse runtime not ready: {result}")
        if result["card_count"] != sum(len(c["probes"]) for c in stress.contracts.values()):
            errors.append(f"P5 must cover all upstream discourse cards; got {result['card_count']}")
        if result["winner"] is not None:
            errors.append("P5 may not select a winner")
        return errors
