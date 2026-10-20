"""Retained authorship across explicit, byte-bound rebind disclosures.

Old inputs may have retired. Attribution verifies retained draft/run/request
bytes and revision links, without claiming a replay of their writing inputs.
The current draft still passes the full writing-history check at release.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from ..assets import AssetError
from ..candidate_reviews import canonical_bytes, digest
from ..generation.records import bound_bytes
from ..generation.session import EXECUTION_BASIS
from ..schema import validate_instance


def _record(root: Path, ref: dict, schema: str) -> dict:
    value = json.loads(bound_bytes(root, ref))
    errors = validate_instance(value, root / f"schemas/{schema}.schema.json")
    if errors:
        raise AssetError(f"invalid attribution {schema}: " + "; ".join(errors))
    return value


def retained_chain(root: Path, ref: dict, chapter: int) -> list[dict]:
    chain, seen = [], set()
    while ref is not None:
        key = ref["sha256"]
        if key in seen:
            raise AssetError("attribution lineage cycle")
        seen.add(key)
        draft = _record(root, ref, "draft_registry")
        if draft["chapter"] != chapter or draft.get("execution_basis") != EXECUTION_BASIS:
            raise AssetError("attribution requires a same-chapter session draft")
        raw = bound_bytes(root, draft["candidate"])
        run = _record(root, draft["run"], "session_author_run")
        expected = [{"principal_id": "session:" + run["session_id"], "kind": "MODEL",
                     "source_id": "session-author:" + draft["run"]["sha256"], "run": draft["run"]}]
        if draft["authors"] != expected or run["output"].encode() != raw or run["output_sha256"] != draft["candidate"]["sha256"]:
            raise AssetError("attribution author/output mismatch")
        prepared = json.loads(bound_bytes(root, run["prepared_request"]))
        if (bound_bytes(root, run["imported_text"]) != raw
                or bound_bytes(root, run["request_source"]) != bound_bytes(root, run["prepared_request"])):
            raise AssetError("attribution retained import/request source mismatch")
        if (digest(canonical_bytes(prepared["request"])) != prepared["request_sha256"]
                or digest(canonical_bytes({k: prepared["request"][k] for k in ("system", "messages")})) != prepared["prompt_sha256"]
                or prepared["request"]["messages"] != [{"role": "user", "content": canonical_bytes(prepared["task"]).decode()}]):
            raise AssetError("attribution frozen request digest/task mismatch")
        for field in ("candidate", "prepared_request", "package", "inputs", "template", "prompt_sha256", "parent", "feedback"):
            if draft[field] != run[field]:
                raise AssetError(f"attribution draft/run {field} mismatch")
        for field in ("package", "inputs", "template", "prompt_sha256", "request_sha256", "parent", "feedback"):
            if run[field] != prepared[field]:
                raise AssetError(f"attribution run/request {field} mismatch")
        if draft["task"] != prepared["task"] or prepared["chapter"] != chapter:
            raise AssetError("attribution request task/chapter mismatch")
        if draft["parent"]:
            parent = json.loads(bound_bytes(root, draft["parent"]))
            feedback = json.loads(bound_bytes(root, draft["feedback"]))
            if (parent["chapter"] != chapter or feedback["draft"] != draft["parent"]
                    or feedback["candidate"] != parent["candidate"] or feedback["inputs"] != parent["inputs"]
                    or draft["task"].get("original") != bound_bytes(root, parent["candidate"]).decode()
                    or draft["task"].get("writing_task") != parent["task"]
                    or draft["task"].get("feedback") != feedback):
                raise AssetError("attribution revision parent/feedback mismatch")
        chain.append({"draft": ref, "candidate": draft["candidate"], "run": draft["run"], "package": draft["package"],
                      "authors": expected, "role": "REVISER" if draft["parent"] else "ORIGINAL_AUTHOR"})
        ref = draft["parent"]
    return chain


def release_attribution(root: Path, row: dict) -> dict | None:
    """Require an explicit disclosure for known rebind sessions; never infer authors."""
    draft = json.loads(bound_bytes(root, row["draft"]))
    run = json.loads(bound_bytes(root, draft["run"]))
    if "rebind_receipt" not in row:
        current, seen = row["draft"], set()
        while current:
            if current["sha256"] in seen:
                raise AssetError("attribution lineage cycle")
            seen.add(current["sha256"])
            ancestor = json.loads(bound_bytes(root, current))
            run = json.loads(bound_bytes(root, ancestor["run"]))
            if run.get("session_id", "").startswith("rebind-"):
                raise AssetError("rebind draft requires an explicit rebind_receipt")
            current = ancestor["parent"]
        return None
    receipt = _record(root, row["rebind_receipt"], "rebind_disclosure")
    newer = retained_chain(root, row["draft"], row["chapter"])
    matches = [link for link in newer if link["draft"] == receipt["current"]["draft"]]
    if len(matches) != 1:
        raise AssetError("rebind receipt current chapter/bindings mismatch")
    rebound = matches[0]
    expected = {"candidate": rebound["candidate"], "draft": rebound["draft"], "writing_package": rebound["package"]}
    if receipt["chapter"] != row["chapter"] or receipt["current"] != expected:
        raise AssetError("rebind receipt current chapter/bindings mismatch")
    previous = receipt["previous"]
    old = json.loads(bound_bytes(root, previous["draft"]))
    if old["candidate"] != previous["candidate"] or old["package"] != previous["writing_package"]:
        raise AssetError("rebind receipt previous bindings mismatch")
    bound_bytes(root, previous["writing_package"])
    before, after = bound_bytes(root, previous["candidate"]), bound_bytes(root, rebound["candidate"])
    identical = before == after
    if receipt["prose_identical_to_previous"] != identical:
        raise AssetError("rebind receipt prose identity declaration mismatch")
    if not identical:
        diff = ["\n".join(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(),
                                              fromfile="previous", tofile="current", n=0, lineterm=""))]
        if receipt.get("coordinator_edit") != diff or not receipt.get("edit_reason", "").strip():
            raise AssetError("rebind receipt must disclose the exact coordinator edit and reason")
    elif receipt.get("coordinator_edit"):
        raise AssetError("identical rebind cannot declare a coordinator edit")
    chain = retained_chain(root, previous["draft"], row["chapter"])
    custodians = [{**a, "role": "REBIND_CUSTODIAN"} for a in rebound["authors"]]
    contributors = [{**a, "role": link["role"]} for link in reversed(chain) for a in link["authors"]]
    if not identical:
        contributors.extend({**a, "role": "COORDINATOR_EDITOR"} for a in rebound["authors"])
    subsequent = newer[:newer.index(rebound)]
    contributors.extend({**a, "role": "REVISER"} for link in reversed(subsequent) for a in link["authors"])
    return {"receipt": row["rebind_receipt"], "declaration": receipt["declaration"],
            "verification": "RETAINED_RECORD_BYTES_AND_AUTHOR_RUN_BINDINGS",
            "previous_writing_inputs_replay": "NOT_CHECKED", "prose_identical_to_previous": identical,
            "contributors": contributors, "custodians": custodians, "chain": chain,
            "rebind_draft": rebound["draft"], "subsequent_revisions": subsequent,
            "coordinator_edit": receipt.get("coordinator_edit", []), "edit_reason": receipt.get("edit_reason"),
            "authority_effect": "NONE"}
