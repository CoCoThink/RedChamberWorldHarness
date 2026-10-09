"""Durable, idempotent roll-forward of multi-file catalog changes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from .paths import AssetError, repository_path
from .store import CatalogStore


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_durable(path: Path, raw: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def sync_directory(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def file_digest(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise AssetError(f"transaction target is not a file: {path}")
    return digest(path.read_bytes())


def apply_operation(store: CatalogStore, directory: Path, operation: dict) -> None:
    target = repository_path(store.root, operation["path"])
    current = file_digest(target)
    before, after = operation["before_sha256"], operation["after_sha256"]
    if current == after:
        return
    if current != before:
        raise AssetError(f"transaction conflict; refusing to overwrite changed file: {operation['path']}")
    if after is None:
        target.unlink()
    else:
        staged = repository_path(directory, operation["staged"])
        raw = staged.read_bytes()
        if digest(raw) != after:
            raise AssetError(f"transaction staging hash mismatch: {operation['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = directory / f"apply-{uuid.uuid4().hex}"
        write_durable(temporary, raw)
        os.replace(temporary, target)
    sync_directory(target.parent)


def finish_transaction(store: CatalogStore, journal: Path) -> str:
    relative = journal.relative_to(store.root).as_posix()
    repository_path(store.root, relative)
    document = json.loads(journal.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict) or document.get("schema_version") != 1
        or document.get("transaction_id") != journal.parent.name
        or not isinstance(document.get("operations"), list)
    ):
        raise AssetError(f"invalid asset transaction: {relative}")
    operations = document["operations"]
    paths = set()
    for operation in operations:
        if not isinstance(operation, dict) or set(operation) != {"path", "before_sha256", "after_sha256", "staged"}:
            raise AssetError(f"invalid transaction operation: {relative}")
        path = operation["path"]
        if not isinstance(path, str):
            raise AssetError(f"invalid transaction target: {relative}")
        repository_path(store.root, path)
        allowed = path in {store.asset_path, store.origin_path} or path.startswith((
            store.receipt_directory + "/", "sources/", "research/", "artifacts/", "releases/", "archive/", "corpus/",
            "data/provenance/sources/", "data/catalog/assets/", "data/catalog/origins/",
            "data/corpus/datasets/",
        ))
        allowed = allowed or path in {"data/catalog/catalog.json", "data/catalog/assets.index.json"}
        if not allowed or path in paths:
            raise AssetError(f"invalid or duplicate transaction target: {path}")
        paths.add(path)
        for sha in (operation["before_sha256"], operation["after_sha256"]):
            if sha is not None and (not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha)):
                raise AssetError(f"invalid transaction hash: {path}")
        after = operation["after_sha256"]
        if after is not None:
            if not isinstance(operation["staged"], str):
                raise AssetError(f"invalid transaction staging path: {path}")
            staged = repository_path(journal.parent, operation["staged"])
            if digest(staged.read_bytes()) != after:
                raise AssetError(f"transaction staging hash mismatch: {path}")
        current = file_digest(repository_path(store.root, path))
        if current not in {operation["before_sha256"], after}:
            raise AssetError(f"transaction conflict; refusing to overwrite changed file: {path}")
    for operation in operations:
        apply_operation(store, journal.parent, operation)
    # Removing the journal is the commit marker. Leftover staging is never a catalog input.
    journal.unlink()
    sync_directory(journal.parent)
    shutil.rmtree(journal.parent)
    sync_directory(journal.parent.parent)
    return document["transaction_id"]


def recover_unlocked(store: CatalogStore) -> list[str]:
    return [finish_transaction(store, journal) for journal in store.pending_transactions()]


def commit_unlocked(store: CatalogStore, changes: dict[str, bytes | None]) -> None:
    """Caller holds the exclusive store lock. Publish intent before the first target write."""
    store.assert_ready()
    transaction_id = uuid.uuid4().hex
    directory = repository_path(store.root, f"{store.transaction_directory}/{transaction_id}")
    directory.mkdir(parents=True)
    operations = []
    try:
        for number, (relative, raw) in enumerate(changes.items()):
            target = repository_path(store.root, relative)
            before = file_digest(target)
            after = None if raw is None else digest(raw)
            if before == after:
                continue
            staged = None
            if raw is not None:
                staged = f"{number}.bin"
                write_durable(directory / staged, raw)
            operations.append({
                "path": relative, "before_sha256": before,
                "after_sha256": after, "staged": staged,
            })
        document = {"schema_version": 1, "transaction_id": transaction_id, "operations": operations}
        temporary = directory / "journal.tmp"
        write_durable(temporary, json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        os.replace(temporary, directory / "journal.json")
        sync_directory(directory)
        sync_directory(directory.parent)
    except BaseException:
        if not (directory / "journal.json").exists():
            shutil.rmtree(directory)
        raise
    finish_transaction(store, directory / "journal.json")
