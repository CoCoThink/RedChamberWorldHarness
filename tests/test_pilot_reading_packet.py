"""Six full byte-identical copies, without fabricated normal-import receipts."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import binding

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pilot_packet", ROOT / "tools/make_pilot_reading_packet.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def store(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(value if isinstance(value, bytes) else canonical_bytes(value))
    return binding(root, path)


@pytest.fixture
def inputs(tmp_path):
    (tmp_path / "schemas").mkdir()
    shutil.copyfile(ROOT / "schemas/agent_packet.schema.json", tmp_path / "schemas/agent_packet.schema.json")
    rows = []
    for chapter in (86, 95, 99):
        parent_text = store(tmp_path, f"parent{chapter}.txt", f"第{chapter}回\n原完整fixture章\r\n".encode())
        pilot_text = store(tmp_path, f"pilot{chapter}.txt", f"第{chapter}回\n新完整fixture章\r\n".encode())
        package = store(tmp_path, f"package{chapter}.json", {"chapter": chapter})
        parent = store(tmp_path, f"parentdraft{chapter}.json", {"chapter": chapter, "candidate": parent_text, "package": package})
        draft = store(tmp_path, f"draft{chapter}.json", {"chapter": chapter, "candidate": pilot_text, "parent": parent, "package": package})
        receipt = store(tmp_path, f"import{chapter}.json", {"status": "PASS", "result": {"status": "PASS", "candidate": pilot_text, "draft": draft}, "changed_original_inputs": []})
        rows.append({"chapter": chapter, "parent": parent_text, "pilot": pilot_text, "parent_draft": parent, "draft": draft, "import_receipt": receipt})
    return tmp_path, {"coordinator_session_id": "fixture-coordinator", "chapters": rows}


def test_full_texts_exact_mapping_separate_and_counterbalanced(inputs):
    root, inventory = inputs
    files = MODULE.packet_files(root, inventory, "public", "coordinator")
    packet = json.loads(files["public/packet.json"])
    mapping = json.loads(files["coordinator/mapping.json"])
    assert len(packet["subjects"]) == 6
    assert mapping["reader_orders"][0] == list(reversed(mapping["reader_orders"][1]))
    assert {row["role"] for row in mapping["mapping"]} == {"parent", "pilot"}
    assert not any("mapping" in path for path in files if path.startswith("public/"))
    for row in mapping["mapping"]:
        assert files[row["public"]["path"]] == (root / row["original"]["path"]).read_bytes()
        assert digest(files[row["public"]["path"]]) == row["public"]["sha256"]
    assert MODULE.packet_files(root, inventory, "public", "coordinator") == files


@pytest.mark.parametrize("fault", ["missing_chapter", "wrong_parent", "wrong_package", "failed_import", "input_drift", "stale_text", "missing_receipt"])
def test_missing_lineage_or_failed_import_cannot_become_reading_packet(inputs, fault):
    root, inventory = inputs
    row = inventory["chapters"][0]
    if fault == "missing_chapter":
        inventory["chapters"].pop()
    elif fault in ("wrong_parent", "wrong_package"):
        draft = json.loads((root / row["draft"]["path"]).read_bytes())
        draft["parent" if fault == "wrong_parent" else "package"] = {"path": "other", "sha256": "0" * 64}
        row["draft"] = store(root, row["draft"]["path"], draft)
        receipt = json.loads((root / row["import_receipt"]["path"]).read_bytes())
        receipt["result"]["draft"] = row["draft"]
        row["import_receipt"] = store(root, row["import_receipt"]["path"], receipt)
    elif fault in ("failed_import", "input_drift"):
        receipt = json.loads((root / row["import_receipt"]["path"]).read_bytes())
        if fault == "failed_import":
            receipt["status"] = "FAIL"
        else:
            receipt["changed_original_inputs"] = ["fixture"]
        row["import_receipt"] = store(root, row["import_receipt"]["path"], receipt)
    elif fault == "stale_text":
        (root / row["pilot"]["path"]).write_bytes(b"changed")
    else:
        (root / row["import_receipt"]["path"]).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        MODULE.packet_files(root, inventory, "public", "coordinator")


@pytest.mark.parametrize("fault", ["stale", "missing"])
def test_matching_package_refs_still_require_actual_bound_package(inputs, fault):
    root, inventory = inputs
    draft = json.loads((root / inventory["chapters"][0]["draft"]["path"]).read_bytes())
    package = root / draft["package"]["path"]
    if fault == "stale":
        package.write_bytes(b"changed")
    else:
        package.unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        MODULE.packet_files(root, inventory, "public", "coordinator")


def test_outputs_need_separate_new_directories(inputs):
    root, inventory = inputs
    ref = store(root, "inventory.json", inventory)
    with pytest.raises(ValueError):
        MODULE.build(root, ref, "public", "public/private")
    MODULE.build(root, ref, "public", "coordinator")
    with pytest.raises(ValueError):
        MODULE.build(root, ref, "public", "another-coordinator")
