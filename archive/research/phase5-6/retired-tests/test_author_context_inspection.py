"""Explicit shared-context disclosures do not certify peer independence."""
import importlib.util
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("author_inspector", ROOT / "tools/inspect_author_contexts.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_actual_disclosed_groups_and_selected_lineages_are_recomputed():
    saved = json.loads((ROOT / "artifacts/agent_research/phase6/advancement/declared-author-context-inspection-v1.json").read_bytes())
    assert saved == MODULE.inspect(ROOT)
    assert [group["chapters"] for group in saved["long_v1_groups"]] == [list(range(start, start + 5)) for start in (81, 86, 91, 96)]
    for group in saved["long_v1_groups"]:
        bound_bytes(ROOT, group["disclosure"])
        assert group["actual_declared_value"] is True or "Same author session" in group["actual_declared_value"]
    assert saved["identity_eligibility"] == "PENDING_INCOMPLETE_MAPPING"
    assert len(saved["selected_lineages"]) == 20
    by_chapter = {row["chapter"]: row for row in saved["selected_lineages"]}
    assert len(by_chapter[86]["chain"]) == 2
    assert len(by_chapter[91]["chain"]) == 3
    assert by_chapter[86]["chain"][0]["session_id"] == "phase6-reviser-ch86-context1"
    assert by_chapter[91]["chain"][0]["session_id"] == "phase6-main-narrow-reviser-ch91"
    assert by_chapter[86]["chain"][0]["candidate"]["sha256"] == "8351a6680a36e7899a583927a57c86a10121b6321e512b0f7b4cd457d24e5721"
    for row in saved["selected_lineages"]:
        for item in row["chain"]:
            for key in ("draft", "run", "candidate"):
                bound_bytes(ROOT, item[key])
            assert item["full_fresh_verification"] == "NOT_PERFORMED_BY_THIS_INSPECTOR"
