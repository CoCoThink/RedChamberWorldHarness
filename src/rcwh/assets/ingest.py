"""Daily asset intake and classification, without evidence or adoption side effects."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import mimetypes
from pathlib import Path
from typing import Any

from ..schema import validate_instance
from .catalog import AssetCatalog
from .paths import AssetError, repository_path
from .receipts import ReceiptLedger
from .store import CatalogStore
from .transactions import commit_unlocked, digest, recover_unlocked


KINDS = {
    "PRIMARY_TEXT_CONTAINER": "sources/primary/received",
    "PROJECT_REFERENCE": "sources/project",
    "PROJECT_RESEARCH": "research/received",
    "HISTORICAL_RECORD": "sources/historical",
    "IMPORT_RECORD": "archive/imports/received",
    "REVIEW_RECORD": "artifacts/reviews",
    "RELEASE_TEXT": "releases/received",
    "UNCLASSIFIED_INPUT": "sources/inbox",
    "CORPUS_DERIVATIVE": "corpus/received",
}
ROLES = ("MASTER_DRAFT", "GOVERNANCE", "FRONT80_INDEX", "CHAPTER_CARD", "HISTORICAL_RESEARCH", "LITERARY_REVIEW")


def json_bytes(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


class AssetIntake:
    def __init__(self, root: Path):
        self.store = CatalogStore(root)
        self.root = self.store.root

    def _load(self) -> tuple[AssetCatalog, dict[str, dict[str, Any]]]:
        assets, origins = self.store.read_unlocked()
        catalog = AssetCatalog(self.root, assets, origins)
        records = self.store.receipts_unlocked()
        findings = catalog.validate(receipt_records=records)
        if findings:
            raise AssetError("invalid asset storage: " + "; ".join(findings))
        return catalog, records

    def _destination(self, kind: str, sha: str, filename: str) -> str:
        if kind not in KINDS:
            raise AssetError(f"unknown asset kind: {kind}")
        if not filename or filename in {".", ".."} or any(c in filename for c in "/\\:\0"):
            raise AssetError(f"unsafe original filename: {filename}")
        return f"{KINDS[kind]}/{sha}/{filename}"

    def _check_destination(self, catalog: AssetCatalog, relative: str, raw: bytes) -> None:
        target = repository_path(self.root, relative)
        for asset in catalog.assets.values():
            if asset["path"].casefold() == relative.casefold() and asset["path"] != relative:
                raise AssetError(f"case-colliding asset path: {relative}")
        # Check unregistered files as well, including names differing only in case.
        parent = self.root
        for part in Path(relative).parts:
            if parent.is_dir() and any(p.name.casefold() == part.casefold() and p.name != part for p in parent.iterdir()):
                raise AssetError(f"case-colliding repository path: {relative}")
            parent = parent / part
        if target.exists() and (not target.is_file() or target.read_bytes() != raw):
            raise AssetError(f"refusing to overwrite different content: {relative}")

    def _receipt_changes(self, records: dict[str, dict[str, Any]]) -> dict[str, bytes]:
        changes = {}
        for record in records.values():
            errors = validate_instance(record, self.root / "schemas/asset_receipt.schema.json")
            if errors:
                raise AssetError("invalid receipt: " + "; ".join(errors))
            changes[self.store.receipt_path(record["receipt_id"])] = json_bytes(record)
        return changes

    def ingest(
        self, file: Path, *, origin: str, kind: str | None = None,
        role: str | None = None, receipt_key: str | None = None,
    ) -> dict[str, Any]:
        if not origin.strip() or (receipt_key is not None and not receipt_key.strip()):
            raise AssetError("origin and an explicit receipt key must be nonempty")
        if role is not None and role not in ROLES:
            raise AssetError(f"unknown intended role: {role}")
        if kind is not None and kind not in KINDS:
            raise AssetError(f"unknown asset kind: {kind}")
        # Retain the received path as an origin; never use it as a runtime carrier.
        file = file.absolute()
        if file.is_symlink() or any(parent.is_symlink() for parent in file.parents):
            raise AssetError(f"symlink is not an intake file: {file}")
        if not file.is_file():
            raise AssetError(f"intake requires a regular file: {file}")
        self._destination(kind or "UNCLASSIFIED_INPUT", "0" * 64, file.name)
        raw = file.read_bytes()
        sha = digest(raw)
        request = {
            "sha256": sha, "origin": origin, "original_path": str(file),
            "kind": kind, "role": role,
        }
        request_sha = digest(json_bytes(request))
        token = digest(("key:" + receipt_key).encode("utf-8")) if receipt_key is not None else request_sha
        receipt_id, origin_id = f"receipt:ingest:{token}", f"origin:ingest:{token}"
        with self.store.lock(exclusive=True):
            recover_unlocked(self.store)
            catalog, records = self._load()
            if receipt_id in records:
                if records[receipt_id]["request_sha256"] != request_sha:
                    raise AssetError("receipt key already used for a different intake request")
                return {**ReceiptLedger(catalog, records).describe(receipt_id), "replayed": True}
            matches = [a for a in catalog.assets.values() if a["sha256"] == sha]
            if len(matches) > 1:
                raise AssetError("duplicate SHA in catalog; repair it before intake")
            if matches:
                asset = matches[0]
                resolved = catalog.resolve(asset["id"])
                if resolved.path.read_bytes() != raw:
                    raise AssetError("deduplication bytes disagree")
                if kind not in {None, "UNCLASSIFIED_INPUT", asset["kind"]}:
                    raise AssetError("existing asset has a different kind; use assets classify for an unclassified asset")
                carrier_changes = {}
            else:
                asset = {
                    "id": f"asset:sha256:{sha}", "path": self._destination(kind or "UNCLASSIFIED_INPUT", sha, file.name),
                    "sha256": sha, "bytes": len(raw), "media_type": mimetypes.guess_type(file.name)[0] or "application/octet-stream",
                    "kind": kind or "UNCLASSIFIED_INPUT", "immutable": True, "origin_refs": [],
                }
                self._check_destination(catalog, asset["path"], raw)
                carrier_changes = {asset["path"]: raw}
                catalog.assets[asset["id"]] = asset
            if origin_id in catalog.origins:
                raise AssetError(f"origin already exists without its receipt: {origin_id}")
            asset["origin_refs"].append(origin_id)
            catalog.origins[origin_id] = {
                "id": origin_id, "asset_ref": asset["id"], "sha256": sha,
                "batch_id": "daily-ingest", "origin_type": "LOCAL_FILE",
                "origin_container": origin, "original_path": str(file),
                "disposition": "DEDUPLICATED" if matches else "RETAINED",
            }
            classified = asset["kind"] != "UNCLASSIFIED_INPUT"
            records[receipt_id] = {
                "schema_version": 1, "receipt_id": receipt_id, "request_sha256": request_sha,
                "asset_ref": asset["id"], "sha256": sha, "bytes": len(raw), "origin_ref": origin_id,
                "origin": origin, "original_filename": file.name, "original_path": str(file),
                "received_at": datetime.now(timezone.utc).isoformat(), "media_type": asset["media_type"],
                "intended_role": role,
                "classification": {"kind": asset["kind"], "roles": [role] if role else []} if classified else None,
            }
            changes = {**carrier_changes, **self.store.serialized_records(catalog.assets, catalog.origins), **self._receipt_changes(records)}
            commit_unlocked(self.store, changes)
            return {**ReceiptLedger(catalog, records).describe(receipt_id), "replayed": False}

    def classify(self, receipt_id: str, *, kind: str) -> dict[str, Any]:
        if kind not in KINDS or kind == "UNCLASSIFIED_INPUT":
            raise AssetError(f"invalid classification kind: {kind}")
        with self.store.lock(exclusive=True):
            recover_unlocked(self.store)
            catalog, records = self._load()
            if receipt_id not in records:
                raise AssetError(f"unknown receipt: {receipt_id}")
            record = records[receipt_id]
            asset = catalog.assets[record["asset_ref"]]
            if asset["kind"] == kind:
                return ReceiptLedger(catalog, records).describe(receipt_id)
            if asset["kind"] != "UNCLASSIFIED_INPUT":
                raise AssetError("asset is already classified; reclassification requires a separate reviewed change")
            old = catalog.resolve(asset["id"])
            raw = old.path.read_bytes()
            destination = self._destination(kind, asset["sha256"], record["original_filename"])
            self._check_destination(catalog, destination, raw)
            asset.update(kind=kind, path=destination)
            for receipt in records.values():
                if receipt["asset_ref"] == asset["id"]:
                    role = receipt["intended_role"]
                    receipt["classification"] = {"kind": kind, "roles": [role] if role else []}
            changes = {
                destination: raw, **self.store.serialized_records(catalog.assets, catalog.origins),
                **self._receipt_changes(records), old.relative_path: None,
            }
            commit_unlocked(self.store, changes)
            return ReceiptLedger(catalog, records).describe(receipt_id)

    def receipt(self, receipt_id: str) -> dict[str, Any]:
        with self.store.lock():
            self.store.assert_ready()
            catalog, records = self._load()
            return ReceiptLedger(catalog, records).describe(receipt_id)

    def recover(self) -> dict[str, Any]:
        with self.store.lock(exclusive=True):
            recovered = recover_unlocked(self.store)
            self._load()
            return {"status": "PASS", "recovered_transactions": recovered, "authority_effect": "NONE"}
