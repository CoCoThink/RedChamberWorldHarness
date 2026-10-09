"""Declared repository inputs and a temporary, per-source regression budget.

Audit URLs and historical receipt paths are never opened as content fallbacks.
The baseline permits only the exact known failures; it is not a closure PASS.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from .assets import AssetCatalog, AssetError
from .assets.discovery import AssetDiscovery
from .assets.paths import repository_path
from .assets.transactions import digest
from .corpus.dataset import CorpusRepository
from .corpus.extraction import canonical_bytes, validate
from .corpus.locators import source_digest
from .io import load_data
from .provenance import ProvenanceRepository
from .workflow import ProjectState


class InputClosure:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.catalog = AssetCatalog.from_repo(self.root)

    def verify(self, *, require_tracked: bool = False) -> dict:
        project = ProjectState.from_repo(self.root)
        if "closure" not in project.data["owners"]:
            raise AssetError("NO_SELECTED_CLOSURE_ROOTS")
        config = project.owner("closure")
        findings = self.catalog.validate(require_tracked=require_tracked)
        paths = {"data/project/current.json", *project.data["owners"].values()}
        paths.update(p.relative_to(self.root).as_posix() for p in (self.root / "src/rcwh").rglob("*.py"))
        paths.update(p.relative_to(self.root).as_posix() for p in (self.root / "schemas").glob("*.schema.json"))
        paths.update({"requirements/extraction.lock.json", "pyproject.toml", ".gitattributes"})
        paths.update(config["required_paths"])
        asset_refs = set()
        visited_records = set()

        def visit_asset(ref, expected=None):
            asset = self.catalog.resolve(ref)
            if expected is not None and asset.sha256 != expected:
                raise AssetError(f"CLOSURE_ASSET_HASH_MISMATCH: {ref}")
            if ref in asset_refs:
                return
            asset_refs.add(ref); paths.add(asset.relative_path)
            for parent in self.catalog.assets[ref].get("derived_from", []):
                visit_asset(parent)

        def visit_record(value):
            # Only typed asset IDs are resolved. Other strings are explanations,
            # never arbitrary paths/URLs to try when a carrier is absent.
            if isinstance(value, dict):
                if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
                    path = repository_path(self.root, value["path"])
                    if digest(path.read_bytes()) != value["sha256"]:
                        raise AssetError(f"CLOSURE_TYPED_FILE_HASH_MISMATCH: {value['path']}")
                    paths.add(value["path"])
                    if value["path"].endswith((".json", ".yaml")) and value["path"] not in visited_records:
                        visited_records.add(value["path"]); visit_record(load_data(path))
                for key, item in value.items():
                    if key in {"origin", "origin_container", "original_path", "url", "retrieved_from"}:
                        continue
                    if isinstance(item, str) and item.startswith("asset:"):
                        visit_asset(item)
                    elif key in {"artifact", "revised_artifact", "experiment_ref"} and isinstance(item, str):
                        path = repository_path(self.root, item)
                        paths.add(item)
                        if item.endswith((".json", ".yaml")) and item not in visited_records:
                            visited_records.add(item); visit_record(load_data(path))
                    else:
                        visit_record(item)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.startswith("asset:"):
                        visit_asset(item)
                    else:
                        visit_record(item)

        repository = ProvenanceRepository.from_repo(self.root)
        source_report = repository.verify_all(require_tracked=require_tracked)
        from .provenance.audit import SourceAudit
        source_audit = SourceAudit(repository).summary()
        for source in repository.graph.sources.values():
            visit_record(source)
        for directory in ("sources", "claims", "decisions", "implementations", "axes"):
            for path in (self.root / "data/provenance" / directory).glob("*.yaml"):
                paths.add(path.relative_to(self.root).as_posix())
        discovery = AssetDiscovery(self.catalog)
        for ref in config["collections"]:
            report = discovery.collection_report(ref)
            for member in report["collections"][0]["members"]:
                visit_asset(member)
        for binding in config["assets"]:
            visit_asset(binding["asset_ref"], binding["sha256"])
        for record in config["records"]:
            path = repository_path(self.root, record["path"])
            if digest(path.read_bytes()) != record["sha256"]:
                raise AssetError(f"CLOSURE_RECORD_HASH_MISMATCH: {record['path']}")
            value = load_data(path)
            validate(self.root, value, record["schema"])
            paths.add(record["path"]); visit_record(value)
        for name in project.data["owners"]:
            visit_record(project.owner(name))
        for relative in config["build_configs"]:
            build = CorpusRepository(self.catalog).config(relative)
            paths.update({relative, build["inputs"]["path"]})
            visit_record(load_data(repository_path(self.root, build["inputs"]["path"])))
        datasets = []
        corpus = CorpusRepository(self.catalog)
        for ref in config["datasets"]:
            datasets.append(corpus.verify(ref, require_tracked=require_tracked))
            manifest, _ = corpus.load(ref, rebuild=False)
            paths.update({manifest["build_config"]["path"], manifest["build_config"]["document"]["inputs"]["path"],
                          f"{corpus.registry_directory}/{digest(ref.encode())}.json"})
            visit_asset(corpus.registry()[ref]["manifest_ref"])
        findings.extend(project.validate(self.catalog))
        file_bindings = []
        for relative in sorted(paths):
            if relative.split("/", 1)[0] in {".rcwh-cache", ".git", ".pytest_cache", "__pycache__"}:
                raise AssetError(f"CACHE_CANNOT_BE_FORMAL_INPUT: {relative}")
            path = repository_path(self.root, relative)
            if not path.is_file():
                findings.append(f"MISSING_CLOSURE_INPUT: {relative}")
            else:
                file_bindings.append({"path": relative, "sha256": digest(path.read_bytes())})
        if require_tracked:
            result = subprocess.run(["git", "ls-files", "-z"], cwd=self.root, capture_output=True, check=False)
            if result.returncode:
                findings.append("GIT_TRACKING_UNAVAILABLE")
            tracked = set(result.stdout.decode().split("\0"))
            findings.extend(f"UNTRACKED_CLOSURE_INPUT: {p}" for p in sorted(paths-tracked))
        failed = source_report["status"] != "PASS" or source_audit["status"] != "PASS" or any(d["status"] != "PASS" for d in datasets) or bool(findings)
        return {"status": "FAIL" if failed else "PASS", "profile": "declared-inputs", "closure_ref": config["id"],
                "scope": config, "root_set_digest": digest(canonical_bytes(config)),
                "input_digest": digest(canonical_bytes(file_bindings)), "inputs": file_bindings,
                "assets": sorted(asset_refs), "sources": source_report, "source_evidence_audit": source_audit, "datasets": datasets,
                "findings": sorted(set(findings)), "authority_effect": "NONE"}

    def gap_check(self, baseline_path: str, *, require_tracked: bool = False, base_ref: str | None = None) -> dict:
        baseline = load_data(repository_path(self.root, baseline_path))
        validate(self.root, baseline, "source_gap_baseline")
        repository = ProvenanceRepository.from_repo(self.root)
        report = repository.verify_all(require_tracked=require_tracked)
        allowed = {g["source_id"]: g for g in baseline["gaps"]}
        if len(allowed) != len(baseline["gaps"]) or not set(allowed) <= set(baseline["source_ids"]):
            raise AssetError("INVALID_SOURCE_GAP_BASELINE")
        findings = [*report.get("graph_findings", []), *report.get("storage_findings", [])]
        if base_ref:
            if base_ref.startswith("-") or ":" in base_ref: raise AssetError("UNSAFE_GIT_BASE_REF")
            previous = subprocess.run(["git", "show", f"{base_ref}:{baseline_path}"], cwd=self.root, capture_output=True)
            if previous.returncode == 0:
                old = json.loads(previous.stdout); validate(self.root, old, "source_gap_baseline")
                old_gaps = {item["source_id"]: item for item in old["gaps"]}
                if not set(old["source_ids"]) <= set(baseline["source_ids"]): findings.append("SOURCE_GAP_BASELINE_REMOVES_ROOTS")
                for identity, gap in allowed.items():
                    if old_gaps.get(identity) != gap: findings.append(f"SOURCE_GAP_WAIVER_EXPANDED: {identity}")
            else:
                commit = subprocess.run(["git", "cat-file", "-e", f"{base_ref}^{{commit}}"], cwd=self.root, capture_output=True)
                if commit.returncode: raise AssetError("UNKNOWN_GIT_BASE_REF")
        removed = set(baseline["source_ids"]) - set(repository.graph.sources)
        findings.extend(f"REMOVED_SOURCE_ROOT: {ref}" for ref in sorted(removed))
        unresolved = []
        for source in report["sources"]:
            if source["status"] == "PASS":
                continue
            ref = source["source_id"]; gap = allowed.get(ref)
            actual = sorted(set(source["findings"]))
            if gap is None or actual != sorted(gap["findings"]) or source_digest(repository.graph.sources[ref]) != gap["source_record_sha256"]:
                findings.append(f"NEW_OR_CHANGED_SOURCE_GAP: {ref}")
            unresolved.append({"source_id": ref, "findings": actual})
        if require_tracked:
            tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=self.root).decode().split("\0"))
            findings.extend(f"UNTRACKED_GAP_BASELINE: {p}" for p in sorted({baseline_path, "schemas/source_gap_baseline.schema.json"}-tracked))
        resolved = sorted(set(allowed)-{s["source_id"] for s in unresolved})
        findings.extend(f"RESOLVED_SOURCE_GAP_REMOVE_WAIVER: {identity}" for identity in resolved)
        return {"status": "FAIL" if findings else "PASS", "scope": "SOURCE_GAP_REGRESSION_ONLY", "closure_status": report["status"],
                "known_gaps_remaining": unresolved, "resolved_gap_ids": resolved,
                "findings": sorted(set(findings)), "authority_effect": "NONE"}

    def regression(self, *, require_tracked: bool = False) -> dict:
        report = self.verify(require_tracked=require_tracked)
        gaps = self.gap_check("data/project/source_gap_baseline.json", require_tracked=require_tracked)
        findings = [*report["findings"], *gaps["findings"]]
        if report["source_evidence_audit"]["status"] == "FAIL":
            findings.append("SOURCE_INDEPENDENT_AUDIT_REJECTED")
        from .corpus.audit import CorpusAudit
        for dataset in report["datasets"]:
            if dataset["status"] != "PASS": findings.extend(dataset["findings"])
            if CorpusAudit(self.catalog).summary(dataset["dataset_ref"], rebuild=False)["status"] == "FAIL":
                findings.append(f"CORPUS_HUMAN_AUDIT_REJECTED: {dataset['dataset_ref']}")
        return {"status": "FAIL" if findings else "PASS", "scope": "DECLARED_INPUT_REGRESSION_ONLY",
                "closure_status": report["status"], "source_gap_check": gaps,
                "input_digest": report["input_digest"], "root_set_digest": report["root_set_digest"],
                "findings": sorted(set(findings)), "authority_effect": "NONE"}
