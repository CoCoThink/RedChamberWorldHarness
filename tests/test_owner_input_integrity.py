"""Owner inputs stay intact; research process records are not code invariants.

Replaces the retired 325-file research freeze list (ADR 0004). Catalogued
sources/corpus assets are hash-checked by the catalog; evidence, world and
imported planning inputs must match the Git checkout; archived research is
history that live records may not bind.
"""
from pathlib import Path
import subprocess

import pytest

from rcwh.assets import AssetCatalog
from rcwh.graph import ProvenanceGraph
from rcwh.validate import archive_reference_errors

ROOT = Path(__file__).resolve().parents[1]
OWNER_INPUTS = ("sources", "data/provenance", "data/world", "data/objects", "data/literals",
                "data/plocks", "data/planning/chapters", "data/planning/scenes", "releases/stable")


def git(*args):
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)
    except OSError:
        pytest.skip("git unavailable")
    if result.returncode:
        pytest.skip("not a Git checkout")
    return result.stdout.decode("utf-8")


def test_catalogued_assets_and_evidence_graph_are_intact():
    catalog = AssetCatalog.from_repo(ROOT)
    assert catalog.validate() == []
    assert ProvenanceGraph.from_repo(ROOT).validate_integrity() == []


def test_immutable_catalog_assets_unchanged_since_head():
    git("rev-parse", "HEAD")
    assert AssetCatalog.from_repo(ROOT).compare_git_baseline("HEAD") == []


def test_tracked_owner_inputs_match_checkout():
    changed = git("status", "--porcelain", "--untracked-files=no", "--", *OWNER_INPUTS)
    assert changed == "", f"owner inputs modified or deleted:\n{changed}"


def test_live_records_do_not_bind_archived_research():
    assert archive_reference_errors(ROOT) == []
