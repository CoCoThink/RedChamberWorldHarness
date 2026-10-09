"""Fixed, rebuildable corpus candidates with exact layer and carrier references."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from ..assets import AssetCatalog, AssetError, CatalogStore
from ..assets.paths import repository_path
from ..assets.transactions import commit_unlocked, digest, recover_unlocked
from ..graph import ProvenanceGraph
from .extraction import ExtractionRepository, canonical_bytes, code_digest, validate
from .inputs import CorpusInputs
from .layers import classify, pdf_runs


def records_bytes(dataset_ref: str, kind: str, records: list[dict]) -> bytes:
    # Even an empty table has a dataset-scoped header, avoiding anonymous empty
    # byte assets and making its coverage explicit.
    header = {"schema_version": 1, "record_type": "FILE_SCOPE", "dataset_ref": dataset_ref, "file_kind": kind}
    return b"".join(canonical_bytes(item) for item in [header, *records])


class CorpusRepository:
    registry_directory = "data/corpus/datasets"

    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root

    def config(self, relative: str) -> dict:
        raw = repository_path(self.root, relative).read_bytes()
        config = json.loads(raw)
        validate(self.root, config, "corpus_build")
        if config["chapters"] != sorted(config["chapters"]):
            raise AssetError("UNSORTED_CORPUS_CHAPTERS")
        if config["scope"] == "FRONT80_CANDIDATE" and config["chapters"] != list(range(1, 81)):
            raise AssetError("INCOMPLETE_FRONT80_SCOPE")
        path = repository_path(self.root, config["inputs"]["path"])
        if digest(path.read_bytes()) != config["inputs"]["sha256"]:
            raise AssetError("STALE_CORPUS_INPUT_CONFIG")
        if config["layer_policy"]["main_size_range"][0] > config["layer_policy"]["main_size_range"][1]:
            raise AssetError("INVALID_CORPUS_SIZE_RANGE")
        return config

    def compile(self, relative: str) -> tuple[dict, dict[str, bytes]]:
        config = self.config(relative)
        inputs = CorpusInputs(self.catalog)
        input_check = inputs.verify(config["inputs"]["path"])
        if input_check["status"] != "PASS":
            raise AssetError("CORPUS_INPUTS_NOT_VERIFIED")
        fixed = inputs.config(config["inputs"]["path"])
        inventory_asset = self.catalog.resolve(fixed["inventory_report"]["asset_ref"])
        inventory = json.loads(inventory_asset.path.read_bytes())
        _, units = ExtractionRepository(self.catalog).load(fixed["pdf"]["extraction_ref"], rebuild=False)
        _, epub = ExtractionRepository(self.catalog).load(fixed["epub"]["extraction_ref"], rebuild=False)
        policy = config["layer_policy"]
        evidence = []
        for ref in policy["evidence_units"]:
            if ref not in units:
                raise AssetError(f"MISSING_LAYER_POLICY_EVIDENCE: {ref}")
            evidence.append({"unit_ref": ref, "text_sha256": units[ref]["text_sha256"], "text": units[ref]["text"]})
        scopes, used = [], set()
        chapter_rows = {row["chapter"]: row for row in inventory["witnesses"]["pdf"]["chapters"]}
        for chapter in config["chapters"]:
            if chapter not in chapter_rows:
                raise AssetError(f"MISSING_CORPUS_CHAPTER: {chapter}")
            scopes.append((chapter, f"chapter:{chapter}", chapter_rows[chapter]["spans"]))
        for appendix in config["appendices"]:
            start, end = appendix["pages"]
            if start > end:
                raise AssetError("INVALID_APPENDIX_SCOPE")
            spans = []
            for page in range(start, end + 1):
                ref = f"pdf:page:{page}"
                if ref not in inventory["witnesses"]["pdf"]["excluded_sections"][1]["units"]:
                    raise AssetError("APPENDIX_OVERLAPS_CHAPTER_SCOPE")
                spans.append({"unit_ref": ref, "start": 0, "end": len(units[ref]["text"])})
            scopes.append((None, appendix["section_ref"], spans))
        for variant in config["variant_starts"]:
            ref, start = variant["unit_ref"], variant["offset"]
            if ref not in units or not units[ref]["text"][start:].startswith(variant["expected_prefix"]):
                raise AssetError("STALE_VARIANT_BOUNDARY")
            if variant["chapter"] not in chapter_rows or not any(s["unit_ref"] == ref and s["start"] <= start < s["end"] for s in chapter_rows[variant["chapter"]]["spans"]):
                raise AssetError("VARIANT_OUTSIDE_DECLARED_CHAPTER")
        import pymupdf
        segments, scope_reports, styles, claimed = [], [], Counter(), {}
        with pymupdf.open(stream=self.catalog.resolve(fixed["pdf"]["asset_ref"]).path.read_bytes(), filetype="pdf") as document:
            page_cache = {}
            for chapter, section, spans in scopes:
                if section in used:
                    raise AssetError("DUPLICATE_CORPUS_SECTION")
                used.add(section)
                chunks = []
                for span in spans:
                    ref = span["unit_ref"]; page = int(ref.rsplit(":", 1)[1])
                    if any(max(span["start"], left) < min(span["end"], right) for left, right in claimed.get(ref, [])):
                        raise AssetError("OVERLAPPING_CORPUS_SCOPE")
                    claimed.setdefault(ref, []).append((span["start"], span["end"]))
                    if ref not in page_cache:
                        page_cache[ref] = pdf_runs(document, page, units[ref]["text"])
                    black_annotation = False
                    for run in page_cache[ref]:
                        start, end = max(span["start"], run["start"]), min(span["end"], run["end"])
                        if start >= end:
                            continue
                        cuts = {start, end}
                        variants = [v for v in config["variant_starts"] if v["chapter"] == chapter]
                        for v in variants:
                            if v["unit_ref"] == ref and start < v["offset"] < end:
                                cuts.add(v["offset"])
                        points = sorted(cuts)
                        for left, right in zip(points, points[1:]):
                            active_variant = any((page, left) >= (int(v["unit_ref"].rsplit(":", 1)[1]), v["offset"]) for v in variants)
                            text = units[ref]["text"][left:right]
                            piece = {**run, "text": text}
                            kind, reason = classify(piece, policy, variant=active_variant, appendix=chapter is None, black_annotation=black_annotation)
                            if kind == "ZHIPI" and reason == "WITNESS_LABEL_GLYPH" and run["style"]["color"] == policy["main_color"]:
                                black_annotation = True
                            elif kind == "MAIN_TEXT":
                                black_annotation = False
                            styles[(run["style"]["font"], run["style"]["size"], run["style"]["color"], kind)] += len(text)
                            item = {"kind": kind, "text": text, "span": {"unit_ref": ref, "start": left, "end": right},
                                    "style": run["style"], "reason": reason}
                            new_witness = kind == "ZHIPI" and reason == "WITNESS_LABEL_GLYPH"
                            if chunks and chunks[-1]["kind"] == kind and not new_witness:
                                chunks[-1]["text"] += text; chunks[-1]["spans"].append(item["span"])
                                if item["style"] not in chunks[-1]["styles"]: chunks[-1]["styles"].append(item["style"])
                                if reason not in chunks[-1]["reasons"]: chunks[-1]["reasons"].append(reason)
                            else:
                                chunks.append({"kind": kind, "text": text, "spans": [item["span"]], "styles": [item["style"]], "reasons": [reason]})
                scope_reports.append({"chapter": chapter, "section_ref": section, "spans": spans,
                                      "characters": sum(s["end"] - s["start"] for s in spans)})
                for index, chunk in enumerate(chunks, 1):
                    compact = []
                    for span in chunk["spans"]:
                        if compact and compact[-1]["unit_ref"] == span["unit_ref"] and compact[-1]["end"] == span["start"]:
                            compact[-1]["end"] = span["end"]
                        else: compact.append(dict(span))
                    segment = {"record_type": "SEGMENT", "dataset_ref": config["dataset_ref"],
                               "segment_id": f"hlm80:{section}:p{index:05d}", "chapter": chapter, "section_ref": section,
                               "kind": chunk["kind"], "text": chunk["text"], "text_sha256": digest(chunk["text"].encode()),
                               "asset_ref": fixed["pdf"]["asset_ref"],
                               "locator": {"extraction_ref": fixed["pdf"]["extraction_ref"], "spans": compact, "transforms": []},
                               "classification": {"method": "DECLARED_PDF_TYPOGRAPHY_V1", "reasons": sorted(chunk["reasons"]),
                                                  "styles": sorted(chunk["styles"], key=lambda s: (s["font"], s["size"], s["color"])), "human_review": "PENDING"}}
                    validate(self.root, segment, "corpus_segment")
                    segments.append(segment)
        annotations, tags, corrections = [], [], []
        for index, segment in enumerate(segments):
            if segment["kind"] == "ZHIPI" and segment["text"].strip():
                witness = re.match(r"\s*([甲己庚戚蒙列杨辰])([眉侧夹]?)", segment["text"])
                linked = []
                for direction in (-1, 1):
                    for other in segments[index + direction::direction] if direction == 1 else reversed(segments[:index]):
                        if other["section_ref"] != segment["section_ref"]: break
                        if other["kind"] == "MAIN_TEXT": linked.append(other["segment_id"]); break
                annotations.append({"record_type": "ANNOTATION", "segment_ref": segment["segment_id"],
                                    "witness": policy["witness_labels"].get(witness[1], "UNKNOWN") if witness else "UNKNOWN",
                                    "witness_label": witness[1] if witness else None, "form": witness[2] if witness and witness[2] else "UNKNOWN",
                                    "linked_main_text": sorted(set(linked)), "link_method": "NEAREST_MAIN_CONTEXT_ONLY", "human_review": "PENDING"})
            tags.append({"record_type": "EDITORIAL_TAG", "segment_ref": segment["segment_id"], "speaker": "UNKNOWN",
                         "relationship": "UNKNOWN", "pressure": "UNKNOWN", "text_form": "UNKNOWN", "human_review": "PENDING"})
        alignment = self.align(segments, inventory, epub, fixed)
        source_links = self.source_links(segments, units, fixed)
        unclassified = [s["segment_id"] for s in segments if s["kind"] == "UNCLASSIFIED" and s["text"].strip()]
        quality = {"schema_version": 1, "dataset_ref": config["dataset_ref"], "scope": config["scope"], "chapters": config["chapters"],
                   "sections": scope_reports, "segments_by_kind": dict(sorted(Counter(s["kind"] for s in segments).items())),
                   "unclassified_nonempty": unclassified, "unknown_annotation_witnesses": sum(a["witness"] == "UNKNOWN" for a in annotations),
                   "unaligned_segments": sum(a["status"] != "EXACT_IN_WHITESPACE_VIEW" for a in alignment), "source_links": source_links,
                   "layer_policy_evidence": evidence, "styles": [{"font": k[0], "size": k[1], "color": k[2], "kind": k[3], "characters": count} for k, count in sorted(styles.items())],
                   "text_corrections_applied": 0, "human_checks": [], "readiness": "CANDIDATE_PENDING_HUMAN_AUDIT",
                   "technical_findings": ["UNCLASSIFIED_TEXT_REQUIRES_REVIEW"] if unclassified else [], "authority_effect": "NONE"}
        products = {"segments.jsonl": records_bytes(config["dataset_ref"], "SEGMENTS", segments),
                    "annotations.jsonl": records_bytes(config["dataset_ref"], "ANNOTATIONS", annotations),
                    "alignment.jsonl": records_bytes(config["dataset_ref"], "ALIGNMENT", alignment),
                    "corrections.jsonl": records_bytes(config["dataset_ref"], "CORRECTIONS", corrections),
                    "editorial_tags.jsonl": records_bytes(config["dataset_ref"], "EDITORIAL_TAGS", tags),
                    "quality_report.json": canonical_bytes(quality)}
        for chapter in config["chapters"]:
            main = [s for s in segments if s["chapter"] == chapter and s["kind"] == "MAIN_TEXT"]
            products[f"chapters/ch{chapter:02d}.json"] = canonical_bytes({"dataset_ref": config["dataset_ref"], "chapter": chapter,
                                                                          "segment_refs": [s["segment_id"] for s in main],
                                                                          "text": "".join(s["text"] for s in main), "view_kind": "MAIN_TEXT_READING_VIEW", "readiness": quality["readiness"]})
        dependencies = [fixed[n][field] for n in ("pdf", "epub") for field in ("asset_ref", "extraction_ref")]
        dependencies.append(fixed["inventory_report"]["asset_ref"])
        manifest = {"schema_version": 1, "dataset_ref": config["dataset_ref"], "scope": config["scope"],
                    "build_config": {"path": relative, "sha256": digest(repository_path(self.root, relative).read_bytes()), "document": config},
                    "builder": {"name": "rcwh-corpus", "version": 1, "code_sha256": code_digest("dataset.py", "layers.py")},
                    "dependencies": [{"asset_ref": ref, "sha256": self.catalog.resolve(ref).sha256} for ref in dependencies],
                    "products": {name: {"asset_ref": f"asset:sha256:{digest(raw)}", "sha256": digest(raw), "bytes": len(raw)} for name, raw in sorted(products.items())},
                    "readiness": quality["readiness"], "authority_effect": "NONE"}
        graph = ProvenanceGraph.from_repo(self.root)
        manifest["source_record_digest"] = digest(canonical_bytes([s for s in sorted(graph.sources.values(), key=lambda s: s["id"])
                                                                  if s.get("container", {}).get("ref") == fixed["pdf"]["asset_ref"]]))
        validate(self.root, manifest, "corpus_manifest")
        return manifest, products

    @staticmethod
    def align(segments: list, inventory: dict, epub: dict, fixed: dict) -> list[dict]:
        chapter_units = {s["chapter"]: s["unit_ref"] for s in inventory["witnesses"]["epub"]["spine"] if s["chapter"] is not None}
        views = {}
        for ref in chapter_units.values():
            text = epub[ref]["text"]; positions = [i for i, char in enumerate(text) if not char.isspace()]
            views[ref] = ("".join(text[i] for i in positions), positions)
        rows = []
        for segment in segments:
            row = {"record_type": "ALIGNMENT", "segment_ref": segment["segment_id"], "status": "UNALIGNED", "matches": [],
                   "transform": "REMOVE_UNICODE_WHITESPACE_ONLY", "edition_equivalence": "NOT_ESTABLISHED"}
            ref = chapter_units.get(segment["chapter"])
            needle = re.sub(r"\s", "", segment["text"])
            if ref and needle and segment["kind"] in {"MAIN_TEXT", "ZHIPI", "VARIANT"}:
                view, positions = views[ref]; matches = []; start = 0
                while (offset := view.find(needle, start)) != -1:
                    matches.append({"asset_ref": fixed["epub"]["asset_ref"], "extraction_ref": fixed["epub"]["extraction_ref"],
                                    "unit_ref": ref, "start": positions[offset], "end": positions[offset + len(needle) - 1] + 1})
                    start = offset + 1
                row["matches"] = matches
                row["status"] = "EXACT_IN_WHITESPACE_VIEW" if len(matches) == 1 else "AMBIGUOUS" if matches else "UNALIGNED"
            rows.append(row)
        return rows

    def source_links(self, segments: list, units: dict, fixed: dict) -> list[dict]:
        rows = []
        for source in sorted(ProvenanceGraph.from_repo(self.root).sources.values(), key=lambda s: s["id"]):
            if source.get("container", {}).get("ref") != fixed["pdf"]["asset_ref"] or source["locator"].get("schema_version") != 2:
                continue
            linked = sorted({segment["segment_id"] for segment in segments for span in segment["locator"]["spans"] for target in source["locator"]["spans"]
                             if target["unit_ref"] == span["unit_ref"] and max(target["start"], span["start"]) < min(target["end"], span["end"])})
            rows.append({"source_ref": source["id"], "segment_refs": linked, "status": "OVERLAPPING_RAW_SPANS" if linked else "OUTSIDE_DATASET_SCOPE"})
        return rows

    def registry(self) -> dict[str, dict]:
        result = {}
        directory = repository_path(self.root, self.registry_directory)
        for path in sorted(directory.glob("*.json")) if directory.exists() else []:
            record = json.loads(repository_path(self.root, path.relative_to(self.root).as_posix()).read_bytes())
            validate(self.root, record, "corpus_dataset")
            if record["dataset_ref"] in result:
                raise AssetError("DUPLICATE_DATASET_REF")
            if path.name != digest(record["dataset_ref"].encode()) + ".json":
                raise AssetError("MISPLACED_DATASET_REGISTRY_RECORD")
            repository_path(self.root, record["directory"])
            result[record["dataset_ref"]] = record
        return result

    def build(self, relative: str, output: str) -> dict:
        destination = repository_path(self.root, output)
        if not output.startswith("corpus/front80/") or destination.exists():
            raise AssetError("CORPUS_OUTPUT_MUST_BE_NEW_FRONT80_DIRECTORY")
        manifest, products = self.compile(relative)
        store = CatalogStore(self.root)
        with store.lock(exclusive=True):
            recover_unlocked(store)
            assets, origins = store.read_unlocked()
            self.catalog = AssetCatalog(self.root, assets, origins)
            findings = self.catalog.validate(receipt_records=store.receipts_unlocked())
            if findings: raise AssetError("invalid storage: " + "; ".join(findings))
            if digest(repository_path(self.root, relative).read_bytes()) != manifest["build_config"]["sha256"]:
                raise AssetError("CORPUS_BUILD_INPUT_CHANGED_DURING_COMPILE")
            for dependency in manifest["dependencies"]:
                if self.catalog.resolve(dependency["asset_ref"]).sha256 != dependency["sha256"]:
                    raise AssetError("CORPUS_BUILD_INPUT_CHANGED_DURING_COMPILE")
            if manifest["dataset_ref"] in self.registry():
                raise AssetError("DATASET_VERSION_ALREADY_EXISTS")
            refs = [item["asset_ref"] for item in manifest["dependencies"]]
            changes = {}
            def register(name, raw, dependencies):
                sha = digest(raw); matches = [a for a in assets.values() if a["sha256"] == sha]
                if matches:
                    raise AssetError(f"CORPUS_PRODUCT_ALREADY_EXISTS: create a new dataset version: {name}")
                path = f"{output}/{name}"; ref = f"asset:sha256:{sha}"
                origin_id = f"origin:corpus:{digest(manifest['dataset_ref'].encode())}:{digest(name.encode())}"
                assets[ref] = {"id": ref, "path": path, "sha256": sha, "bytes": len(raw),
                               "media_type": "application/x-ndjson" if name.endswith(".jsonl") else "application/json",
                               "kind": "CORPUS_DERIVATIVE", "immutable": True, "origin_refs": [origin_id], "derived_from": dependencies}
                origins[origin_id] = {"id": origin_id, "asset_ref": ref, "sha256": sha, "batch_id": manifest["dataset_ref"],
                                      "origin_type": "DETERMINISTIC_CORPUS_BUILD", "origin_container": relative,
                                      "original_path": path, "disposition": "RETAINED"}
                changes[path] = raw
                return ref
            for name, raw in products.items(): register(name, raw, refs)
            manifest_ref = register("manifest.json", canonical_bytes(manifest), refs + [p["asset_ref"] for p in manifest["products"].values()])
            registry_path = f"{self.registry_directory}/{digest(manifest['dataset_ref'].encode())}.json"
            registry = {"schema_version": 1, "dataset_ref": manifest["dataset_ref"], "manifest_ref": manifest_ref,
                        "manifest_sha256": assets[manifest_ref]["sha256"], "directory": output}
            changes[registry_path] = canonical_bytes(registry)
            changes.update(store.serialized_records(assets, origins))
            commit_unlocked(store, changes)
            return {"status": "PASS", "scope": "CORPUS_BUILD", **registry, "readiness": manifest["readiness"], "authority_effect": "NONE"}

    def load(self, dataset_ref: str, *, rebuild: bool = True) -> tuple[dict, dict[str, bytes]]:
        registry = self.registry()
        if dataset_ref not in registry: raise AssetError(f"UNKNOWN_DATASET: {dataset_ref}")
        binding = registry[dataset_ref]; asset = self.catalog.resolve(binding["manifest_ref"])
        if asset.sha256 != binding["manifest_sha256"] or self.catalog.assets[asset.id]["kind"] != "CORPUS_DERIVATIVE":
            raise AssetError("CORPUS_MANIFEST_BINDING_MISMATCH")
        manifest = json.loads(asset.path.read_bytes())
        validate(self.root, manifest, "corpus_manifest")
        if manifest["dataset_ref"] != dataset_ref: raise AssetError("CORPUS_DATASET_ID_MISMATCH")
        inputs = [d["asset_ref"] for d in manifest["dependencies"]]
        if asset.relative_path != f"{binding['directory']}/manifest.json" or self.catalog.assets[asset.id].get("derived_from") != inputs + [p["asset_ref"] for p in manifest["products"].values()]:
            raise AssetError("CORPUS_MANIFEST_DERIVATION_MISMATCH")
        for dependency in manifest["dependencies"]:
            if self.catalog.resolve(dependency["asset_ref"]).sha256 != dependency["sha256"]:
                raise AssetError("CORPUS_DEPENDENCY_HASH_MISMATCH")
        config = self.config(manifest["build_config"]["path"])
        if config != manifest["build_config"]["document"] or digest(repository_path(self.root, manifest["build_config"]["path"]).read_bytes()) != manifest["build_config"]["sha256"]:
            raise AssetError("STALE_CORPUS_BUILD_CONFIG")
        products = {}
        for name, record in manifest["products"].items():
            product = self.catalog.resolve(record["asset_ref"])
            if self.catalog.assets[product.id]["kind"] != "CORPUS_DERIVATIVE" or self.catalog.assets[product.id].get("derived_from") != inputs:
                raise AssetError("CORPUS_PRODUCT_DERIVATION_MISMATCH")
            if (product.sha256, product.size) != (record["sha256"], record["bytes"]) or product.relative_path != f"{binding['directory']}/{name}":
                raise AssetError("CORPUS_PRODUCT_BINDING_MISMATCH")
            products[name] = product.path.read_bytes()
        if rebuild:
            expected_manifest, expected_products = self.compile(manifest["build_config"]["path"])
            if canonical_bytes(expected_manifest) != asset.path.read_bytes() or expected_products != products:
                raise AssetError("STALE_CORPUS_BUILD_OR_PRODUCTS")
        return manifest, products

    def verify(self, dataset_ref: str, *, rebuild: bool = True, require_tracked: bool = False) -> dict:
        manifest, products = self.load(dataset_ref, rebuild=rebuild)
        quality = json.loads(products["quality_report.json"])
        findings = self.catalog.validate(require_tracked=require_tracked)
        if require_tracked:
            tracked = subprocess.run(["git", "ls-files", "-z"], cwd=self.root, capture_output=True, check=False)
            files = set(tracked.stdout.decode().split("\0"))
            required = {manifest["build_config"]["path"], manifest["build_config"]["document"]["inputs"]["path"],
                        f"{self.registry_directory}/{digest(dataset_ref.encode())}.json",
                        "schemas/corpus_build.schema.json", "schemas/corpus_segment.schema.json",
                        "schemas/corpus_manifest.schema.json", "schemas/corpus_dataset.schema.json"}
            required.update(f"src/rcwh/corpus/{name}.py" for name in ("dataset", "layers", "inputs", "extraction", "adapters"))
            required.update(p.relative_to(self.root).as_posix() for p in (self.root / "data/provenance/sources").glob("*.yaml"))
            findings.extend(f"untracked corpus dependency: {p}" for p in sorted(required-files))
        return {"status": "FAIL" if findings else "PASS", "scope": "CORPUS_INTEGRITY_AND_REBUILD" if rebuild else "CORPUS_STORAGE", "dataset_ref": dataset_ref,
                "findings": findings, "segments_by_kind": quality["segments_by_kind"], "unclassified_nonempty": len(quality["unclassified_nonempty"]),
                "readiness": quality["readiness"], "human_checks": quality["human_checks"], "authority_effect": "NONE"}

    def query(self, dataset_ref: str, *, kind: str = "MAIN_TEXT", chapter: int | None = None, keyword: str | None = None, limit: int = 20) -> dict:
        if kind not in {"MAIN_TEXT", "ZHIPI", "EDITORIAL", "VARIANT", "APPENDIX", "UNCLASSIFIED"} or not 1 <= limit <= 200:
            raise AssetError("INVALID_CORPUS_QUERY")
        manifest, products = self.load(dataset_ref, rebuild=True)
        segments = [json.loads(line) for line in products["segments.jsonl"].splitlines()][1:]
        selected = [s for s in segments if s["kind"] == kind and s["text"].strip() and (chapter is None or s["chapter"] == chapter) and (keyword is None or keyword in s["text"])]
        results = []
        for segment in selected[:limit]:
            item = dict(segment); offset = segment["text"].find(keyword) if keyword else 0
            item["context"] = segment["text"][max(0, offset-60):offset+len(keyword or "")+120]
            item["match_reason"] = "EXACT_KEYWORD_AND_METADATA" if keyword else "METADATA_FILTER"
            results.append(item)
        return {"status": "PASS", "dataset_ref": dataset_ref, "count": len(selected), "segments": results,
                "readiness": manifest["readiness"], "authority_effect": "NONE"}

    def show(self, dataset_ref: str, segment_id: str) -> dict:
        _, products = self.load(dataset_ref, rebuild=True)
        for line in products["segments.jsonl"].splitlines()[1:]:
            segment = json.loads(line)
            if segment["segment_id"] == segment_id: return segment
        raise AssetError(f"UNKNOWN_CORPUS_SEGMENT: {dataset_ref}/{segment_id}")
