"""Capture retained-v2 selections, separating live inputs from saved diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes

BASE = "artifacts/agent_research/phase6/revisions-v2"
SELECTION = f"{BASE}/continuity-reading-selection-v1.json"
REQUEST = f"{BASE}/release-evaluation/request-v1.json"
EXPERIMENT = "artifacts/agent_research/phase6/advancement/corpus-title-compatibility-v1"
V1 = "artifacts/agent_research/phase6/advancement/m2-input-freeze-v1/freeze.json"
V2 = "artifacts/agent_research/phase6/advancement/m2-input-freeze-v2/freeze.json"


def validate_selected_draft(row: dict, draft: dict) -> None:
    if (draft["chapter"] != row["chapter"] or draft["candidate"] != row["candidate"]
            or draft["package"] != row["writing_package"]):
        raise ValueError("selected draft chapter/candidate/package relationship differs")


def validate_prepared_package(row: dict, prepared: dict) -> None:
    if prepared["chapter"] != row["chapter"] or prepared["package"] != row["writing_package"]:
        raise ValueError("selected package differs from historical prepared package")


def binding(root: Path, path: str) -> dict:
    return {"path": path, "sha256": digest(repository_path(root, path).read_bytes())}


def load_bound(root: Path, ref: dict):
    return json.loads(bound_bytes(root, ref))


def direct_prepared_inputs(prepared: dict) -> list[dict]:
    """Match session._verify_prepared_request's direct binding validation scope."""
    return prepared["inputs"] + [prepared[key] for key in ("template", "package", "parent", "feedback")
                                 if prepared[key] is not None]


def saved_binding_observations(root: Path, value, pointer="") -> list[dict]:
    """Record saved diagnostics, never promote recursive path-shaped data to input."""
    rows = []
    if isinstance(value, dict):
        if set(value) == {"path", "sha256"} and isinstance(value["path"], str):
            path = repository_path(root, value["path"])
            actual = digest(path.read_bytes()) if path.is_file() else None
            if actual != value["sha256"]:
                rows.append({"pointer": pointer, "declared": value, "actual_sha256": actual,
                             "role": "EMBEDDED_SAVED_OBSERVATION_NOT_DIRECT_INPUT"})
        else:
            for key, item in value.items():
                escaped = key.replace("~", "~0").replace("/", "~1")
                rows.extend(saved_binding_observations(root, item, pointer + "/" + escaped))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(saved_binding_observations(root, item, pointer + f"/{index}"))
    return rows


def project(root: Path) -> tuple[dict, dict]:
    root = root.resolve()
    inputs = {}

    def retain(ref):
        bound_bytes(root, ref)
        if ref["path"] in inputs and inputs[ref["path"]] != ref:
            raise ValueError("conflicting direct input binding")
        inputs[ref["path"]] = dict(ref)
        return dict(ref)

    def read(path):
        ref = retain(binding(root, path))
        return json.loads(bound_bytes(root, ref)), ref

    request, request_ref = read(REQUEST)
    selection, selection_ref = read(SELECTION)
    for value in (request, selection):
        if [row["chapter"] for row in value["chapters"]] != list(range(81, 101)):
            raise ValueError("selection must cover chapters81–100 exactly in order")
    selected = {row["chapter"]: row for row in selection["chapters"]}
    chapters, prepared_refs, observations, count = {}, {}, [], 0
    for row in request["chapters"]:
        ch = row["chapter"]
        reading = selected[ch]
        candidate = retain(row["candidate"])
        retain(reading["candidate"])
        if reading["candidate"]["sha256"] != candidate["sha256"]:
            raise ValueError("release and reading candidate selections differ")
        package = retain(row["writing_package"])
        policy = retain(row["policy"])
        draft = retain(row["draft"])
        validate_selected_draft(row, load_bound(root, draft))
        package_value = load_bound(root, package)
        if package_value["chapter"] != ch:
            raise ValueError("package chapter mismatch")
        exemplar = retain(package_value["exemplar_set"])
        if exemplar["path"] != "data/writing/exemplars/ch89-research-v2.json":
            raise ValueError("selected package does not retain shared v2 exemplar")
        exemplar_value = load_bound(root, exemplar)
        if exemplar_value["dataset_ref"] != "corpus:front80:v2-candidate":
            raise ValueError("selected exemplar does not retain corpus v2")
        config, config_ref = read("data/corpus/builds/front80-v2-candidate.json")
        manifest, manifest_ref = read("corpus/front80/v2-candidate/manifest.json")
        if manifest_ref["sha256"] != exemplar_value["manifest_sha256"] or config_ref != {
                key: manifest["build_config"][key] for key in ("path", "sha256")}:
            raise ValueError("corpus config/manifest/exemplar mismatch")
        prepared, prepared_ref = read(f"{BASE}/requests/ch{ch}.json")
        prepared_refs[str(ch)] = prepared_ref
        validate_prepared_package(row, prepared)
        refs = direct_prepared_inputs(prepared)
        for ref in refs:
            retain(ref)
        count += len(refs)
        observations.extend({"chapter": ch, "prepared": prepared_ref, **item}
                            for item in saved_binding_observations(root, prepared["task"], "/task"))
        chapters[str(ch)] = {"chapter": ch, "candidate": candidate, "draft": draft,
                            "policy": policy, "package": package, "exemplar": exemplar,
                            "reading_revision": reading["revision"],
                            "selection_effect": reading["selection_effect"],
                            "input_delta": "NO_SELECTED_PACKAGE_CHANGE_RETAIN_V2",
                            "new_revision_request_required": ch in (86, 95, 99)}
    report, report_ref = read(f"{EXPERIMENT}/report.json")
    churn, churn_ref = read(f"{EXPERIMENT}/product-churn.json")
    impact, impact_ref = read(f"{EXPERIMENT}/package-impact.json")
    mask, mask_ref = read(f"{EXPERIMENT}/interval-change-mask.json")
    if len(mask) != report["analysis"]["interval_count"]:
        raise ValueError("experiment mask count differs from report")
    changes = sum(not row["same_after_dataset_identity_only"] for row in churn)
    if changes != report["analysis"]["products_changed_beyond_dataset_identity"]:
        raise ValueError("experiment product churn count differs from report")
    # The user retained the v2 corpus/package line. The pilot may explicitly use
    # an already imported newer parent without rewriting the release selection.
    import86, import86_ref = read(f"{BASE}/imports/ch86-v2-direct.json")
    pilot86 = import86["result"].get("draft")
    if pilot86 is None:
        raise ValueError("normal ch86-v2 import receipt has no draft")
    retain(pilot86)
    pilot86_doc = load_bound(root, pilot86)
    if pilot86_doc["package"] != chapters["86"]["package"] or pilot86_doc["chapter"] != 86:
        raise ValueError("pilot86 parent must retain its actual package and chapter")
    retain(pilot86_doc["candidate"])
    pilot_parents = {"86": {"draft": pilot86, "candidate": pilot86_doc["candidate"],
                            "basis": import86_ref, "selection_effect": "PILOT_PARENT_ONLY_NOT_RELEASE_ADOPT"}}
    for ch in (95, 99):
        pilot_parents[str(ch)] = {"draft": chapters[str(ch)]["draft"], "candidate": chapters[str(ch)]["candidate"],
                                 "selection_effect": "PILOT_PARENT_ONLY_NOT_RELEASE_ADOPT"}
    protected, protected_ref = read("artifacts/agent_research/phase5/verification/protected-originals-final.json")
    for path, sha in protected["checked_files"].items():
        retain({"path": path, "sha256": sha})
    # Bind prior negatives and adverse findings, not only convenient input successes.
    history = [f"{BASE}/release-evaluation/report-v3.json",
               "artifacts/agent_research/phase6/corpus/reader1-opinion-v1.json",
               "artifacts/agent_research/phase6/corpus/reader2-opinion-v1.json",
               "artifacts/agent_research/phase6/advancement/source-range-adverse-findings-v1.json",
               f"{BASE}/continuity/fullbook-reading-reconciliation-v1.json",
               f"{BASE}/readings/ch91-v1-reader1.json",
               f"{BASE}/ch86-policy-gate-diagnostic-v1.json"]
    prior_records = [retain(binding(root, path)) for path in history]
    prior_v1 = retain(binding(root, V1))
    prior_v2 = retain(binding(root, V2))
    inventory = {"kind": "M2_DIRECT_INPUT_BYTE_INVENTORY", "schema_version": 1,
                 "bindings": inputs, "direct_prepared_binding_occurrences": count,
                 "embedded_saved_observations": observations, "authority_effect": "NONE"}
    result = {"schema_version": 3, "kind": "RESEARCH_INPUT_FREEZE",
              "status": "FROZEN_RETAIN_V2_NOT_ADOPTED", "authority_effect": "NONE",
              "evidence_effect": "NONE", "qualification": "MODEL", "operation_scope": "RESEARCH_ONLY",
              "selection": selection_ref, "release_request": request_ref, "chapters": chapters,
              "prepared_requests": prepared_refs, "pilot_parents": pilot_parents,
              "prior_records": prior_records, "protected_originals": protected_ref,
              "protected_count": len(protected["checked_files"]),
              "shared_inputs": {"selected_binding_count": len(inputs),
                  "direct_prepared_binding_occurrences": count, "direct_stale_bindings": [],
                  "embedded_saved_observation_count": len(observations)},
              "delta_decision": {"corpus": "RETAIN_V2", "exemplar": "RETAIN_EXISTING_V2",
                  "packages": "NO_NEW_PACKAGES", "old_prepared_requests": "UNCHANGED_HISTORICAL_REQUESTS",
                  "new_pilot_prepared_requests": "REQUIRED_BEFORE_WRITING", "v3_candidate": "NOT_SELECTED_FOR_THIS_ROUND"},
              "v3_experiment_impact": {"report": report_ref, "product_churn": churn_ref,
                  "package_impact": impact_ref, "interval_mask": mask_ref, "status": report["status"],
                  "interval_count": len(mask), "products_changed_beyond_dataset_identity": changes,
                  "shifted_exact_locator_segment_count": report["analysis"]["shifted_exact_locator_segment_count"],
                  "new_package_or_lineage_calls": bool(impact["lineage_calls"] or impact["new_exemplar_or_package_created"])},
              "pilot_gate": {"status": "READY_FOR_NEW_REVISION_PREPARATION_NOT_YET_FRESH_VERIFIED",
                  "chapters": [86, 95, 99], "fresh_preparation_run": False, "import_run": False},
              "authorities": {"source_qualification": "PENDING", "corpus_human_acceptance": "PENDING",
                  "policy_semantics": "PENDING", "contract_runtime": "PENDING", "literary_adoption": "NOT_GRANTED",
                  "independent_human_admission": False, "stable_active_effect": "NONE"},
              "correction": {"prior_v1": prior_v1, "superseded_for_current_use": prior_v2,
                  "reason": "v1 confused product count86 with mask30 and saved diagnostics with live inputs; v2 count omitted its correction binding and lacked explicit draft/prepared-package relation checks. Both prior versions retained."},
              "limitations": ["Direct input byte custody is not fresh renderer validation or generation consumption.",
                  "Embedded old-lock diagnostics remain untouched; new preparation uses the unchanged existing validator.",
                  "Pilot parents are explicit research choices, not release selection replacements.",
                  "Freezing does not discharge source/corpus/semantic/contract gates or authorize build/commit/push/stable."]}
    inventory["bindings"] = inputs
    return result, inventory


def freeze(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite input freeze: {output}")
    if not output.is_relative_to(root) or output == root:
        raise ValueError("freeze output must be a new repository subdirectory")
    result, inventory = project(root)
    inventory_raw = canonical_bytes(inventory)
    result["input_inventory"] = {"path": (output / "input-inventory.json").relative_to(root).as_posix(),
                                 "sha256": digest(inventory_raw)}
    result["freeze_sha256"] = digest(canonical_bytes(result))
    # Check captured live bytes again before any success record is published.
    for ref in inventory["bindings"].values():
        bound_bytes(root, ref)
    output.mkdir(parents=True)
    with (output / "input-inventory.json").open("xb") as stream:
        stream.write(inventory_raw)
    with (output / "freeze.json").open("xb") as stream:
        stream.write(canonical_bytes(result))
    return {"chapters": len(result["chapters"]), "selected_bindings": len(inventory["bindings"]),
            "pilot_gate": result["pilot_gate"]["status"], "freeze_sha256": result["freeze_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.root, args.output), ensure_ascii=False, indent=2))
