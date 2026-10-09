"""Reproducible paired blind packets and hash-bound submitted review signals."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED

from .assets import AssetCatalog, AssetError
from .assets.paths import repository_path
from .assets.transactions import digest
from .contracts import record_sha256
from .corpus.extraction import canonical_bytes, validate
from .io import load_data
from .microdraft import ControlledMicrodraftRuntime
from .workflow import ProjectState


class PairedReview:
    selection_path = "data/evaluation/paired_selection.json"

    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root

    def bound_file(self, binding: dict) -> bytes:
        raw = repository_path(self.root, binding["path"]).read_bytes()
        if digest(raw) != binding["sha256"]:
            raise AssetError(f"STALE_PAIRED_REVIEW_INPUT: {binding['path']}")
        return raw

    def bound_asset(self, binding: dict) -> bytes:
        asset = self.catalog.resolve(binding["asset_ref"])
        if asset.sha256 != binding["sha256"]:
            raise AssetError("STALE_PAIRED_REVIEW_ASSET")
        return asset.path.read_bytes()

    def packet(self, relative: str) -> tuple[bytes, dict]:
        protocol = load_data(repository_path(self.root, relative))
        validate(self.root, protocol, "paired_review_protocol")
        experiment = json.loads(self.bound_file(protocol["experiment"]))
        selected = ProjectState.from_repo(self.root)
        if experiment != selected.experiment():
            raise AssetError("PAIRED_REVIEW_EXPERIMENT_NOT_SELECTED")
        if selected.capability()["status"] != "PASS":
            raise AssetError("PAIRED_REVIEW_EXPERIMENT_INPUTS_INVALID")
        lab = ControlledMicrodraftRuntime.from_repo(self.root)
        lab.require_snapshot(experiment["source_basis"]["p6_ref"], experiment["source_basis"]["p6_snapshot_sha256"])
        ordered = sorted(experiment["pairs"], key=lambda p: digest((protocol["seed"] + p["baseline_token"]).encode()))
        mapping = []; public = []; files = {}
        for index, pair in enumerate(ordered, 1):
            pair_id = f"pair-{index:02d}"
            baseline_path = lab.drafts[pair["baseline_token"]]["artifact"]
            revised_path = pair["revised_artifact"]
            # Deterministically counterbalance old/new positions. The mapping is
            # stored separately and is never included in the reviewer archive.
            a, b = (baseline_path, revised_path) if index % 2 else (revised_path, baseline_path)
            entry = {"pair_id": pair_id, "baseline_token": pair["baseline_token"], "revised_token": pair["revised_token"],
                     "baseline_label": "A" if a == baseline_path else "B", "inputs": {}}
            candidates = []
            for label, path in (("A", a), ("B", b)):
                raw = repository_path(self.root, path).read_bytes()
                name = f"{pair_id}/{label}.txt"; files[name] = raw
                entry["inputs"][label] = {"path": path, "sha256": digest(raw)}
                candidates.append({"label": label, "file": name, "sha256": digest(raw)})
            mapping.append(entry); public.append({"pair_id": pair_id, "candidates": candidates})
        public_manifest = {"schema_version": 1, "kind": "PAIRED_BLIND_REVIEW_PACKET", "pairs": public,
                           "questions": protocol["questions"], "dimensions": protocol["dimensions"],
                           "instruction": "独立阅读每对 A/B，提交偏好、两份评分和理由。不要猜测来源路线或修订身份。",
                           "authority_effect": "NONE"}
        files["manifest.json"] = canonical_bytes(public_manifest)
        forbidden = ["baseline_token", "revised_token", "scenario_id", "probe_id", "focalizer", "MD-W", "RV-W", "artifacts/"]
        if any(term.encode() in raw for term in forbidden for raw in files.values()):
            raise AssetError("PAIRED_BLIND_PACKET_METADATA_LEAK")
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
            for name, raw in sorted(files.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.create_system = 3; info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
        packet = buffer.getvalue()
        coordinator = {"schema_version": 1, "protocol": {"path": relative, "sha256": digest(repository_path(self.root, relative).read_bytes())},
                       "packet_sha256": digest(packet), "experiment_sha256": record_sha256(experiment), "pairs": mapping,
                       "visibility": "COORDINATOR_ONLY_DO_NOT_SHARE_WITH_REVIEWER", "authority_effect": "NONE"}
        return packet, coordinator

    def selected_summary(self) -> dict:
        if not (self.root / self.selection_path).is_file():
            return {"status": "PENDING", "scope": "PAIRED_REVIEW_SUBMISSIONS", "review_count": 0, "authority_effect": "NONE"}
        selected = load_data(repository_path(self.root, self.selection_path))
        validate(self.root, selected, "paired_review_selection")
        self.bound_file(selected["protocol"])
        packet, mapping = self.packet(selected["protocol"]["path"])
        if self.bound_asset(selected["packet"]) != packet or self.bound_asset(selected["mapping"]) != canonical_bytes(mapping):
            raise AssetError("STALE_PAIRED_BLIND_PACKET_OR_MAPPING")
        protocol = load_data(repository_path(self.root, selected["protocol"]["path"]))
        pair_index = {p["pair_id"]: p for p in mapping["pairs"]}
        reviewers = set(); review_ids = set(); preferences = {"BASELINE": 0, "REVISED": 0, "TIE": 0, "NEITHER": 0}
        for binding in selected["reviews"]:
            review = json.loads(self.bound_file(binding)); validate(self.root, review, "paired_review")
            if review["protocol_sha256"] != selected["protocol"]["sha256"] or review["packet_sha256"] != selected["packet"]["sha256"]:
                raise AssetError("REVIEW_BINDING_DRIFT")
            reviewer = review["reviewer"]["id"]
            if reviewer in reviewers or reviewer in protocol["author_ids"] or review["id"] in review_ids:
                raise AssetError("DUPLICATE_OR_AUTHOR_PAIRED_REVIEWER")
            reviewers.add(reviewer); review_ids.add(review["id"])
            rows = {r["pair_id"]: r for r in review["pairs"]}
            if len(rows) != len(review["pairs"]) or set(rows) != set(pair_index):
                raise AssetError("INCOMPLETE_OR_DUPLICATE_PAIRED_REVIEW")
            if self.catalog.assets[review["raw_review"]["asset_ref"]]["kind"] != "REVIEW_RECORD":
                raise AssetError("PAIRED_REVIEW_RAW_ASSET_KIND")
            raw = json.loads(self.bound_asset(review["raw_review"]))
            projection = {key: review[key] for key in ("reviewer", "protocol_sha256", "packet_sha256", "pairs")}
            if raw != projection:
                raise AssetError("RAW_PAIRED_REVIEW_DOES_NOT_SUPPORT_RECORD")
            for pair_id, row in rows.items():
                if set(row["scores"]) != set(protocol["dimensions"]):
                    raise AssetError("PAIRED_REVIEW_DIMENSION_MISMATCH")
                preference = row["preference"]
                interpreted = preference if preference in {"TIE", "NEITHER"} else "BASELINE" if preference == pair_index[pair_id]["baseline_label"] else "REVISED"
                preferences[interpreted] += 1
        return {"status": "PASS" if len(reviewers) >= protocol["minimum_reviewers"] else "PENDING",
                "scope": "PAIRED_REVIEW_SUBMISSION_INTEGRITY", "review_count": len(reviewers),
                "minimum_reviewers": protocol["minimum_reviewers"], "pair_count": len(pair_index), "preferences": preferences,
                "independence_basis": "SUBMITTED_REVIEWER_ATTESTATIONS", "automatic_literary_pass": False,
                "winner": None, "stable_active_effect": "NONE", "authority_effect": "NONE"}
