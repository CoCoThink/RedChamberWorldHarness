"""Validate focused audit material without granting global corpus acceptance."""
from pathlib import Path

from ..assets import AssetCatalog
from ..corpus.dataset import CorpusRepository
from ..io import load_data


def focus_report(root: Path) -> dict:
    packet = load_data(root / "data/evaluation/corpus_focus_packet.json")
    catalog = AssetCatalog.from_repo(root)
    corpus = CorpusRepository(catalog)
    binding = corpus.registry()[packet["dataset_ref"]]
    if binding["manifest_sha256"] != packet["manifest_sha256"]:
        raise ValueError("stale focused audit manifest")
    _, products = corpus.load(packet["dataset_ref"], rebuild=False)
    import json
    index = {s["segment_id"]: s for s in (json.loads(line) for line in products["segments.jsonl"].splitlines()[1:])}
    for sample in packet["samples"]:
        stored = index[sample["segment_id"]]
        if any(sample[k] != stored[k] for k in ("text_sha256", "text", "locator", "kind", "chapter")):
            raise ValueError(f"stale focused audit sample: {sample['segment_id']}")
        if catalog.resolve(stored["asset_ref"]).sha256 != packet["carrier_sha256"]:
            raise ValueError("stale focused audit carrier")
    return {"status": "PENDING", "scope": "FOCUSED_CORPUS_AUDIT_MATERIAL", "sample_count": len(packet["samples"]),
            "unknown_witness_count": packet["unknown_witness_count"], "alignment_counts": packet["alignment_counts"],
            "internal_visual_observations": len(packet["internal_visual_observations"]),
            "independent_human_review_count": 0, "findings": ["INDEPENDENT_CORPUS_LAYER_REVIEW_REQUIRED"],
            "global_corpus_acceptance": False, "authority_effect": "NONE"}
