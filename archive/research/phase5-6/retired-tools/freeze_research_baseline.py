"""Freeze the current research tree and existing outcomes without reevaluating them."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path("artifacts/agent_research/phase6")
REVISIONS = BASE / "revisions-v2"
CHECKPOINT = BASE / "verification/engineering-checkpoint-19"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def document(root: Path, path: Path):
    return json.loads((root / path).read_bytes())


def binding(root: Path, path: Path) -> dict:
    raw = (root / path).read_bytes()
    return {"path": path.as_posix(), "sha256": digest(raw), "bytes": len(raw)}


def category(path: str) -> str:
    if path.startswith("data/catalog/"):
        return "CATALOG_GENERATED_CUSTODY"
    if path.startswith(("src/", "schemas/", "tools/")):
        return "IMPLEMENTATION"
    if path.startswith("tests/"):
        return "TEST"
    if path.startswith(("releases/proposals/", "data/releases/proposals/")):
        return "UNACTIVATED_PROPOSAL"
    if path.startswith(("artifacts/", "research/")):
        return "RESEARCH_EVIDENCE_OR_EXECUTION"
    if path.startswith(("corpus/", "data/corpus/")):
        return "CORPUS_PRODUCT_OR_CONFIGURATION"
    if path.startswith("data/"):
        return "VERSIONED_INPUT_OR_RECORD"
    return "OTHER_RETAINED_INPUT"


def capture(root: Path, excluded: Path) -> dict:
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).decode().split("\0")
    tracked = set(subprocess.check_output(
        ["git", "ls-files", "--cached", "-z"], cwd=root
    ).decode().split("\0"))
    dirty = set(subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD", "-z"], cwd=root
    ).decode().split("\0"))
    rows = {}
    for name in sorted(set(paths) - {""}):
        path = root / name
        if path.is_relative_to(excluded):
            continue
        if path.is_symlink():
            raise ValueError(f"snapshot input is a symlink: {name}")
        if not path.is_file():
            raise ValueError(f"snapshot input missing: {name}")
        rows[name] = {
            **binding(root, Path(name)), "category": category(name),
            "git_state": "UNTRACKED" if name not in tracked else "MODIFIED" if name in dirty else "TRACKED_UNCHANGED",
            "authorship": "NOT_INFERRED_FROM_GIT_STATE",
            "disposition": "RETAIN_NO_CLEANUP_OR_STAGING_AUTHORIZED",
        }
    return rows


def verify_expected(root: Path, expected: dict) -> list[str]:
    return [name for name, sha in expected.items()
            if not (root / name).is_file() or digest((root / name).read_bytes()) != sha]


def gate_items(report: dict) -> list[dict]:
    items = []
    for chapter in report["chapters"]:
        for gate, status in chapter["gates"].items():
            if status == "PASS":
                continue
            if gate == "CORPUS_PEERS" and status == "FAIL":
                reason, route = "RETAINED_NEGATIVE", "P2"
            elif gate == "CHAPTER_SAFETY_POLICY" and status == "FAIL":
                reason, route = "SELECTED_VERSION_CONFLICT", "P3/P4"
            elif gate == "CHAPTER_SAFETY_POLICY":
                reason, route = "MISSING_SEMANTIC_CONSUMER", "P3"
            elif gate == "SUPPLEMENTAL_SOURCE_EVIDENCE":
                reason, route = "MISSING_EVIDENCE_CONSUMER", "P1/P3"
            elif gate == "WRITING_PACKAGE" and status == "FAIL":
                reason, route = "UNRESOLVED_SOURCE_DEPENDENCY", "P1"
            elif gate == "COORDINATOR_DECISION":
                reason, route = "MISSING_DECISION", "P6"
            elif gate.endswith("_PEERS") and not (gate == "CORPUS_PEERS" and chapter["chapter"] == 86):
                reason, route = "MISSING_QUALIFYING_SCOPE_REVIEW", "P6"
            else:
                reason, route = "NOT_REACHED_OR_REQUIRES_INVESTIGATION", "P1/P2/P3"
            items.append({"chapter": chapter["chapter"], "gate": gate, "status": status,
                          "blocker_class": reason, "route": route,
                          "evidence_pointer": f"/chapters/{report['chapters'].index(chapter)}/gates/{gate}",
                          "owner_role": "RESEARCH_COORDINATOR", "task_state": "OPEN",
                          "interpretation": "Historical evaluator outcome; classification is a routing aid, not a new verdict."})
    return items


def freeze(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    if not output.is_relative_to(root) or output == root:
        raise ValueError("baseline output must be a new directory within the repository")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite baseline: {output}")
    protected_path = Path("artifacts/agent_research/phase5/verification/protected-originals-final.json")
    protected = document(root, protected_path)["checked_files"]
    prior = document(root, CHECKPOINT / "snapshot-inputs.json")
    for label, expected in (("protected originals", protected), ("checkpoint19 inputs", prior)):
        changed = verify_expected(root, expected)
        if changed:
            raise ValueError(f"{label} changed: {changed}")
    files = capture(root, output)
    report_path = REVISIONS / "release-evaluation/report-v3.json"
    report = document(root, report_path)
    selection_path = REVISIONS / "continuity-reading-selection-v1.json"
    selection = document(root, selection_path)
    if report["status"] != "FAIL" or report["output"]["text"] is not None:
        raise ValueError("unexpected historical evaluation outcome")
    if binding(root, Path(report["baseline"]["path"]))["sha256"] != report["baseline"]["sha256"]:
        raise ValueError("stable baseline differs from historical evaluation")
    if (root / report["output"]["directory"]).exists():
        raise ValueError("unexpected research release output already exists")
    if [row["chapter"] for row in report["chapters"]] != list(range(81, 101)):
        raise ValueError("release baseline must contain chapters81–100 exactly once in order")
    selected = {row["chapter"]: row for row in selection["chapters"]}
    for row in report["chapters"]:
        actual = binding(root, Path(row["bindings"]["candidate"]["path"]))
        if actual["sha256"] != row["bindings"]["candidate"]["sha256"] or actual["sha256"] != selected[row["chapter"]]["candidate"]["sha256"]:
            raise ValueError("release and continuity selections differ")
    record_paths = [
        protected_path, CHECKPOINT / "result.json", CHECKPOINT / "pytest.log", CHECKPOINT / "validate.json",
        selection_path, REVISIONS / "frozen-revisions-inventory-v10.json", REVISIONS / "final-audit-v1.json",
        REVISIONS / "release-evaluation/request-v1.json", REVISIONS / "release-evaluation/report-v1.json",
        report_path, REVISIONS / "release-evaluation/snapshot-custody-v3.json",
        REVISIONS / "release-evaluation/reader-fix-attempt-history-v1.json",
        REVISIONS / "comparison/coordinator/threeway-full-reading-synthesis-v1.json",
        REVISIONS / "continuity/fullbook-reading-reconciliation-v1.json",
        REVISIONS / "continuity/independent-two-queries-verification-v1.json",
        REVISIONS / "imports/ch86-v2-direct.json", REVISIONS / "authored/ch86-v2.txt",
        REVISIONS / "authored/ch91-v2.txt", REVISIONS / "readings/ch86-v2-reader2-custody-v1.json",
        BASE / "provenance/ch86-source-authority-closure-matrix-v1.json",
        BASE / "provenance/ch86-research-inputs-v1/observation.json",
        BASE / "provenance/ch86-research-inputs-v2/observation.json",
        BASE / "corpus/reader1-opinion-v1.json", BASE / "corpus/reader2-opinion-v1.json",
        Path("data/releases/proposals/v1.5.json"), Path("data/project/current.json"),
        Path("releases/stable/v1.4/manifest.json"), Path(report["baseline"]["path"]),
    ]
    records = [binding(root, path) for path in record_paths]
    retained_negatives = []
    for row in report["chapters"]:
        for review in row["reviews"].get("corpus_reviews", []):
            for finding in review.get("findings", []):
                if finding not in retained_negatives:
                    retained_negatives.append(finding)
    rows = [{"chapter": row["chapter"], "bindings": row["bindings"], "gates": row["gates"],
             "status": row["status"], "findings": row["findings"],
             "reading_revision": selected[row["chapter"]]["revision"]} for row in report["chapters"]]
    milestones = [{"id": key, "state": "OPEN", "scope": scope} for key, scope in (
        ("M1", "Source/corpus reviews, semantic specifications and minimal justified engineering"),
        ("M2", "Input freeze and explicit lineage-impact decision"),
        ("M3", "At most three genuine literary pilot revisions and comparison"),
        ("M4", "All20 editorial dispositions and version-appropriate rereading"),
        ("M5", "Final evaluation; blocked archive or separately authorized research build"))]
    ledger = {"schema_version": 1, "kind": "RESEARCH_ADVANCEMENT_BASELINE", "authority_effect": "NONE",
              "status": "NOT_ADOPTED_NOT_RELEASED", "evaluation_rerun": False,
              "evaluation": binding(root, report_path), "records": records, "chapters": rows,
              "open_gate_items": gate_items(report), "retained_corpus_negatives": retained_negatives,
              "milestones": [{"id": "M0", "state": "BASELINE_FROZEN_ENGINEERING_CHECK_PENDING"}] + milestones,
              "baseline_engineering": {"checkpoint": 19, "result": document(root, CHECKPOINT / "result.json"),
                                       "current_run": "NOT_YET_RUN"},
              "preservation": {"protected_count": len(protected), "protected_changed": [],
                               "checkpoint19_inputs_changed": [],
                               "stable_current_and_proposal": [ref for ref in records if ref["path"].startswith(("releases/", "data/project/", "data/releases/"))]},
              "unreached_semantics": [{"gate": "ADVISORY_CONTRACT_PROSE", "status": "NOT_CHECKED",
                                        "route": "P3", "reason": "Coverage inventory and consumer specification required; not a new release gate."}],
              "authorization": {"catalog_write": False, "new_all20_lineage": False, "gate_redefinition": False,
                                "build": False, "commit": False, "push": False, "stable_activation": False},
              "limitations": ["Bindings preserve actual files, not truth or authority.",
                              "Git state classifies custody, not authorship or permission to delete.",
                              "Policy/supplemental capability classification awaits specification review.",
                              "Full historical negative records remain in the captured tree; this index is not a replacement for them."]}
    changed = verify_expected(root, {name: row["sha256"] for name, row in files.items()})
    if changed:
        raise ValueError(f"input drift before baseline publication: {changed}")
    inventory = {"schema_version": 1, "kind": "ACTUAL_WORKTREE_CUSTODY_INVENTORY",
                 "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip(),
                 "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root).decode().strip(),
                 "files": files, "counts": dict(Counter(row["category"] for row in files.values())),
                 "git_state_counts": dict(Counter(row["git_state"] for row in files.values())),
                 "excluded": output.relative_to(root).as_posix(), "authority_effect": "NONE"}
    output.mkdir(parents=True)
    for name, value in (("inventory.json", inventory), ("baseline.json", ledger)):
        with (output / name).open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return {"files": len(files), "chapters": len(rows), "open_gate_items": len(ledger["open_gate_items"]),
            "retained_corpus_negative_records": len(retained_negatives), "protected_files": len(protected)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.root, args.output), indent=2))
