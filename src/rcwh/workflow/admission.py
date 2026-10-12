"""Conservative chapter input admission, distinct from publication acceptance.

Human coverage is recomputed from the existing protocols; neither a locator nor
an unrelated global PASS can confer independent review coverage.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..assets import AssetCatalog, AssetError
from ..assets.paths import repository_path
from ..assets.transactions import digest
from ..contracts import project_chapters, unique_index
from ..corpus.extraction import validate
from ..graph import ProvenanceGraph
from ..io import load_data
from ..mechanism_adapters import HistoricalAdapterRuntime

def chapter_scope(root: Path, package_path: str) -> dict:
    package = load_data(repository_path(root, package_path))
    graph = ProvenanceGraph.from_repo(root)
    chapter = package["chapter"]
    declared = {item["source_ref"] for item in package["sources"]}
    used = set(declared)
    findings = []
    paths = {package_path, package["exemplar_set"]["path"]}
    exemplars = load_data(repository_path(root, package["exemplar_set"]["path"]))
    contracts = []
    for path in sorted((root / "data/scenes").glob("*")):
        if path.suffix not in {".yaml", ".json"}:
            continue
        contract = load_data(path)
        if contract.get("chapter") == chapter:
            validate(root, contract, "scene_contract")
            contracts.append(contract)
            paths.add(path.relative_to(root).as_posix())
    if not contracts:
        findings.append("CHAPTER_SCENE_SCOPE_MISSING")

    def source(ref):
        used.add(ref)
        if ref not in graph.sources:
            findings.append(f"UNRESOLVED_DEPENDENT_SOURCE: {ref}")

    def claim(ref):
        record = graph.claims.get(ref)
        if record is None:
            findings.append(f"UNRESOLVED_DEPENDENT_CLAIM: {ref}")
            return
        for edge in record.get("support", []):
            source(edge["source"])

    def refs(record):
        for ref in record.get("source_refs", []):
            if ref.startswith("asset:"):
                # Adapter carrier references do not themselves possess an audit
                # verdict. Resolve them to explicitly registered source records.
                def contains(value):
                    if isinstance(value, dict):
                        return any(contains(v) for v in value.values())
                    if isinstance(value, list):
                        return any(contains(v) for v in value)
                    return value == ref
                matched = [s["id"] for s in graph.sources.values() if contains(s)]
                if not matched:
                    findings.append(f"UNRESOLVED_DEPENDENT_SOURCE_ASSET: {ref}")
                for identity in matched:
                    source(identity)
            else:
                source(ref)
        for ref in record.get("claim_refs", []):
            claim(ref)

    adapter_refs = {ref for c in contracts for ref in c.get("historical_adapters", [])}
    adapters = HistoricalAdapterRuntime.from_repo(root).adapters if adapter_refs else {}
    mechanisms = {}
    if adapter_refs:
        paths.add("data/mechanism_adapters/v04.json")
    for path in sorted((root / "data/mechanisms").glob("*.yaml")):
        paths.add(path.relative_to(root).as_posix())
        for identity, record in unique_index(load_data(path).get("historical_mechanisms", [])).items():
            if identity in mechanisms:
                raise AssetError(f"DUPLICATE_ADMISSION_MECHANISM: {identity}")
            mechanisms[identity] = record
    for contract in contracts:
        refs(contract)
    for identity in sorted(adapter_refs):
        adapter = adapters.get(identity)
        if adapter is None:
            findings.append(f"UNRESOLVED_HISTORICAL_ADAPTER: {identity}")
            continue
        refs(adapter)
        for ref in adapter.get("mechanism_refs", []):
            mechanism = mechanisms.get(ref)
            if mechanism is None:
                findings.append(f"UNRESOLVED_DEPENDENT_MECHANISM: {ref}")
            else:
                refs(mechanism)
    for implementation in graph.implementations.values():
        if implementation.get("chapter") != chapter:
            continue
        refs(implementation)
        # Historical implementations often have no decision edges; mechanisms
        # name them in the reverse direction. These claims are still dependencies.
        for mechanism in mechanisms.values():
            if implementation["id"] in mechanism.get("implementation_refs", []):
                refs(mechanism)
        for ref in implementation.get("decision_refs", []):
            decision = graph.decisions.get(ref)
            if decision is None:
                findings.append(f"UNRESOLVED_DEPENDENT_DECISION: {ref}")
            else:
                for claim_ref in decision.get("based_on", []):
                    claim(claim_ref)
        used.update(s["id"] for s in graph.trace(implementation["id"])["sources"])
    missing = used - declared
    findings.extend(f"PACKAGE_SOURCE_SCOPE_MISMATCH: {ref}" for ref in sorted(missing))
    return {"chapter": chapter, "package_path": package_path,
            "used_source_ids": sorted(used), "declared_source_ids": sorted(declared),
            "dependent_source_ids": sorted(used - declared),
            "dataset_refs": [exemplars["dataset_ref"]], "paths": sorted(paths),
            "findings": sorted(set(findings)), "authority_effect": "NONE"}


class ChapterAdmission:
    def __init__(self, catalog: AssetCatalog | Path):
        self.root = catalog if isinstance(catalog, Path) else catalog.root
        self._catalog = None if isinstance(catalog, Path) else catalog

    @property
    def catalog(self):
        if self._catalog is None:
            self._catalog = AssetCatalog.from_repo(self.root)
        return self._catalog

    def for_competition(self, record: dict) -> dict:
        if record.get("mode") != "PRODUCTION_43_0":
            return {"status": "NOT_APPLICABLE", "scope": "RESEARCH_COMPETITION",
                    "authority_effect": "NONE"}
        binding = record.get("writing_package")
        if not binding:
            return {"status": "PENDING", "production_blockers": ["WRITING_PACKAGE_BINDING_MISSING"],
                    "authority_effect": "NONE"}
        try:
            path = repository_path(self.root, binding["path"])
            if digest(path.read_bytes()) != binding["sha256"]:
                raise AssetError("STALE_COMPETITION_WRITING_PACKAGE")
            return self.summary(record["chapter"], binding["path"])
        except (AssetError, OSError, KeyError, ValueError) as exc:
            return {"status": "FAIL", "findings": [str(exc)], "production_blockers": [str(exc)],
                    "authority_effect": "NONE"}

    def summary(self, chapter: int, writing_package: str, *, require_tracked: bool = False) -> dict:
        from ..corpus.dataset import CorpusRepository
        from ..literary_inputs import LiteraryInputs
        from ..provenance import ProvenanceRepository
        from ..provenance.audit import SourceAudit
        from ..reconstruction import ReconstructionRegistry
        from ..world import WorldRuntime
        from .project import ProjectState

        inputs = LiteraryInputs(self.catalog).package(writing_package, require_tracked=require_tracked)
        spec = inputs["package"]
        scope = chapter_scope(self.root, writing_package)
        findings = [*inputs["findings"], *scope["findings"]]
        blockers = []
        if spec["chapter"] != chapter:
            findings.append("WRITING_PACKAGE_CHAPTER_MISMATCH")
        if chapter not in project_chapters(self.root):
            findings.append("PRODUCTION_CHAPTER_OUTSIDE_PROJECT_SCOPE")
        if spec.get("operation_scope") in {"RESEARCH", "BACKTEST"}:
            findings.append("WRITING_PACKAGE_NOT_PRODUCTION_SCOPE")

        repository = ProvenanceRepository.from_repo(self.root)
        for identity in scope["used_source_ids"]:
            source = repository.graph.sources.get(identity)
            if source is not None and repository.source_report(source, locators=True)["status"] != "PASS":
                findings.append(f"CHAPTER_SOURCE_LOCATOR_UNVERIFIED: {identity}")
        for ref in scope["dataset_refs"]:
            rebuilt = CorpusRepository(self.catalog).verify(ref, require_tracked=require_tracked)
            if rebuilt["status"] != "PASS":
                findings.append(f"CHAPTER_CORPUS_REBUILD_FAILED: {ref}")
                findings.extend(rebuilt.get("findings", []))
        if require_tracked:
            tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=self.root).decode().split("\0"))
            findings.extend(f"UNTRACKED_CHAPTER_INPUT: {path}" for path in scope["paths"] if path not in tracked)

        audit = SourceAudit(repository).summary()
        required = set(audit.get("required_source_ids", []))
        covered = required - set(audit.get("pending_source_ids", required))
        used = set(scope["used_source_ids"])
        rejected = [row for row in audit.get("findings", []) if row.get("source_ref") in used]
        if rejected:
            findings.append("CHAPTER_SOURCE_AUDIT_REJECTED")
        # An unscoped failure cannot safely be treated as unrelated.
        if audit["status"] == "FAIL" and (not audit.get("findings") or
                any(not row.get("source_ref") for row in audit.get("findings", []))):
            findings.append("SOURCE_AUDIT_FAILURE_SCOPE_UNKNOWN")
        unknown = used - required
        pending = (used & required) - covered
        if unknown:
            blockers.append("CHAPTER_SOURCE_AUDIT_COVERAGE_UNKNOWN")
        if pending:
            blockers.append("CHAPTER_SOURCE_AUDIT_PENDING")
        examples = inputs["exemplars"]
        corpus_audit = examples["human_audit"]
        if corpus_audit["status"] == "FAIL":
            findings.append("CORPUS_HUMAN_LAYER_AUDIT_FAILED")
        elif corpus_audit["status"] != "PASS":
            blockers.append("CORPUS_HUMAN_LAYER_AUDIT_PENDING")
        if any(row["status"] != "PASS" for row in inputs["sources"]):
            findings.append("WRITING_SOURCE_LOCATOR_UNVERIFIED")

        expected_world = {f"data/world/m3_{name}.json" for name in
                          ("core", "locations", "presence", "body", "resources", "knowledge")}
        project = ProjectState.from_repo(self.root)
        if {item["path"] for item in spec["world"]} != expected_world:
            findings.append("WRITING_PACKAGE_WORLD_INPUTS_INCOMPLETE")
        if project.data["owners"]["plan_constraints"] not in {item["path"] for item in spec["plan"]}:
            findings.append("WRITING_PACKAGE_SELECTED_PLAN_MISSING")
        findings.extend(WorldRuntime.from_repo(self.root).validate_integrity(
            self.catalog, ReconstructionRegistry.from_repo(self.root)))
        from .agent_panel import AgentPanel
        return {"status": "FAIL" if findings else "PENDING" if blockers else "PASS",
                "agent_panel": AgentPanel(self.root).summary(),
                "scope": "CHAPTER_PRODUCTION_INPUT_ADMISSION", "chapter": chapter,
                "input_scope": scope, "used_source_ids": scope["used_source_ids"],
                "writing_inputs": inputs,
                "source_audit": {"covered_source_ids": sorted(used & covered),
                                 "pending_source_ids": sorted(pending), "unknown_source_ids": sorted(unknown),
                                 "relevant_findings": rejected},
                "corpus_audit": corpus_audit, "findings": sorted(set(findings)),
                "production_blockers": sorted(set([*findings, *blockers])),
                "publication_preconditions": {"global_source_audit": audit,
                                              "p9": "ASSESSED_BY_PROJECT_ACCEPTANCE"},
                "authority_effect": "NONE"}
