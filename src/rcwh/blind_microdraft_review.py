from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .assets import AssetCatalog
from .contracts import unique_index, coverage_errors
from .io import load_data
from .microdraft import ControlledMicrodraftRuntime


@dataclass
class BlindMicrodraftReviewRuntime:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "BlindMicrodraftReviewRuntime":
        return cls(root, load_data(root / "data/blind_review/v013.json") or {})

    def mapping(self, lab: ControlledMicrodraftRuntime | None = None) -> dict[str, Any]:
        basis = self.data["source_basis"]
        if not basis.get("mapping_unsealed_after_review"):
            raise ValueError("blind mapping may only be unsealed after review")
        lab = lab or ControlledMicrodraftRuntime.from_repo(self.root)
        lab.require_snapshot(basis["microdraft_ref"], basis["microdraft_snapshot_sha256"])
        return {token: {key: spec[key] for key in ("scenario_id", "probe_id", "cell_id")}
                for token, spec in lab.drafts.items()}

    def raw_review(self) -> str:
        asset = AssetCatalog.from_repo(self.root).resolve(self.data["source_basis"]["raw_review_asset_ref"])
        return asset.path.read_text(encoding="utf-8")

    def reviews(self, lab: ControlledMicrodraftRuntime | None = None) -> dict[str, dict[str, Any]]:
        mapping = self.mapping(lab)
        original = unique_index(self.data["reviews"], "token")
        rankings = self.data["cell_rankings"]
        errors = coverage_errors(original, mapping, "reviewed draft tokens")
        errors.extend(coverage_errors(rankings, {r["cell_id"] for r in mapping.values()}, "blind ranking cells"))
        if errors:
            raise ValueError("; ".join(errors))
        result = {}
        for cell, tokens in rankings.items():
            if not tokens:
                raise ValueError(f"{cell}: empty ranking")
            for rank, token in enumerate(tokens, 1):
                if token in result:
                    raise ValueError(f"duplicate ranked token: {token}")
                if token not in mapping or mapping[token]["cell_id"] != cell:
                    raise ValueError(f"{token}: ranking cell binding drift")
                if original[token]["verdict"] not in self.data["verdict_categories"]:
                    raise ValueError(f"{token}: verdict has no declared statistical category")
                result[token] = {**original[token], **mapping[token], "rank": rank, "top2": rank <= 2}
        if set(result) != set(original):
            raise ValueError("rankings must cover every reviewed token exactly once")
        return result

    def token(self, token: str) -> dict[str, Any]:
        return self.reviews()[token]

    def _scenario_summary(self, scenario_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        verdicts = Counter(self.data["verdict_categories"][row["verdict"]] for row in rows)
        engineering = Counter(row["engineering_feel"] for row in rows)
        rank_sum = sum(row["rank"] for row in rows)
        return {
            **self.data["scenario_summary"][scenario_id],
            "rank_sum": rank_sum, "mean_rank": rank_sum / len(rows),
            "first_place_count": sum(row["rank"] == 1 for row in rows),
            "top2_count": sum(row["top2"] for row in rows),
            "verdict_counts": {key: verdicts[key] for key in ("PASS", "EDGE", "FAIL")},
            "engineering_counts": {key: engineering[key] for key in ("低", "中", "高")},
        }

    def scenario(self, scenario_id: str) -> dict[str, Any]:
        if scenario_id not in self.data["scenario_summary"]:
            raise KeyError(f"Unknown review scenario: {scenario_id}")
        rows = sorted((row for row in self.reviews().values() if row["scenario_id"] == scenario_id),
                      key=lambda row: row["cell_id"])
        if not rows:
            raise ValueError(f"{scenario_id}: no reviewed drafts")
        return {"scenario_id": scenario_id, "summary": self._scenario_summary(scenario_id, rows),
                "cells": rows, "winner": None, "route_eliminated": False}

    def summary(self) -> dict[str, Any]:
        rows = list(self.reviews().values())
        errors = coverage_errors(self.data["scenario_summary"], {row["scenario_id"] for row in rows}, "blind scenario summaries")
        if errors:
            raise ValueError("; ".join(errors))
        return {
            "status": self.data["status"], "review_count": len(rows),
            "cell_count": len(self.data["cell_rankings"]),
            "scenario_summary": {sid: self._scenario_summary(sid, [r for r in rows if r["scenario_id"] == sid])
                                 for sid in self.data["scenario_summary"]},
            "revision_targets": self.data["revision_targets"],
            "winner": None, "route_eliminated": False, "next_gate": self.data["next_gate"],
        }

    def validate_integrity(self, lab: ControlledMicrodraftRuntime) -> list[str]:
        errors = []
        if self.data.get("authority") != "SHADOW_ONLY":
            errors.append("blind review must remain SHADOW_ONLY")
        if self.data.get("output_authority") != "BLIND_REVIEW_SIGNAL_ONLY":
            errors.append("blind review output authority drift")
        policy = self.data.get("policy", {})
        for key in ("evidence_effect", "open_interface_effect", "stable_active_effect", "canonical_prose_effect", "competition_effect"):
            if policy.get(key) != "NONE":
                errors.append(f"blind review authority effect {key} must remain NONE")
        for key in ("automatic_winner", "automatic_route_elimination"):
            if policy.get(key) is not False:
                errors.append(f"blind review policy {key} must remain false")
        try:
            rows = self.reviews(lab)
        except (ValueError, KeyError, OSError) as exc:
            return [*errors, str(exc)]
        errors.extend(coverage_errors(self.data["scenario_summary"], {r["scenario_id"] for r in rows.values()}, "blind scenario summaries"))
        raw = self.raw_review()
        for token in rows:
            if token not in raw:
                errors.append(f"Raw review missing token {token}")
        if "各 cell 排序汇总" not in raw or "跨 cell 总体观察" not in raw:
            errors.append("Raw review missing required summary sections")
        return errors
