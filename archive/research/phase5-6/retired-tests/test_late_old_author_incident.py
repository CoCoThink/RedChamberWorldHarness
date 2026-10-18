"""Late unregistered output is retained; authorized restoration is exact."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/agent_research/phase6/advancement/late-old-author-incident-v1"


def test_late_old_author_bytes_preserved_and_original_paths_restored():
    incident = json.loads((BASE / "incident.json").read_bytes())
    restored = json.loads((BASE / "restoration-v1.json").read_bytes())
    bound_bytes(ROOT, restored["source_incident"])
    assert restored["status"] == "RESTORED_EXACT_CHECKPOINT26_BYTES"
    assert restored["chapters"] == list(range(96, 101))
    assert incident["old_task_state"] == "STOP_CONFIRMED"
    assert incident["preparation_attempt"]["status"] == "FAIL_INPUT_DRIFT_NO_COPYBACK"
    assert not incident["preparation_attempt"]["request_delivery_completed"]
    assert not restored["late_bytes_deleted"]
    for item in restored["restored"]:
        bound_bytes(ROOT, {"path": item["path"], "sha256": item["sha256"]})
        late = bound_bytes(ROOT, item["late_bytes_retained"])
        old = next(row for row in incident["rows"] if row["changed_path"] == item["path"])
        assert item["late_bytes_retained"]["sha256"] == old["observed_sha256"]
        assert item["sha256"] == old["expected_sha256"] != old["observed_sha256"]
        assert late != bound_bytes(ROOT, old["registered_original"])
