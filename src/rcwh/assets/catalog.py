from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

from ..io import load_data
from ..schema import validate_instance


class AssetError(ValueError):
    """A declared asset cannot be resolved to the expected repository bytes."""


def repository_path(root: Path, relative: str) -> Path:
    """Reject external paths and links, including links that resolve internally."""
    path = PurePosixPath(relative)
    if (
        not relative or path.is_absolute() or ".." in path.parts
        or "\\" in relative or ":" in relative or str(path) != relative
    ):
        raise AssetError(f"unsafe repository path: {relative}")
    root = root.resolve()
    candidate = root.joinpath(*path.parts)
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise AssetError(f"symlink is not an asset: {relative}")
    if not candidate.resolve().is_relative_to(root):
        raise AssetError(f"asset leaves repository: {relative}")
    return candidate


@dataclass(frozen=True)
class ResolvedAsset:
    id: str
    path: Path
    relative_path: str
    sha256: str
    size: int

    def summary(self) -> dict[str, Any]:
        return {
            "asset_id": self.id, "path": self.relative_path,
            "sha256": self.sha256, "bytes": self.size,
        }


@dataclass
class AssetCatalog:
    root: Path
    assets: dict[str, dict[str, Any]]
    origins: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "AssetCatalog":
        root = root.resolve()
        document = load_data(root / "data/catalog/assets.yaml")
        problems = validate_instance(document, root / "schemas/asset_catalog.schema.json")
        if problems:
            raise AssetError("invalid asset catalog: " + "; ".join(problems))
        assets: dict[str, dict[str, Any]] = {}
        for asset in document["assets"]:
            if asset["id"] in assets:
                raise AssetError(f"duplicate asset id: {asset['id']}")
            assets[asset["id"]] = asset
        origins: dict[str, dict[str, Any]] = {}
        schema = load_data(root / "schemas/asset_origin.schema.json")
        path = root / "data/catalog/origins.jsonl"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                origin = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AssetError(f"origins line {number}: {exc}") from exc
            problems = validate_instance(origin, schema)
            if problems:
                raise AssetError(f"origins line {number}: " + "; ".join(problems))
            if origin["id"] in origins:
                raise AssetError(f"duplicate origin id: {origin['id']}")
            origins[origin["id"]] = origin
        return cls(root, assets, origins)

    def resolve(self, asset_id: str) -> ResolvedAsset:
        if asset_id not in self.assets:
            raise AssetError(f"unknown asset: {asset_id}")
        asset = self.assets[asset_id]
        path = repository_path(self.root, asset["path"])
        if not path.is_file():
            raise AssetError(f"{asset_id}: missing file {asset['path']}")
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != asset["sha256"] or len(raw) != asset["bytes"]:
            raise AssetError(
                f"{asset_id}: byte mismatch at {asset['path']} "
                f"(expected {asset['sha256']}/{asset['bytes']}, got {actual}/{len(raw)})"
            )
        return ResolvedAsset(asset_id, path, asset["path"], actual, len(raw))

    def validate(self, *, require_tracked: bool = False) -> list[str]:
        errors: list[str] = []
        paths: dict[str, str] = {}
        hashes: dict[str, str] = {}
        for asset_id, asset in self.assets.items():
            if asset_id.startswith("asset:sha256:") and asset_id != f"asset:sha256:{asset['sha256']}":
                errors.append(f"content-addressed asset id disagrees with SHA: {asset_id}")
            try:
                self.resolve(asset_id)
            except (AssetError, OSError) as exc:
                errors.append(str(exc))
            folded = asset["path"].casefold()
            if folded in paths:
                errors.append(f"case-colliding asset paths: {paths[folded]} and {asset_id}")
            paths[folded] = asset_id
            if asset["sha256"] in hashes:
                errors.append(f"duplicate asset bytes: {hashes[asset['sha256']]} and {asset_id}")
            hashes[asset["sha256"]] = asset_id
            for ref in asset["origin_refs"]:
                origin = self.origins.get(ref)
                if origin is None:
                    errors.append(f"{asset_id}: unknown origin {ref}")
                elif origin["asset_ref"] != asset_id or origin["sha256"] != asset["sha256"]:
                    errors.append(f"{asset_id}: inconsistent origin {ref}")
            for ref in asset.get("derived_from", []):
                if ref not in self.assets:
                    errors.append(f"{asset_id}: unknown derived input {ref}")
        for origin_id, origin in self.origins.items():
            asset = self.assets.get(origin["asset_ref"])
            if asset is None or origin_id not in asset["origin_refs"]:
                errors.append(f"{origin_id}: origin lacks asset back-reference")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(asset_id: str) -> None:
            if asset_id in visiting:
                errors.append(f"derived asset cycle at {asset_id}")
                return
            if asset_id in visited or asset_id not in self.assets:
                return
            visiting.add(asset_id)
            for ref in self.assets[asset_id].get("derived_from", []):
                visit(ref)
            visiting.remove(asset_id)
            visited.add(asset_id)

        for asset_id in self.assets:
            visit(asset_id)
        from .history import HistoryArchive
        try:
            errors.extend(HistoryArchive(self).validate())
        except (AssetError, OSError, ValueError) as exc:
            errors.append(f"asset history integrity: {exc}")
        if require_tracked:
            result = subprocess.run(
                ["git", "ls-files", "-z"], cwd=self.root,
                capture_output=True, check=False,
            )
            if result.returncode:
                errors.append("tracked-file check requires a Git checkout")
            else:
                tracked = set(result.stdout.decode("utf-8").split("\0"))
                required = {a["path"] for a in self.assets.values()}
                required.update({"data/catalog/assets.yaml", "data/catalog/origins.jsonl"})
                if (self.root / "data/catalog/history.json").exists():
                    required.add("data/catalog/history.json")
                errors.extend(f"untracked formal asset: {p}" for p in sorted(required - tracked))
        return errors

    def compare_immutable(self, previous: dict[str, Any]) -> list[str]:
        errors = []
        for old in previous["assets"]:
            if not old["immutable"]:
                continue
            current = self.assets.get(old["id"])
            if current is None or (
                current["sha256"], current["bytes"]
            ) != (old["sha256"], old["bytes"]):
                errors.append(f"immutable asset changed or removed: {old['id']}")
        return errors

    def compare_git_baseline(self, ref: str) -> list[str]:
        if ref.startswith("-") or not ref:
            raise AssetError("invalid Git baseline reference")
        result = subprocess.run(
            ["git", "show", f"{ref}:data/catalog/assets.yaml"], cwd=self.root,
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise AssetError(f"cannot read catalog at Git baseline {ref}")
        import yaml
        previous = yaml.safe_load(result.stdout)
        errors = validate_instance(previous, self.root / "schemas/asset_catalog.schema.json")
        if errors:
            raise AssetError("invalid baseline catalog: " + "; ".join(errors))
        return self.compare_immutable(previous)

    def summary(self) -> dict[str, Any]:
        return {
            "assets": len(self.assets), "origins": len(self.origins),
            "content_bytes": sum(a["bytes"] for a in self.assets.values()),
            "authority_effect": "NONE",
        }
