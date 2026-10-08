from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..assets import AssetCatalog, AssetError
from ..assets.catalog import repository_path
from ..io import load_data
from ..schema import validate_instance


@dataclass
class ReleaseManifest:
    data: dict[str, Any]
    catalog: AssetCatalog

    @classmethod
    def from_repo(cls, root: Path, path: str, catalog: AssetCatalog | None = None) -> "ReleaseManifest":
        data = load_data(repository_path(root, path))
        errors = validate_instance(data, root / "schemas/release_manifest.schema.json")
        if errors:
            raise AssetError("invalid release manifest: " + "; ".join(errors))
        return cls(data, catalog or AssetCatalog.from_repo(root))

    def validate_storage(self) -> list[str]:
        errors = []
        for ref in [self.data["text_asset_ref"], *self.data["related_asset_refs"]]:
            try:
                self.catalog.resolve(ref)
            except (AssetError, OSError) as exc:
                errors.append(str(exc))
        text = self.catalog.assets.get(self.data["text_asset_ref"])
        if text is not None and text["sha256"] != self.data["text_sha256"]:
            errors.append("release text SHA disagrees with asset")
        return errors

    def summary(self) -> dict[str, Any]:
        errors = self.validate_storage()
        return {
            "profile": "release-storage", "release_id": self.data["id"],
            "status": "FAIL" if errors else "PASS", "findings": errors,
            "text": self.catalog.assets.get(self.data["text_asset_ref"]),
            "evidence_closure": self.data["evidence_closure"],
            "adoption_effect": "NONE",
        }
