from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data
from .literary_eval import evaluate_literary_candidate
from .plocks import LiteraryProtectionRegistry
from .regression import run_r4_evidence_regression


PIPELINE = [
    "BASELINE_EXCERPT",
    "STRUCTURAL_REORDER",
    "SMALL_TRIAL",
    "SIX_FIELD_REGRESSION",
    "PLOCK_REGRESSION",
    "BLIND_READ",
]

SIX_FIELDS = ["PROVENANCE", "ROLE", "MODALITY", "TARGET", "PLACEMENT", "IMPLEMENTATION"]


def git_blob_sha(data: bytes) -> str:
    payload = f"blob {len(data)}\0".encode("utf-8") + data
    return hashlib.sha1(payload).hexdigest()


@dataclass
class CompetitionRegistry:
    records: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "CompetitionRegistry":
        result: dict[str, dict[str, Any]] = {}
        path = root / "data" / "competitions"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("competition_records", []):
                    item_id = item["id"]
                    if item_id in result:
                        raise ValueError(f"Duplicate competition id: {item_id}")
                    result[item_id] = item
        return cls(result)

    @staticmethod
    def load_file(path: Path) -> list[dict[str, Any]]:
        return (load_data(path) or {}).get("competition_records", [])

    def validate_integrity(
        self,
        root: Path,
        plocks: LiteraryProtectionRegistry,
        stable_active: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        production = [x for x in self.records.values() if x.get("mode") == "PRODUCTION_43_0"]
        expected = {
            "comp:43-0:ch86:pressure-test": (86, 1),
            "comp:43-0:ch89:pressure-test": (89, 2),
            "comp:43-0:ch92:pressure-test": (92, 3),
            "comp:43-0:ch97:pressure-test": (97, 4),
        }
        actual = {x["id"]: (x["chapter"], x["sequence"]) for x in production}
        if actual != expected:
            errors.append(f"43-0 competition order mismatch expected={expected} actual={actual}")

        ordered = sorted(production, key=lambda x: x["sequence"])
        for index, record in enumerate(ordered):
            errors.extend(self.validate_record(root, record, plocks, stable_active, True))
            if index > 0 and ordered[index - 1]["state"] != "ADJUDICATED":
                if record["state"] != "BLOCKED_BY_PREDECESSOR":
                    errors.append(
                        f"{record['id']}: must remain BLOCKED_BY_PREDECESSOR until "
                        f"{ordered[index-1]['id']} is ADJUDICATED"
                    )

        active = [x for x in ordered if x["state"] in {"READY_FOR_CANDIDATES", "IN_REVIEW"}]
        if len(active) > 1:
            errors.append(f"43-0 has multiple active competitions {[x['id'] for x in active]}")
        return errors

    def validate_record(
        self,
        root: Path,
        record: dict[str, Any],
        plocks: LiteraryProtectionRegistry,
        stable_active: dict[str, Any],
        production: bool = False,
    ) -> list[str]:
        errors: list[str] = []
        record_id = record["id"]

        if record["plock_ref"] not in plocks.locks:
            errors.append(f"{record_id}: unknown P-Lock {record['plock_ref']}")
        if record["baseline"] != stable_active:
            errors.append(f"{record_id}: baseline differs from frozen stable ACTIVE")
        if record["pipeline"] != PIPELINE:
            errors.append(f"{record_id}: pipeline order must be exactly {PIPELINE}")
        if record["stable_active_effect"] != "SEPARATE_PROMOTION_ONLY":
            errors.append(f"{record_id}: stable ACTIVE may only change through separate promotion")

        seen_unresolved = False
        for stage in PIPELINE:
            status = record["workflow_progress"][stage]
            if status in {"PENDING", "FAIL"}:
                seen_unresolved = True
            elif seen_unresolved:
                errors.append(
                    f"{record_id}: workflow stage {stage} cannot PASS before earlier stage resolves"
                )

        candidate_ids: set[str] = set()
        labels: set[str] = set()
        blind_tokens: set[str] = set()
        for candidate in record["candidates"]:
            cid = candidate["id"]
            if cid in candidate_ids:
                errors.append(f"{record_id}: duplicate candidate id {cid}")
            candidate_ids.add(cid)
            if candidate["label"] in labels:
                errors.append(f"{record_id}: duplicate candidate label {candidate['label']}")
            labels.add(candidate["label"])
            if candidate["blind_token"] in blind_tokens:
                errors.append(f"{record_id}: duplicate blind token {candidate['blind_token']}")
            blind_tokens.add(candidate["blind_token"])

            if list(candidate["six_field"].keys()) != SIX_FIELDS:
                errors.append(f"{record_id}/{cid}: six-field order must be {SIX_FIELDS}")

            artifact = candidate["artifact"]
            if artifact["kind"] == "REPO_FILE":
                required = ["path", "git_blob_sha", "source_commit"]
                missing = [x for x in required if not artifact.get(x)]
                if missing:
                    errors.append(f"{record_id}/{cid}: missing repo artifact fields {missing}")
                else:
                    path = root / artifact["path"]
                    if not path.exists():
                        errors.append(f"{record_id}/{cid}: artifact path missing {artifact['path']}")
                    else:
                        actual_sha = git_blob_sha(path.read_bytes())
                        if actual_sha != artifact["git_blob_sha"]:
                            errors.append(
                                f"{record_id}/{cid}: git blob identity mismatch "
                                f"{actual_sha} != {artifact['git_blob_sha']}"
                            )
            else:
                if artifact.get("file_ref") != stable_active["file_ref"]:
                    errors.append(f"{record_id}/{cid}: stable artifact file_ref mismatch")
                if artifact.get("sha256") != stable_active["sha256"]:
                    errors.append(f"{record_id}/{cid}: stable artifact SHA mismatch")

        adjudication = record["adjudication"]
        if adjudication["outcome"] == "WINNER":
            if not adjudication["winner_candidate_id"] or adjudication["winner_candidate_id"] not in candidate_ids:
                errors.append(f"{record_id}: WINNER outcome requires valid candidate id")
        elif adjudication["winner_candidate_id"] is not None:
            errors.append(f"{record_id}: non-WINNER outcome cannot carry winner_candidate_id")

        if adjudication["outcome"] == "PENDING" and adjudication["promotion_state"] != "NOT_ELIGIBLE":
            errors.append(f"{record_id}: pending competition cannot be promotion candidate")
        if production and record["state"] == "BLOCKED_BY_PREDECESSOR" and record["candidates"]:
            errors.append(f"{record_id}: blocked competition cannot already contain candidates")
        return errors

    def evaluate_record(self, root: Path, record: dict[str, Any]) -> dict[str, Any]:
        regression = run_r4_evidence_regression(root)
        results = []
        for candidate in record["candidates"]:
            artifact = candidate["artifact"]
            machine = None
            machine_match = None
            if artifact["kind"] == "REPO_FILE":
                text = (root / artifact["path"]).read_text(encoding="utf-8")
                machine = evaluate_literary_candidate(
                    root, record["plock_ref"], text, candidate_name=candidate["id"]
                )
                expected = candidate.get("machine_expected_status")
                machine_match = expected is None or machine["machine_status"] == expected

            machine_status = machine["machine_status"] if machine else "NOT_EVALUATED"
            six_pass = all(candidate["six_field"][field] == "PASS" for field in SIX_FIELDS)
            can_continue = machine_status in {"READY_FOR_BLIND_READ", "REPLACEMENT_CASE"}
            if machine_status == "REPLACEMENT_CASE":
                human_pass = candidate["human_plock"]["status"] == "REPLACEMENT_ACCEPTED"
            else:
                human_pass = candidate["human_plock"]["status"] == "PASS"
            blind = candidate["blind_read"]
            blind_pass = blind["status"] == "PASS" and blind["reviewer_blinded"] is True
            eligible = (
                regression["overall"] == "PASS"
                and can_continue
                and six_pass
                and human_pass
                and blind_pass
            )
            results.append({
                "id": candidate["id"],
                "label": candidate["label"],
                "blind_token": candidate["blind_token"],
                "machine_status": machine_status,
                "machine_expected_status": candidate.get("machine_expected_status"),
                "machine_matches_ledger": machine_match,
                "six_field_pass": six_pass,
                "human_plock_status": candidate["human_plock"]["status"],
                "blind_read_status": blind["status"],
                "reviewer_blinded": blind["reviewer_blinded"],
                "adjudication_eligible": eligible,
                "automatic_promotion": False,
            })

        by_id = {x["id"]: x for x in results}
        adj = record["adjudication"]
        consistency = []
        winner = adj["winner_candidate_id"]
        if winner:
            item = by_id.get(winner)
            if item is None or not item["adjudication_eligible"]:
                consistency.append(f"declared winner {winner} has not passed all promotion gates")
            if adj["promotion_state"] != "PROMOTION_CANDIDATE":
                consistency.append("eligible declared winner must be marked PROMOTION_CANDIDATE")
        elif adj["promotion_state"] == "PROMOTION_CANDIDATE":
            consistency.append("PROMOTION_CANDIDATE requires an adjudicated eligible winner")

        return {
            "competition": record["id"],
            "mode": record["mode"],
            "chapter": record["chapter"],
            "state": record["state"],
            "evidence_core_regression": regression["overall"],
            "stable_active_effect": record["stable_active_effect"],
            "workflow_progress": record["workflow_progress"],
            "candidate_results": results,
            "adjudication": adj,
            "consistency_errors": consistency,
            "stable_active_mutated": False,
            "note": "A winner can only become a promotion candidate; this layer never overwrites stable ACTIVE.",
        }


def format_competition(payload: dict[str, Any]) -> str:
    out = [
        "LITERARY COMPETITION",
        f"id: {payload['competition']}",
        f"mode: {payload['mode']}",
        f"chapter: {payload['chapter']}",
        f"state: {payload['state']}",
        f"evidence_core_regression: {payload['evidence_core_regression']}",
        f"stable_active_effect: {payload['stable_active_effect']}",
        "stable_active_mutated: false",
        "",
        "WORKFLOW",
    ]
    for stage in PIPELINE:
        out.append(f"- {stage}: {payload['workflow_progress'][stage]}")
    out.extend(["", "CANDIDATES"])
    if payload["candidate_results"]:
        for item in payload["candidate_results"]:
            out.append(
                f"- {item['label']} / {item['id']} / blind={item['blind_token']}: "
                f"machine={item['machine_status']}; six_field={item['six_field_pass']}; "
                f"human_plock={item['human_plock_status']}; blind={item['blind_read_status']}; "
                f"eligible={item['adjudication_eligible']}"
            )
    else:
        out.append("- none yet")
    out.extend(["", "ADJUDICATION"])
    out.append(f"- outcome: {payload['adjudication']['outcome']}")
    out.append(f"- winner: {payload['adjudication']['winner_candidate_id']}")
    out.append(f"- promotion_state: {payload['adjudication']['promotion_state']}")
    if payload["consistency_errors"]:
        out.extend(["", "CONSISTENCY ERRORS"])
        out.extend(f"- {x}" for x in payload["consistency_errors"])
    out.extend(["", payload["note"]])
    return "\n".join(out)
