"""Explicit shadow allocation examples, not competing historical facts."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from ..io import load_data
from ..assets.paths import repository_path
from ..schema import validate_instance
from .references import BOUNDARY, record, verify_record, write_new


@dataclass
class BookPlan:
    root: Path
    data: dict

    @classmethod
    def read(cls, root: Path, path: str):
        return cls(root, load_data(repository_path(root, path)))


def materialize_books(root: Path) -> list[str]:
    opens = load_data(root / "data/open_interfaces/r4_open.yaml")["open_interfaces"]
    selected = [record(root, "data/open_interfaces/r4_open.yaml", f"/open_interfaces/{i}", row)
                for i, row in enumerate(opens) if row["id"] in {"OL-001", "OL-005", "OL-007", "OL-023"}]
    events = load_data(root / "data/world/m3_core.json")["events"]
    claim_records = []
    for path, wanted in [("data/provenance/claims/canary.yaml", {"claim:cliff-release:future-interface"}),
                         ("data/provenance/claims/r4_core_completion.yaml", {"claim:daiyu:death-direction"})]:
        claim_records.extend(record(root, path, f"/claims/{i}", row) for i, row in enumerate(load_data(root / path)["claims"]) if row["id"] in wanted)
    hypotheses = [{"id": identity, "status": "SHADOW_ILLUSTRATIVE", "total_chapters": total,
                   "open_refs": [x["value"]["id"] for x in selected],
                   "interpretation": "Illustrative allocation only; no claim of original chapter count or event dating."}
                  for identity, total in [("current-100", 100), ("extended-110", 110)]]
    structure = {**BOUNDARY, "id": "book-structure-shadow", "status": "SHADOW_ONLY", "source_records": selected,
                 "hypotheses": hypotheses, "claim_records": claim_records,
                 "corpus_citations": [], "corpus_link_status": "PENDING_NO_EDITOR_SELECTED_SEGMENTS",
                 "production_scope_effect": "NONE", "selection": None}
    outputs = [("data/research/book_structure.json", structure)]
    for hypothesis in hypotheses:
        extended = hypothesis["total_chapters"] > 100
        mapped = []
        for index, event in enumerate(events):
            # Explicit hypothetical extra space, never an evidence-backed placement.
            allocation = 81 + ((event["chapter"] - 81) * 29 // 19) if extended else event["chapter"]
            mapped.append({"event_id": event["id"], "chapter": allocation,
                           "source_record": record(root, "data/world/m3_core.json", f"/events/{index}", event),
                           "placement_status": "ILLUSTRATIVE_DRAFT"})
        start, end = 81, hypothesis["total_chapters"]
        book = {**BOUNDARY, "id": hypothesis["id"], "status": "SHADOW_ILLUSTRATIVE", "total_chapters": end,
                "hypothesis_ref": f"data/research/book_structure.json#{hypothesis['id']}",
                "hypothesis": hypothesis, "event_allocations": mapped,
                "chapters": [{"chapter": chapter, "event_ids": [x["event_id"] for x in mapped if x["chapter"] == chapter],
                              "planned_han_characters": None, "burden_status": "EVENT_COUNT_PROXY_ONLY"} for chapter in range(start, end + 1)],
                "hint_allocations": [], "unresolved": ["editorial_choice", "scene_allocation", "length_budget", "hint_allocation", "world_replay"],
                "production_scope_effect": "NONE"}
        outputs.append((f"data/planning/books/{hypothesis['id']}.json", book))
    for path, _ in outputs:
        if repository_path(root, path).exists():
            raise FileExistsError(path)
    for path, data in outputs:
        write_new(repository_path(root, path), data)
    return [path for path, _ in outputs]


def compare_books(root: Path, paths=None, *, books=None, reference_lengths=None) -> dict:
    if books is None:
        paths = paths or [path.relative_to(root).as_posix() for path in sorted((root / "data/planning/books").glob("*.json"))]
        books = [BookPlan.read(root, path).data for path in paths]
    reference = {"status": "NOT_CHECKED", "reason": "No checked front80 distribution supplied."}
    if reference_lengths is None and (root / "data/corpus/datasets").exists():
        try:
            reference = front80_lengths(root)
            reference_lengths = [row["han_characters"] for row in reference["chapters"]]
        except (OSError, KeyError, ValueError, TypeError) as exc:
            reference = {"status": "NOT_CHECKED", "reason": str(exc)}
    elif reference_lengths:
        reference = {"status": "SUPPLIED_FIXTURE", "chapters": [{"han_characters": x} for x in reference_lengths]}
    rows = []
    for book in books:
        errors = validate_instance(book, root / "schemas/book_plan.schema.json")
        if errors:
            rows.append({"id": book.get("id"), "status": "FAIL", "findings": errors})
            continue
        structure_path, _, hypothesis_id = book.get("hypothesis_ref", "").partition("#")
        try:
            structure = load_data(repository_path(root, structure_path))
            hypothesis = next(row for row in structure["hypotheses"] if row["id"] == hypothesis_id)
            if book.get("hypothesis") != hypothesis:
                errors.append("BOOK_HYPOTHESIS_BINDING_MISMATCH")
            for source in structure.get("source_records", []) + structure.get("claim_records", []):
                errors.extend(verify_record(root, source))
        except (OSError, KeyError, ValueError, TypeError, StopIteration) as exc:
            errors.append(f"BOOK_HYPOTHESIS_INVALID: {exc}")
        for item in book.get("event_allocations", []):
            errors.extend(verify_record(root, item["source_record"]))
        counts = [{"chapter": x["chapter"], "events": len(x["event_ids"])} for x in book.get("chapters", [])]
        known_chapters = {x["chapter"] for x in book.get("chapters", [])}
        declared_chapters = [x["chapter"] for x in book["chapters"]]
        if len(declared_chapters) != len(known_chapters):
            errors.append("DUPLICATE_BOOK_CHAPTER")
        if declared_chapters != sorted(declared_chapters) or any(ch > book["total_chapters"] for ch in declared_chapters):
            errors.append("INVALID_BOOK_CHAPTER_ORDER_OR_SCOPE")
        event_ids = [x["event_id"] for x in book.get("event_allocations", [])]
        if len(event_ids) != len(set(event_ids)):
            errors.append("DUPLICATE_EVENT_ALLOCATION")
        allocated = {}
        for allocation in book.get("event_allocations", []):
            if allocation["chapter"] not in known_chapters or allocation["event_id"] != allocation["source_record"]["value"].get("id"):
                errors.append("INVALID_EVENT_ALLOCATION")
            allocated.setdefault(allocation["chapter"], []).append(allocation["event_id"])
        for chapter in book.get("chapters", []):
            if sorted(chapter["event_ids"]) != sorted(allocated.get(chapter["chapter"], [])):
                errors.append("CHAPTER_BURDEN_ALLOCATION_MISMATCH")
        lengths = [x["planned_han_characters"] for x in book.get("chapters", []) if x.get("planned_han_characters") is not None]
        length_check = {"status": "NOT_CHECKED", "reason": "No draft chapter length budgets or checked front80 distribution."}
        if lengths and reference_lengths:
            length_check = {"status": "ILLUSTRATIVE_ONLY", "planned_mean": sum(lengths) / len(lengths),
                            "front80_mean": sum(reference_lengths) / len(reference_lengths), "not_literary_verdict": True}
        hints = [{"hint_id": x["hint_id"], "chapter": x.get("chapter"),
                  "status": "DECLARED_REACHABLE" if x.get("chapter") in known_chapters else "PENDING"} for x in book.get("hint_allocations", [])]
        rows.append({"id": book["id"], "total_chapters": book["total_chapters"], "status": "FAIL" if errors else "SHADOW_ILLUSTRATIVE",
                     "findings": errors, "event_density": counts,
                     "length_comparison": length_check, "hint_reachability": {"status": "DECLARATION_ONLY" if hints else "PENDING", "rows": hints},
                     "world_replay": {"status": "NOT_CHECKED", "reason": "No framework-specific scene/event/state bindings; legacy 81–100 replay cannot validate a relocated or extended allocation."}})
    return {**BOUNDARY, "status": "FAIL" if any(x["status"] == "FAIL" for x in rows) else "PENDING", "books": rows,
            "front80_length_reference": reference,
            "comparison_policy": "PARETO_DIMENSIONS_NO_TOTAL_SCORE", "automatic_winner": None, "production_scope_effect": "NONE"}


def front80_lengths(root: Path) -> dict:
    """Byte-verified corpus reference; dataset human review is not implied."""
    import json
    import re
    from ..assets import AssetCatalog
    from ..corpus.dataset import CorpusRepository
    from .references import digest
    dataset = "corpus:front80:v1-candidate"
    catalog = AssetCatalog.from_repo(root)
    corpus = CorpusRepository(catalog)
    binding = corpus.registry()[dataset]
    manifest_asset = catalog.resolve(binding["manifest_ref"])
    if digest(manifest_asset.path.read_bytes()) != binding["manifest_sha256"]:
        raise ValueError("CORPUS_MANIFEST_BINDING_MISMATCH")
    manifest, products = corpus.load(dataset, rebuild=False)
    lengths = {chapter: 0 for chapter in range(1, 81)}
    for line in products["segments.jsonl"].splitlines()[1:]:
        segment = json.loads(line)
        if segment["kind"] == "MAIN_TEXT":
            if segment["chapter"] not in lengths:
                raise ValueError("FRONT80_MAIN_TEXT_OUTSIDE_SCOPE")
            lengths[segment["chapter"]] += len(re.findall(r"[㐀-䶿一-鿿]", segment["text"]))
    return {"status": "BYTE_CHECKED_REFERENCE_NOT_HUMAN_REVIEW", "dataset_ref": dataset,
            "manifest_sha256": binding["manifest_sha256"], "readiness": manifest["readiness"],
            "chapters": [{"chapter": chapter, "han_characters": value} for chapter, value in lengths.items()],
            "unit_caveat": "79–80 are split units of one original chapter; descriptive lengths are not literary targets."}
