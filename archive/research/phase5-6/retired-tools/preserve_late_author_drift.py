"""Preserve unexpected late-author output; never overwrite frozen draft paths."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def preserve(root: Path, output: Path):
    if output.exists():
        raise FileExistsError("refusing to overwrite incident evidence")
    checkpoint_path = "artifacts/agent_research/phase6/verification/engineering-checkpoint-26/snapshot-inputs.json"
    snapshot_raw = (root / checkpoint_path).read_bytes()
    snapshot = json.loads(snapshot_raw)
    products, rows = {}, []
    for chapter in range(96, 101):
        path = f"artifacts/agent_research/phase6/authored-v3/batch96-100/candidate-ch{chapter}.txt"
        current = (root / path).read_bytes()
        expected = snapshot[path]
        original_path = f"artifacts/candidates/ch{chapter}/{expected}.txt"
        original = (root / original_path).read_bytes()
        if sha(original) != expected:
            raise ValueError("preserved registered original differs from checkpoint")
        if sha(current) == expected:
            continue
        name = f"ch{chapter}-late-unregistered-{sha(current)}.txt"
        products[name] = current
        rows.append({"chapter": chapter, "changed_path": path,
                     "expected_sha256": expected, "observed_sha256": sha(current),
                     "preserved_late_bytes": {"path": (output / name).relative_to(root).as_posix(), "sha256": sha(current)},
                     "registered_original": {"path": original_path, "sha256": expected},
                     "restored": False})
    for row in rows:
        if sha((root / row["changed_path"]).read_bytes()) != row["observed_sha256"]:
            raise ValueError("late-author input still changing; no success archive")
    report = {"schema_version": 1, "kind": "LATE_OLD_AUTHOR_DRIFT_INCIDENT", "authority_effect": "NONE",
              "status": "LATE_OUTPUT_PRESERVED_ORIGINAL_PATH_RESTORATION_PENDING", "rows": rows,
              "checkpoint": {"path": checkpoint_path, "sha256": sha(snapshot_raw)},
              "stopped_old_task": "adf19c5f2a3d01a8f", "old_task_state": "STOP_CONFIRMED",
              "preparation_attempt": {"task": "bgvmmqhel", "status": "FAIL_INPUT_DRIFT_NO_COPYBACK",
                 "snapshot_fresh_chapters": [86, 95, 99], "request_delivery_completed": False},
              "limitation": "Late bytes are unregistered historical-author continuation, not selected pilot, imported revision or qualified result. No original path overwritten by this preservation tool."}
    output.mkdir(parents=True)
    for name, raw in products.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
    with (output / "incident.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"preserved_chapters": [row["chapter"] for row in rows], "restored": False}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preserve(args.root.resolve(), args.output.resolve())
