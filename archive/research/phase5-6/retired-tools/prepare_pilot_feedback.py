"""Bind actually authored pilot editorial notes to their genuine draft parents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance

BASE = "artifacts/agent_research/phase6/advancement"


def create(root: Path, output: str) -> dict:
    destination = repository_path(root, output)
    if destination.exists():
        raise FileExistsError("refusing to overwrite pilot feedback")
    freeze_path = f"{BASE}/m2-input-freeze-v3/freeze.json"
    freeze_raw = repository_path(root, freeze_path).read_bytes()
    frozen = json.loads(freeze_raw)
    if frozen["delta_decision"]["corpus"] != "RETAIN_V2":
        raise ValueError("pilot requires selected retained-v2 line")
    rows, products = [], {}
    for chapter in (86, 95, 99):
        parent = frozen["pilot_parents"][str(chapter)]
        draft = json.loads(bound_bytes(root, parent["draft"]))
        if draft["candidate"] != parent["candidate"] or draft["chapter"] != chapter:
            raise ValueError("pilot parent mismatch")
        bound_bytes(root, draft["candidate"])
        for ref in draft["inputs"]:
            bound_bytes(root, ref)
        notes_path = f"{BASE}/pilot-notes-v2/notes-ch{chapter}-v1.txt"
        notes_raw = repository_path(root, notes_path).read_bytes()
        report = {"schema_version": 1, "kind": "WRITING_FEEDBACK", "qualification": "FEEDBACK_ONLY",
                  "draft": parent["draft"], "candidate": draft["candidate"], "inputs": draft["inputs"],
                  "checks": [{"evaluator": "COORDINATOR_ACTUAL_FULL_CHAPTER_EDITORIAL_PREFLIGHT",
                      "status": "PENDING", "notes": {"path": notes_path, "sha256": digest(notes_raw)},
                      "freeze": {"path": freeze_path, "sha256": digest(freeze_raw)},
                      "scope": "Actual chapter reading and editorial notes; no semantic/provider/human qualification.",
                      "finding": "Pilot may improve voice and scene rhythm; retained parent and full notes govern, not guaranteed acceptance."}],
                  "semantic_requests": [], "semantic_runs": [], "formal_eligibility": False,
                  "authority_effect": "NONE"}
        errors = validate_instance(report, root / "schemas/writing_feedback.schema.json")
        if errors:
            raise ValueError("; ".join(errors))
        raw = canonical_bytes(report)
        path = f"{output}/feedback-ch{chapter}.json"
        products[path] = raw
        rows.append({"chapter": chapter, "draft": parent["draft"],
                     "feedback": {"path": path, "sha256": digest(raw)},
                     "notes": {"path": notes_path, "sha256": digest(notes_raw)}})
    inventory = {"schema_version": 1, "kind": "PILOT_EDITORIAL_REVISION_INPUTS", "chapters": rows,
                 "authority_effect": "NONE", "status": "AWAITING_NORMAL_FRESH_PREPARATION",
                 "freeze": {"path": freeze_path, "sha256": digest(freeze_raw)}}
    products[f"{output}/inventory.json"] = canonical_bytes(inventory)
    destination.mkdir(parents=True)
    for path, raw in products.items():
        with repository_path(root, path).open("xb") as handle:
            handle.write(raw)
    return {"chapters": [86, 95, 99], "status": inventory["status"], "output": output}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(create(args.root.resolve(), args.output), indent=2))
