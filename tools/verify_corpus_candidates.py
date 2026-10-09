"""Rebuild selected corpus products in two fresh, offline Python processes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import subprocess
import sys


CHILD = r'''
import json, socket, sys
from pathlib import Path
from rcwh.assets import AssetCatalog
from rcwh.assets.transactions import digest
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import canonical_bytes
from rcwh.workflow import ProjectState
def denied(*args, **kwargs):
    raise RuntimeError("Network forbidden during corpus rebuild")
socket.create_connection=denied
socket.getaddrinfo=denied
socket.socket.connect=denied
socket.socket.connect_ex=denied
root=Path(sys.argv[1]); corpus=CorpusRepository(AssetCatalog.from_repo(root))
datasets=ProjectState.from_repo(root).owner("closure")["datasets"]
if not datasets: raise RuntimeError("No declared corpus datasets")
result={}
for ref in datasets:
    binding=corpus.registry()[ref]
    stored_manifest, stored_products=corpus.load(ref, rebuild=False)
    manifest, products=corpus.compile(stored_manifest["build_config"]["path"])
    if manifest!=stored_manifest or products!=stored_products:
        raise RuntimeError("Stored corpus differs from independent rebuild: "+ref)
    result[ref]={"manifest_sha256":digest(canonical_bytes(manifest)),
                 "products":{name:digest(raw) for name,raw in sorted(products.items())}}
print(json.dumps(result,ensure_ascii=False,sort_keys=True))
'''


def verify(root: Path) -> dict:
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    builds = []
    for _ in range(2):
        result = subprocess.run([sys.executable, "-c", CHILD, str(root)], cwd=root, env=env,
                                capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        builds.append(json.loads(result.stdout))
    if builds[0] != builds[1]:
        raise RuntimeError("Independent corpus builds are not byte-identical")
    return {"schema_version": 1, "status": "PASS", "scope": "TWO_INDEPENDENT_CORPUS_REBUILDS",
            "processes": 2, "cache_policy": "Extractor and corpus builder are uncached; fresh processes and no bytecode cache",
            "network_policy": "Socket and DNS calls forbidden", "datasets": builds[0],
            "human_layer_audit": "PENDING", "authority_effect": "NONE"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve()), ensure_ascii=False, indent=2))
