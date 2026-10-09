from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hypotheses import HypothesisRuntime
from .io import load_data
from .scenarios import ScenarioRuntime
from .world import WorldRuntime


@dataclass
class CounterfactualReplayRuntime:
    data: dict[str, Any]
    effects_by_hypothesis: dict[str, list[dict[str, Any]]]
    pressures_by_hypothesis: dict[str, list[dict[str, Any]]]
    local_locations: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "CounterfactualReplayRuntime":
        data = load_data(root / "data" / "research" / "scenario_replay.json") or {}
        effects: dict[str, list[dict[str, Any]]] = {}
        for item in data.get("hypothesis_effects", []):
            effects.setdefault(item["hypothesis_id"], []).append(item)
        for values in effects.values():
            values.sort(key=lambda x: (x["priority"], x["id"]))
        pressures: dict[str, list[dict[str, Any]]] = {}
        for item in data.get("pressure_rules", []):
            pressures.setdefault(item["hypothesis_id"], []).append(item)
        return cls(
            data=data,
            effects_by_hypothesis=effects,
            pressures_by_hypothesis=pressures,
            local_locations={x["id"]: x for x in data.get("local_locations", [])},
        )

    def _effects_for(self, scenario: dict[str, Any], chapter: int) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for hypothesis_id in scenario["hypotheses"]:
            for item in self.effects_by_hypothesis.get(hypothesis_id, []):
                if item["chapter_start"] <= chapter <= item["chapter_end"]:
                    result.append(item)
        return sorted(result, key=lambda x: (x["priority"], x["id"]))

    def snapshot(
        self,
        scenario_id: str,
        chapter: int,
        scenarios: ScenarioRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        if chapter < 81 or chapter > 100:
            raise KeyError(f"Replay only covers chapters 81..100: {chapter}")
        scenario = scenarios.get(scenario_id)
        state = deepcopy(world.snapshot(chapter))
        annotations: dict[str, Any] = {}
        applied: list[str] = []
        for effect in self._effects_for(scenario, chapter):
            kind = effect["kind"]
            if kind == "WORLD_OVERRIDE":
                _assign(state, effect["set"], deepcopy(effect.get("value")))
            elif kind == "WORLD_COPY":
                _assign(state, effect["set"], deepcopy(_get(state, effect["from_path"])))
            elif kind == "ANNOTATION":
                annotations[effect["annotation"]] = deepcopy(effect.get("value"))
            else:
                raise ValueError(f"Unknown replay effect kind: {kind}")
            applied.append(effect["id"])

        object_state = self._object_view(chapter, state, annotations)
        return {
            "scenario_id": scenario_id,
            "chapter": chapter,
            "state": state,
            "annotations": annotations,
            "object_state": object_state,
            "applied_effects": applied,
            "authority": "SCENARIO_ONLY",
            "evidence_effect": "NONE",
            "stable_active_effect": "NONE",
        }

    def _object_view(
        self,
        chapter: int,
        state: dict[str, Any],
        annotations: dict[str, Any],
    ) -> dict[str, Any]:
        departure = annotations.get("baoyu_departure_chapter", 99)
        baoyu = state["characters"]["baoyu"]
        if chapter < departure:
            tongling = {
                "holder": "baoyu",
                "location": baoyu["location"],
                "status": "WITH_BAOYU_SCENARIO_REPLAY",
                "frame_status": "IN_HUMAN_WORLD",
            }
        elif chapter < 100:
            tongling = {
                "holder": "UNKNOWN",
                "location": "UNKNOWN",
                "status": "EARTHLY_ROUTE_OPEN_AFTER_SA_SHOU",
                "frame_status": "IN_HUMAN_WORLD",
            }
        else:
            tongling = {
                "holder": "UNKNOWN",
                "location": "UNKNOWN",
                "status": "EARTHLY_ROUTE_OPEN_AFTER_SA_SHOU",
                "frame_status": "RETURNED_TO_ESSENCE_QINGGENG_FRAME",
            }
        return {
            "tongling_jade": tongling,
            "snow_jade_identity": annotations.get("snow_jade_identity", "OPEN"),
            "snow_transfer_chain": annotations.get("snow_transfer_chain"),
            "sent_jade_identity": annotations.get("sent_jade_identity", "OPEN"),
            "sent_jade_transfer": annotations.get("sent_jade_transfer"),
            "zhen_baoyu_encounter": annotations.get("zhen_baoyu_encounter"),
            "boundary": "Scenario object view never merges canonical M4 identity nodes or promotes an identity assumption into Evidence.",
        }

    def _digest(self, snap: dict[str, Any]) -> dict[str, Any]:
        s = snap["state"]
        c = s["characters"]
        r = s["relations"]
        return {
            "chapter": snap["chapter"],
            "economy_stage": s["global"]["economy_stage"],
            "outer_frame": s["global"]["outer_frame"],
            "baoyu": {
                "location": c["baoyu"]["location"],
                "legal_status": c["baoyu"]["legal_status"],
                "marital_status": c["baoyu"]["marital_status"],
                "household_role": c["baoyu"]["household_role"],
            },
            "baochai": {
                "location": c["baochai"]["location"],
                "marital_status": c["baochai"]["marital_status"],
                "household_role": c["baochai"]["household_role"],
            },
            "jiamu": {
                "life_state": c["jiamu"]["life_state"],
                "location": c["jiamu"]["location"],
            },
            "fengjie": {
                "life_state": c["fengjie"]["life_state"],
                "legal_status": c["fengjie"]["legal_status"],
                "location": c["fengjie"]["location"],
                "body_state": c["fengjie"]["body_state"],
            },
            "qiaojie_location": c["qiaojie"]["location"],
            "miaoyu_location": c["miaoyu"]["location"],
            "spouse_relation": r["rel:baoyu_baochai"]["status"],
            "sheyue_relation": r["rel:sheyue_baoyu"]["status"],
            "qiaojie_caregiver": r["rel:liulaolao_qiaojie"]["status"],
            "annotations": snap["annotations"],
            "object_state": snap["object_state"],
        }

    def _blocker(
        self,
        findings: list[dict[str, Any]],
        kind: str,
        chapter: int,
        message: str,
    ) -> None:
        findings.append({
            "severity": "BLOCKER",
            "kind": kind,
            "chapter": chapter,
            "message": message,
        })

    def _findings(
        self,
        scenario: dict[str, Any],
        snaps: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        # Local location registry and relation-state coherence.
        for chapter, snap in snaps.items():
            state = snap["state"]
            for character_id, cstate in state["characters"].items():
                loc = cstate.get("location")
                if isinstance(loc, str) and loc.startswith("SCN-LOC-") and loc not in self.local_locations:
                    self._blocker(
                        findings, "LOCATION_REFERENCE_ERROR", chapter,
                        f"{character_id} references unregistered scenario location {loc}",
                    )

            rel = state["relations"]["rel:baoyu_baochai"]["status"]
            b = state["characters"]["baoyu"]["marital_status"]
            bc = state["characters"]["baochai"]["marital_status"]
            if rel == "ACTIVE_SPOUSES" and (b != "MARRIED_BAOCHAI" or bc != "MARRIED_BAOYU"):
                self._blocker(
                    findings, "RELATION_STATE_CONFLICT", chapter,
                    "Spouse relation is ACTIVE_SPOUSES but character marital states disagree.",
                )
            if rel == "NOT_MARRIED" and (b == "MARRIED_BAOCHAI" or bc == "MARRIED_BAOYU"):
                self._blocker(
                    findings, "RELATION_STATE_CONFLICT", chapter,
                    "Spouse relation is NOT_MARRIED but one character is already marked married.",
                )

            fj = state["characters"]["fengjie"]["life_state"]
            for relation_id in ("rel:fengjie_ping", "rel:fengjie_qiaojie"):
                status = state["relations"][relation_id]["status"]
                if fj == "DEAD" and status == "ACTIVE":
                    self._blocker(
                        findings, "RELATION_STATE_CONFLICT", chapter,
                        f"{relation_id} remains ACTIVE after Fengjie is dead.",
                    )

            jade = snap["object_state"]["tongling_jade"]
            if jade["holder"] == "baoyu" and jade["location"] != state["characters"]["baoyu"]["location"]:
                self._blocker(
                    findings, "OBJECT_TELEPORTATION", chapter,
                    "Tongling jade holder/location diverges from Baoyu while marked WITH_BAOYU.",
                )

        # R05: real detention and ordinary release remain present.
        ch92 = snaps[92]
        if ch92["state"]["characters"]["baoyu"]["legal_status"] != "DETAINED_PENDING_INQUIRY":
            self._blocker(findings, "TIMELINE_CONTRADICTION", 92, "R05 detention state is missing.")
        if ch92["state"]["characters"]["baoyu"]["location"] != "S07":
            self._blocker(findings, "TIMELINE_CONTRADICTION", 92, "R05 detention is not in the detention-space runtime.")
        ch93 = snaps[93]
        if ch93["state"]["characters"]["baoyu"]["legal_status"] != "RELEASED_NO_RESTORATION":
            self._blocker(findings, "TIMELINE_CONTRADICTION", 93, "Ordinary release/no-restoration state is missing.")

        # R37/R38: Qiaojie rescue/rural placement.
        ch94 = snaps[94]
        if ch94["state"]["characters"]["qiaojie"]["location"] != "S08":
            self._blocker(findings, "TIMELINE_CONTRADICTION", 94, "Qiaojie is not in the Liu rural household by the rescue checkpoint.")
        if ch94["state"]["relations"]["rel:liulaolao_qiaojie"]["status"] != "ACTIVE_CAREGIVER":
            self._blocker(findings, "RELATION_STATE_CONFLICT", 94, "Liu/Qiaojie caregiver relation is not active at the rescue checkpoint.")

        # O05 boundary: Fengjie must be unable to protect Qiaojie when crisis resolves.
        fj94 = ch94["state"]["characters"]["fengjie"]
        protection = ch94["annotations"].get("fengjie_protection_capacity")
        if fj94["life_state"] != "DEAD" and protection != "NONE":
            self._blocker(
                findings, "RELATION_STATE_CONFLICT", 94,
                "Fengjie is alive at the Qiaojie crisis checkpoint without an explicit NONE protection capacity.",
            )

        # R29 eventual death.
        if snaps[100]["state"]["characters"]["fengjie"]["life_state"] != "DEAD":
            self._blocker(findings, "TIMELINE_CONTRADICTION", 100, "R29 eventual Fengjie death has not occurred by terminal replay.")

        # R43/P09: wife and Sheyue relation exist immediately before departure.
        departure = snaps[81]["annotations"].get("baoyu_departure_chapter", 99)
        pre = departure - 1
        if pre < 81:
            self._blocker(findings, "TIMELINE_CONTRADICTION", departure, "Invalid departure chapter.")
        else:
            pre_state = snaps[pre]["state"]
            if pre_state["relations"]["rel:baoyu_baochai"]["status"] != "ACTIVE_SPOUSES":
                self._blocker(findings, "RELATION_STATE_CONFLICT", pre, "Baoyu/Baochai are not active spouses immediately before Sa-shou.")
            if pre_state["relations"]["rel:sheyue_baoyu"]["status"] != "ACTIVE":
                self._blocker(findings, "RELATION_STATE_CONFLICT", pre, "Sheyue/Baoyu relation is not active immediately before Sa-shou.")

        dep_state = snaps[departure]["state"]
        if dep_state["relations"]["rel:baoyu_baochai"]["status"] != "SPOUSES_SEPARATED_BY_BAOYU_DEPARTURE":
            self._blocker(findings, "RELATION_STATE_CONFLICT", departure, "Spouse relation is not separated by Baoyu's departure at the declared departure chapter.")

        # Object assumptions must carry explicit transfer bookkeeping when they claim identity.
        ch91 = snaps[91]
        if ch91["annotations"].get("snow_jade_identity") == "TONGLING_ASSUMED_FOR_REPLAY":
            if not ch91["annotations"].get("snow_transfer_chain"):
                self._blocker(findings, "OBJECT_TELEPORTATION", 91, "Single-jade snow hypothesis lacks a transfer chain.")
        ch98 = snaps[98]
        if ch98["annotations"].get("sent_jade_identity") == "TONGLING_ASSUMED_FOR_REPLAY":
            if not ch98["annotations"].get("sent_jade_transfer"):
                self._blocker(findings, "OBJECT_TELEPORTATION", 98, "Single-jade sent hypothesis lacks a return transfer chain.")

        # R01/R08/R09 terminal frame.
        end = snaps[100]["state"]["global"]
        if end.get("outer_frame") != "S15_OPEN":
            self._blocker(findings, "TIMELINE_CONTRADICTION", 100, "Terminal outer frame is not open.")
        if end.get("human_access_to_outer_frame_knowledge") is not False:
            self._blocker(findings, "KNOWLEDGE_LEAK", 100, "Outer-frame knowledge leaked into the human world.")

        # Historical/resource/W2 pressures are non-blocking and never create plot authority.
        present = set(scenario["hypotheses"])
        for hypothesis_id in scenario["hypotheses"]:
            for pressure in self.pressures_by_hypothesis.get(hypothesis_id, []):
                findings.append(deepcopy(pressure))

        # A late marriage in E2 is feasible but must not silently spend current-C resources.
        if "HYP-G2" in present:
            stage = snaps[94]["state"]["global"]["economy_stage"]
            if stage != "E2":
                self._blocker(
                    findings, "RESOURCE_IMPOSSIBILITY", 94,
                    f"G2 late-marriage replay expected E2 pressure context, got {stage}.",
                )

        return findings

    def evaluate(
        self,
        scenario_id: str,
        scenarios: ScenarioRuntime,
        world: WorldRuntime,
        chapter: int | None = None,
    ) -> dict[str, Any]:
        scenario = scenarios.get(scenario_id)
        snaps = {
            ch: self.snapshot(scenario_id, ch, scenarios, world)
            for ch in sorted(world.presence)
        }
        findings = self._findings(scenario, snaps)
        blockers = [x for x in findings if x["severity"] == "BLOCKER"]
        pressures = [x for x in findings if x["severity"] == "PRESSURE"]
        status = (
            "REPLAY_BLOCKED" if blockers
            else "REPLAY_PASS_WITH_PRESSURE" if pressures
            else "REPLAY_PASS"
        )
        payload: dict[str, Any] = {
            "scenario_id": scenario_id,
            "status": status,
            "blockers": blockers,
            "pressures": pressures,
            "authority": "SCENARIO_ONLY",
            "automatic_winner": False,
            "single_total_score": False,
            "evidence_effect": "NONE",
            "open_interface_effect": "NONE",
            "stable_active_effect": "NONE",
        }
        if chapter is not None:
            payload["chapter"] = self._digest(snaps[chapter])
        else:
            payload["checkpoints"] = [
                self._digest(snaps[ch])
                for ch in (83, 85, 87, 89, 91, 92, 94, 95, 97, 98, 99, 100)
            ]
        return payload

    def evaluate_all(
        self,
        scenarios: ScenarioRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        rows = []
        for scenario_id in sorted(scenarios.scenarios):
            result = self.evaluate(scenario_id, scenarios, world)
            rows.append({
                "scenario_id": scenario_id,
                "status": result["status"],
                "blockers": len(result["blockers"]),
                "pressures": len(result["pressures"]),
            })
        return {
            "status": "PASS" if all(x["blockers"] == 0 for x in rows) else "BLOCKED_SCENARIOS_PRESENT",
            "scenarios": rows,
            "automatic_winner": False,
            "single_total_score": False,
            "next_gate": "P3_PARETO_EVALUATION",
        }

    def frontier(
        self,
        scenarios: ScenarioRuntime,
        world: WorldRuntime,
    ) -> dict[str, Any]:
        rows = self.evaluate_all(scenarios, world)["scenarios"]
        return {
            "status": "REPLAY_COMPLETE_NOT_RANKED",
            "replay_survivors": [x["scenario_id"] for x in rows if x["blockers"] == 0],
            "blocked": [x["scenario_id"] for x in rows if x["blockers"] > 0],
            "single_total_score": False,
            "automatic_winner": False,
            "next_gate": "P3_PARETO_EVALUATION",
        }

    def validate_integrity(
        self,
        hypotheses: HypothesisRuntime,
        scenarios: ScenarioRuntime,
        world: WorldRuntime,
    ) -> list[str]:
        errors: list[str] = []
        if self.data.get("authority") != "SHADOW_ONLY":
            errors.append("Scenario replay must remain SHADOW_ONLY")
        for field, value in self.data.get("effects", {}).items():
            if value != "NONE":
                errors.append(f"Scenario replay effect {field} must remain NONE")
        if self.data.get("automatic_winner") is not False:
            errors.append("Scenario replay may not auto-select a winner")
        if self.data.get("single_total_score") is not False:
            errors.append("Scenario replay may not collapse to a single total score")

        for effect in self.data.get("hypothesis_effects", []):
            hid = effect["hypothesis_id"]
            if hid not in hypotheses.hypotheses:
                errors.append(f"{effect['id']}: unknown hypothesis {hid}")
                continue
            if effect["chapter_start"] > effect["chapter_end"]:
                errors.append(f"{effect['id']}: invalid chapter range")
            if effect["kind"] == "WORLD_OVERRIDE":
                try:
                    _get(world.snapshot(effect["chapter_start"]), effect["set"])
                except KeyError:
                    errors.append(f"{effect['id']}: unknown world path {effect.get('set')}")
            elif effect["kind"] == "WORLD_COPY":
                try:
                    snap = world.snapshot(effect["chapter_start"])
                    _get(snap, effect["set"])
                    _get(snap, effect["from_path"])
                except KeyError:
                    errors.append(f"{effect['id']}: invalid WORLD_COPY path")
            elif effect["kind"] == "ANNOTATION":
                if not effect.get("annotation"):
                    errors.append(f"{effect['id']}: annotation key required")
            else:
                errors.append(f"{effect['id']}: unsupported effect kind")

            value = effect.get("value")
            if isinstance(value, str) and value.startswith("SCN-LOC-") and value not in self.local_locations:
                errors.append(f"{effect['id']}: unregistered scenario location {value}")

        current = self.evaluate("SCN-CURRENT-C", scenarios, world)
        if current["blockers"]:
            errors.append(f"Current-C reference replay has blockers: {current['blockers']}")
        for chapter in sorted(world.presence):
            baseline = world.snapshot(chapter)
            replay = self.snapshot("SCN-CURRENT-C", chapter, scenarios, world)["state"]
            if replay != baseline:
                errors.append(f"Current-C reference drifted from M3 at chapter {chapter}")

        all_result = self.evaluate_all(scenarios, world)
        for row in all_result["scenarios"]:
            if row["blockers"]:
                errors.append(
                    f"{row['scenario_id']}: P2 replay blocker count {row['blockers']}"
                )
        return errors


def _get(state: dict[str, Any], dotted: str) -> Any:
    cur: Any = state
    for part in dotted.split("."):
        if part not in cur:
            raise KeyError(dotted)
        cur = cur[part]
    return cur


def _assign(state: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur: Any = state
    for part in parts[:-1]:
        if part not in cur:
            raise KeyError(dotted)
        cur = cur[part]
    if parts[-1] not in cur:
        raise KeyError(dotted)
    cur[parts[-1]] = value
