"""Catalog persistence boundary with one selected layout and old Git readers."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterator

import yaml

from ..schema import validate_instance
from .paths import AssetError, repository_path


class CatalogStore:
    asset_path = "data/catalog/assets.yaml"
    origin_path = "data/catalog/origins.jsonl"
    receipt_directory = "data/catalog/receipts"
    transaction_directory = "data/catalog/.transactions"

    def __init__(self, root: Path):
        self.root = root.resolve()

    @contextmanager
    def lock(self, *, exclusive: bool = False) -> Iterator[None]:
        """OS locks are released even when a writer is killed; fail fast on contention."""
        path = repository_path(self.root, ".rcwh-cache/asset-catalog.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    if not handle.read(1):
                        handle.write(b"\0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                    fcntl.flock(handle.fileno(), mode | fcntl.LOCK_NB)
            except OSError as exc:
                raise AssetError("catalog is locked by another operation; retry after it finishes") from exc
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def pending_transactions(self) -> list[Path]:
        directory = repository_path(self.root, self.transaction_directory)
        return sorted(directory.glob("*/journal.json")) if directory.exists() else []

    def assert_ready(self) -> None:
        if self.pending_transactions():
            raise AssetError("unfinished asset transaction; run rcwh assets recover before reading the catalog")

    def read(self) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        with self.lock():
            self.assert_ready()
            return self.read_unlocked()

    def read_unlocked(self) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        from .layout import CatalogLayout
        layout = CatalogLayout(self)
        return layout.read(layout.selected(), lambda path: repository_path(self.root, path).read_bytes())

    @staticmethod
    def unique(records: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
        result = {}
        for record in records:
            if record["id"] in result:
                raise AssetError(f"duplicate {kind} id: {record['id']}")
            result[record["id"]] = record
        return result

    def check_document(self, document: dict[str, Any]) -> None:
        errors = validate_instance(document, self.root / "schemas/asset_catalog.schema.json")
        if errors:
            raise AssetError("invalid asset catalog: " + "; ".join(errors))

    def serialized_records(
        self, assets: dict[str, dict[str, Any]], origins: dict[str, dict[str, Any]],
        *, migrate: bool = False,
    ) -> dict[str, bytes | None]:
        document = {"schema_version": 1, "assets": list(assets.values())}
        self.check_document(document)
        for origin in origins.values():
            errors = validate_instance(origin, self.root / "schemas/asset_origin.schema.json")
            if errors:
                raise AssetError("invalid origin: " + "; ".join(errors))
        from .layout import CatalogLayout
        return CatalogLayout(self).serialized(assets, origins, migrate=migrate)

    def receipt_paths(self) -> list[str]:
        directory = repository_path(self.root, self.receipt_directory)
        return [p.relative_to(self.root).as_posix() for p in sorted(directory.glob("*.json"))]

    def receipts_unlocked(self) -> dict[str, dict[str, Any]]:
        records = {}
        for relative in self.receipt_paths():
            record = json.loads(repository_path(self.root, relative).read_text(encoding="utf-8"))
            errors = validate_instance(record, self.root / "schemas/asset_receipt.schema.json")
            if errors:
                raise AssetError(f"invalid receipt {relative}: " + "; ".join(errors))
            expected = self.receipt_path(record["receipt_id"])
            if relative != expected or record["receipt_id"] in records:
                raise AssetError(f"duplicate or misplaced receipt: {relative}")
            records[record["receipt_id"]] = record
        return records

    def receipt_path(self, receipt_id: str) -> str:
        import hashlib
        key = hashlib.sha256(receipt_id.encode("utf-8")).hexdigest()
        return f"{self.receipt_directory}/{key}.json"

    def metadata_paths(self) -> set[str]:
        from .layout import CatalogLayout, INDEX, LAYOUT
        layout = CatalogLayout(self).selected()
        paths = ({LAYOUT, INDEX, "schemas/asset_catalog_layout.schema.json", *layout["assets"], *layout["origins"]}
                 if layout else {self.asset_path, self.origin_path})
        paths.update(self.receipt_paths())
        if (self.root / "data/catalog/history.json").exists():
            paths.add("data/catalog/history.json")
        discovery = self.discovery_paths()
        paths.update(discovery)
        if discovery:
            paths.update({"schemas/asset_annotation.schema.json", "schemas/asset_collection.schema.json"})
        return paths

    def discovery_paths(self) -> list[str]:
        paths = []
        for name in ("annotations", "collections"):
            directory = repository_path(self.root, f"data/catalog/{name}")
            if not directory.exists():
                continue
            for path in sorted(directory.iterdir()):
                relative = path.relative_to(self.root).as_posix()
                repository_path(self.root, relative)
                if not path.is_file() or path.suffix not in {".yaml", ".yml", ".json"}:
                    raise AssetError(f"unsupported discovery metadata path: {relative}")
                paths.append(relative)
        return paths

    def read_git_catalog(self, ref: str) -> dict[str, Any]:
        if not ref or ref.startswith("-"):
            raise AssetError("invalid Git baseline reference")
        from .layout import CatalogLayout, LAYOUT
        def reader(path: str) -> bytes:
            result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=self.root, capture_output=True, check=False)
            if result.returncode:
                raise AssetError(f"cannot read catalog at Git baseline {ref}: {path}")
            return result.stdout
        exists = subprocess.run(["git", "cat-file", "-e", f"{ref}:{LAYOUT}"], cwd=self.root, capture_output=True, check=False)
        layout = CatalogLayout(self)
        config = layout.validate(json.loads(reader(LAYOUT))) if exists.returncode == 0 else None
        if config is not None:
            legacy = subprocess.run(["git", "cat-file", "-e", f"{ref}:{self.asset_path}"], cwd=self.root, capture_output=True, check=False)
            if legacy.returncode == 0:
                raise AssetError("AMBIGUOUS_GIT_CATALOG_LAYOUT")
        assets, _ = layout.read(config, reader)
        return {"schema_version": 1, "assets": list(assets.values())}

    def migrate_shards(self) -> dict[str, Any]:
        from .transactions import commit_unlocked, recover_unlocked
        with self.lock(exclusive=True):
            recover_unlocked(self)
            assets, origins = self.read_unlocked()
            from .catalog import AssetCatalog
            findings = AssetCatalog(self.root, assets, origins).validate(receipt_records=self.receipts_unlocked())
            if findings:
                raise AssetError("invalid catalog before migration: " + "; ".join(findings))
            before = (assets, origins)
            changes = self.serialized_records(assets, origins, migrate=True)
            commit_unlocked(self, changes)
            if self.read_unlocked() != before:
                raise AssetError("CATALOG_MIGRATION_SEMANTIC_CHANGE")
            return {"status": "PASS", "assets": len(assets), "origins": len(origins), "authority_effect": "NONE"}

    def index_report(self, *, rebuild: bool = False) -> dict[str, Any]:
        from .layout import CatalogLayout, INDEX, LAYOUT
        from .transactions import commit_unlocked, recover_unlocked
        with self.lock(exclusive=rebuild):
            if rebuild:
                recover_unlocked(self)
            self.assert_ready()
            assets, origins = self.read_unlocked()
            layout = CatalogLayout(self)
            config = layout.selected()
            if config is None:
                raise AssetError("CATALOG_INDEX_REQUIRES_SHARDED_LAYOUT")
            if rebuild:
                files = {p: repository_path(self.root, p).read_bytes() for p in [LAYOUT, *config["assets"], *config["origins"]]}
                commit_unlocked(self, {INDEX: layout.index(assets, origins, files)})
            findings = layout.index_findings(assets, origins)
            return {"status": "FAIL" if findings else "PASS", "findings": findings, "index": INDEX, "authority_effect": "NONE"}
