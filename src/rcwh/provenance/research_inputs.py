"""Opt-in, byte-bound supplementary records; never a global graph overlay.

Integrity permits research preparation only. MODEL reading references and even
successful derivative locators cannot qualify an original facsimile reading.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..assets import AssetCatalog, AssetError, CatalogStore
from ..assets.paths import repository_path
from ..assets.transactions import digest
from ..corpus.extraction import validate
from ..graph import ProvenanceGraph
from ..io import load_data
from ..schema import validate_instance
from .repository import ProvenanceRepository


LIMITATIONS = (
    "MODEL_ONLY: supplementary records have no adoption or publication authority.",
    "READING_REFS_BYTE_IDENTITY_ONLY: matching bytes do not qualify a reading.",
    "DERIVATIVE_LOCATORS_ONLY: machine checks cannot establish original-image transcription fidelity.",
    "NO_SUPERSESSION: old IDs, cashflow duration and completed property allocation claims remain unchanged.",
    "NO_HISTORICAL_TO_NARRATIVE_UPGRADE: historical feasibility is not a novel event assertion.",
)


class ResearchSourceInputs:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root

    def report(self, relative: str | dict, *, chapter: int, mode: str = "RESEARCH") -> dict:
        """Return PENDING evidence with PASS integrity, or FAIL with no usable records.

        ``relative`` may be an exact {path, sha256} binding (preferred by request
        renderers). Paths are repository-relative and include schemas, root graph
        files, catalog metadata and all reachable registered/bound asset bytes.
        Unregistered references without a byte binding are explicitly unresolved.
        """
        result: dict[str, Any] = {
            "status": "FAIL", "integrity_status": "FAIL", "evidence_readiness": "PENDING",
            "scope": "EXPLICIT_SUPPLEMENTARY_RESEARCH_INPUTS", "qualification": "MODEL",
            "authority_effect": "NONE", "chapter": chapter, "records": {"sources": [], "claims": []},
            "source_reports": [], "reading_refs": [], "paths": [], "findings": [],
            "limitations": list(LIMITATIONS), "unregistered_asset_refs": [],
        }
        paths: set[str] = set()
        try:
            if mode != "RESEARCH":
                raise AssetError("RESEARCH_SOURCE_SET_REQUIRES_RESEARCH_MODE")
            if isinstance(chapter, bool) or not isinstance(chapter, int):
                raise AssetError("INVALID_RESEARCH_CHAPTER")
            spec_path = relative["path"] if isinstance(relative, dict) else relative
            if isinstance(relative, dict):
                self._bound(relative, paths)
            spec = load_data(repository_path(self.root, spec_path)); paths.add(spec_path)
            self._validate(spec, "research_source_set", paths)
            if chapter not in spec["chapters"]:
                raise AssetError("RESEARCH_SOURCE_SET_CHAPTER_OUT_OF_SCOPE")
            self._no_supersession(spec)
            result["spec"] = spec
            result["input_sha256"] = digest(repository_path(self.root, spec_path).read_bytes())
            bindings = spec["source_bindings"] + spec["claim_bindings"] + spec["reading_refs"]
            if len({b["path"] for b in bindings}) != len(bindings):
                raise AssetError("DUPLICATE_RESEARCH_INPUT_PATH")
            sources = self._records(spec["source_bindings"], "sources", "source", paths)
            claims = self._records(spec["claim_bindings"], "claims", "claim", paths)
            for ref in spec["reading_refs"]:
                self._bound(ref, paths)
            result["reading_refs"] = spec["reading_refs"]

            # Load the untouched legacy graph, never merge or write supplementary IDs.
            for dirname in ("sources", "claims", "decisions", "implementations", "axes"):
                for file in sorted((self.root / f"data/provenance/{dirname}").glob("*.yaml")):
                    path = file.relative_to(self.root).as_posix()
                    repository_path(self.root, path); paths.add(path)
            graph = ProvenanceGraph.from_repo(self.root)
            for records, schema in ((graph.sources, "source"), (graph.claims, "claim"),
                                    (graph.decisions, "decision"), (graph.implementations, "implementation"),
                                    (graph.title_axes, "title_axis")):
                for record in records.values():
                    self._validate(record, schema, paths)
            old_ids = set(graph.sources) | set(graph.claims) | set(graph.decisions) | set(graph.implementations) | set(graph.title_axes)
            new_ids = [record["id"] for record in sources + claims]
            if len(set(new_ids)) != len(new_ids):
                raise AssetError("DUPLICATE_RESEARCH_RECORD_ID")
            if old_ids.intersection(new_ids):
                raise AssetError("RESEARCH_RECORD_OLD_ID_COLLISION: " + ", ".join(sorted(old_ids.intersection(new_ids))))
            source_index = {source["id"]: source for source in sources}
            used_sources = dict(source_index)
            for claim in claims:
                if "research_report" in claim:
                    self._bound(claim["research_report"], paths)
                if not claim["support"]:
                    raise AssetError(f"RESEARCH_CLAIM_MISSING_SUPPORT: {claim['id']}")
                for edge in claim["support"]:
                    identity = edge["source"]
                    if identity not in source_index and identity not in graph.sources:
                        raise AssetError(f"RESEARCH_CLAIM_UNKNOWN_SUPPORT: {identity}")
                    used_sources[identity] = source_index.get(identity, graph.sources.get(identity))

            asset_bindings = {}
            for binding in spec.get("asset_bindings", []):
                if binding["asset_ref"] in asset_bindings:
                    raise AssetError("DUPLICATE_RESEARCH_ASSET_BINDING")
                self._bound(binding, paths)
                if binding["asset_ref"].startswith("asset:sha256:") and binding["asset_ref"] != f"asset:sha256:{binding['sha256']}":
                    raise AssetError("RESEARCH_ASSET_ID_HASH_MISMATCH")
                asset_bindings[binding["asset_ref"]] = binding
            # These metadata files determine registration, without scanning unrelated carriers.
            paths.update(CatalogStore(self.root).metadata_paths())
            repository = ProvenanceRepository(graph, self.catalog)
            unknown: set[str] = set()
            visited: set[str] = set()
            for source in used_sources.values():
                self._source_dependencies(source, paths, asset_bindings, unknown, visited)
                computed = repository.source_report(source, locators=True)
                hard = [finding for finding in computed["findings"]
                        if not any(f"unknown asset: {ref}" in finding for ref in unknown)
                        and not finding.startswith("LOCATOR_VERSION_UNVERIFIED:")
                        and not finding.startswith("MISSING_LOCAL_CONTAINER:")
                        and finding != "MISSING_LOCAL_CONTAINER"]
                row = {"source_id": source["id"], "status": "FAIL" if hard else "PENDING",
                       "evidence_readiness": "PENDING", "computed_source_report": computed,
                       "limitations": list(LIMITATIONS)}
                result["source_reports"].append(row)
                if hard:
                    result["findings"].extend(f"{source['id']}: {finding}" for finding in hard)
            result["unregistered_asset_refs"] = sorted(unknown)
            if not result["findings"]:
                result.update(status="PENDING", integrity_status="PASS", records={"sources": sources, "claims": claims})
            if unknown:
                result["limitations"].append("ASSET_REGISTRATION_PENDING: " + ", ".join(sorted(unknown)))
            if not spec["reading_refs"]:
                result["limitations"].append("NO_READING_REFERENCES: declared PASS is not evidence of a completed reading.")
            result["limitations"].extend(spec.get("limitations", []))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            result["findings"].append(str(exc))
        result["paths"] = sorted(paths)
        result["findings"] = sorted(set(result["findings"]))
        return result

    def _bound(self, binding: dict, paths: set[str]) -> bytes:
        raw = repository_path(self.root, binding["path"]).read_bytes()
        paths.add(binding["path"])
        if digest(raw) != binding["sha256"]:
            raise AssetError(f"STALE_RESEARCH_INPUT: {binding['path']}")
        return raw

    def _validate(self, record: Any, schema: str, paths: set[str]) -> None:
        relative = f"schemas/{schema}.schema.json"
        repository_path(self.root, relative); paths.add(relative)
        validate(self.root, record, schema)

    @staticmethod
    def _no_supersession(record: Any) -> None:
        if isinstance(record, dict):
            for key, value in record.items():
                if key.lower() in {"supersedes", "superseded_by", "replaces", "replacement_for", "same_as", "explicit_mappings"}:
                    raise AssetError(f"RESEARCH_SUPERSESSION_FORBIDDEN: {key}")
                ResearchSourceInputs._no_supersession(value)
        elif isinstance(record, list):
            for value in record:
                ResearchSourceInputs._no_supersession(value)

    def _records(self, bindings: list[dict], wrapper: str, schema: str, paths: set[str]) -> list[dict]:
        records = []
        for binding in bindings:
            self._bound(binding, paths)
            document = load_data(repository_path(self.root, binding["path"]))
            if isinstance(document, dict) and wrapper in document:
                if document.get("schema_version") != 1 or not isinstance(document[wrapper], list) or not document[wrapper]:
                    raise AssetError(f"INVALID_RESEARCH_{wrapper.upper()}_WRAPPER")
                items = document[wrapper]
            else:
                items = [document]
            self._no_supersession(document)
            for record in items:
                self._validate(record, schema, paths)
                if record.get("authority_effect", "NONE") != "NONE":
                    raise AssetError("RESEARCH_RECORD_AUTHORITY_UPGRADE")
                records.append(record)
        return records

    def _asset(self, ref: str, expected: str | None, paths: set[str], bindings: dict,
               unknown: set[str], visited: set[str]) -> bytes | None:
        if ref in self.catalog.assets:
            asset = self.catalog.resolve(ref)
            if expected is not None and asset.sha256 != expected:
                raise AssetError(f"RESEARCH_ASSET_HASH_MISMATCH: {ref}")
            paths.add(asset.relative_path)
            raw = asset.path.read_bytes()
            if ref in bindings and (bindings[ref]["sha256"] != asset.sha256 or bindings[ref]["path"] != asset.relative_path):
                raise AssetError(f"RESEARCH_ASSET_BINDING_CONFLICT: {ref}")
            if ref not in visited:
                visited.add(ref)
                for parent in self.catalog.assets[ref].get("derived_from", []):
                    self._asset(parent, None, paths, bindings, unknown, visited)
            return raw
        unknown.add(ref)
        if ref not in bindings:
            return None
        binding = bindings[ref]
        if expected is not None and binding["sha256"] != expected:
            raise AssetError(f"RESEARCH_ASSET_HASH_MISMATCH: {ref}")
        return self._bound(binding, paths)

    def _source_dependencies(self, source: dict, paths: set[str], bindings: dict,
                             unknown: set[str], visited: set[str]) -> None:
        self._validate(source, "source", paths)
        if digest(source["text"].encode("utf-8")) != source["text_sha256"]:
            raise AssetError(f"SOURCE_TEXT_SHA_MISMATCH: {source['id']}")
        verification = source["locator_verification"]
        if verification["status"] == "STALE":
            raise AssetError(f"STALE_RESEARCH_LOCATOR: {source['id']}")
        for field in ("container", "carrier_capture", "excerpt_revision"):
            if field in source:
                binding = source[field]
                self._asset(binding["ref"], binding["sha256"], paths, bindings, unknown, visited)
                if field != "container":
                    paths.add(f"schemas/{'source_capture' if field == 'carrier_capture' else 'source_excerpt_review'}.schema.json")
        if "report_ref" in verification:
            self._asset(verification["report_ref"], verification["report_sha256"], paths, bindings, unknown, visited)
            paths.add("schemas/source_locator_report.schema.json")
        if "research_report" in source:
            self._bound(source["research_report"], paths)
        role = source.get("container_role", "")
        if role.startswith("MODEL_TRANSCRIPTION_DERIVATIVE"):
            if role != "MODEL_TRANSCRIPTION_DERIVATIVE_NOT_OFFICIAL_TEXT_LAYER" or source.get("tier") in {"W1_DIRECT", "W1_SEEN"}:
                raise AssetError("RESEARCH_DERIVATIVE_IDENTITY_UPGRADE")
            facsimile = source.get("facsimile_binding")
            schema_path = repository_path(self.root, "schemas/research_source_set.schema.json")
            definition = load_data(schema_path)
            errors = validate_instance(facsimile, {"$ref": "#/$defs/facsimile_binding", "$defs": definition["$defs"]})
            if errors:
                raise AssetError("INVALID_RESEARCH_FACSIMILE_BINDING: " + "; ".join(errors))
            for kind in ("image", "pdf"):
                self._asset(facsimile[f"{kind}_asset_ref"], facsimile[f"{kind}_sha256"], paths, bindings, unknown, visited)
            if source["container"]["ref"] in {facsimile["image_asset_ref"], facsimile["pdf_asset_ref"]}:
                raise AssetError("RESEARCH_DERIVATIVE_IS_NOT_ORIGINAL_FACSIMILE")
        locator = source["locator"]
        if locator.get("schema_version") == 2:
            self._validate(locator, "locator_v2", paths)
            if any(span["start"] >= span["end"] for span in locator["spans"]):
                raise AssetError("INVALID_RESEARCH_LOCATOR_SPAN")
            raw = self._asset(locator["extraction_ref"], None, paths, bindings, unknown, visited)
            if raw is not None:
                manifest = json.loads(raw)
                self._validate(manifest, "extraction_manifest", paths)
                self._validate(manifest["config"], "extraction_config", paths)
                self._bound(manifest["dependency_lock"], paths)
                if manifest["input"] != {"asset_ref": source.get("container", {}).get("ref"), "sha256": source.get("container", {}).get("sha256")}:
                    raise AssetError("RESEARCH_LOCATOR_CARRIER_MISMATCH")
                if manifest["output"]["sha256"] != locator["output_sha256"]:
                    raise AssetError("RESEARCH_LOCATOR_OUTPUT_HASH_MISMATCH")
                output = manifest["output"]
                units_raw = self._asset(output["asset_ref"], output["sha256"], paths, bindings, unknown, visited)
                if units_raw is not None:
                    units = {}
                    for line in units_raw.splitlines():
                        unit = json.loads(line)
                        self._validate(unit, "extraction_unit", paths)
                        identity = unit["unit_ref"]
                        if identity in units:
                            raise AssetError("DUPLICATE_RESEARCH_TEXT_UNIT")
                        if unit["input"] != manifest["input"]:
                            raise AssetError("RESEARCH_UNIT_INPUT_MISMATCH")
                        if digest(unit["text"].encode("utf-8")) != unit["text_sha256"]:
                            raise AssetError("RESEARCH_UNIT_TEXT_HASH_MISMATCH")
                        units[identity] = unit
                    if list(units) != manifest["unit_refs"]:
                        raise AssetError("RESEARCH_EXTRACTION_UNIT_COVERAGE_MISMATCH")
                    if len(units_raw) != output["bytes"]:
                        raise AssetError("RESEARCH_EXTRACTION_OUTPUT_SIZE_MISMATCH")
                    kinds = {"TEXT": "TEXT_SPANS", "PDF": "PDF_TEXT_SPANS",
                             "HTML": "HTML_TEXT_SPANS", "EPUB": "EPUB_TEXT_SPANS"}
                    if locator["kind"] != kinds[manifest["config"]["format"]]:
                        raise AssetError("LOCATOR_FORMAT_MISMATCH")
                    positions = {identity: index for index, identity in enumerate(units)}
                    previous, chunks = (-1, 0), []
                    for span in locator["spans"]:
                        identity = span["unit_ref"]
                        if identity not in units:
                            raise AssetError("UNKNOWN_TEXT_UNIT")
                        text = units[identity]["text"]
                        if not 0 <= span["start"] < span["end"] <= len(text):
                            raise AssetError("LOCATOR_SPAN_OUT_OF_RANGE")
                        position = (positions[identity], span["start"])
                        if position < previous:
                            raise AssetError("OVERLAPPING_OR_REORDERED_SPANS")
                        previous = (position[0], span["end"])
                        chunks.append(text[span["start"]:span["end"]])
                    excerpt = locator["joiner"].join(chunks)
                    if digest(excerpt.encode("utf-8")) != locator["raw_text_sha256"]:
                        raise AssetError("LOCATOR_EXCERPT_HASH_MISMATCH")
                    if excerpt != source["text"]:
                        raise AssetError("EXCERPT_MISMATCH")
            paths.update({"schemas/source_locator_report.schema.json", "schemas/extraction_manifest.schema.json",
                          "schemas/extraction_config.schema.json", "schemas/extraction_unit.schema.json",
                          "requirements/extraction.lock.json"})
