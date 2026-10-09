"""Fixed extraction recipes and catalog-registered, reproducible output files."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
from typing import Any

from ..assets import AssetCatalog, AssetError, CatalogStore
from ..assets.paths import repository_path
from ..assets.transactions import commit_unlocked, digest, recover_unlocked
from ..schema import validate_instance
from .adapters import extract_units


LOCK_PATH = "requirements/extraction.lock.json"
FORMATS = {"application/pdf": "PDF", "application/epub+zip": "EPUB", "text/html": "HTML", "application/xhtml+xml": "HTML"}


class ExtractionConfigError(AssetError):
    """A malformed extraction request; CLI returns usage/configuration exit code 2."""


def canonical_bytes(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def validate(root: Path, document: Any, schema: str) -> None:
    findings = validate_instance(document, root / f"schemas/{schema}.schema.json")
    if findings:
        raise AssetError(f"INVALID_{schema.upper()}: " + "; ".join(findings))


def code_digest(*names: str) -> str:
    return digest(b"".join(name.encode("utf-8") + b"\0" + (Path(__file__).parent / name).read_bytes() for name in names))


def toolchain_diff(registered: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Describe execution metadata changes without declaring a content change."""
    return {
        key: {"registered": registered.get(key), "current": current.get(key)}
        for key in sorted(registered.keys() | current.keys())
        if registered.get(key) != current.get(key)
    }


class ExtractionRepository:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.root = catalog.root
        self.rebuild_reports: dict[str, dict[str, Any]] = {}

    def config(self, asset_ref: str, supplied: dict[str, Any] | None = None) -> dict[str, Any]:
        supplied = {} if supplied is None else supplied
        if not isinstance(supplied, dict):
            raise ExtractionConfigError("extraction config must be an object")
        media_type = self.catalog.assets[asset_ref]["media_type"]
        format_name = supplied.get("format", FORMATS.get(media_type, "TEXT" if media_type.startswith("text/") else None))
        document = {
            "format": format_name, "encoding": "utf-8", "normalization": "NONE",
            "newline_conversion": "NONE", "markup_breaks": "BR_TO_LF", **supplied,
        }
        findings = validate_instance(document, self.root / "schemas/extraction_config.schema.json")
        if findings:
            raise ExtractionConfigError("invalid extraction config: " + "; ".join(findings))
        if "pdf_pages" in document and document["pdf_pages"] != sorted(document["pdf_pages"]):
            raise ExtractionConfigError("pdf_pages must be unique and in ascending physical-page order")
        return document

    def extractor(self, format_name: str) -> dict[str, Any]:
        raw = repository_path(self.root, LOCK_PATH).read_bytes()
        lock = json.loads(raw)
        if lock.get("schema_version") != 1 or lock.get("python") not in {">=3.10", ">=3.12,<3.13"} or lock.get("markup") != {"package": "python-stdlib", "adapter_version": 1} or lock.get("text") != {
            "encoding": "utf-8", "newline_conversion": "NONE", "unicode_normalization": "NONE",
        }:
            raise ExtractionConfigError("unsupported extraction dependency lock")
        package_version = None
        if format_name == "PDF":
            if lock.get("pdf", {}).get("package") != "PyMuPDF" or not isinstance(lock["pdf"].get("version"), str) or not lock["pdf"]["version"]:
                raise ExtractionConfigError("unsupported PDF extractor dependency")
            try:
                package_version = importlib.metadata.version("PyMuPDF")
            except importlib.metadata.PackageNotFoundError as exc:
                raise AssetError("PDF_EXTRACTOR_NOT_INSTALLED: install declared project dependencies") from exc
        return {
            "name": "rcwh-extraction", "version": 1,
            "code_sha256": code_digest("adapters.py", "extraction.py"),
            "python": f"{platform.python_implementation()} {platform.python_version()}",
            "package_version": package_version,
        }

    def execution_stamp(self, format_name: str) -> dict[str, Any]:
        return {
            "extractor": self.extractor(format_name),
            "dependency_lock": {"path": LOCK_PATH, "sha256": digest(repository_path(self.root, LOCK_PATH).read_bytes())},
        }

    def compile(self, asset_ref: str, supplied: dict[str, Any] | None = None) -> tuple[dict[str, Any], bytes]:
        asset = self.catalog.resolve(asset_ref)
        config = self.config(asset_ref, supplied)
        extractor = self.extractor(config["format"])
        units = extract_units(asset.path.read_bytes(), config)
        for item in units:
            item["input"] = {"asset_ref": asset_ref, "sha256": asset.sha256}
            validate(self.root, item, "extraction_unit")
        output = b"".join(canonical_bytes(item) for item in units)
        output_sha = digest(output)
        matches = [record for record in self.catalog.assets.values() if record["sha256"] == output_sha]
        if len(matches) > 1:
            raise AssetError("duplicate extraction output SHA")
        output_ref = f"asset:sha256:{output_sha}"
        if matches:
            record = matches[0]
            if record["kind"] != "CORPUS_DERIVATIVE" or record.get("derived_from") != [asset_ref]:
                raise AssetError("EXTRACTION_DEDUP_PROVENANCE_CONFLICT")
            if self.catalog.resolve(record["id"]).path.read_bytes() != output:
                raise AssetError("extraction deduplication bytes disagree")
            output_ref = record["id"]
        body = {
            "schema_version": 1, "input": {"asset_ref": asset_ref, "sha256": asset.sha256},
            "config": config, "extractor": extractor,
            "dependency_lock": {"path": LOCK_PATH, "sha256": digest(repository_path(self.root, LOCK_PATH).read_bytes())},
            "output": {"asset_ref": output_ref, "sha256": output_sha, "bytes": len(output)},
            "unit_refs": [item["unit_ref"] for item in units],
        }
        manifest = {**body, "id": f"extraction:{digest(canonical_bytes(body))}"}
        validate(self.root, manifest, "extraction_manifest")
        return manifest, output

    def build(self, asset_ref: str, supplied: dict[str, Any] | None = None) -> dict[str, Any]:
        store = CatalogStore(self.root)
        with store.lock(exclusive=True):
            recover_unlocked(store)
            assets, origins = store.read_unlocked()
            catalog = AssetCatalog(self.root, assets, origins)
            findings = catalog.validate(receipt_records=store.receipts_unlocked())
            if findings:
                raise AssetError("invalid storage before extraction: " + "; ".join(findings))
            self.catalog = catalog
            manifest, output = self.compile(asset_ref, supplied)
            token = manifest["id"].split(":", 1)[1]
            directory = f"corpus/extractions/{token}"
            changes = {}

            def register(relative: str, raw: bytes, inputs: list[str]) -> str:
                sha = digest(raw)
                matches = [item for item in assets.values() if item["sha256"] == sha]
                if len(matches) > 1:
                    raise AssetError("duplicate extraction output SHA")
                origin_id = f"origin:extraction:{token}:{Path(relative).stem}"
                if matches:
                    record = matches[0]
                    if catalog.resolve(record["id"]).path.read_bytes() != raw:
                        raise AssetError("extraction deduplication bytes disagree")
                    # A provenance declaration cannot be silently added to unrelated bytes.
                    if record.get("kind") != "CORPUS_DERIVATIVE" or record.get("derived_from") != inputs:
                        raise AssetError("EXTRACTION_DEDUP_PROVENANCE_CONFLICT")
                else:
                    target = repository_path(self.root, relative)
                    if target.exists():
                        raise AssetError(f"extraction output path already exists: {relative}")
                    record = {
                        "id": f"asset:sha256:{sha}", "path": relative, "sha256": sha, "bytes": len(raw),
                        "media_type": "application/x-ndjson" if relative.endswith(".jsonl") else "application/json",
                        "kind": "CORPUS_DERIVATIVE", "immutable": True, "origin_refs": [], "derived_from": inputs,
                    }
                    assets[record["id"]] = record
                    changes[relative] = raw
                origin = {
                    "id": origin_id, "asset_ref": record["id"], "sha256": sha, "batch_id": manifest["id"],
                    "origin_type": "DETERMINISTIC_EXTRACTION", "origin_container": asset_ref,
                    "original_path": relative, "disposition": "DEDUPLICATED" if matches else "RETAINED",
                }
                if origin_id in origins:
                    existing = origins[origin_id]
                    if any(existing[key] != value for key, value in origin.items() if key != "disposition"):
                        raise AssetError("extraction origin identity conflict")
                else:
                    origins[origin_id] = origin
                    record["origin_refs"].append(origin_id)
                return record["id"]

            output_ref = register(f"{directory}/units.jsonl", output, [asset_ref])
            manifest["output"]["asset_ref"] = output_ref
            manifest_ref = register(f"{directory}/manifest.json", canonical_bytes(manifest), [asset_ref, output_ref])
            changes.update(store.serialized_records(assets, origins))
            commit_unlocked(store, changes)
            return {"manifest_ref": manifest_ref, "manifest": manifest, "authority_effect": "NONE"}

    def load(self, manifest_ref: str, *, rebuild: bool = True) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        # A failed recheck must not leave a previous PASS observation available.
        self.rebuild_reports.pop(manifest_ref, None)
        manifest_asset = self.catalog.resolve(manifest_ref)
        if self.catalog.assets[manifest_ref]["kind"] != "CORPUS_DERIVATIVE":
            raise AssetError("INVALID_EXTRACTION_ASSET_KIND")
        manifest = json.loads(manifest_asset.path.read_bytes())
        validate(self.root, manifest, "extraction_manifest")
        input_asset = self.catalog.resolve(manifest["input"]["asset_ref"])
        if input_asset.sha256 != manifest["input"]["sha256"]:
            raise AssetError("EXTRACTION_INPUT_HASH_MISMATCH")
        output = self.catalog.resolve(manifest["output"]["asset_ref"])
        if (output.sha256, output.size) != (manifest["output"]["sha256"], manifest["output"]["bytes"]):
            raise AssetError("EXTRACTION_OUTPUT_HASH_MISMATCH")
        body = {key: value for key, value in manifest.items() if key != "id"}
        if manifest["id"] != f"extraction:{digest(canonical_bytes(body))}":
            raise AssetError("EXTRACTION_ID_MISMATCH")
        expected_relations = {
            manifest_ref: [input_asset.id, output.id], output.id: [input_asset.id],
        }
        for reference, inputs in expected_relations.items():
            record = self.catalog.assets[reference]
            if record["kind"] != "CORPUS_DERIVATIVE" or record.get("derived_from") != inputs:
                raise AssetError("EXTRACTION_DERIVATION_MISMATCH")
        units = {}
        for line in output.path.read_bytes().splitlines():
            item = json.loads(line)
            validate(self.root, item, "extraction_unit")
            if item["input"] != manifest["input"]:
                raise AssetError("EXTRACTION_UNIT_INPUT_MISMATCH")
            if item["unit_ref"] in units or item["text_sha256"] != digest(item["text"].encode("utf-8")):
                raise AssetError("DUPLICATE_UNIT_OR_TEXT_HASH_MISMATCH")
            cursor = 0
            for node in item["nodes"]:
                if not cursor == node["start"] <= node["end"] <= len(item["text"]):
                    raise AssetError("INVALID_EXTRACTION_NODE_MAPPING")
                cursor = node["end"]
            if cursor != len(item["text"]):
                raise AssetError("INCOMPLETE_EXTRACTION_NODE_MAPPING")
            units[item["unit_ref"]] = item
        if list(units) != manifest["unit_refs"]:
            raise AssetError("EXTRACTION_UNIT_SET_MISMATCH")
        if rebuild:
            current_config = self.config(input_asset.id, manifest["config"])
            if current_config != manifest["config"]:
                raise AssetError("STALE_EXTRACTION_CONFIG")
            recreated, raw = self.compile(input_asset.id, current_config)
            content_fields = ("schema_version", "input", "config", "output", "unit_refs")
            if raw != output.path.read_bytes() or any(recreated[key] != manifest[key] for key in content_fields):
                raise AssetError("EXTRACTION_REBUILD_MISMATCH")
            registered = {key: manifest[key] for key in ("extractor", "dependency_lock")}
            current = {key: recreated[key] for key in ("extractor", "dependency_lock")}
            self.rebuild_reports[manifest_ref] = {
                "status": "PASS", "scope": "EXTRACTION_CONTENT_REBUILD",
                "manifest_ref": manifest_ref, "output_sha256": manifest["output"]["sha256"],
                "unit_count": len(units), "registered_toolchain": registered,
                "current_toolchain": current, "toolchain_diff": toolchain_diff(registered, current),
            }
        return manifest, units
