from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from ..assets import AssetCatalog, AssetError
from ..provenance import ProvenanceRepository
from ..workflow import ProjectState


def add_foundation_commands(subparsers: argparse._SubParsersAction, default_root: Callable[[], Path]) -> None:
    def command(args: argparse.Namespace) -> int:
        root = Path(args.root).resolve() if args.root else default_root()
        try:
            if args.foundation == "project":
                state = ProjectState.from_repo(root)
                payload = state.summary()
                payload["findings"] = state.validate()
                payload["integrity_status"] = "FAIL" if payload["findings"] else "PASS"
                if payload["findings"]:
                    payload["status"] = "FAIL"
            elif args.foundation == "assets":
                catalog = AssetCatalog.from_repo(root)
                if args.action == "summary":
                    payload = catalog.summary()
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
                else:
                    payload = repository.check(locators=args.locators)
            else:
                catalog = AssetCatalog.from_repo(root)
                findings = catalog.validate(require_tracked=args.require_tracked)
                if args.profile == "asset-storage":
                    payload = {**catalog.summary(), "profile": args.profile, "status": "FAIL" if findings else "PASS", "findings": findings}
                elif args.profile == "release-storage":
                    payload = ProjectState.from_repo(root).release(catalog).summary()
                else:
                    payload = ProvenanceRepository.from_repo(root).check(locators=args.profile == "source-locators")
                if findings:
                    payload["storage_findings"] = findings
                    payload["status"] = "FAIL"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1 if payload.get("status", payload.get("content_status")) == "FAIL" else 0
        except (AssetError, OSError, KeyError, ValueError) as exc:
            print(json.dumps({"status": "FAIL", "findings": [str(exc)]}, ensure_ascii=False, indent=2))
            return 1

    assets = subparsers.add_parser("assets", help="Versioned physical files and their origins")
    assets.set_defaults(foundation="assets", func=command)
    actions = assets.add_subparsers(dest="action", required=True)
    actions.add_parser("summary")
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

    project = subparsers.add_parser("project", help="Explicit owners of current project state")
    project.set_defaults(foundation="project", func=command)
    project.add_subparsers(dest="action", required=True).add_parser("status")

    closure = subparsers.add_parser("self-contained", help="Scoped closure checks; no implicit full-repository PASS")
    closure.set_defaults(foundation="self-contained", func=command)
    check = closure.add_subparsers(dest="action", required=True).add_parser("check")
    check.add_argument("--profile", required=True, choices=["asset-storage", "source-content", "source-locators", "release-storage"])
    check.add_argument("--require-tracked", action="store_true")
