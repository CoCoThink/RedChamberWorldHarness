from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


@dataclass
class MigrationRegistry:
    packages: dict[str, dict[str, Any]]
    documents: dict[str, dict[str, Any]]
    content_hashes: dict[str, dict[str, Any]]
    lineage: list[dict[str, Any]]
    authority_statuses: dict[str, dict[str, Any]]
    package_class_policies: dict[str, dict[str, Any]]
    current_authority: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "MigrationRegistry":
        doc = load_data(root / "data" / "registry" / "m1.json") or {}
        packages = _index(doc.get("packages", []), "package")
        documents = _index(doc.get("documents", []), "document")
        content_hashes = _index(doc.get("content_hashes", []), "content hash")
        authority_statuses = _index(doc.get("authority_statuses", []), "authority status")
        class_policies = {
            item["classification"]: item
            for item in doc.get("package_class_policies", [])
        }
        return cls(
            packages=packages,
            documents=documents,
            content_hashes=content_hashes,
            lineage=doc.get("package_lineage", []),
            authority_statuses=authority_statuses,
            package_class_policies=class_policies,
            current_authority=doc.get("current_authority", {}),
        )

    def validate_integrity(self) -> list[str]:
        errors: list[str] = []

        if len(self.packages) != 19:
            errors.append(f"PackageRegistry must contain exactly 19 packages; got {len(self.packages)}")

        filenames: dict[str, str] = {}
        package_hashes: dict[str, str] = {}
        for package_id, package in self.packages.items():
            filename = package["filename"]
            sha = package["sha256"]
            if filename in filenames:
                errors.append(
                    f"duplicate package filename {filename}: {filenames[filename]} and {package_id}"
                )
            filenames[filename] = package_id
            if sha in package_hashes:
                errors.append(
                    f"duplicate package SHA256 {sha}: {package_hashes[sha]} and {package_id}"
                )
            package_hashes[sha] = package_id

            policy = self.package_class_policies.get(package["classification"])
            if policy is None:
                errors.append(
                    f"{package_id}: no AuthorityStatus policy for {package['classification']}"
                )
                continue
            for field in ("authority", "runtime_authority", "allow_current_import"):
                if package[field] != policy[field]:
                    errors.append(
                        f"{package_id}: {field}={package[field]!r} violates class policy {policy[field]!r}"
                    )

            if package["classification"] in {"SUPERSEDED", "REVOKED_RELEASE"}:
                if package["runtime_authority"] != "NO" or package["allow_current_import"]:
                    errors.append(
                        f"{package_id}: superseded/revoked package may not have runtime authority"
                    )

        current_packages = [
            p for p in self.packages.values() if p["classification"] == "CURRENT_CANONICAL"
        ]
        if len(current_packages) != 1 or current_packages[0]["id"] != "pkg:stable-active-v4.1":
            errors.append("pkg:stable-active-v4.1 must be the sole CURRENT_CANONICAL package")

        for edge in self.lineage:
            if edge["from"] not in self.packages:
                errors.append(f"lineage: unknown from package {edge['from']}")
            if edge["to"] not in self.packages:
                errors.append(f"lineage: unknown to package {edge['to']}")
            if edge["relation"] == "SUPERSEDED_BY" and edge["from"] in self.packages:
                old = self.packages[edge["from"]]
                if old["runtime_authority"] != "NO":
                    errors.append(f"{edge['from']}: superseded package still has runtime authority")

        doc_hashes: dict[str, str] = {}
        current_paths: dict[str, str] = {}
        v41_members: set[str] = set()
        for doc_id, doc in self.documents.items():
            sha = doc["sha256"]
            if sha in doc_hashes:
                errors.append(f"duplicate document SHA256 {sha}: {doc_hashes[sha]} and {doc_id}")
            doc_hashes[sha] = doc_id
            if doc["canonical_package_ref"] not in self.packages:
                errors.append(
                    f"{doc_id}: unknown canonical package {doc['canonical_package_ref']}"
                )
            if doc.get("v4_1_package_member"):
                v41_members.add(doc_id)

            current_path = doc.get("current_runtime_path")
            if current_path:
                if current_path in current_paths:
                    errors.append(
                        f"duplicate CURRENT runtime path {current_path}: {current_paths[current_path]} and {doc_id}"
                    )
                current_paths[current_path] = doc_id
                if doc["authority"] != "CURRENT" or doc["runtime_authority"] != "YES":
                    errors.append(f"{doc_id}: CURRENT runtime document lacks CURRENT/YES authority")

            machine = doc["machine_representation"]
            if machine["markdown_only"] != (machine["semantic_coverage"] == "NONE"):
                errors.append(f"{doc_id}: markdown_only disagrees with semantic_coverage")
            if not machine["target_node"] or not machine["target_path"] or not machine["migration_action"]:
                errors.append(f"{doc_id}: missing explicit machine landing")

            hash_id = f"hash:{sha}"
            h = self.content_hashes.get(hash_id)
            if h is None:
                errors.append(f"{doc_id}: no ContentHashRegistry record for {sha}")
            elif doc_id not in h["document_refs"] or h["canonical_document_ref"] != doc_id:
                errors.append(f"{doc_id}: ContentHashRegistry back-reference is inconsistent")

        if len(v41_members) != 23:
            errors.append(f"stable ACTIVE v4.1 package must have 23 registered documents; got {len(v41_members)}")
        if len(current_paths) != 15:
            errors.append(f"02_CURRENT_RUNTIME must have 15 registered documents; got {len(current_paths)}")

        if len(self.content_hashes) != len(self.documents):
            errors.append(
                "M1 ContentHashRegistry and DocumentRegistry must be 1:1 by unique SHA256"
            )
        for hash_id, item in self.content_hashes.items():
            expected_id = f"hash:{item['sha256']}"
            if hash_id != expected_id:
                errors.append(f"{hash_id}: content-hash id must be hash:<sha256>")
            if item["deduplication_key"] != "SHA256":
                errors.append(f"{hash_id}: deduplication_key must remain SHA256")
            for doc_ref in item["document_refs"]:
                if doc_ref not in self.documents:
                    errors.append(f"{hash_id}: unknown document ref {doc_ref}")

        errors.extend(self._validate_current_authority(v41_members, current_paths))
        return errors

    def _validate_current_authority(
        self, v41_members: set[str], current_paths: dict[str, str]
    ) -> list[str]:
        errors: list[str] = []
        current = self.current_authority
        if not current:
            return ["missing current_authority registry"]
        if current.get("stable_package_ref") != "pkg:stable-active-v4.1":
            errors.append("Current Authority must point to pkg:stable-active-v4.1")
        if current.get("stable_active_sha256") != "4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320":
            errors.append("stable ACTIVE SHA256 changed during migration")
        if set(current.get("v4_1_package_document_refs", [])) != v41_members:
            errors.append("Current Authority v4.1 23-file map disagrees with DocumentRegistry")

        refs = current.get("current_runtime_document_refs", [])
        if set(refs) != set(current_paths.values()):
            errors.append("Current Authority 15-file map disagrees with 02_CURRENT_RUNTIME registry")
        coverage = {"FULL": 0, "PARTIAL": 0, "MINIMAL": 0, "NONE": 0}
        for doc_ref in refs:
            doc = self.documents.get(doc_ref)
            if doc is None:
                errors.append(f"Current Authority: unknown document {doc_ref}")
                continue
            semantic = doc["machine_representation"]["semantic_coverage"]
            coverage[semantic] += 1
        if coverage != current.get("semantic_coverage_counts"):
            errors.append(
                f"Current Authority coverage count mismatch: computed={coverage} declared={current.get('semantic_coverage_counts')}"
            )
        if current.get("registry_coverage") != "FULL":
            errors.append("M1 registry coverage must be FULL")
        if current.get("completion_gate_ready"):
            errors.append("M1 may not mark Completion Gate ready")
        return errors

    def package(self, package_id: str) -> dict[str, Any]:
        if package_id not in self.packages:
            raise KeyError(f"Unknown package: {package_id}")
        return self.packages[package_id]

    def document(self, key: str) -> dict[str, Any]:
        if key in self.documents:
            return self.documents[key]
        for doc in self.documents.values():
            if key in {doc["sha256"], doc.get("current_runtime_path"), doc["self_contained_path"]}:
                return doc
        raise KeyError(f"Unknown document: {key}")

    def content_hash(self, sha256: str) -> dict[str, Any]:
        key = sha256 if sha256.startswith("hash:") else f"hash:{sha256}"
        if key not in self.content_hashes:
            raise KeyError(f"Unknown content hash: {sha256}")
        return self.content_hashes[key]

    def current_summary(self) -> dict[str, Any]:
        return self.current_authority


def _index(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["id"]
        if item_id in result:
            raise ValueError(f"Duplicate {label} id: {item_id}")
        result[item_id] = item
    return result


def format_registry_package(item: dict[str, Any]) -> str:
    return "\n".join(
        [
            "PACKAGE",
            f"id: {item['id']}",
            f"filename: {item['filename']}",
            f"sha256: {item['sha256']}",
            f"classification: {item['classification']}",
            f"authority: {item['authority']}",
            f"runtime_authority: {item['runtime_authority']}",
            f"allow_current_import: {str(item['allow_current_import']).lower()}",
            f"files: {item['file_count_observed']}",
        ]
    )


def format_registry_document(item: dict[str, Any]) -> str:
    machine = item["machine_representation"]
    out = [
        "DOCUMENT",
        f"id: {item['id']}",
        f"filename: {item['filename']}",
        f"sha256: {item['sha256']}",
        f"authority: {item['authority']} / runtime={item['runtime_authority']}",
        f"self_contained_path: {item['self_contained_path']}",
        f"canonical_package: {item['canonical_package_ref']}",
        f"canonical_path: {item['canonical_path']}",
        "registry_coverage: FULL",
        f"semantic_coverage: {machine['semantic_coverage']}",
        f"machine_target: {machine['target_node']} -> {machine['target_path']}",
    ]
    if item.get("current_runtime_path"):
        out.append(f"current_runtime_path: {item['current_runtime_path']}")
    return "\n".join(out)


def format_current_authority(item: dict[str, Any]) -> str:
    coverage = item["semantic_coverage_counts"]
    return "\n".join(
        [
            "CURRENT AUTHORITY M1",
            f"stable_package: {item['stable_package_ref']}",
            f"stable_active_sha256: {item['stable_active_sha256']}",
            f"v4.1 package files registered: {item['v4_1_package_file_count']}/23",
            f"CURRENT runtime documents registered: {item['current_runtime_document_count']}/15",
            f"registry_coverage: {item['registry_coverage']}",
            "semantic_coverage: "
            f"FULL={coverage['FULL']} PARTIAL={coverage['PARTIAL']} "
            f"MINIMAL={coverage['MINIMAL']} NONE={coverage['NONE']}",
            f"completion_gate_ready: {str(item['completion_gate_ready']).lower()}",
        ]
    )
