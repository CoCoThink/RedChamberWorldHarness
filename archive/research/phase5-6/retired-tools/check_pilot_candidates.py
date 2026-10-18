"""Read-only actual pilot mechanical checks; no import or literary verdict."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.agent_policies import evaluate_agent_policy
from rcwh.candidate_reviews import digest
from rcwh.generation.prose_integrity import prose_integrity
from rcwh.workflow.agent_release import _integrity

BASE = "artifacts/agent_research/phase6/advancement"


def check(root: Path) -> dict:
    old = json.loads((root / "artifacts/agent_research/phase6/revisions-v2/release-evaluation/report-v3.json").read_bytes())
    minimum = {row["chapter"]: row["minimum_body_characters"] for row in old["chapters"]}
    rows = []
    for chapter in (86, 95, 99):
        path = f"{BASE}/pilot-authored-v1/ch{chapter}-pilot-v1.txt"
        raw = (root / path).read_bytes()
        text = raw.decode("utf-8")
        integrity = _integrity(text)
        policy = json.loads((root / f"data/promotion/policies/agent/ch{chapter}.v1.json").read_bytes())
        policy_report = evaluate_agent_policy(root, policy, chapter, raw)
        lint = prose_integrity(text)
        request_path = f"{BASE}/pilot-requests-v2/ch{chapter}.json"
        request_raw = (root / request_path).read_bytes()
        request = json.loads(request_raw)
        if request["chapter"] != chapter or request["context"]["operation"] != "revise":
            raise ValueError("pilot request chapter or mode differs")
        rows.append({"chapter": chapter, "candidate": {"path": path, "sha256": digest(raw)},
                     "request": {"path": request_path, "sha256": digest(request_raw)},
                     "parent": request["parent"], "package": request["package"],
                     "integrity": integrity, "minimum_body_characters": minimum[chapter],
                     "length_status": "PASS" if integrity["body_characters"] >= minimum[chapter] else "FAIL",
                     "prose_integrity": lint, "policy": policy_report,
                     "disclosure": {"path": f"{BASE}/pilot-authored-v1/ch{chapter}-pilot-v1-disclosure.json",
                        "sha256": digest((root / f"{BASE}/pilot-authored-v1/ch{chapter}-pilot-v1-disclosure.json").read_bytes())}})
    failed = any(row["length_status"] == "FAIL" or row["prose_integrity"]["status"] == "FAIL"
                 or row["policy"]["anchor_status"] == "FAIL" for row in rows)
    return {"schema_version": 1, "kind": "PILOT_MECHANICAL_OBSERVATION", "authority_effect": "NONE",
            "status": "FAIL" if failed else "MECHANICAL_CHECKS_PASS_NOT_ACCEPTANCE",
            "chapters": rows, "import_called": False, "literary_adoption": "NOT_GRANTED",
            "limitation": "Length, headings, literal anchors and repeated-paragraph lint only; policy semantics remain pending."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = check(args.root.resolve())
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": value["status"], "chapters": [
        {"chapter": row["chapter"], "body": row["integrity"]["body_characters"],
         "minimum": row["minimum_body_characters"], "length": row["length_status"],
         "lint": row["prose_integrity"]["status"], "anchors": row["policy"]["anchor_status"]} for row in value["chapters"]]}, indent=2))
