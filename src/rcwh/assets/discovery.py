"""Editable reading metadata. Roles and collections grant no authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..schema import validate_instance
from .catalog import AssetCatalog
from .ingest import ROLES
from .paths import AssetError, repository_path
from .store import CatalogStore


class AssetDiscovery:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog
        self.annotations: dict[str, dict[str, Any]] = {}
        self.collections: dict[str, dict[str, Any]] = {}
        self.findings: list[str] = []
        store = CatalogStore(catalog.root)
        for relative in store.discovery_paths():
            try:
                document = yaml.safe_load(repository_path(catalog.root, relative).read_bytes())
                kind = "annotation" if relative.startswith("data/catalog/annotations/") else "collection"
                errors = validate_instance(document, catalog.root / f"schemas/asset_{kind}.schema.json")
                if errors:
                    raise AssetError("; ".join(errors))
                key = document["asset_ref"] if kind == "annotation" else document["id"]
                records = self.annotations if kind == "annotation" else self.collections
                if key in records:
                    raise AssetError(f"duplicate {kind} ID: {key}")
                records[key] = document
            except (AssetError, OSError, ValueError, yaml.YAMLError) as exc:
                self.findings.append(f"{relative}: {exc}")
        for key in self.annotations:
            if key not in catalog.assets:
                self.findings.append(f"unknown annotated asset: {key}")
        for collection in self.collections.values():
            for member in collection["members"]:
                if member not in catalog.assets:
                    self.findings.append(f"{collection['id']}: unknown collection member: {member}")

    def validate(self) -> list[str]:
        return list(self.findings)

    def _ready(self) -> None:
        if self.findings:
            raise AssetError("invalid discovery metadata: " + "; ".join(self.findings))

    def query(
        self, *, role: str | None = None, collection: str | None = None,
        chapter: int | None = None, tag: str | None = None,
    ) -> dict[str, Any]:
        self._ready()
        if role is not None and role not in ROLES:
            raise AssetError(f"unknown discovery role: {role}")
        if chapter is not None and not 1 <= chapter <= 100:
            raise AssetError("chapter must be between 1 and 100")
        if collection is not None and collection not in self.collections:
            raise AssetError(f"unknown collection: {collection}")
        members = set(self.collections[collection]["members"]) if collection else set(self.catalog.assets)
        # Classified intake roles are discovery hints until an explicit annotation
        # replaces them. Receipt intent never becomes an evidence/adoption flag.
        receipt_roles: dict[str, set[str]] = {}
        store = CatalogStore(self.catalog.root)
        store.assert_ready()
        from .layout import CatalogLayout
        findings = CatalogLayout(store).index_findings(self.catalog.assets, self.catalog.origins)
        if findings:
            raise AssetError("; ".join(findings))
        for receipt in store.receipts_unlocked().values():
            if receipt["classification"]:
                receipt_roles.setdefault(receipt["asset_ref"], set()).update(receipt["classification"]["roles"])
        results = []
        for asset_id in sorted(members):
            asset = self.catalog.assets[asset_id]
            annotation = self.annotations.get(asset_id)
            metadata = annotation or {
                "title": Path(asset["path"]).name, "version": None,
                "roles": sorted(receipt_roles.get(asset_id, set())), "tags": [], "chapters": [],
            }
            if role is not None and role not in metadata["roles"]:
                continue
            if chapter is not None and chapter not in metadata["chapters"]:
                continue
            if tag is not None and tag not in metadata["tags"]:
                continue
            resolved = self.catalog.resolve(asset_id)
            results.append({
                **resolved.summary(), "title": metadata["title"], "version": metadata.get("version"),
                "kind": asset["kind"], "roles": sorted(metadata["roles"]),
                "tags": sorted(metadata["tags"]), "chapters": sorted(metadata["chapters"]),
                "collections": sorted(key for key, value in self.collections.items() if asset_id in value["members"]),
                "role_origin": "ANNOTATION" if annotation else "RECEIPT_CLASSIFICATION",
            })
        return {"status": "PASS", "authority_effect": "NONE", "count": len(results), "assets": results}

    def collection_report(self, collection_id: str | None = None) -> dict[str, Any]:
        self._ready()
        if collection_id is not None and collection_id not in self.collections:
            raise AssetError(f"unknown collection: {collection_id}")
        records = [self.collections[key] for key in sorted(self.collections) if collection_id is None or key == collection_id]
        return {"status": "PASS", "authority_effect": "NONE", "collections": records}
