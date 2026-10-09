from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from ..assets import AssetCatalog, AssetError
from ..provenance import ProvenanceRepository
from ..workflow import ProjectState
from ..corpus.extraction import ExtractionConfigError, ExtractionRepository, canonical_bytes
from ..corpus.locators import SourceLocatorVerifier


def add_foundation_commands(subparsers: argparse._SubParsersAction, default_root: Callable[[], Path]) -> None:
    def command(args: argparse.Namespace) -> int:
        root = Path(args.root).resolve() if args.root else default_root()
        try:
            if args.foundation == "project":
                if args.action == "acceptance":
                    from ..acceptance import ProjectAcceptance
                    payload = ProjectAcceptance(root).summary(require_tracked=args.require_tracked)
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                    return int(payload["status"] == "FAIL" or (args.require_complete and payload["status"] != "PASS"))
                else:
                    state = ProjectState.from_repo(root)
                    payload = state.summary()
                    payload["findings"] = state.validate()
                    payload["integrity_status"] = "FAIL" if payload["findings"] else "PASS"
                    if payload["findings"]:
                        payload["status"] = "FAIL"
            elif args.foundation == "literary-inputs":
                from ..literary_inputs import LiteraryInputs
                inputs = LiteraryInputs(AssetCatalog.from_repo(root))
                if args.action == "exemplars":
                    payload = inputs.exemplars(args.config)
                elif args.action == "package":
                    payload = inputs.package(args.config, production=args.production, require_tracked=args.require_tracked)
                elif args.action == "index-map":
                    payload = inputs.index_map(args.dataset_ref, args.collection)
                    if args.output:
                        from ..assets.paths import repository_path
                        with repository_path(root, args.output).open("xb") as handle:
                            handle.write(canonical_bytes(payload))
                        payload = {"status": "PASS", "output": args.output, "rows": len(payload["rows"]),
                                   "unresolved_rows": payload["unresolved_rows"], "authority_effect": "NONE"}
                else:
                    payload = inputs.dataset_map(args.old_dataset, args.new_dataset)
                    if args.output:
                        from ..assets.paths import repository_path
                        with repository_path(root, args.output).open("xb") as handle:
                            handle.write(canonical_bytes(payload))
                        payload = {"status": "PASS", "output": args.output, "rows": len(payload["rows"]), "authority_effect": "NONE"}
            elif args.foundation == "paired-review":
                from ..paired_review import PairedReview
                review = PairedReview(AssetCatalog.from_repo(root))
                if args.action == "summary":
                    payload = review.selected_summary()
                else:
                    from ..assets.paths import repository_path
                    packet, mapping = review.packet(args.protocol)
                    packet_path = repository_path(root, args.output)
                    mapping_path = repository_path(root, args.mapping)
                    if packet_path.exists() or mapping_path.exists() or packet_path == mapping_path:
                        raise AssetError("PAIRED_REVIEW_OUTPUT_MUST_BE_NEW")
                    packet_path.parent.mkdir(parents=True, exist_ok=True)
                    mapping_path.parent.mkdir(parents=True, exist_ok=True)
                    with packet_path.open("xb") as handle: handle.write(packet)
                    with mapping_path.open("xb") as handle: handle.write(canonical_bytes(mapping))
                    payload = {"status": "PASS", "scope": "PAIRED_BLIND_PACKET_EXPORT", "packet": args.output,
                               "packet_sha256": mapping["packet_sha256"], "mapping": args.mapping, "reviews": "PENDING", "authority_effect": "NONE"}
            elif args.foundation == "assets":
                from ..assets.ingest import AssetIntake
                intake_actions = {"ingest", "classify", "receipt", "recover", "migrate-shards", "index"}
                catalog = None if args.action in intake_actions else AssetCatalog.from_repo(root)
                if args.action == "ingest":
                    payload = AssetIntake(root).ingest(
                        Path(args.file), origin=args.origin, kind=args.kind,
                        role=args.role, receipt_key=args.receipt_key,
                    )
                elif args.action == "classify":
                    payload = AssetIntake(root).classify(args.receipt_id, kind=args.kind)
                elif args.action == "receipt":
                    payload = AssetIntake(root).receipt(args.receipt_id)
                elif args.action == "recover":
                    payload = AssetIntake(root).recover()
                elif args.action == "migrate-shards":
                    from ..assets.store import CatalogStore
                    payload = CatalogStore(root).migrate_shards()
                elif args.action == "index":
                    from ..assets.store import CatalogStore
                    payload = CatalogStore(root).index_report(rebuild=args.rebuild)
                elif args.action == "summary":
                    payload = catalog.summary()
                elif args.action in {"list", "collections"}:
                    from ..assets.discovery import AssetDiscovery
                    discovery = AssetDiscovery(catalog)
                    payload = discovery.collection_report(args.collection_id) if args.action == "collections" else discovery.query(
                        role=args.role, collection=args.collection, chapter=args.chapter, tag=args.tag,
                    )
                elif args.action == "resolve":
                    payload = catalog.resolve(args.asset_id).summary()
                elif args.action == "history":
                    from ..assets.history import HistoryArchive
                    archive = HistoryArchive(catalog)
                    payload = archive.summary()
                    if args.list_versions:
                        payload["versions"] = [
                            {"asset_id": key, "path": record["asset"]["path"],
                             "reason": record["reason"], "anchor_ref": record["anchor_ref"]}
                            for key, record in sorted(archive.records.items())
                        ]
                    if args.key:
                        records = archive.lookup(args.key)
                        if not records:
                            raise AssetError(f"unknown historical asset or alias: {args.key}")
                        payload["records"] = [{k: v for k, v in r.items() if k != "changes"} for r in records]
                        if args.restore_to:
                            if len(records) != 1:
                                raise AssetError("ambiguous historical alias; use the full asset ID")
                            raw = archive.restore(records[0]["asset"]["id"])
                            output = Path(args.restore_to)
                            with output.open("xb") as handle:
                                handle.write(raw)
                            payload["restored_to"] = str(output)
                    elif args.restore_to:
                        raise AssetError("restoration requires a historical asset ID")
                else:
                    findings = catalog.validate(require_tracked=args.require_tracked)
                    if args.base_ref:
                        findings.extend(catalog.compare_git_baseline(args.base_ref))
                    payload = {**catalog.summary(), "status": "FAIL" if findings else "PASS", "findings": findings}
            elif args.foundation == "sources":
                repository = ProvenanceRepository.from_repo(root)
                if args.action == "trace":
                    payload = repository.trace(args.node_id)
                elif args.action == "verify-all":
                    payload = repository.verify_all(require_tracked=args.require_tracked)
                elif args.action == "gap-check":
                    from ..closure import InputClosure
                    payload = InputClosure(root).gap_check(args.baseline, require_tracked=args.require_tracked, base_ref=args.base_ref)
                elif args.action == "audit":
                    from ..provenance.audit import SourceAudit
                    payload = SourceAudit(repository).summary()
                elif args.action == "verify":
                    payload = repository.source_report(repository.graph.sources[args.source_id], locators=True)
                    if args.report_output:
                        with Path(args.report_output).open("xb") as output:
                            output.write(canonical_bytes(payload["verification_report"]))
                        payload["report_output"] = args.report_output
                elif args.action == "locate":
                    payload = SourceLocatorVerifier(repository.catalog).locate(
                        repository.graph.sources[args.source_id], args.extraction, unit_ref=args.unit,
                        allow_line_break_spans=args.allow_line_break_spans,
                    )
                else:
                    payload = repository.check(locators=args.locators)
            elif args.foundation == "corpus":
                catalog = AssetCatalog.from_repo(root)
                repository = ExtractionRepository(catalog)
                if args.action == "extract":
                    config = {"format": args.format} if args.format else {}
                    if args.pdf_pages is not None:
                        config["pdf_pages"] = args.pdf_pages
                    payload = repository.build(args.asset_id, config)
                elif args.action in {"inputs", "input-inventory"}:
                    from ..corpus.inputs import CorpusInputs
                    inputs = CorpusInputs(catalog)
                    if args.action == "inputs":
                        payload = inputs.verify(args.config, require_tracked=args.require_tracked)
                    else:
                        inventory = inputs.inventory(args.config)
                        with Path(args.output).open("xb") as output:
                            output.write(canonical_bytes(inventory))
                        payload = {"status": "PASS", "output": args.output, "authority_effect": "NONE", "corpus_status": "NOT_BUILT"}
                elif args.action in {"build", "query"} or args.manifest_ref.startswith("corpus:"):
                    from ..corpus.dataset import CorpusRepository
                    corpus = CorpusRepository(catalog)
                    if args.action == "build":
                        payload = corpus.build(args.config, args.output)
                    elif args.action == "query":
                        payload = corpus.query(args.dataset_ref, kind=args.kind, chapter=args.chapter, keyword=args.keyword, limit=args.limit)
                    elif args.action == "show":
                        if args.segment_id is None:
                            raise AssetError("corpus show requires a segment ID")
                        payload = corpus.show(args.manifest_ref, args.segment_id)
                    else:
                        payload = corpus.verify(args.manifest_ref, rebuild=True, require_tracked=args.require_tracked)
                        from ..corpus.audit import CorpusAudit
                        payload["human_acceptance"] = CorpusAudit(catalog).summary(args.manifest_ref, rebuild=False)
                else:
                    manifest, units = repository.load(args.manifest_ref, rebuild=True)
                    payload = {"status": "PASS", "manifest_ref": args.manifest_ref, "manifest": manifest, "units": len(units)}
                    if args.action == "show" and args.unit is not None:
                        payload["unit"] = units[args.unit]
                    if args.require_tracked:
                        findings = catalog.validate(require_tracked=True)
                        payload["findings"] = findings
                        if findings:
                            payload["status"] = "FAIL"
            else:
                catalog = AssetCatalog.from_repo(root)
                findings = catalog.validate(require_tracked=args.require_tracked)
                if args.profile in {"declared-inputs", "declared-inputs-regression"}:
                    from ..closure import InputClosure
                    closure = InputClosure(root)
                    payload = closure.regression(require_tracked=args.require_tracked) if args.profile.endswith("-regression") else closure.verify(require_tracked=args.require_tracked)
                elif args.profile == "asset-storage":
                    payload = {**catalog.summary(), "profile": args.profile, "status": "FAIL" if findings else "PASS", "findings": findings}
                elif args.profile == "release-storage":
                    payload = ProjectState.from_repo(root).release(catalog).summary()
                elif args.profile == "source-locators":
                    payload = ProvenanceRepository.from_repo(root).verify_all(require_tracked=args.require_tracked)
                    payload["profile"] = args.profile
                else:
                    payload = ProvenanceRepository.from_repo(root).check()
                if findings:
                    payload["storage_findings"] = list(dict.fromkeys(payload.get("storage_findings", []) + findings))
                    payload["status"] = "FAIL"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1 if payload.get("status", payload.get("content_status")) == "FAIL" else 0
        except ExtractionConfigError as exc:
            print(json.dumps({"status": "FAIL", "findings": [str(exc)]}, ensure_ascii=False, indent=2))
            return 2
        except (AssetError, OSError, KeyError, ValueError) as exc:
            print(json.dumps({"status": "FAIL", "findings": [str(exc)]}, ensure_ascii=False, indent=2))
            return 1

    assets = subparsers.add_parser("assets", help="Versioned physical files and their origins")
    assets.set_defaults(foundation="assets", func=command)
    actions = assets.add_subparsers(dest="action", required=True)
    actions.add_parser("summary")
    listing = actions.add_parser("list", help="Find fixed assets by reading role, collection or chapter")
    collections = actions.add_parser("collections", help="List reading collections; membership grants no authority")
    collections.add_argument("collection_id", nargs="?")
    from ..assets.ingest import KINDS, ROLES
    listing.add_argument("--role", choices=ROLES)
    listing.add_argument("--collection")
    listing.add_argument("--chapter", type=int)
    listing.add_argument("--tag")
    ingest = actions.add_parser("ingest", help="Receive a local file without granting evidence or adoption authority")
    ingest.add_argument("file")
    ingest.add_argument("--origin", required=True)
    ingest.add_argument("--kind", choices=sorted(KINDS))
    ingest.add_argument("--role", choices=ROLES, help="Intended discovery role; does not grant authority")
    ingest.add_argument("--receipt-key", help="Idempotency key; use a new key to record another occurrence")
    classify = actions.add_parser("classify", help="Classify a received asset while preserving its identity and bytes")
    classify.add_argument("receipt_id")
    classify.add_argument("--kind", required=True, choices=sorted(set(KINDS) - {"UNCLASSIFIED_INPUT"}))
    receipt = actions.add_parser("receipt", help="Inspect receipt facts, current bindings and Git tracking")
    receipt.add_argument("receipt_id")
    actions.add_parser("recover", help="Finish an interrupted asset transaction; never overwrite conflicting edits")
    actions.add_parser("migrate-shards", help="Atomically select ID-based catalog shards without changing asset identity")
    index = actions.add_parser("index", help="Verify or rebuild the disposable catalog index")
    index.add_argument("--rebuild", action="store_true")
    resolve = actions.add_parser("resolve")
    resolve.add_argument("asset_id")
    history = actions.add_parser("history", help="Inspect retired versions or recover their exact bytes")
    history.add_argument("key", nargs="?")
    history.add_argument("--list", dest="list_versions", action="store_true", help="Generate the historical version index from the archive")
    history.add_argument("--restore-to", help="Write a historical version to a new file; never makes it current")
    validate = actions.add_parser("validate")
    validate.add_argument("--require-tracked", action="store_true")
    validate.add_argument("--base-ref")

    sources = subparsers.add_parser("sources", help="Trace provenance to physical source assets")
    sources.set_defaults(foundation="sources", func=command)
    actions = sources.add_subparsers(dest="action", required=True)
    trace = actions.add_parser("trace")
    trace.add_argument("node_id")
    check = actions.add_parser("check")
    check.add_argument("--locators", action="store_true")
    verify_all = actions.add_parser("verify-all", help="Verify carriers and actual excerpt locators for all Source roots")
    verify_all.add_argument("--require-tracked", action="store_true")
    actions.add_parser("audit", help="Show independently submitted evidence review status")
    gap = actions.add_parser("gap-check", help="Reject new or changed Source gaps; never declares closure complete")
    gap.add_argument("--baseline", default="data/project/source_gap_baseline.json")
    gap.add_argument("--require-tracked", action="store_true")
    gap.add_argument("--base-ref", help="Git version whose Source gap waivers may only shrink")
    verify = actions.add_parser("verify", help="Recompute one Source locator verification report")
    verify.add_argument("source_id")
    verify.add_argument("--report-output", help="Write the verification report to a new file without changing the Source")
    locate = actions.add_parser("locate", help="Propose a Locator v2 only when an exact excerpt has a unique match")
    locate.add_argument("source_id")
    locate.add_argument("--extraction", required=True)
    locate.add_argument("--unit", help="Limit matching to one physical text unit")
    locate.add_argument("--allow-line-break-spans", action="store_true", help="Propose explicit PDF spans across LF breaks, preserving the Source text")

    corpus = subparsers.add_parser("corpus", help="Build and verify deterministic source extractions")
    corpus.set_defaults(foundation="corpus", func=command)
    actions = corpus.add_subparsers(dest="action", required=True)
    extract = actions.add_parser("extract")
    extract.add_argument("asset_id")
    extract.add_argument("--format", choices=["PDF", "EPUB", "HTML", "TEXT"])
    extract.add_argument("--pdf-pages", nargs="+", type=int, help="Selected physical pages, in ascending order, starting at 1")
    inputs = actions.add_parser("inputs", help="Verify fixed input selection and rebuild its registered inventory")
    inputs.add_argument("config", help="Repository-relative input selection JSON")
    inputs.add_argument("--require-tracked", action="store_true")
    inventory = actions.add_parser("input-inventory", help="Write a new inventory for review and registration")
    inventory.add_argument("config")
    inventory.add_argument("--output", required=True)
    build = actions.add_parser("build", help="Build a new corpus candidate with fixed text layer rules")
    build.add_argument("--config", required=True)
    build.add_argument("--output", required=True, help="New repository-relative corpus/front80 directory")
    query = actions.add_parser("query", help="Find exact text in one fixed corpus dataset")
    query.add_argument("dataset_ref")
    query.add_argument("--kind", default="MAIN_TEXT", choices=["MAIN_TEXT", "ZHIPI", "EDITORIAL", "VARIANT", "APPENDIX", "UNCLASSIFIED"])
    query.add_argument("--chapter", type=int)
    query.add_argument("--keyword")
    query.add_argument("--limit", type=int, default=20)
    for action in ("verify", "show"):
        parser = actions.add_parser(action)
        parser.add_argument("manifest_ref")
        parser.add_argument("--require-tracked", action="store_true")
        parser.add_argument("--rebuild", action="store_true", help="Rebuild verification is always performed")
        if action == "show":
            parser.add_argument("--unit")
            parser.add_argument("segment_id", nargs="?")

    project = subparsers.add_parser("project", help="Explicit owners of current project state")
    project.set_defaults(foundation="project", func=command)
    actions = project.add_subparsers(dest="action", required=True)
    actions.add_parser("status")
    acceptance = actions.add_parser("acceptance", help="Compute current Review follow-up input acceptance")
    acceptance.add_argument("--require-tracked", action="store_true")
    acceptance.add_argument("--require-complete", action="store_true", help="Fail while any admission or review is pending")

    literary = subparsers.add_parser("literary-inputs", help="Validate frozen corpus examples and writing inputs")
    literary.set_defaults(foundation="literary-inputs", func=command)
    actions = literary.add_subparsers(dest="action", required=True)
    exemplar = actions.add_parser("exemplars")
    exemplar.add_argument("config")
    package = actions.add_parser("package")
    package.add_argument("config")
    package.add_argument("--production", action="store_true")
    package.add_argument("--require-tracked", action="store_true")
    mapping = actions.add_parser("index-map")
    mapping.add_argument("dataset_ref")
    mapping.add_argument("--collection", default="collection:front80:literary-exemplars")
    mapping.add_argument("--output", help="Write to a new repository-relative file")
    versions = actions.add_parser("dataset-map")
    versions.add_argument("old_dataset")
    versions.add_argument("new_dataset")
    versions.add_argument("--output")
    paired = subparsers.add_parser("paired-review", help="Prepare blind pairs and validate real submitted reviews")
    paired.set_defaults(foundation="paired-review", func=command)
    actions = paired.add_subparsers(dest="action", required=True)
    actions.add_parser("summary")
    packet = actions.add_parser("packet")
    packet.add_argument("--protocol", required=True)
    packet.add_argument("--output", required=True)
    packet.add_argument("--mapping", required=True, help="Separate coordinator-only file; do not share with reviewers")

    closure = subparsers.add_parser("self-contained", help="Scoped closure checks; no implicit full-repository PASS")
    closure.set_defaults(foundation="self-contained", func=command)
    check = closure.add_subparsers(dest="action", required=True).add_parser("check")
    check.add_argument("--profile", required=True, choices=["asset-storage", "source-content", "source-locators", "release-storage", "declared-inputs", "declared-inputs-regression"])
    check.add_argument("--require-tracked", action="store_true")
