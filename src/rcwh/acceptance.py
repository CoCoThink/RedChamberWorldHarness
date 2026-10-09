"""Live acceptance of the Review follow-up's declared inputs.

This reports admission, not literary adjudication or full-book delivery. A
pending external submission cannot be turned into a PASS by editing progress.
"""
from __future__ import annotations

from pathlib import Path

from .assets import AssetCatalog, AssetError
from .closure import InputClosure
from .corpus.audit import CorpusAudit
from .literary_inputs import LiteraryInputs
from .paired_review import PairedReview
from .workflow import ProjectState


class ProjectAcceptance:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def summary(self, *, require_tracked: bool = False) -> dict:
        checks = {}
        engineering = []

        def check(name, operation, *, technical=False):
            try:
                result = operation()
            except (AssetError, OSError, KeyError, ValueError) as exc:
                result = {"status": "FAIL", "findings": [str(exc)]}
            checks[name] = result
            if technical:
                engineering.append(name)
            return result

        catalog = AssetCatalog.from_repo(self.root)
        project = ProjectState.from_repo(self.root)
        scope = project.owner("closure")
        closure = check("declared_input_closure", lambda: InputClosure(self.root).verify(require_tracked=require_tracked))
        if "sources" in closure:
            checks["source_locators"] = closure["sources"]
            engineering.append("source_locators")
            checks["source_independent_reviews"] = closure["source_evidence_audit"]
            checks["declared_input_integrity"] = {
                "status": "FAIL" if closure["findings"] else "PASS",
                "findings": closure["findings"],
            }
            engineering.append("declared_input_integrity")
            for dataset in closure["datasets"]:
                name = f"corpus_rebuild:{dataset['dataset_ref']}"
                checks[name] = dataset
                engineering.append(name)
            if (closure["status"] == "FAIL" and not closure["findings"]
                    and closure["sources"]["status"] == "PASS"
                    and all(d["status"] == "PASS" for d in closure["datasets"])
                    and closure["source_evidence_audit"]["status"] == "PENDING"):
                checks["declared_input_closure"] = {
                    "status": "BLOCKED", "strict_status": "FAIL",
                    "blocked_by": ["source_independent_reviews"],
                    "input_digest": closure["input_digest"],
                    "root_set_digest": closure["root_set_digest"],
                }
        else:
            engineering.append("declared_input_closure")
        for dataset_ref in scope["datasets"]:
            check(f"corpus_human_review:{dataset_ref}", lambda ref=dataset_ref: CorpusAudit(catalog).summary(ref, rebuild=False))
        check("p9_submissions", lambda: PairedReview(catalog).selected_summary())
        packages = [binding for binding in scope["records"] if binding["schema"] == "writing_package"]
        if not packages:
            checks["writing_inputs"] = {"status": "FAIL", "findings": ["NO_DECLARED_WRITING_PACKAGE"]}
            engineering.append("writing_inputs")
        for binding in packages:
            path = binding["path"]
            name = f"writing_inputs:{path}"
            inputs = LiteraryInputs(catalog)
            def research(binding=binding, path=path):
                inputs.record(binding)
                return inputs.package(path, require_tracked=require_tracked)
            check(name, research, technical=True)
            production = check(f"production_admission:{path}", lambda path=path: inputs.package(path, production=True, require_tracked=require_tracked))
            pending = {"CORPUS_HUMAN_LAYER_AUDIT_PENDING", "DECLARED_INPUT_CLOSURE_INCOMPLETE", "P9_PAIRED_REVIEW_PENDING"}
            if (production["status"] == "FAIL" and not production.get("findings")
                    and production.get("production_blockers")
                    and set(production["production_blockers"]) <= pending):
                production["strict_status"] = "FAIL"
                production["status"] = "BLOCKED"
        failures = sorted(name for name, row in checks.items() if row["status"] == "FAIL")
        pending = sorted(name for name, row in checks.items() if row["status"] in {"PENDING", "BLOCKED"})
        return {
            "schema_version": 1, "scope": "REVIEW_FOLLOWUP_INPUT_ACCEPTANCE",
            "status": "FAIL" if failures else "PENDING" if pending else "PASS",
            "engineering_status": "PASS" if engineering and all(checks[name]["status"] == "PASS" for name in engineering) else "FAIL",
            "closure_ref": scope["id"], "checks": checks,
            "failed_checks": failures, "pending_checks": pending,
            "full_design_acceptance": "NOT_ASSESSED",
            "automatic_literary_pass": False, "authority_effect": "NONE",
        }
