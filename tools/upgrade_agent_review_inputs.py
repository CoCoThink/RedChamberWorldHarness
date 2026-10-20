"""Move the unreviewed current edition to scoped packets and carrier readings.

Preserves prose, drafts, author receipts and the continuity segments. Old request
snapshots and campaign plans remain immutable. Does not create review opinions.
"""
from __future__ import annotations

import json
from pathlib import Path

from rcwh.assets import AssetCatalog
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.io import load_data
from rcwh.workflow.release_packets import chapter_packets, source_subject, _packet, _write_immutable
from rcwh.workflow.review_campaign import plan

ROOT = Path(__file__).resolve().parents[1]
BASE = "data/agent_release/research-81-100-v1"


def main():
    root = ROOT
    if list((root / "data/agent_panel/records").glob("*.json")):
        raise ValueError("this one-time upgrade is only for the edition before formal review")
    request = json.loads((root / BASE / "request.json").read_bytes())
    _write_immutable(root, f"{BASE}/review-requests/{digest(canonical_bytes(request))}.json", request)
    rows = {r["chapter"]: r for r in request["chapters"] if r["mode"] == "AGENT_CANDIDATE"}
    subjects = {}
    sources = {}
    coordinator = None
    for row in rows.values():
        packet = json.loads((root / row["panel"]["packet"]["path"]).read_bytes())
        coordinator = packet["coordinator_session_id"]
        subjects.update({s["id"]: s for s in packet["subjects"]})
        for ref in row["source_reviews"]:
            packet = json.loads((root / ref["packet"]["path"]).read_bytes())
            subject = next(s for s in packet["subjects"] if s["id"] == ref["subject_id"])
            document = load_data(root / subject["binding"]["path"])
            sources[subject["source_ref"]] = next(s for s in document["sources"] if s["id"] == subject["source_ref"])
    chapter_refs = chapter_packets(root, list(subjects.values()), rows, coordinator)
    catalog = AssetCatalog.from_repo(root)
    source_cache = {}
    source_rows = [source_subject(root, sources[k], catalog, source_cache) for k in sorted(sources)]
    document = _packet("sources", "inputs-v3", coordinator, source_rows)
    source_ref = _write_immutable(root, f"data/agent_release/review-packets/{digest(canonical_bytes(document))}.json", document)
    for chapter, row in rows.items():
        row["panel"]["packet"] = chapter_refs[chapter]
        packet = json.loads((root / chapter_refs[chapter]["path"]).read_bytes())
        _write_immutable(root, f"{BASE}/reading/ch{chapter}-v3.json", {
            "schema_version": 3, "chapter": chapter, "packet": chapter_refs[chapter],
            "read_in_full": packet["subjects"], "policy": row.get("policy"),
            "severity_rule": "docs/decisions/0004_EVIDENCE_FLOOR_SEVERITY.md"})
        for ref in row["source_reviews"]:
            ref["packet"] = source_ref
    (root / BASE / "request.json").write_bytes(canonical_bytes(request))
    print(json.dumps(plan(root, f"{BASE}/request.json", f"{BASE}/review-campaign-v3.json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
