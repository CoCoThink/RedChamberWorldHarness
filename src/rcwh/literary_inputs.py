"""Frozen literary examples and writing inputs, without adoption authority."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from .assets import AssetCatalog, AssetError
from .assets.discovery import AssetDiscovery
from .assets.paths import repository_path
from .assets.transactions import digest
from .corpus.dataset import CorpusRepository
from .corpus.extraction import canonical_bytes, validate
from .corpus.locators import source_digest
from .graph import ProvenanceGraph
from .io import load_data
from .provenance import ProvenanceRepository


class LiteraryInputs:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root

    def record(self, binding: dict) -> dict:
        raw = repository_path(self.root, binding["path"]).read_bytes()
        if digest(raw) != binding["sha256"]:
            raise AssetError(f"STALE_WRITING_INPUT: {binding['path']}")
        return load_data(repository_path(self.root, binding["path"]))

    def exemplars(self, relative: str) -> dict:
        spec = load_data(repository_path(self.root, relative))
        validate(self.root, spec, "exemplar_set")
        corpus = CorpusRepository(self.catalog)
        manifest, products = corpus.load(spec["dataset_ref"], rebuild=True)
        binding = corpus.registry()[spec["dataset_ref"]]
        if (binding["manifest_ref"], binding["manifest_sha256"]) != (spec["manifest_ref"], spec["manifest_sha256"]):
            raise AssetError("STALE_EXEMPLAR_DATASET")
        index = {s["segment_id"]: s for s in (json.loads(line) for line in products["segments.jsonl"].splitlines()[1:])}
        selected = []; seen = set()
        for item in spec["segments"]:
            if item["segment_id"] in seen:
                raise AssetError("DUPLICATE_EXEMPLAR_SEGMENT")
            seen.add(item["segment_id"])
            segment = index.get(item["segment_id"])
            if segment is None or segment["kind"] != "MAIN_TEXT" or not segment["text"].strip() or segment["text_sha256"] != item["text_sha256"]:
                raise AssetError(f"INVALID_OR_STALE_MAIN_EXEMPLAR: {item['segment_id']}")
            selected.append({**segment, "selection_reason": item["reason"]})
        from .corpus.audit import CorpusAudit
        audit = CorpusAudit(self.catalog).summary(spec["dataset_ref"], rebuild=False)
        return {"status": "PASS", "scope": "EXEMPLAR_REFERENCES", "spec": spec, "segments": selected,
                "report_kind": "COMPUTED_CHECK", "formal_exemplar_authorized": audit["status"] == "PASS",
                "readiness": "VERIFIED" if audit["status"] == "PASS" else manifest["readiness"], "human_audit": audit, "authority_effect": "NONE"}

    def package(self, relative: str, *, production: bool = False, require_tracked: bool = False) -> dict:
        spec = load_data(repository_path(self.root, relative))
        validate(self.root, spec, "writing_package")
        self.record(spec["exemplar_set"])
        examples = self.exemplars(spec["exemplar_set"]["path"])
        paths = {relative, spec["exemplar_set"]["path"], "schemas/writing_package.schema.json", "schemas/exemplar_set.schema.json"}
        findings = self.catalog.validate(require_tracked=require_tracked)
        for binding in spec["assets"]:
            asset = self.catalog.resolve(binding["asset_ref"])
            if asset.sha256 != binding["sha256"]:
                raise AssetError("STALE_WRITING_ASSET")
        for domain in ("world", "plan"):
            if len({item["path"] for item in spec[domain]}) != len(spec[domain]):
                raise AssetError(f"DUPLICATE_WRITING_{domain.upper()}_INPUT")
            for binding in spec[domain]:
                self.record(binding); paths.add(binding["path"])
        graph = ProvenanceGraph.from_repo(self.root)
        if len({s["source_ref"] for s in spec["sources"]}) != len(spec["sources"]):
            raise AssetError("DUPLICATE_WRITING_SOURCE")
        repository = ProvenanceRepository.from_repo(self.root)
        source_rows = []
        for binding in spec["sources"]:
            source = graph.sources.get(binding["source_ref"])
            if source is None or source_digest(source) != binding["record_sha256"]:
                raise AssetError("STALE_WRITING_SOURCE")
            source_rows.append(repository.source_report(source, locators=True))
        paths.update(p.relative_to(self.root).as_posix() for p in (self.root / "data/provenance/sources").glob("*.yaml"))
        if require_tracked:
            tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=self.root).decode().split("\0"))
            findings.extend(f"UNTRACKED_WRITING_INPUT: {p}" for p in sorted(paths-tracked))
        blockers = []
        if examples["readiness"] != "VERIFIED":
            blockers.append("CORPUS_HUMAN_LAYER_AUDIT_FAILED" if examples["human_audit"]["status"] == "FAIL" else "CORPUS_HUMAN_LAYER_AUDIT_PENDING")
        if any(row["status"] != "PASS" for row in source_rows): blockers.append("WRITING_SOURCE_LOCATOR_UNVERIFIED")
        # Actual full-source closure and paired blind-review admission are runtime
        # prerequisites. Frozen research packages cannot authorize production.
        if production:
            from .closure import InputClosure
            if InputClosure(self.root).verify(require_tracked=require_tracked)["status"] != "PASS":
                blockers.append("DECLARED_INPUT_CLOSURE_INCOMPLETE")
            from .paired_review import PairedReview
            if PairedReview(self.catalog).selected_summary()["status"] != "PASS":
                blockers.append("P9_PAIRED_REVIEW_PENDING")
            from .workflow import ProjectState
            from .world import WorldRuntime
            from .reconstruction import ReconstructionRegistry
            expected_world = {f"data/world/m3_{name}.json" for name in ("core", "locations", "presence", "body", "resources", "knowledge")}
            project = ProjectState.from_repo(self.root)
            if {item["path"] for item in spec["world"]} != expected_world:
                blockers.append("WRITING_PACKAGE_WORLD_INPUTS_INCOMPLETE")
            if project.data["owners"]["plan_constraints"] not in {item["path"] for item in spec["plan"]}:
                blockers.append("WRITING_PACKAGE_SELECTED_PLAN_MISSING")
            findings.extend(WorldRuntime.from_repo(self.root).validate_integrity(self.catalog, ReconstructionRegistry.from_repo(self.root)))
        return {"status": "FAIL" if findings or (production and blockers) else "PASS",
                "scope": "PRODUCTION_INPUT_ADMISSION" if production else "FROZEN_RESEARCH_WRITING_INPUTS",
                "package": spec, "input_sha256": digest(canonical_bytes(spec)), "exemplars": examples,
                "sources": source_rows, "findings": sorted(set(findings)), "production_blockers": blockers,
                "authority_effect": "NONE"}

    def index_map(self, dataset_ref: str, collection_ref: str) -> dict:
        """Map each Markdown table row; thematic references stay unresolved.

        An exact quoted phrase gives a text occurrence, not validation of the
        research interpretation. Ordinary names and chapter numbers cannot make
        a row count as resolved.
        """
        manifest, products = CorpusRepository(self.catalog).load(dataset_ref, rebuild=True)
        segments = [json.loads(line) for line in products["segments.jsonl"].splitlines()[1:]]
        assets = AssetDiscovery(self.catalog).query(collection=collection_ref)["assets"]
        rows = []
        for asset in assets:
            raw = self.catalog.resolve(asset["asset_id"]).path.read_bytes().decode("utf-8")
            offset = 0; table_header = None
            for line in raw.splitlines(keepends=True):
                stripped = line.strip()
                if not stripped.startswith("|"):
                    if stripped: table_header = None
                    offset += len(line); continue
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if all(re.fullmatch(r":?-+:?", cell or " ") for cell in cells):
                    offset += len(line); continue
                if table_header is None:
                    table_header = cells; offset += len(line); continue
                phrases = sorted(set(re.findall(r"[“《]([^”》]{4,})[”》]", line)))
                matches = []
                for phrase in phrases:
                    for segment in segments:
                        if segment["kind"] not in {"MAIN_TEXT", "ZHIPI"}: continue
                        start = 0
                        while (position := segment["text"].find(phrase, start)) != -1:
                            matches.append({"phrase": phrase, "segment_ref": segment["segment_id"],
                                            "kind": segment["kind"], "start": position, "end": position+len(phrase)})
                            start = position+1
                rows.append({"index_asset_ref": asset["asset_id"], "index_sha256": asset["sha256"],
                             "raw_span": {"start": offset, "end": offset+len(line)}, "row": cells, "table_header": table_header,
                             "status": "EXACT_TEXT_OCCURRENCES" if matches else "UNRESOLVED_THEMATIC_REFERENCE",
                             "matches": matches, "interpretation_review": "PENDING"})
                offset += len(line)
        return {"schema_version": 1, "dataset_ref": dataset_ref, "collection_ref": collection_ref,
                "manifest_sha256": CorpusRepository(self.catalog).registry()[dataset_ref]["manifest_sha256"],
                "index_assets": [{"asset_ref": a["asset_id"], "sha256": a["sha256"]} for a in assets],
                "rows": rows, "resolved_text_occurrences": sum(bool(r["matches"]) for r in rows),
                "unresolved_rows": sum(not r["matches"] for r in rows), "authority_effect": "NONE"}

    def dataset_map(self, old_ref: str, new_ref: str) -> dict:
        corpus = CorpusRepository(self.catalog)
        datasets = {}
        for ref in (old_ref, new_ref):
            _, products = corpus.load(ref, rebuild=True)
            datasets[ref] = [json.loads(line) for line in products["segments.jsonl"].splitlines()[1:]]
        old, new = datasets[old_ref], datasets[new_ref]
        by_unit = {}
        for segment in new:
            for span in segment["locator"]["spans"]:
                by_unit.setdefault((segment["asset_ref"], span["unit_ref"]), []).append((span, segment))
        targets = {}; reverse = {}
        for segment in old:
            matched = {}
            for span in segment["locator"]["spans"]:
                for other, candidate in by_unit.get((segment["asset_ref"], span["unit_ref"]), []):
                    if max(span["start"], other["start"]) < min(span["end"], other["end"]):
                        matched[candidate["segment_id"]] = candidate
            targets[segment["segment_id"]] = matched
            for identity in matched: reverse.setdefault(identity, []).append(segment["segment_id"])
        rows = []
        for segment in old:
            matched = targets[segment["segment_id"]]
            many_origins = any(len(reverse[identity])>1 for identity in matched)
            cardinality = "UNMAPPED" if not matched else "MANY_TO_MANY" if len(matched)>1 and many_origins else "ONE_TO_MANY" if len(matched)>1 else "MANY_TO_ONE" if many_origins else "ONE_TO_ONE"
            rows.append({"old_segment_ref": segment["segment_id"], "new_segment_refs": sorted(matched), "cardinality": cardinality,
                         "exact_text_and_layer": len(matched)==1 and next(iter(matched.values()))["text_sha256"]==segment["text_sha256"] and next(iter(matched.values()))["kind"]==segment["kind"]})
        registry = corpus.registry()
        return {"schema_version": 1, "old_dataset_ref": old_ref, "new_dataset_ref": new_ref,
                "old_manifest_sha256": registry[old_ref]["manifest_sha256"], "new_manifest_sha256": registry[new_ref]["manifest_sha256"],
                "method": "RAW_CARRIER_SPAN_OVERLAP_ONLY", "rows": rows,
                "new_unmapped_segments": sorted(s["segment_id"] for s in new if s["segment_id"] not in reverse), "authority_effect": "NONE"}
