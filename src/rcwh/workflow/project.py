from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..assets import AssetCatalog, AssetError
from ..assets.catalog import repository_path
from ..io import load_data
from ..publication import ReleaseManifest
from ..schema import validate_instance


@dataclass
class ProjectState:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "ProjectState":
        data = load_data(root / "data/project/current.json")
        errors = validate_instance(data, root / "schemas/project_owners.schema.json")
        if errors:
            raise AssetError("invalid project owners: " + "; ".join(errors))
        return cls(root, data)

    def owner(self, name: str) -> dict[str, Any]:
        value = load_data(repository_path(self.root, self.data["owners"][name]))
        if not isinstance(value, dict):
            raise AssetError(f"project owner {name} must be an object")
        schemas = {"implementation": "implementation_progress", "capability": "capability_selection", "literary": "literary_resume_state", "plan_constraints": "plan_constraints", "closure": "closure_roots"}
        if name in schemas:
            errors = validate_instance(value, self.root / f"schemas/{schemas[name]}.schema.json")
            if errors:
                raise AssetError(f"invalid {name} owner: " + "; ".join(errors))
        if name == "implementation":
            if value["status"] == "COMPLETE" and any(v != "COMPLETE" for v in value["stages"].values()):
                raise AssetError("implementation cannot be COMPLETE with unfinished stages")
        return value

    def experiment(self) -> dict[str, Any]:
        selection = self.owner("capability")
        path = repository_path(self.root, selection["experiment_ref"])
        value = load_data(path)
        errors = validate_instance(value, self.root / "schemas/revision_ablation.schema.json")
        if errors:
            raise AssetError("invalid selected experiment: " + "; ".join(errors))
        return value

    def capability(self) -> dict[str, Any]:
        from ..blind_microdraft_review import BlindMicrodraftReviewRuntime
        from ..microdraft import ControlledMicrodraftRuntime
        from ..narrative_discourse import NarrativeDiscourseRuntime
        from ..literary_stress import ScenarioLiteraryStressRuntime
        from ..literary_suite import LiteraryEvaluatorSuite
        from ..revision_ablation import CrossRouteRevisionAblationRuntime
        selection = self.owner("capability")
        experiment = CrossRouteRevisionAblationRuntime(self.root, self.experiment())
        findings = experiment.validate_integrity(
            ControlledMicrodraftRuntime.from_repo(self.root), BlindMicrodraftReviewRuntime.from_repo(self.root),
            NarrativeDiscourseRuntime.from_repo(self.root), ScenarioLiteraryStressRuntime.from_repo(self.root),
            LiteraryEvaluatorSuite.from_repo(self.root),
        )
        return {
            "id": experiment.data["id"], "kind": selection["kind"],
            "status": "BLOCKED" if findings else "PASS", "findings": findings,
            "authority": experiment.data["authority"], "next_gate": experiment.data["next_gate"],
        }

    def release(self, catalog: AssetCatalog | None = None) -> ReleaseManifest:
        return ReleaseManifest.from_repo(self.root, self.data["owners"]["release"], catalog)

    def plan_constraints(self, catalog: AssetCatalog | None = None) -> dict[str, Any]:
        from ..contracts import record_sha256, unique_index

        plan = self.owner("plan_constraints")
        binding = self.data["plan_constraints_binding"]
        if plan["id"] != binding["id"] or record_sha256(plan) != binding["sha256"]:
            raise AssetError("selected plan constraint version/hash mismatch")
        release = self.release(catalog)
        if plan["baseline"] != {"release_id": release.data["id"], "text_sha256": release.data["text_sha256"]}:
            raise AssetError("selected plan baseline disagrees with release")
        refs = set()
        for rules in plan["rules"].values():
            unique_index(rules)
            paths = [tuple(rule["path"]) for rule in rules]
            if len(paths) != len(set(paths)):
                raise AssetError("duplicate plan constraint path")
            refs.update(ref for rule in rules for ref in rule["basis_refs"])
        for ref in sorted(refs):
            release.catalog.resolve(ref)
        return plan

    def validate(self, catalog: AssetCatalog | None = None) -> list[str]:
        errors = []
        for name in self.data["owners"]:
            try:
                self.owner(name)
            except (AssetError, OSError, ValueError) as exc:
                errors.append(f"{name}: {exc}")
        if errors:
            return errors
        release = self.release(catalog)
        errors.extend(release.validate_storage())
        expected = release.data["text_sha256"]
        if self.owner("implementation")["status"] == "COMPLETE":
            errors.append("full implementation acceptance is not implemented yet")
        if self.owner("capability").get("stable_active_sha256") != expected:
            errors.append("capability owner disagrees with ACTIVE release SHA")
        if self.owner("literary").get("stable_active", {}).get("sha256") != expected:
            errors.append("literary owner disagrees with ACTIVE release SHA")
        try:
            self.plan_constraints(catalog)
        except (AssetError, OSError, KeyError, ValueError) as exc:
            errors.append(f"plan constraints: {exc}")
        try:
            errors.extend(f"capability: {finding}" for finding in self.capability()["findings"])
        except (AssetError, OSError, KeyError, ValueError) as exc:
            errors.append(f"capability: {exc}")
        from ..literary_production import LiteraryProductionRuntime
        from ..competition import CompetitionRegistry
        errors.extend(LiteraryProductionRuntime.from_repo(self.root).validate_integrity(CompetitionRegistry.from_repo(self.root)))
        return errors

    def summary(self) -> dict[str, Any]:
        from ..literary_production import LiteraryProductionRuntime
        capability = self.capability()
        records = self.owner("competitions")["competition_records"]
        release = self.release()
        plan = self.plan_constraints(release.catalog)
        chapters = {
            str(record["chapter"]): {
                "state": record["state"],
                "workflow_progress": record["workflow_progress"],
                "adjudication": record["adjudication"],
            }
            for record in records
        }
        return {
            "project_id": self.data["id"], "owners": self.data["owners"],
            "status": self.owner("implementation")["status"],
            "capability": capability,
            "literary_next_gate": LiteraryProductionRuntime.from_repo(self.root).summary()["next_gate"], "chapters": chapters,
            "active_release": {"id": release.data["id"], "sha256": release.data["text_sha256"]},
            "plan_constraints": {**self.data["plan_constraints_binding"], "authority": plan["authority"], "provenance": plan["provenance"]},
            "implementation": self.owner("implementation"),
        }
