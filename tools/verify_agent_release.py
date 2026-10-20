"""Verify current research release attribution, coverage and optional cloned build.

Pending reviews are expected; integrity failures are not. --build-smoke uses a
disposable clone of committed HEAD, so no publication files enter the worktree.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.review_campaign import _load

REQUEST = "data/agent_release/research-81-100-v1/request.json"
PLAN = "data/agent_release/research-81-100-v1/review-campaign-v2.json"


def verify(root: Path) -> dict:
    manifest = AgentRelease(root).evaluate(REQUEST)
    if manifest["status"] == "FAIL" or manifest["findings"]:
        raise ValueError(f"release integrity failed: {manifest['findings']}")
    plan = _load(root, PLAN)
    request = json.loads((root / REQUEST).read_bytes())
    expected = set()
    for row in request["chapters"]:
        if row["mode"] != "AGENT_CANDIDATE":
            continue
        report = next(c for c in manifest["chapters"] if c["chapter"] == row["chapter"])
        if report["gates"]["AUTHOR_PROVENANCE"] != "PASS" or not report["reviews"]["author_lineage"]["contributors"]:
            raise ValueError(f"missing original attribution: {row['chapter']}")
        if "rebind_receipt" not in report["bindings"]:
            raise ValueError("manifest dropped rebind receipt")
        packet = json.loads((root / row["panel"]["packet"]["path"]).read_bytes())
        required = [row["panel"]["subject_id"]] + [s["id"] for s in packet["subjects"]
                    if s["binding"] in [row["writing_package"], *report["reviews"]["contract_peer_bindings"]]]
        expected.update((row["panel"]["packet"]["sha256"], s) for s in required)
        expected.update((r["packet"]["sha256"], r["subject_id"]) for key in ("source_reviews", "corpus_reviews") for r in row.get(key, []))
    book = request["book_review"]
    from rcwh.workflow.book_review import subjects as book_subjects
    segments = book_subjects(root, book, chapters=[r["chapter"] for r in request["chapters"]])
    expected.update((book["packet"]["sha256"], s["id"]) for s in segments)
    coverage = Counter((j["packet"]["sha256"], s) for j in plan["jobs"] for s in j["subjects"])
    if set(coverage) != expected or set(coverage.values()) != {2}:
        raise ValueError("campaign must assign exactly two readers to every required subject")
    if manifest["advisories"]["book_continuity"]["status"] == "INVALID":
        raise ValueError("current whole-book review packet invalid")
    return {"status": "PASS", "release_status": manifest["status"], "failures": manifest["findings"],
            "request_sha256": manifest["request_sha256"],
            "chapters": len(manifest["changed_chapters"]), "jobs": dict(Counter(j["kind"] for j in plan["jobs"])),
            "continuity_segments": [s.get("chapters") for s in segments],
            "continuity_seams": len({tuple(seam) for j in plan["jobs"] for seam in j.get("continuity", {}).get("seams", [])}),
            "largest_reading_bytes": max(j["reading_bytes"] for j in plan["jobs"]),
            "batch_size": plan["batch_size"], "authority_effect": "NONE"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-smoke", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    report = verify(root)
    if args.build_smoke:
        with tempfile.TemporaryDirectory(prefix="rcwh-release-smoke-") as temporary:
            clone = Path(temporary) / "repo"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(root), str(clone)], check=True)
            environment = {**os.environ, "PYTHONPATH": str(clone / "src")}
            result = subprocess.run([sys.executable, "-m", "rcwh.cli", "agent-release", "build", REQUEST,
                                     "--allow-pending", "--json"], cwd=clone, env=environment, capture_output=True, check=False)
            if result.returncode not in (0, 2):
                raise ValueError(f"cloned build failed: {result.stdout.decode()} {result.stderr.decode()}")
            built = json.loads(result.stdout)
            stored = json.loads((clone / built["output"]["manifest_path"]).read_bytes())
            if stored != built or stored["status"] == "FAIL":
                raise ValueError("cloned manifest differs from build result")
            if built["request_sha256"] != report["request_sha256"]:
                raise ValueError("committed HEAD request differs from verified working tree")
            if any(not c["reviews"].get("author_lineage", {}).get("contributors") for c in built["chapters"]
                   if c["chapter"] in built["changed_chapters"]):
                raise ValueError("cloned manifest lost original author lineage")
            if built["status"] == "PENDING" and (clone / built["output"]["directory"] / "book.md").exists():
                raise ValueError("pending staging must not emit reviewed prose")
            report["cloned_build"] = {"status": "PASS", "release_status": built["status"],
                "manifest_path": built["output"]["manifest_path"], "text": built["output"]["text"]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
