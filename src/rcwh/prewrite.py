from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


STABLE_SHA = "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320"
EXPECTED_EXECUTION_ORDER = [33, 34, 35, 40, 39, 38, 37, 36, 41, 42]
EXPECTED_CHAPTERS = set(range(81, 101))
FOUR_CHAINS = ["people", "money", "material", "information"]


def _source_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            refs |= _source_refs(item)
    elif isinstance(value, list):
        for item in value:
            refs |= _source_refs(item)
    elif isinstance(value, str) and value.startswith("doc:"):
        refs.add(value)
    return refs


@dataclass
class V5PrewriteRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "V5PrewriteRuntime":
        return cls(
            root=root,
            data=load_data(root / "data" / "prewrite" / "v06.json") or {},
        )

    @property
    def gaps(self) -> dict[int, dict[str, Any]]:
        return {x["chapter"]: x for x in self.data.get("gap_cards", [])}

    @property
    def planners(self) -> dict[int, dict[str, Any]]:
        return {x["chapter"]: x for x in self.data.get("omitted_scene_plans", [])}

    @property
    def steps(self) -> dict[int, dict[str, Any]]:
        return {x["step"]: x for x in self.data.get("steps", [])}

    @property
    def corpus_profiles(self) -> dict[str, dict[str, Any]]:
        return {x["id"]: x for x in self.data.get("corpus_ecology_profiles", [])}

    def summary(self) -> dict[str, Any]:
        completion = self.data.get("completion", {})
        return {
            "id": self.data.get("id"),
            "status": self.data.get("status"),
            "authority": self.data.get("authority"),
            "evidence_effect": self.data.get("evidence_effect"),
            "stable_active_effect": self.data.get("stable_active_effect"),
            "execution_order": self.data.get("execution_order", []),
            "corpus_profiles": len(self.corpus_profiles),
            "gap_dimensions": len(self.data.get("gap_dimensions", [])),
            "gap_chapters": len(self.gaps),
            "omitted_scene_chapters": len(self.planners),
            "omitted_scene_candidates": sum(
                len(x.get("candidate_scenes", [])) for x in self.planners.values()
            ),
            "machine_readable_chapter_contracts": completion.get(
                "machine_readable_chapter_contracts"
            ),
            "feeds_staging": completion.get("feeds_staging"),
            "becomes_evidence": completion.get("becomes_evidence"),
        }

    def corpus(self, profile_id: str | None = None) -> dict[str, Any]:
        if profile_id is None:
            return {
                "step": 33,
                "mode": "IMPORTED_AUDITED_PROFILE",
                "state": self.steps[33]["state"],
                "profiles": list(self.corpus_profiles.values()),
                "authority": "STAGING_BASELINE_ONLY",
                "evidence_effect": "NONE",
            }
        if profile_id not in self.corpus_profiles:
            raise KeyError(f"Unknown Step33 corpus profile: {profile_id}")
        return {
            "step": 33,
            "mode": "IMPORTED_AUDITED_PROFILE",
            "profile": self.corpus_profiles[profile_id],
            "authority": "STAGING_BASELINE_ONLY",
            "evidence_effect": "NONE",
        }

    def gap(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.gaps:
            raise KeyError(f"Step34 gap card covers chapters 81..100: {chapter}")
        return {
            "step": 34,
            **self.gaps[chapter],
            "authority": "STAGING_DIAGNOSTIC_ONLY",
            "evidence_effect": "NONE",
        }

    def scenes(self, chapter: int) -> dict[str, Any]:
        if chapter not in self.planners:
            raise KeyError(f"Step35 planner covers chapters 81..100: {chapter}")
        return {
            "step": 35,
            **self.planners[chapter],
            "authority": "STAGING_PLAN_ONLY",
            "evidence_effect": "NONE",
            "may_create_evidence": False,
        }

    def step(
        self,
        step: int,
        chapter: int | None,
        literary: Any,
        adapters: Any,
    ) -> dict[str, Any]:
        if step not in self.steps:
            raise KeyError(f"v5 prewrite covers steps 33..42 only: {step}")
        meta = self.steps[step]
        base = {
            "step": step,
            "id": meta["id"],
            "name": meta["name"],
            "state": meta["state"],
            "authority": "STAGING_ONLY",
            "evidence_effect": "NONE",
            "stable_active_effect": "NONE",
        }
        if step == 33:
            return {**base, **self.corpus()}
        if step == 34:
            if chapter is None:
                return {
                    **base,
                    "chapters": 20,
                    "dimensions": self.data["gap_dimensions"],
                    "legend": self.data["gap_status_legend"],
                }
            return {**base, "gap_card": self.gap(chapter)}
        if step == 35:
            if chapter is None:
                return {
                    **base,
                    "chapters": 20,
                    "candidate_scenes": sum(
                        len(x["candidate_scenes"]) for x in self.planners.values()
                    ),
                }
            return {**base, "scene_plan": self.scenes(chapter)}
        if chapter is None:
            return {
                **base,
                "source_refs": meta.get("source_refs", []),
                "chapter_required": step in {36, 37, 38, 39, 40, 41, 42},
            }

        if chapter not in EXPECTED_CHAPTERS:
            raise KeyError(f"Prewrite chapter must be 81..100: {chapter}")
        gap = self.gap(chapter)["states"]
        if step == 36:
            return {
                **base,
                "chapter": chapter,
                "author_verse_policy": literary.author_rhyme[chapter],
                "rule": "A/B/C author-verse options remain downstream literary choices; no verse is inferred from gap status.",
            }
        if step == 37:
            return {
                **base,
                "chapter": chapter,
                "text_ecology": literary.post80_text[chapter],
                "global_evidence_nodes": sorted(literary.evidence),
                "global_g_layer": sorted(literary.g_layer),
                "rule": "A/B/C evidence identity and G generation containers remain distinct; G never becomes evidence.",
            }
        if step == 38:
            return {
                **base,
                "chapter": chapter,
                "arts_gap": gap["arts"],
                "source_refs": meta.get("source_refs", []),
                "rule": "Restore old cultural life only where dramatically attached; no four-arts quota.",
            }
        if step == 39:
            candidates: list[str] = []
            if gap["body"] != "NOT_APPLICABLE":
                candidates.extend(["medical", "household_economy"])
            if gap["ritual"] != "NOT_APPLICABLE":
                candidates.append("mourning_marriage")
            candidates = [x for x in dict.fromkeys(candidates) if x in adapters.adapters]
            return {
                **base,
                "chapter": chapter,
                "body_gap": gap["body"],
                "ritual_gap": gap["ritual"],
                "candidate_feasibility_adapters": candidates,
                "rule": "Body/ritual additions must continue existing bodily history and remain feasibility-only.",
            }
        if step == 40:
            return {
                **base,
                "chapter": chapter,
                "economy_gap": gap["economy"],
                "four_chains": FOUR_CHAINS,
                "core_process": self.planners[chapter]["core_process"],
                "rule": "Major events must expose people/money/material/information execution chains; supporting agents need their own constraints.",
            }
        if step == 41:
            return {
                **base,
                "chapter": chapter,
                "metaphysics_gap": gap["metaphysics"],
                "dream_symbol_gap": gap["dream_symbol"],
                "ambiguity_required": True,
                "qingbang_boundary": literary.qingbang() if chapter == 100 else None,
                "rule": "Dream/religion/metaphysics must preserve multiple readings and may not replace social causation.",
            }
        if step == 42:
            return {**base, "chapter": chapter, "generated_by": "contract"}
        raise KeyError(f"Unsupported prewrite step: {step}")

    def contract(
        self,
        chapter: int,
        reconstruction: Any,
        literary: Any,
        plocks: Any,
        adapters: Any,
        registry: Any,
    ) -> dict[str, Any]:
        chapter_node = reconstruction.chapter(chapter)
        gap = self.gap(chapter)
        planner = self.scenes(chapter)
        literary_chapter = literary.chapter(chapter)
        lock_refs = sorted(
            lock_id for lock_id, lock in plocks.locks.items()
            if lock.get("chapter") == chapter
        )
        timeline = reconstruction.timeline_at(chapter)
        source_refs = set()
        source_refs |= _source_refs(chapter_node)
        source_refs |= _source_refs(gap)
        source_refs |= _source_refs(planner)
        source_refs |= _source_refs(literary_chapter)
        source_refs |= set(self.steps[38].get("source_refs", []))
        source_refs |= set(self.steps[39].get("source_refs", []))
        source_refs |= set(self.steps[40].get("source_refs", []))
        source_refs |= set(self.steps[41].get("source_refs", []))

        contract = {
            "id": f"prewrite:ch{chapter}:v0.6",
            "chapter": chapter,
            "authority": "STAGING_ONLY",
            "evidence_effect": "NONE",
            "stable_active_effect": "NONE",
            "stable_active_sha256": registry.current_summary()["stable_active_sha256"],
            "current_working_title": chapter_node["title"],
            "title_status": chapter_node["title_status"],
            "hard_context": {
                "anchor_refs": chapter_node.get("anchor_refs", []),
                "key_constraints": chapter_node.get("key_constraints", []),
                "note": "Upstream references are read-only inputs; this contract cannot create or upgrade evidence.",
            },
            "timeline_context": timeline,
            "step34_gap_card": gap,
            "step35_scene_plan": planner,
            "step36_author_verse": literary_chapter["author_rhyme"],
            "step37_text_ecology": literary_chapter["text_ecology"],
            "step38_cultural_life": self.step(38, chapter, literary, adapters),
            "step39_body_ritual": self.step(39, chapter, literary, adapters),
            "step40_social_infrastructure": self.step(40, chapter, literary, adapters),
            "step41_metaphysics": self.step(41, chapter, literary, adapters),
            "plock_refs": lock_refs,
            "source_refs": sorted(source_refs),
            "staging": {
                "lane": "staging",
                "ready": True,
                "allowed_outputs": [
                    "SCENE_PLAN",
                    "SCENE_CONTRACT_DRAFT",
                    "CANDIDATE_BRIEF",
                    "REVIEW_CHECKLIST",
                ],
                "forbidden_outputs": [
                    "EVIDENCE_NODE",
                    "EVIDENCE_ROLE_CHANGE",
                    "OPEN_CLOSE",
                    "STABLE_ACTIVE_OVERWRITE",
                    "AUTO_PROMOTION",
                ],
                "automatic_prose_generation": False,
                "automatic_promotion": False,
                "next_gate": "STEP43_CANDIDATE_WORKFLOW",
            },
        }
        return contract

    def staging_packet(
        self,
        chapter: int,
        reconstruction: Any,
        literary: Any,
        plocks: Any,
        adapters: Any,
        registry: Any,
    ) -> dict[str, Any]:
        contract = self.contract(
            chapter, reconstruction, literary, plocks, adapters, registry
        )
        return {
            "kind": "V5_PREWRITE_STAGING_PACKET",
            "chapter": chapter,
            "contract_id": contract["id"],
            "authority": "STAGING_ONLY",
            "evidence_effect": "NONE",
            "stable_active_effect": "NONE",
            "staging_lane": "staging",
            "input_contract": contract,
            "write_permissions": {
                "staging_artifacts": True,
                "evidence": False,
                "reconstruction_truth": False,
                "open_interfaces": False,
                "stable_active": False,
                "promotion": False,
            },
            "next_gate": "STEP43_CANDIDATE_WORKFLOW",
        }

    def validate_integrity(
        self,
        registry: Any,
        reconstruction: Any,
        literary: Any,
        plocks: Any,
        adapters: Any,
    ) -> list[str]:
        errors: list[str] = []
        if self.data.get("issue") != 6:
            errors.append("v5 prewrite harness must be bound to issue #6")
        if self.data.get("authority") != "STAGING_ONLY":
            errors.append("prewrite authority must remain STAGING_ONLY")
        if self.data.get("evidence_effect") != "NONE":
            errors.append("prewrite harness may not create evidence")
        if self.data.get("stable_active_effect") != "NONE":
            errors.append("prewrite harness may not mutate stable ACTIVE")
        if self.data.get("execution_order") != EXPECTED_EXECUTION_ORDER:
            errors.append("v5.2 actual execution order drifted")
        if set(self.steps) != set(range(33, 43)):
            errors.append("prewrite step registry must contain steps 33..42 exactly")
        if len(self.corpus_profiles) != 6:
            errors.append("Step33 must expose six frozen ecology profiles")
        if len(self.data.get("gap_dimensions", [])) != 12:
            errors.append("Step34 must expose exactly twelve dimensions")
        if set(self.gaps) != EXPECTED_CHAPTERS:
            errors.append("Step34 gap cards must cover chapters 81..100")
        if set(self.planners) != EXPECTED_CHAPTERS:
            errors.append("Step35 planner must cover chapters 81..100")
        scene_count = sum(
            len(x.get("candidate_scenes", [])) for x in self.planners.values()
        )
        if scene_count != 85:
            errors.append(f"Step35 candidate-scene count drifted: {scene_count} != 85")

        expected_counts = {
            "main_process": {"SUFFICIENT": 0, "THIN": 11, "MISSING": 9, "NOT_APPLICABLE": 0},
            "secondary_plot": {"SUFFICIENT": 18, "THIN": 2, "MISSING": 0, "NOT_APPLICABLE": 0},
            "minor_agents": {"SUFFICIENT": 18, "THIN": 2, "MISSING": 0, "NOT_APPLICABLE": 0},
            "poetry": {"SUFFICIENT": 0, "THIN": 12, "MISSING": 7, "NOT_APPLICABLE": 1},
            "arts": {"SUFFICIENT": 0, "THIN": 10, "MISSING": 6, "NOT_APPLICABLE": 4},
            "body": {"SUFFICIENT": 1, "THIN": 9, "MISSING": 4, "NOT_APPLICABLE": 6},
            "metaphysics": {"SUFFICIENT": 0, "THIN": 9, "MISSING": 4, "NOT_APPLICABLE": 7},
            "ritual": {"SUFFICIENT": 0, "THIN": 10, "MISSING": 8, "NOT_APPLICABLE": 2},
            "economy": {"SUFFICIENT": 0, "THIN": 9, "MISSING": 11, "NOT_APPLICABLE": 0},
            "comic_folk": {"SUFFICIENT": 20, "THIN": 0, "MISSING": 0, "NOT_APPLICABLE": 0},
            "dream_symbol": {"SUFFICIENT": 15, "THIN": 2, "MISSING": 3, "NOT_APPLICABLE": 0},
            "chapter_frame": {"SUFFICIENT": 16, "THIN": 3, "MISSING": 1, "NOT_APPLICABLE": 0},
        }
        for key, expected in expected_counts.items():
            actual = {name: 0 for name in expected}
            for item in self.gaps.values():
                actual[item["states"][key]] += 1
            if actual != expected:
                errors.append(f"Step34 aggregate drift for {key}: {actual} != {expected}")

        for ref in sorted(_source_refs(self.data)):
            if ref not in registry.documents:
                errors.append(f"prewrite source not registered: {ref}")

        literary_sources = set(literary.data.get("sources", {}))
        for item in self.corpus_profiles.values():
            if item["source_ref"] not in literary_sources:
                errors.append(
                    f"Step33 profile source is not in Literary Ecology runtime: {item['source_ref']}"
                )

        policy = self.data.get("staging_policy", {})
        for key in (
            "evidence_write_allowed",
            "evidence_role_change_allowed",
            "open_close_allowed",
            "stable_mutation_allowed",
            "automatic_prose_generation",
            "automatic_promotion",
        ):
            if policy.get(key) is not False:
                errors.append(f"staging permission drift: {key} must remain false")
        if registry.current_summary().get("stable_active_sha256") != STABLE_SHA:
            errors.append("prewrite harness observed stable ACTIVE drift")

        contracts = []
        for chapter in range(81, 101):
            try:
                contract = self.contract(
                    chapter, reconstruction, literary, plocks, adapters, registry
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"chapter {chapter} contract failed: {exc}")
                continue
            contracts.append(contract)
            if contract["authority"] != "STAGING_ONLY":
                errors.append(f"chapter {chapter}: contract authority drift")
            if contract["evidence_effect"] != "NONE":
                errors.append(f"chapter {chapter}: contract gained evidence effect")
            if contract["stable_active_sha256"] != STABLE_SHA:
                errors.append(f"chapter {chapter}: stable baseline drift")
            if contract["staging"]["automatic_prose_generation"] is not False:
                errors.append(f"chapter {chapter}: prewrite may not auto-generate prose")
            if contract["staging"]["automatic_promotion"] is not False:
                errors.append(f"chapter {chapter}: prewrite may not auto-promote")
        if len(contracts) != 20:
            errors.append(f"Step42 must generate 20 contracts; got {len(contracts)}")
        return errors


def format_prewrite(kind: str, payload: dict[str, Any]) -> str:
    if kind == "summary":
        return "\n".join([
            "V5 PREWRITE HARNESS v0.6",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"execution_order: {' -> '.join(str(x) for x in payload['execution_order'])}",
            f"Step33 profiles: {payload['corpus_profiles']}/6",
            f"Step34 gaps: {payload['gap_chapters']}/20 x {payload['gap_dimensions']}D",
            f"Step35 scene candidates: {payload['omitted_scene_candidates']}",
            f"Step42 contracts: {payload['machine_readable_chapter_contracts']}/20",
            f"feeds_staging: {str(payload['feeds_staging']).lower()}",
            f"becomes_evidence: {str(payload['becomes_evidence']).lower()}",
        ])
    if kind == "gap":
        return "\n".join([
            f"STEP34 GAP CARD ch{payload['chapter']}",
            f"priority: {payload['priority']}",
            *[f"- {k}: {v}" for k, v in payload["states"].items()],
            "authority: STAGING_DIAGNOSTIC_ONLY",
        ])
    if kind == "scenes":
        lines = [
            f"STEP35 SCENE PLAN ch{payload['chapter']}",
            f"action: {payload['action']} / intensity={payload['intensity']}",
            f"core_process: {payload['core_process']}",
        ]
        lines.extend(f"- {x['id']}: {x['title']}" for x in payload["candidate_scenes"])
        lines.append("evidence_effect: NONE")
        return "\n".join(lines)
    if kind == "contract":
        return "\n".join([
            f"STEP42 PREWRITE CONTRACT ch{payload['chapter']}",
            f"id: {payload['id']}",
            f"title: {payload['current_working_title']}",
            f"title_status: {payload['title_status']}",
            f"plocks: {', '.join(payload['plock_refs']) or 'none'}",
            f"staging_ready: {str(payload['staging']['ready']).lower()}",
            f"next_gate: {payload['staging']['next_gate']}",
            "authority: STAGING_ONLY",
            "evidence_effect: NONE",
            "automatic_prose_generation: false",
            "automatic_promotion: false",
        ])
    if kind == "stage":
        return "\n".join([
            f"V5 PREWRITE STAGING PACKET ch{payload['chapter']}",
            f"contract: {payload['contract_id']}",
            f"lane: {payload['staging_lane']}",
            "evidence write: false",
            "stable mutation: false",
            "promotion: false",
            f"next_gate: {payload['next_gate']}",
        ])
    if kind == "corpus":
        profiles = payload.get("profiles")
        if profiles is not None:
            lines = ["STEP33 CORPUS ECOLOGY", "mode: IMPORTED_AUDITED_PROFILE"]
            lines.extend(f"- {x['id']}: {x['name']}" for x in profiles)
            lines.append("evidence_effect: NONE")
            return "\n".join(lines)
        item = payload["profile"]
        return "\n".join([
            f"STEP33 CORPUS PROFILE {item['id']}",
            f"name: {item['name']}",
            f"source_ref: {item['source_ref']}",
            *[f"- {x}" for x in item["frozen_conclusions"]],
            "evidence_effect: NONE",
        ])
    if kind == "step":
        return "\n".join(f"{k}: {v}" for k, v in payload.items())
    return str(payload)
