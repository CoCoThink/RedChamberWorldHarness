"""Explicit, immutable semantic inputs for opt-in version 2 review contexts.

Audit submission ledgers are qualification inputs, not authored context. Their
qualification is recomputed by admission; the old context algorithm is untouched.
This first manifest is conservative: all current substantive domain records are
bound, rather than claiming a minimal dependency slice has been established.
"""
from __future__ import annotations

from pathlib import Path

from .assets.catalog import repository_path
from .candidate_reviews import bound_data, canonical_bytes, digest
from .io import load_data
from .schema import validate_instance


DOMAINS = (
    "reconstruction", "world", "knowledge", "objects", "scenes", "planning",
    "literary_eval", "plocks", "mechanisms", "mechanism_adapters",
)
PROVENANCE = ("sources", "claims", "decisions", "implementations", "axes")


def semantic_inputs(root: Path, record: dict) -> list[dict]:
    """Enumerate bytes actually frozen by the v2 protocol, including package I/O."""
    paths = set()
    directories = [root / "data" / name for name in DOMAINS]
    directories.extend(root / "data/provenance" / name for name in PROVENANCE)
    for directory in directories:
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".yaml", ".yml"}:
                paths.add(path.relative_to(root).as_posix())
    for relative in ("data/project/current.json", "data/project/scope.json"):
        if (root / relative).is_file():
            paths.add(relative)
    if (root / "data/project/current.json").is_file():
        current = load_data(root / "data/project/current.json")
        if "plan_constraints" in current.get("owners", {}):
            paths.add(current["owners"]["plan_constraints"])
    if not record.get("writing_package"):
        raise ValueError("CONTEXT_V2_WRITING_PACKAGE_REQUIRED")
    package = bound_data(root, record["writing_package"])
    errors = validate_instance(package, root / "schemas/writing_package.schema.json")
    if errors:
        raise ValueError("invalid context writing package: " + "; ".join(errors))
    if package["chapter"] != record["chapter"]:
        raise ValueError("CONTEXT_V2_PACKAGE_CHAPTER_MISMATCH")
    paths.add(record["writing_package"]["path"])
    for binding in [package["exemplar_set"], *package["world"], *package["plan"]]:
        bound_data(root, binding)
        paths.add(binding["path"])
    examples = bound_data(root, package["exemplar_set"])
    from .assets import AssetCatalog
    from .corpus.dataset import CorpusRepository
    catalog = AssetCatalog.from_repo(root)
    corpus = CorpusRepository(catalog)
    registry = corpus.registry()[examples["dataset_ref"]]
    if (registry["manifest_ref"], registry["manifest_sha256"]) != (examples["manifest_ref"], examples["manifest_sha256"]):
        raise ValueError("CONTEXT_V2_EXEMPLAR_MANIFEST_MISMATCH")
    corpus.load(examples["dataset_ref"], rebuild=False)
    refs = {item["asset_ref"] for item in package["assets"]}
    refs.add(examples["manifest_ref"])

    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.startswith("asset:sha256:"):
            refs.add(value)

    for relative in sorted(paths):
        collect(load_data(repository_path(root, relative)))
    for reference in sorted(refs):
        asset = catalog.resolve(reference)
        paths.add(asset.path.relative_to(root).as_posix())
    for candidate in record["candidates"]:
        for author in candidate.get("authors", []):
            if author.get("run"):
                run = bound_data(root, author["run"])
                paths.add(author["run"]["path"])
                if run.get("raw_run"):
                    bound_data(root, run["raw_run"])
                    paths.add(run["raw_run"]["path"])
    return [{"path": relative, "sha256": digest(repository_path(root, relative).read_bytes())}
            for relative in sorted(paths)]


def prepare_manifest(root: Path, record: dict) -> dict:
    return {"schema_version": 2, "kind": "REVIEW_SEMANTIC_INPUT_MANIFEST",
            "competition": record["id"], "chapter": record["chapter"],
            "inputs": semantic_inputs(root, record), "authority_effect": "NONE"}


def context_v2(root: Path, record: dict) -> str:
    from .candidate_reviews import candidate_bytes
    manifest = bound_data(root, record["context_manifest"])
    errors = validate_instance(manifest, root / "schemas/review_context_manifest.schema.json")
    if errors:
        raise ValueError("invalid context manifest: " + "; ".join(errors))
    if manifest != prepare_manifest(root, record):
        raise ValueError("STALE_OR_INCOMPLETE_CONTEXT_MANIFEST")
    protocol = bound_data(root, record["review_protocol"])
    candidates = [{"id": c["id"], "blind_token": c["blind_token"],
                   "sha256": digest(candidate_bytes(root, c)), "authors": c.get("authors", [])}
                  for c in record["candidates"]]
    return digest(canonical_bytes({"context_version": 2, "manifest": record["context_manifest"],
        "competition": record["id"], "chapter": record["chapter"],
        "baseline": record["baseline"], "plock_ref": record["plock_ref"],
        "protocol": record["review_protocol"], "protocol_content": protocol,
        "candidates": candidates}))
