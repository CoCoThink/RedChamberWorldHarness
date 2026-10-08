"""Compact historical versions, with exact recovery and no runtime authority."""
from __future__ import annotations

import csv
from difflib import SequenceMatcher
import hashlib
import io
import json
import re
from typing import Any

from .catalog import AssetCatalog, AssetError, repository_path
from ..schema import validate_instance


def make_patch(anchor: bytes, historical: bytes) -> list[dict[str, Any]]:
    before = anchor.decode("utf-8").splitlines(keepends=True)
    after = historical.decode("utf-8").splitlines(keepends=True)
    return [
        {"start": i, "stop": j, "text": "".join(after[k:l])}
        for tag, i, j, k, l in SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
        if tag != "equal"
    ]


def apply_patch(anchor: bytes, changes: list[dict[str, Any]]) -> bytes:
    lines = anchor.decode("utf-8").splitlines(keepends=True)
    result: list[str] = []
    cursor = 0
    for change in changes:
        start, stop = change["start"], change["stop"]
        if not (cursor <= start <= stop <= len(lines)):
            raise AssetError("invalid or overlapping historical line ranges")
        result.extend(lines[cursor:start])
        result.append(change["text"])
        cursor = stop
    result.extend(lines[cursor:])
    return "".join(result).encode("utf-8")


def checksum_manifest_text(raw: bytes) -> bytes:
    """Rebuild a sha256sum list in the original CSV row order."""
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if not {"sha256", "path"} <= set(rows.fieldnames or []):
        raise AssetError("checksum CSV requires sha256 and path columns")
    lines = []
    for row in rows:
        sha, path = row.get("sha256"), row.get("path")
        if not sha or not re.fullmatch(r"[a-f0-9]{64}", sha) or not path:
            raise AssetError("invalid checksum CSV row")
        lines.append(f"{sha}  {path}\n")
    return "".join(lines).encode("utf-8")


def project_csv(raw: bytes, projection: dict[str, Any]) -> bytes:
    """Recover a historical CSV view without storing its repeated rows."""
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    columns, where = projection["columns"], projection["where"]
    if not (set(columns) | set(where)) <= set(rows.fieldnames or []):
        raise AssetError("CSV projection references missing columns")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator=projection["lineterminator"])
    writer.writeheader()
    for row in rows:
        if all(row[key] == value for key, value in where.items()):
            writer.writerow({key: row[key] for key in columns})
    return output.getvalue().encode(projection["encoding"])


class HistoryArchive:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.records: dict[str, dict[str, Any]] = {}
        self.pack_refs: list[str] = []
        index = catalog.root / "data/catalog/history.json"
        if not index.exists():
            if any(a["path"].startswith("archive/history/") for a in catalog.assets.values()):
                raise AssetError("history packs exist without their index")
            return
        document = json.loads(index.read_text(encoding="utf-8"))
        problems = validate_instance(document, catalog.root / "schemas/asset_history_index.schema.json")
        if problems:
            raise AssetError("invalid history index: " + "; ".join(problems))
        self.pack_refs = document["pack_refs"]
        for ref in self.pack_refs:
            if catalog.assets.get(ref, {}).get("kind") != "HISTORICAL_RECORD":
                raise AssetError(f"history pack must be a historical asset: {ref}")
            pack = json.loads(catalog.resolve(ref).path.read_text(encoding="utf-8"))
            problems = validate_instance(pack, catalog.root / "schemas/asset_history_pack.schema.json")
            if problems:
                raise AssetError("invalid history pack: " + "; ".join(problems))
            for record in pack["records"]:
                key = record["asset"]["id"]
                if key in self.records or key in catalog.assets:
                    raise AssetError(f"duplicate or still-live retired asset: {key}")
                self.records[key] = {**record, "pack_ref": ref}

    def restore(self, asset_id: str) -> bytes:
        record = self.records[asset_id]
        anchor = self.catalog.resolve(record["anchor_ref"])
        raw = anchor.path.read_bytes()
        if record.get("anchor_format", "RAW") == "SHA256_MANIFEST_CSV":
            raw = checksum_manifest_text(raw)
        elif record.get("anchor_format") == "CSV_PROJECTION":
            raw = project_csv(raw, record["csv_projection"])
        raw = apply_patch(raw, record["changes"])
        asset = record["asset"]
        if hashlib.sha256(raw).hexdigest() != asset["sha256"] or len(raw) != asset["bytes"]:
            raise AssetError(f"historical recovery mismatch: {asset_id}")
        return raw

    def lookup(self, key: str) -> list[dict[str, Any]]:
        return [r for r in self.records.values() if key in (
            r["asset"]["id"], r["asset"]["sha256"], r["asset"]["path"], *r["aliases"],
        )]

    def validate(self) -> list[str]:
        errors = []
        origins_seen = set(self.catalog.origins)
        for key, record in self.records.items():
            asset = record["asset"]
            if key.startswith("asset:sha256:") and key != f"asset:sha256:{asset['sha256']}":
                errors.append(f"retired identity disagrees with SHA: {key}")
            try:
                if repository_path(self.catalog.root, asset["path"]).exists():
                    errors.append(f"retired body still exists: {asset['path']}")
            except AssetError as exc:
                errors.append(str(exc))
            origin_ids = {o["id"] for o in record["origins"]}
            if origin_ids != set(asset["origin_refs"]) or len(origin_ids) != len(record["origins"]):
                errors.append(f"retired origins incomplete: {key}")
            for origin in record["origins"]:
                problems = validate_instance(origin, self.catalog.root / "schemas/asset_origin.schema.json")
                if problems or origin["asset_ref"] != key or origin["sha256"] != asset["sha256"]:
                    errors.append(f"inconsistent retired origin: {origin['id']}")
                if origin["id"] in origins_seen:
                    errors.append(f"duplicate retired origin: {origin['id']}")
                origins_seen.add(origin["id"])
            if record["anchor_ref"] not in self.catalog.assets:
                errors.append(f"missing history anchor: {record['anchor_ref']}")
            try:
                self.restore(key)
            except (AssetError, KeyError, UnicodeError) as exc:
                errors.append(str(exc))
        return errors

    def summary(self) -> dict[str, Any]:
        return {
            "retired_versions": len(self.records), "history_packs": len(self.pack_refs),
            "recoverable_bytes": sum(r["asset"]["bytes"] for r in self.records.values()),
            "authority_effect": "NONE", "runtime_resolution": "DISALLOWED",
        }
