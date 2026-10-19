"""One-off: derive v4 research writing packages from v3 after input corrections.

v4 differs from v3 only by: the corrected exemplar set, relabelled Cao 1728
sources (``:npm005664`` ids, ADR 0004 disclosure), and recomputed source record
hashes. Output is deterministic; existing files must match byte for byte.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.assets.transactions import digest
from rcwh.corpus.locators import source_digest
from rcwh.graph import ProvenanceGraph

EXEMPLARS = "data/writing/exemplars/ch89-research-v3.json"
RELABEL = {f"src:history:cao:1728:{name}": f"src:history:cao:1728:{name}:npm005664"
           for name in ("inventory-seal", "pawn-tickets", "family-housing")}


def derive(root: Path, chapter: int) -> dict:
    graph = ProvenanceGraph.from_repo(root)
    package = json.loads((root / f"data/writing/packages/ch{chapter}-agent-research-v3.json").read_bytes())
    package["id"] = f"writing-package:ch{chapter}:agent-research:v4"
    package["exemplar_set"] = {"path": EXEMPLARS, "sha256": digest((root / EXEMPLARS).read_bytes())}
    sources = {}
    for item in package["sources"]:
        identity = RELABEL.get(item["source_ref"], item["source_ref"])
        sources[identity] = {"source_ref": identity, "record_sha256": source_digest(graph.sources[identity])}
    package["sources"] = [sources[key] for key in sorted(sources)]
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--chapters", default="81-100")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    first, last = (int(part) for part in args.chapters.split("-"))
    for chapter in range(first, last + 1):
        raw = (json.dumps(derive(root, chapter), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        path = root / f"data/writing/packages/ch{chapter}-agent-research-v4.json"
        if path.exists() and path.read_bytes() != raw:
            raise SystemExit(f"{path} exists with different bytes")
        path.write_bytes(raw)
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
