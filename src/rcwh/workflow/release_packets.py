"""Prepare review packets and a request for an agent research edition.

From a live chapter selection (candidate, draft, package, policy, P-Lock per
chapter) this writes:

- content-addressed per-chapter packets under ``review-packets/``, binding
  the candidate, package, policy and selected contracts for that chapter;
- source record projections and evidence under ``source-records/`` and
  ``source-reading/``, including surrounding text and original page images;
- edition-local source/corpus packets, ``reading/chNN.json`` and
  ``request.json``, binding these inputs and available coordinator decisions.

All paths are relative to ``data/agent_release/``.

Packets are immutable once written: re-preparing with different bytes raises
instead of silently invalidating registered opinions. The request is derived
and may be regenerated (e.g. after decisions are added).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..assets import AssetCatalog, AssetError
from ..assets.paths import repository_path
from ..assets.transactions import digest
from ..candidate_reviews import canonical_bytes
from ..generation.records import bound_bytes
from ..contracts import project_chapters
from ..io import load_data
from ..schema import validate_instance
from .agent_panel import verify_packet

DIRECTORY = "data/agent_release"


def _binding(root: Path, relative: str) -> dict:
    return {"path": relative, "sha256": digest(repository_path(root, relative).read_bytes())}


def _write_immutable(root: Path, relative: str, document: dict | bytes) -> dict:
    raw = document if isinstance(document, bytes) else canonical_bytes(document)
    path = repository_path(root, relative)
    if path.exists() and path.read_bytes() != raw:
        raise AssetError(f"packet already exists with different bytes; use a new edition id: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)
    return {"path": relative, "sha256": digest(raw)}


def _source_files(root: Path) -> dict[str, str]:
    files = {}
    for file in sorted((root / "data/provenance/sources").glob("*.yaml")):
        relative = file.relative_to(root).as_posix()
        for record in (load_data(file) or {}).get("sources", []):
            files[record["id"]] = relative
    return files


def _packet(edition: str, kind: str, coordinator: str, subjects: list[dict]) -> dict:
    return {"schema_version": 1, "packet_kind": "AGENT_REVIEW_PACKET", "id": f"{edition}:{kind}",
            "coordinator_session_id": coordinator, "subjects": subjects,
            "authority_effect": "NONE", "usage": "RESEARCH_ONLY"}


def chapter_packets(root: Path, candidates: list[dict], rows: dict, coordinator: str) -> dict[int, dict]:
    """Stable, per-chapter review contexts survive unrelated edition changes."""
    packets = {}
    for chapter, row in sorted(rows.items()):
        context = [row[k] for k in ("candidate", "writing_package", "policy") if k in row]
        subjects = [{**s, "context": context} for s in candidates
                    if s["id"] in {f"chapter-{chapter}", f"package-{chapter}"}
                    or s["id"].startswith(f"contract-{chapter}-")]
        document = _packet(f"chapter-{chapter}", "inputs-v3", coordinator, subjects)
        packets[chapter] = _write_immutable(root,
            f"{DIRECTORY}/review-packets/{digest(canonical_bytes(document))}.json", document)
    return packets


def source_subject(root: Path, source: dict, catalog: AssetCatalog, cache=None) -> dict:
    from .source_reading import prepare as prepare_evidence
    raw = canonical_bytes({"schema_version": 1, "sources": [source]})
    binding = _write_immutable(root, f"{DIRECTORY}/source-records/{digest(raw)}.json", raw)
    evidence = prepare_evidence(catalog, source, f"{DIRECTORY}/source-reading", _write_immutable, cache)
    images = json.loads(bound_bytes(root, evidence))["images"]
    return {"id": f"source:{source['id']}", "scope": "SOURCE", "source_ref": source["id"],
            "binding": binding, "evidence": evidence, "context": [],
            **({"samples": [{"id": f"{source['id']}:image:{i}", "binding": image["binding"]}
                             for i, image in enumerate(images, 1)]} if images else {})}


def prepare(root: Path, edition: str, selection_path: str, chapters: list[int], *,
            coordinator_session_id: str, max_book_read_bytes: int = 197 * 1024) -> dict:
    """Write packets, reading lists and the request; return their bindings."""
    from .admission import chapter_scope
    from ..corpus.dataset import CorpusRepository

    root = Path(root).resolve()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", edition) or not coordinator_session_id.strip():
        raise AssetError("valid edition id and nonblank coordinator session required")
    selection = load_data(repository_path(root, selection_path))
    rows = {row["chapter"]: row for row in selection["chapters"]}
    scope_chapters = project_chapters(root)
    if not chapters or any(ch not in rows or ch not in scope_chapters for ch in chapters):
        raise AssetError("selected chapters must be in both the selection and project scope")
    base = f"{DIRECTORY}/{edition}"
    catalog = AssetCatalog.from_repo(root)
    source_cache = {}
    sources = _source_files(root)
    candidates, source_subjects, scopes, dataset_samples = [], {}, {}, {}
    for chapter in sorted(chapters):
        row = rows[chapter]
        scope = chapter_scope(root, row["writing_package"]["path"], plan_contracts=True)
        if scope["chapter"] != chapter:
            raise AssetError(f"writing package chapter mismatch: {chapter}")
        scopes[chapter] = scope
        contracts = [path for path in scope["paths"]
                     if path.startswith("data/scenes/") or path in scope.get("advisory_contract_paths", [])]
        candidates.append({"id": f"chapter-{chapter}", "scope": "CANDIDATE", "binding": row["candidate"]})
        candidates.append({"id": f"package-{chapter}", "scope": "PACKAGE", "binding": row["writing_package"]})
        candidates.extend({"id": f"contract-{chapter}-{index}", "scope": "CONTRACT", "binding": _binding(root, path)}
                          for index, path in enumerate(contracts, 1))
        for identity in scope["used_source_ids"]:
            if identity not in sources:
                raise AssetError(f"dependent source has no provenance record file: {identity}")
            if identity not in source_subjects:
                source = next(s for s in load_data(repository_path(root, sources[identity]))["sources"] if s["id"] == identity)
                source_subjects[identity] = source_subject(root, source, catalog, source_cache)
        package = load_data(repository_path(root, row["writing_package"]["path"]))
        exemplars = load_data(repository_path(root, package["exemplar_set"]["path"]))
        dataset_samples.setdefault(exemplars["dataset_ref"], set()).update(
            segment["segment_id"] for segment in exemplars["segments"])

    registry = CorpusRepository(catalog).registry()
    corpus_subjects = []
    for dataset_ref, segment_ids in sorted(dataset_samples.items()):
        binding = registry[dataset_ref]
        manifest_asset = catalog.resolve(binding["manifest_ref"])
        manifest = json.loads(manifest_asset.path.read_bytes())
        segments = catalog.resolve(manifest["products"]["segments.jsonl"]["asset_ref"])
        carrier = {"path": segments.relative_path, "sha256": segments.sha256}
        corpus_subjects.append({"id": dataset_ref, "scope": "CORPUS", "dataset_ref": dataset_ref,
                                "binding": {"path": manifest_asset.relative_path, "sha256": manifest_asset.sha256},
                                "samples": [{"id": identity, "binding": carrier} for identity in sorted(segment_ids)]})

    chapter_refs = chapter_packets(root, candidates, {ch: rows[ch] for ch in chapters}, coordinator_session_id)
    packets = {f"chapter-{ch}": ref for ch, ref in chapter_refs.items()}
    if source_subjects:
        packets["sources"] = _write_immutable(root, f"{base}/packets/sources.json", _packet(
            edition, "sources", coordinator_session_id, [source_subjects[k] for k in sorted(source_subjects)]))
    packets["corpus"] = _write_immutable(root, f"{base}/packets/corpus.json",
                                         _packet(edition, "corpus", coordinator_session_id, corpus_subjects))
    for binding in packets.values():
        verify_packet(root, binding)

    reading = {}
    for chapter in sorted(chapters):
        subjects = [s for s in candidates if s["id"] in {f"chapter-{chapter}", f"package-{chapter}"}
                    or s["id"].startswith(f"contract-{chapter}-")]
        document = {"schema_version": 1, "chapter": chapter, "packet": chapter_refs[chapter],
                    "read_in_full": [{"subject_id": s["id"], "scope": s["scope"], **s["binding"]} for s in subjects],
                    "policy": rows[chapter].get("policy"), "plock_ref": rows[chapter]["plock_ref"],
                    "severity_rule": "docs/decisions/0004_EVIDENCE_FLOOR_SEVERITY.md"}
        reading[chapter] = _write_immutable(root, f"{base}/reading/ch{chapter}.json", document)

    request = {"schema_version": 1, "id": edition, "baseline": selection["baseline"], "chapters": []}
    for chapter in scope_chapters:
        if chapter not in chapters:
            request["chapters"].append({"chapter": chapter, "mode": "NOT_NEW_AUTHORED"})
            continue
        row = rows[chapter]
        entry = {key: row[key] for key in ("candidate", "draft", "writing_package", "policy", "plock_ref",
                                           "minimum_body_characters", "minimum_baseline_ratio", "rebind_receipt") if key in row}
        from .attribution import release_attribution
        release_attribution(root, {**entry, "chapter": chapter})
        entry.update(chapter=chapter, mode="AGENT_CANDIDATE",
                     panel={"packet": chapter_refs[chapter], "subject_id": f"chapter-{chapter}"},
                     source_reviews=[{"packet": packets["sources"], "subject_id": f"source:{identity}"}
                                     for identity in scopes[chapter]["used_source_ids"]],
                     corpus_reviews=[{"packet": packets["corpus"], "subject_id": ref}
                                     for ref in scopes[chapter]["dataset_refs"]])
        decision = f"{base}/decisions/ch{chapter}.json"
        if repository_path(root, decision).is_file():
            entry["decision"] = _binding(root, decision)
        request["chapters"].append(entry)
    # Exact current full-scope reader, not an archived phase-5 draft.
    from .agent_release import _split
    baseline = catalog.resolve(selection["baseline"]["asset_ref"])
    if baseline.sha256 != selection["baseline"]["sha256"]:
        raise AssetError("book review baseline digest mismatch")
    prefix, prose = _split(baseline.path.read_bytes().decode(), scope_chapters)
    for chapter in chapters:
        candidate = rows[chapter]["candidate"]
        if _binding(root, candidate["path"]) != candidate:
            raise AssetError("book review candidate digest mismatch")
        text = repository_path(root, candidate["path"]).read_bytes().decode()
        candidate_prefix, _ = _split(text, (chapter,))
        if candidate_prefix:
            raise AssetError("book review chapter has unbound prefix")
        prose[chapter] = text
    book = _write_immutable(root, f"{base}/reading/book.md", (prefix + "".join(prose[ch] for ch in scope_chapters)).encode())
    from .book_review import partition, subjects as verify_book_subjects
    segments = []
    for span in partition(list(scope_chapters), prose, max_book_read_bytes):
        label = f"{span[0]}-{span[-1]}"
        binding = _write_immutable(root, f"{base}/reading/book-segments-v2/ch{label}.md",
                                   "".join(prose[ch] for ch in span).encode())
        segments.append({"id": f"book-continuity-{label}", "scope": "BOOK", "chapters": span,
                         "binding": binding, "review_policy": "ADVISORY"})
    packets["book"] = _write_immutable(root, f"{base}/packets/book-segments-v2.json", _packet(
        edition, "book-segments-v2", coordinator_session_id, segments))
    request["book_review"] = {"packet": packets["book"], "subject_ids": [s["id"] for s in segments]}
    verify_book_subjects(root, request["book_review"], book=bound_bytes(root, book), chapters=list(scope_chapters))
    _write_immutable(root, f"{base}/reading/book-segments-v2.json", {
        "schema_version": 2, "packet": packets["book"], "assembled_book": book,
        "max_read_bytes": max_book_read_bytes, "overlap_chapters": 1, "segments": segments,
        "chapter_candidates": [{"chapter": ch, "candidate": rows[ch]["candidate"]} for ch in sorted(chapters)],
        "seams": [[a, b] for a, b in zip(scope_chapters, scope_chapters[1:])],
        "focus": ["回际接缝与时间顺序", "物件持有与流转状态", "称谓和人物语体", "知识获得与后文照应"],
        "severity": "ADVISORY", "gate_effect": "NONE"})
    schema = load_data(repository_path(root, "schemas/agent_release_manifest.schema.json"))
    errors = validate_instance(request, {"$ref": "#/$defs/request", "$defs": schema["$defs"]})
    if errors:
        raise AssetError("invalid prepared request: " + "; ".join(errors))
    request_path = repository_path(root, f"{base}/request.json")
    request_path.write_bytes(canonical_bytes(request))
    return {"status": "PASS", "edition": edition, "packets": packets, "reading": reading,
            "request": _binding(root, f"{base}/request.json"),
            "subjects": {"candidates": len(candidates), "sources": len(source_subjects),
                         "corpus_samples": sum(len(s["samples"]) for s in corpus_subjects)},
            "authority_effect": "NONE"}
