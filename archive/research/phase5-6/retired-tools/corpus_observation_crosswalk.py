"""Append a carrier-overlap correction; never edit an original model opinion."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def overlap(old, new):
    left, right = old["locator"], new["locator"]
    if left["extraction_ref"] != right["extraction_ref"] or left.get("transforms", []) != right.get("transforms", []):
        return False
    return any(a["unit_ref"] == b["unit_ref"] and max(a["start"], b["start"]) < min(a["end"], b["end"])
               for a in left["spans"] for b in right["spans"])


def crosswalk(root: Path) -> dict:
    paths = {
        "observations": "artifacts/agent_research/phase6/corpus/reader2-observations-v1.json",
        "opinion": "artifacts/agent_research/phase6/corpus/reader2-opinion-v1.json",
        "samples": "artifacts/agent_research/phase6/corpus/review-samples-v1.json",
        "old_segments": "corpus/front80/v1-candidate/segments.jsonl",
        "new_segments": "corpus/front80/v2-candidate/segments.jsonl",
        "map": "artifacts/agent_research/phase6/corpus/dataset-map-v1-to-v2.json",
    }
    raw = {key: (root / path).read_bytes() for key, path in paths.items()}
    observations = json.loads(raw["observations"])["observations"]
    old = [row for line in raw["old_segments"].splitlines() if (row := json.loads(line)).get("record_type") == "SEGMENT"]
    new = [row for line in raw["new_segments"].splitlines() if (row := json.loads(line)).get("record_type") == "SEGMENT"]
    if not old or not new:
        raise ValueError("canonical SEGMENT records missing")
    for records in (old, new):
        if len({row["segment_id"] for row in records}) != len(records):
            raise ValueError("duplicate canonical segment ID")
        if any(sha(row["text"].encode("utf-8")) != row["text_sha256"] for row in records):
            raise ValueError("canonical segment text hash mismatch")
    by_id = {row["segment_id"]: row for row in new}
    old_by_unit = {}
    for row in old:
        for unit in {span["unit_ref"] for span in row["locator"]["spans"]}:
            old_by_unit.setdefault(unit, []).append(row)
    sample_rows = json.loads(raw["samples"])["segments"]
    samples = {row["segment_id"]: row for row in sample_rows}
    if len(samples) != len(sample_rows):
        raise ValueError("duplicate sample ID")
    opinion = json.loads(raw["opinion"])
    results = [row for row in opinion["results"] if row["subject_id"] == "corpus-v2"]
    if len(results) != 1:
        raise ValueError("expected one original corpus-v2 result")
    original_checks = results[0]["sample_checks"]
    if len({item["sample_id"] for item in original_checks}) != len(original_checks):
        raise ValueError("duplicate original opinion sample")
    verdicts = {item["sample_id"]: item["verdict"] for item in original_checks}
    if results[0]["verdict"] != "FAIL" or not any(value == "FAIL" for value in verdicts.values()):
        raise ValueError("original negative result missing")
    mapping = json.loads(raw["map"])
    reverse = {}
    for row in mapping["rows"]:
        for identity in row["new_segment_refs"]:
            reverse.setdefault(identity, set()).add(row["old_segment_ref"])
    rows = []
    for index, item in enumerate(observations):
        identity = item["sample_id"]
        current = by_id[identity]
        if verdicts.get(identity) != item["verdict"]:
            raise ValueError("observation verdict differs from original opinion")
        sample = {key: value for key, value in samples[identity].items() if key != "review_context"}
        if sample != current or item["locator"] != current["locator"]:
            raise ValueError("observation/sample/canonical locator mismatch")
        candidates = {row["segment_id"]: row for span in current["locator"]["spans"]
                      for row in old_by_unit.get(span["unit_ref"], [])}
        actual = [row for row in candidates.values() if overlap(row, current)]
        if {row["segment_id"] for row in actual} != reverse.get(identity, set()):
            raise ValueError("stored map disagrees with carrier overlap")
        kinds = sorted({row["kind"] for row in actual})
        claimed = item["evidence"]["old_kind"]
        rows.append({"sample_id": identity, "observation_pointer": f"/observations/{index}/evidence/old_kind",
                     "claimed_old_kind": claimed, "actual_old_kinds": kinds,
                     "matches": kinds == [claimed], "original_sample_verdict": item["verdict"],
                     "old_segments": [{"segment_id": row["segment_id"], "kind": row["kind"],
                                       "locator": row["locator"], "text_sha256": row["text_sha256"]} for row in actual],
                     "new_locator": current["locator"], "new_text_sha256": current["text_sha256"]})
    if len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate observation sample")
    if set(samples) != {row["sample_id"] for row in rows} or set(samples) != set(verdicts):
        raise ValueError("observations/opinion do not cover the exact selected samples")
    errors = [row for row in rows if not row["matches"]]
    return {"schema_version": 1, "kind": "CORPUS_OBSERVATION_CORRECTION_CROSSWALK",
            "authority_effect": "NONE", "qualification": "MODEL", "evidence_effect": "NONE",
            "method": "Same extraction/unit/overlapping Unicode spans; verify stored map, never equal p-number guessing.",
            "bindings": {key: {"path": paths[key], "sha256": sha(value)} for key, value in raw.items()},
            "checked": len(rows), "mismatches": len(errors),
            "negative_samples_with_mapping_error": sum(row["original_sample_verdict"] == "FAIL" for row in errors),
            "mismatch_groups": dict(Counter(f"{row['claimed_old_kind']} -> {','.join(row['actual_old_kinds'])}" for row in errors)),
            "rows": rows, "original_opinion_changed": False, "original_fail_retained": True,
            "corpus_product_changed": False, "literary_or_human_admission": False,
            "limitations": ["Corrects observation metadata only, not the reader's verdict or semantic truth.",
                            "No new extraction/rebuild, classification, review acceptance or release result."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = crosswalk(args.root.resolve())
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("checked", "mismatches", "negative_samples_with_mapping_error", "mismatch_groups")}, indent=2))
