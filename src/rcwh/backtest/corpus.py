"""Read-only manifest and row verification for a single-edition holdout."""
import json

from ..assets import AssetCatalog, AssetError
from ..candidate_reviews import digest
from ..corpus.dataset import CorpusRepository


def verified_corpus(root, config):
    catalog = AssetCatalog.from_repo(root)
    repository = CorpusRepository(catalog)
    binding = repository.registry()[config["dataset_ref"]]
    expected = config["manifest_sha256"]
    if binding["manifest_sha256"] != expected:
        raise AssetError("BACKTEST_STALE_MANIFEST")
    asset = catalog.resolve(binding["manifest_ref"])
    if asset.sha256 != expected or digest(asset.path.read_bytes()) != expected:
        raise AssetError("BACKTEST_STALE_MANIFEST")
    # This verifies registered config, dependencies and all product bytes. Never
    # rebuild or register a corpus derivative from a research command.
    manifest, products = repository.load(config["dataset_ref"], rebuild=False)
    if manifest["dataset_ref"] != config["dataset_ref"]:
        raise AssetError("BACKTEST_DATASET_MISMATCH")
    declared = manifest["build_config"]["document"]["chapters"]
    if declared != list(range(1, 81)):
        raise AssetError("BACKTEST_REQUIRES_COMPLETE_FRONT80")
    lines = [json.loads(line) for line in products["segments.jsonl"].splitlines()]
    if not lines or lines[0].get("record_type") != "FILE_SCOPE" or lines[0].get("dataset_ref") != config["dataset_ref"]:
        raise AssetError("BACKTEST_SEGMENTS_SCOPE_MISMATCH")
    identities, segments, main = set(), [], {chapter: [] for chapter in declared}
    for row in lines[1:]:
        if row["segment_id"] in identities:
            raise AssetError("BACKTEST_DUPLICATE_SEGMENT")
        identities.add(row["segment_id"])
        if row["dataset_ref"] != config["dataset_ref"] or digest(row["text"].encode()) != row["text_sha256"]:
            raise AssetError("BACKTEST_STALE_SEGMENT_SHA")
        if row["kind"] == "MAIN_TEXT":
            if row["chapter"] not in main:
                raise AssetError("BACKTEST_MAIN_TEXT_SCOPE_MISMATCH")
            if row["asset_ref"] != config["edition_asset_ref"]:
                raise AssetError("BACKTEST_MIXED_EDITION")
            main[row["chapter"]].append(row)
        segments.append(row)
    for chapter in declared:
        view = json.loads(products[f"chapters/ch{chapter:02d}.json"])
        rows = main[chapter]
        if not rows or view["dataset_ref"] != config["dataset_ref"] or view["chapter"] != chapter or view["segment_refs"] != [row["segment_id"] for row in rows] or view["text"] != "".join(row["text"] for row in rows):
            raise AssetError("BACKTEST_STALE_CHAPTER_VIEW")
    return manifest, segments
