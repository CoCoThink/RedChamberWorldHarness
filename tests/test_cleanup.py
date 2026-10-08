from pathlib import Path
import shutil

import pytest

from rcwh.assets import AssetCatalog, AssetError
from rcwh.implementation_alignment import ImplementationAlignmentRuntime


ROOT = Path(__file__).resolve().parents[1]
STABLE_ASSET = "asset:release:stable:v1.4:readable"


def test_domain_trace_rechecks_local_bytes_without_migration_registry(tmp_path):
    catalog = AssetCatalog.from_repo(ROOT)
    stable = catalog.resolve(STABLE_ASSET)
    path = tmp_path / stable.relative_path
    path.parent.mkdir(parents=True)
    shutil.copyfile(stable.path, path)
    catalog.root = tmp_path
    runtime = ImplementationAlignmentRuntime.from_repo(ROOT)
    trace = runtime.trace("source", STABLE_ASSET, catalog)
    source = trace["resolved_sources"][0]
    assert trace["trace_complete"] is True
    assert source["path"] == stable.relative_path
    assert "authority" not in source and "semantic_coverage" not in source
    path.write_bytes(b"Changed baseline under the same asset identity")
    with pytest.raises(AssetError, match="byte mismatch"):
        runtime.trace("source", STABLE_ASSET, catalog)


def test_domain_trace_rejects_old_document_ids_and_hash_prefixes():
    catalog = AssetCatalog.from_repo(ROOT)
    runtime = ImplementationAlignmentRuntime.from_repo(ROOT)
    for key in ("doc:4645da79b1be", "4645da79b1be", "baseline.md"):
        with pytest.raises(KeyError):
            runtime.trace("source", key, catalog)
