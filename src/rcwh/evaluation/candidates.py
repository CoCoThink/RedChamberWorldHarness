"""One semantic qualification path shared by competition and promotion."""
from pathlib import Path

from ..candidate_reviews import bound_data
from ..io import load_data
from ..knowledge import CharacterKnowledgeRuntime
from .semantics import check_reading, make_request, registered_reading
from .state import SceneStateAdapter


def candidate_semantics(root: Path, chapter: int, text: str, candidate: dict) -> dict:
    reports = []
    try:
        contracts = [load_data(p) for p in sorted((root / "data/scenes").glob("*.yaml"))]
        contracts = [c for c in contracts if c["chapter"] == chapter]
        if not contracts:
            return {"status": "PENDING", "pending": ["NO_SCENE_CONTRACT"], "reports": []}
        knowledge = CharacterKnowledgeRuntime.from_repo(root)
        schema = load_data(root / "schemas/semantic_reading.schema.json")
        supplied = [bound_data(root, b) for b in candidate.get("semantic_readings", [])]
        for contract in contracts:
            state = SceneStateAdapter(root, contract)
            request = make_request(contract, text, state.snapshot(), candidate.get("authors", []))
            matching = [r for r in supplied if r.get("contract_sha256") == request["contract_sha256"]]
            if len(matching) > 1:
                raise ValueError("duplicate semantic reading for scene")
            reading = matching[0] if matching else registered_reading(root, request)
            report = check_reading(request, reading, schema, knowledge, root)
            report["scene_id"] = contract["id"]
            preconditions = state.assert_contract_preconditions(contract)
            if preconditions:
                report["findings"].extend(preconditions)
                report["status"] = "FAIL"
            reports.append(report)
        status = "FAIL" if any(r["status"] == "FAIL" for r in reports) else "PENDING" if any(r["status"] != "PASS" for r in reports) else "PASS"
        return {"status": status, "reports": reports, "automatic_literary_pass": False}
    except (KeyError, OSError, ValueError) as exc:
        return {"status": "FAIL", "findings": [str(exc)], "reports": reports}
