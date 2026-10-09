"""Materialize review copies from retained, registered byte-identical bundles."""
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

from .assets import AssetCatalog
from .candidate_reviews import canonical_bytes, digest
from .io import load_data


class BundleDelivery:
    def __init__(self, root: Path):
        self.root = root
        self.catalog = AssetCatalog.from_repo(root)
        self.config = load_data(root / "data/project/delivery.json")

    def selected(self, identity: str):
        row = next(r for r in self.config["bundles"] if r["id"] == identity)
        asset = self.catalog.resolve(row["asset_ref"])
        if asset.sha256 != row["sha256"]:
            raise ValueError("delivery bundle identity mismatch")
        return row, asset

    def summary(self) -> dict:
        rows = []
        for item in self.config["bundles"]:
            row, asset = self.selected(item["id"])
            rows.append({**row, "registered_path": asset.relative_path, "bytes": asset.path.stat().st_size})
        return {"status": "PASS", "scope": "LOCAL_DELIVERY_STORAGE", "bundles": rows,
                "removed_duplicate_bytes": sum(r["bytes"] for r in self.config["removed_copies"]),
                "immutable_assets_relocated": False, "network_publication": False, "authority_effect": "NONE"}

    def materialize(self, identity: str, destination: Path) -> dict:
        row, asset = self.selected(identity)
        if destination.exists():
            raise ValueError("materialization destination must be new")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="rcwh-delivery-", dir=destination.parent) as staging:
            temp = Path(staging) / "contents"; temp.mkdir()
            files = []
            if row["kind"] == "ZIP":
                with zipfile.ZipFile(asset.path) as archive:
                    names = set()
                    for member in archive.infolist():
                        p = PurePosixPath(member.filename)
                        mode = member.external_attr >> 16
                        if p.is_absolute() or ".." in p.parts or "\\" in member.filename or ":" in member.filename or member.filename in names or stat.S_ISLNK(mode):
                            raise ValueError("unsafe or duplicate delivery archive path")
                        names.add(member.filename)
                    for member in archive.infolist():
                        target = temp / member.filename
                        if member.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        raw = archive.read(member); target.write_bytes(raw)
                        files.append({"path": member.filename, "sha256": digest(raw), "bytes": len(raw)})
            else:
                raw = asset.path.read_bytes(); (temp / row["filename"]).write_bytes(raw)
                files.append({"path": row["filename"], "sha256": digest(raw), "bytes": len(raw)})
            temp.rename(destination)
        return {"status": "PASS", "scope": "VERIFIED_MATERIALIZATION", "bundle": identity,
                "asset_ref": asset.id, "sha256": asset.sha256, "destination": str(destination), "files": files,
                "authority_effect": "NONE"}

    def attachments(self, destination: Path) -> dict:
        destination.mkdir(exist_ok=False)
        records = []
        for identity in (r["id"] for r in self.config["bundles"]):
            row, asset = self.selected(identity)
            target = destination / (identity + Path(row["filename"]).suffix)
            shutil.copyfile(asset.path, target)
            if digest(target.read_bytes()) != asset.sha256:
                raise ValueError("delivery attachment copy differs")
            records.append({"filename": target.name, "asset_ref": asset.id, "sha256": asset.sha256, "bytes": target.stat().st_size})
        (destination / "manifest.json").write_bytes(canonical_bytes({"files": records, "publication": "NOT_PUBLISHED", "authority_effect": "NONE"}))
        return {"status": "PASS", "scope": "RELEASE_ATTACHMENT_PREPARATION", "directory": str(destination),
                "files": records, "publication": "NOT_PUBLISHED"}
