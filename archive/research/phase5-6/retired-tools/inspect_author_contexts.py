"""Inspect explicitly disclosed long-author groups; never authenticate identities."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def inspect(root: Path) -> dict:
    base = "artifacts/agent_research/phase6/revisions-v2"

    def bound(path):
        raw = (root / path).read_bytes()
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}

    declarations = [
        (list(range(81, 86)), 85, "/extra_context_exposure/same_session_as_chapters_81_through_84"),
        (list(range(86, 91)), 90, "/additional_author_context/same_continuing_context_as_ch86_through_ch89"),
        (list(range(91, 96)), 95, "/model_declaration/same_author_context_as91_to94"),
        (list(range(96, 101)), 100, "/actual_consumption/adjacent_author_context/reason"),
    ]
    groups = []
    for chapters, chapter, pointer in declarations:
        path = f"{base}/authored/ch{chapter}-v1-disclosure.json"
        value = json.loads((root / path).read_bytes())
        for key in pointer.split("/")[1:]:
            value = value[key]
        groups.append({"local_group_key": f"disclosed-long-v1-{chapters[0]}-{chapters[-1]}",
                       "chapters": chapters, "disclosure": bound(path), "pointer": pointer,
                       "actual_declared_value": value,
                       "basis": "EXPLICIT_EXISTING_DISCLOSURE_NOT_PROVIDER_CONTEXT_ATTESTATION"})
    selection_path = f"{base}/release-evaluation/request-v1.json"
    selection = json.loads((root / selection_path).read_bytes())
    lineages = []
    for row in selection["chapters"]:
        current, seen, chain = row["draft"], set(), []
        while current is not None:
            if current["sha256"] in seen:
                raise ValueError("author lineage cycle")
            seen.add(current["sha256"])
            if bound(current["path"]) != current:
                raise ValueError("stale draft binding")
            draft = json.loads((root / current["path"]).read_bytes())
            if draft["package"] != row["writing_package"] or draft["chapter"] != row["chapter"]:
                raise ValueError("draft crosses chapter/package lineage")
            if not chain and draft["candidate"] != row["candidate"]:
                raise ValueError("selected candidate differs from draft")
            if bound(draft["candidate"]["path"]) != draft["candidate"] or bound(draft["run"]["path"]) != draft["run"]:
                raise ValueError("stale candidate or author run")
            run = json.loads((root / draft["run"]["path"]).read_bytes())
            expected = [{"principal_id": "session:" + run["session_id"],
                         "source_id": "session-author:" + draft["run"]["sha256"],
                         "kind": "MODEL", "run": draft["run"]}]
            if draft["authors"] != expected or run["output"].encode() != (root / draft["candidate"]["path"]).read_bytes():
                raise ValueError("draft/run author-output mismatch")
            chain.append({"draft": current, "run": draft["run"], "candidate": draft["candidate"],
                          "session_id": run["session_id"], "authors": draft["authors"],
                          "full_fresh_verification": "NOT_PERFORMED_BY_THIS_INSPECTOR"})
            current = draft["parent"]
        lineages.append({"chapter": row["chapter"], "chain": chain})
    return {"schema_version": 1, "kind": "DECLARED_AUTHOR_CONTEXT_INSPECTION",
            "authority_effect": "NONE", "qualification": "MODEL", "selection": bound(selection_path),
            "long_v1_groups": groups, "selected_lineages": lineages,
            "coordinator_narrow_disclosures": [bound(f"{base}/authored/ch{chapter}-v2-disclosure.json") for chapter in (86, 91)],
            "identity_eligibility": "PENDING_INCOMPLETE_MAPPING",
            "limitations": ["Local group keys label explicit disclosures; not authenticated runtime context IDs.",
                            "Selected ancestry includes short-parent authors not assigned to long-v1 groups.",
                            "Coordinator narrow contributions remain separately disclosed;86v2not selected.",
                            "No provider verification, full fresh renderer/import or positive independence count."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = inspect(args.root.resolve())
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"groups": len(value["long_v1_groups"]), "chapters": len(value["selected_lineages"]),
                      "identity_eligibility": value["identity_eligibility"]}))
