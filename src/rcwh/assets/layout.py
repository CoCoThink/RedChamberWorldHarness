"""One selected catalog layout; historical Git v1 remains readable."""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Any

import yaml

from ..schema import validate_instance
from .paths import AssetError, repository_path


LAYOUT = "data/catalog/catalog.json"
INDEX = "data/catalog/assets.index.json"
LEGACY = ("data/catalog/assets.yaml", "data/catalog/origins.jsonl")


def canonical(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def shard_path(record_id: str, kind: str) -> str:
    suffix = "yaml" if kind == "assets" else "jsonl"
    return f"data/catalog/{kind}/{sha(record_id.encode())[:2]}.{suffix}"


class CatalogLayout:
    def __init__(self, store):
        self.store = store
        self.root = store.root

    def selected(self) -> dict | None:
        path = repository_path(self.root, LAYOUT)
        if not path.exists():
            for directory in ("assets", "origins"):
                if repository_path(self.root, f"data/catalog/{directory}").exists():
                    raise AssetError("UNSELECTED_CATALOG_SHARDS")
            return None
        if any(repository_path(self.root, p).exists() for p in LEGACY):
            raise AssetError("AMBIGUOUS_CATALOG_LAYOUT: legacy files coexist with sharded layout")
        config = self.validate(json.loads(path.read_bytes()))
        declared = set(config["assets"] + config["origins"])
        actual = set()
        for name in ("assets", "origins"):
            directory = repository_path(self.root, f"data/catalog/{name}")
            if directory.exists():
                for p in directory.iterdir():
                    relative = p.relative_to(self.root).as_posix()
                    repository_path(self.root, relative)
                    if not p.is_file():
                        raise AssetError(f"invalid catalog shard: {relative}")
                    actual.add(relative)
        if actual != declared:
            raise AssetError(f"CATALOG_SHARD_SET_MISMATCH: missing={sorted(declared-actual)}, undeclared={sorted(actual-declared)}")
        return config

    def validate(self, config: dict) -> dict:
        errors = validate_instance(config, self.root / "schemas/asset_catalog_layout.schema.json")
        if errors:
            raise AssetError("invalid catalog layout: " + "; ".join(errors))
        if any(config[key] != sorted(config[key]) for key in ("assets", "origins")):
            raise AssetError("UNSORTED_CATALOG_SHARD_LIST")
        return config

    def read(self, config: dict | None, reader: Callable[[str], bytes]) -> tuple[dict, dict]:
        paths = {"assets": config["assets"] if config else [LEGACY[0]],
                 "origins": config["origins"] if config else [LEGACY[1]]}
        assets, origins = [], []
        for path in paths["assets"]:
            try:
                document = yaml.safe_load(reader(path))
            except yaml.YAMLError as exc:
                raise AssetError(f"invalid catalog YAML: {path}: {exc}") from exc
            self.store.check_document(document)
            records = document["assets"]
            if config:
                self.check_shard(records, path, "assets")
            assets.extend(records)
        for path in paths["origins"]:
            records = []
            for number, line in enumerate(reader(path).decode("utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                origin = json.loads(line)
                errors = validate_instance(origin, self.root / "schemas/asset_origin.schema.json")
                if errors:
                    raise AssetError(f"{path}:{number}: " + "; ".join(errors))
                records.append(origin)
            if config:
                self.check_shard(records, path, "origins")
            origins.extend(records)
        return self.store.unique(assets, "asset"), self.store.unique(origins, "origin")

    @staticmethod
    def check_shard(records: list, path: str, kind: str) -> None:
        if not records or [r["id"] for r in records] != sorted(r["id"] for r in records):
            raise AssetError(f"EMPTY_OR_UNSORTED_CATALOG_SHARD: {path}")
        if any(shard_path(r["id"], kind) != path for r in records):
            raise AssetError(f"MISPLACED_CATALOG_RECORD: {path}")

    def index(self, assets: dict, origins: dict, files: dict[str, bytes]) -> bytes:
        inputs = {path: sha(raw) for path, raw in files.items() if path != INDEX}
        inputs.update({path: sha(repository_path(self.root, path).read_bytes()) for path in self.store.discovery_paths()})
        return canonical({"schema_version": 1, "authority_effect": "NONE", "inputs": inputs,
                          "assets": [assets[key] for key in sorted(assets)], "origin_ids": sorted(origins)})

    def serialized(self, assets: dict, origins: dict, *, migrate: bool = False) -> dict[str, bytes | None]:
        selected = self.selected()
        if selected is None and not migrate:
            return {LEGACY[0]: yaml.safe_dump({"schema_version": 1, "assets": list(assets.values())}, allow_unicode=True, sort_keys=False).encode(),
                    LEGACY[1]: b"".join(canonical(origin) for origin in origins.values())}
        files = {}
        groups: dict[str, list] = {}
        for kind, records in (("assets", assets), ("origins", origins)):
            for key in sorted(records):
                groups.setdefault(shard_path(key, kind), []).append(records[key])
        for path, records in sorted(groups.items()):
            files[path] = (yaml.safe_dump({"schema_version": 1, "assets": records}, allow_unicode=True, sort_keys=False).encode()
                           if path.endswith(".yaml") else b"".join(canonical(record) for record in records))
        config = {"schema_version": 2, "layout": "ID_SHA256_PREFIX_V1",
                  "assets": sorted(p for p in files if p.endswith(".yaml")),
                  "origins": sorted(p for p in files if p.endswith(".jsonl"))}
        self.validate(config)
        files[LAYOUT] = canonical(config)
        index = self.index(assets, origins, files)
        changes: dict[str, bytes | None] = {**files, INDEX: index}
        obsolete = set((selected["assets"] + selected["origins"]) if selected else LEGACY) - set(files)
        for path in obsolete:
            if repository_path(self.root, path).exists():
                changes[path] = None
        return changes

    def index_findings(self, assets: dict, origins: dict) -> list[str]:
        config = self.selected()
        if config is None:
            return []
        path = repository_path(self.root, INDEX)
        if not path.exists():
            return ["MISSING_CATALOG_INDEX: run rcwh assets index --rebuild"]
        files = {p: repository_path(self.root, p).read_bytes() for p in [LAYOUT, *config["assets"], *config["origins"]]}
        if path.read_bytes() != self.index(assets, origins, files):
            return ["STALE_CATALOG_INDEX: run rcwh assets index --rebuild"]
        return []
