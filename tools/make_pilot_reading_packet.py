"""Freeze six whole chapter copies after genuine imports; keep mapping separate."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance


def packet_files(root: Path, inventory: dict, public: str, coordinator: str) -> dict[str, bytes]:
    rows = inventory["chapters"]
    if [row["chapter"] for row in rows] != [86, 95, 99]:
        raise ValueError("pilot packet must contain exactly86,95,99 in order")
    if not isinstance(inventory["coordinator_session_id"], str) or not inventory["coordinator_session_id"].strip():
        raise ValueError("coordinator session required")
    sources, mapping = [], []
    # Validate full receipts rather than mistaking a finished .txt for an import.
    for row in rows:
        imported = json.loads(bound_bytes(root, row["import_receipt"]))
        result = imported["result"]
        if imported["status"] != "PASS" or result["status"] != "PASS" or imported["changed_original_inputs"]:
            raise ValueError("pilot import did not complete without drift")
        if result["candidate"] != row["pilot"] or result["draft"] != row["draft"]:
            raise ValueError("pilot import candidate/draft mismatch")
        draft = json.loads(bound_bytes(root, row["draft"]))
        parent = json.loads(bound_bytes(root, row["parent_draft"]))
        if (draft["chapter"] != row["chapter"] or parent["chapter"] != row["chapter"]
                or draft["candidate"] != row["pilot"] or parent["candidate"] != row["parent"]
                or draft["parent"] != row["parent_draft"] or draft["package"] != parent["package"]):
            raise ValueError("reading packet requires exact same-package genuine parent lineage")
        bound_bytes(root, draft["package"])
        for role in ("parent", "pilot"):
            raw = bound_bytes(root, row[role])
            raw.decode("utf-8")
            sources.append({"chapter": row["chapter"], "role": role, "binding": row[role], "raw": raw})
    identity = digest(canonical_bytes([{key: value for key, value in source.items() if key != "raw"} for source in sources]))
    rng = random.Random(int(identity, 16))
    subjects, files = [], {}
    for row in rows:
        pair = [source for source in sources if source["chapter"] == row["chapter"]]
        rng.shuffle(pair)
        for index, source in enumerate(pair):
            token = digest(canonical_bytes({"experiment": identity, "chapter": row["chapter"], "slot": index}))[:20]
            path = f"{public}/text-{token}.txt"
            files[path] = source["raw"]
            binding = {"path": path, "sha256": digest(source["raw"])}
            subjects.append({"id": f"text-{token}", "scope": "CANDIDATE", "binding": binding})
            mapping.append({"subject_id": f"text-{token}", "chapter": row["chapter"], "role": source["role"],
                            "original": source["binding"], "public": binding})
    packet = {"schema_version": 1, "packet_kind": "AGENT_REVIEW_PACKET", "id": "pilot-reading-" + identity[:20],
              "coordinator_session_id": inventory["coordinator_session_id"], "subjects": subjects,
              "authority_effect": "NONE", "usage": "RESEARCH_ONLY"}
    errors = validate_instance(packet, root / "schemas/agent_packet.schema.json")
    if errors:
        raise ValueError("invalid packet: " + "; ".join(errors))
    packet_raw = canonical_bytes(packet)
    files[f"{public}/packet.json"] = packet_raw
    files[f"{public}/reading-instructions.txt"] = (
        "Research-only anonymous whole-chapter comparison. Read every complete bound text; hash checks do not count as reading.\n"
        "Do not open coordinator mapping, authored originals, disclosures, notes, prior reviews or other reader opinions.\n"
        "Compare paired chapter versions on voice, causal scenes, rhythm, emotional turns, material/knowledge consistency and completeness.\n"
        "Keep concrete adverse evidence, ambiguity and relative preference separate. Quote exact file/line or Unicode spans.\n"
        "Do not certify source truth, human/provider independence, technical isolation, policy eligibility or literary adoption.\n"
        "No samples are declared: opinion sample_checks must be []. Complete reading is not itself a PASS verdict.\n"
    ).encode()
    order = [subject["id"] for subject in subjects]
    files[f"{coordinator}/mapping.json"] = canonical_bytes({
        "schema_version": 1, "kind": "PILOT_READING_COORDINATOR_MAPPING", "authority_effect": "NONE",
        "packet": {"path": f"{public}/packet.json", "sha256": digest(packet_raw)},
        "mapping": mapping, "reader_orders": [order, list(reversed(order))],
        "input_inventory": deepcopy(inventory),
        "limitations": ["Deterministic permutation is not cryptographic identity secrecy or technical isolation.",
                        "Parent86 is registered narrowv2, not the historical release-selectedv1.",
                        "Old negatives are preserved separately; copied anonymous paths do not automatically inherit peer credit."]})
    return files


def build(root: Path, inventory_ref: dict, public: str, coordinator: str) -> dict:
    root = root.resolve()
    public_path, private_path = repository_path(root, public), repository_path(root, coordinator)
    if (public_path.exists() or private_path.exists() or public_path == private_path
            or public_path.is_relative_to(private_path) or private_path.is_relative_to(public_path)):
        raise ValueError("reading packet requires separate new public/coordinator directories")
    inventory = json.loads(bound_bytes(root, inventory_ref))
    files = packet_files(root, inventory, public, coordinator)
    # All dependencies rechecked before copying; no generated prose or source edit.
    for row in inventory["chapters"]:
        for key in ("parent", "pilot", "draft", "parent_draft", "import_receipt"):
            bound_bytes(root, row[key])
        draft = json.loads(bound_bytes(root, row["draft"]))
        bound_bytes(root, draft["package"])
    for relative, raw in files.items():
        path = repository_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
    return {"status": "FROZEN_READING_PACKET_NOT_ADOPTED", "texts": 6,
            "packet": {"path": f"{public}/packet.json", "sha256": digest(files[f"{public}/packet.json"])},
            "authority_effect": "NONE"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--public", required=True)
    parser.add_argument("--coordinator", required=True)
    args = parser.parse_args()
    raw = repository_path(args.root, args.inventory).read_bytes()
    print(json.dumps(build(args.root, {"path": args.inventory, "sha256": digest(raw)}, args.public, args.coordinator), indent=2))
