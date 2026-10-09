"""Apply a reviewed local Source closure plan, preserving evidence semantics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.assets import AssetError
from rcwh.provenance.migration import SourceClosureMigration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--audit-output", default="artifacts/migration/source-closure/audit.json")
    args = parser.parse_args()
    try:
        service = SourceClosureMigration(args.root)
        proposal = service.propose(json.loads(args.plan.read_bytes()))
        if args.apply:
            proposal = service.apply(proposal, audit_path=args.audit_output)
        print(json.dumps({
            key: proposal[key] for key in ("status", "verification_status", "evidence_sha256", "authority_effect")
        } | {"roots": len(proposal["results"]), "verified": sum(item["status"] == "PASS" for item in proposal["results"])}, ensure_ascii=False, indent=2))
        return 0
    except (AssetError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "findings": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
