"""Verify current research release attribution, coverage and optional cloned build.

Pending reviews are expected; integrity failures are not. --build-smoke uses a
disposable clone of committed HEAD, so no publication files enter the worktree.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.review_campaign import _load
from rcwh.candidate_reviews import digest
from rcwh.contracts import record_sha256
from rcwh.assets.paths import repository_path

REQUEST = "data/agent_release/research-81-100-v4-r2/request.json"
PLAN = "data/agent_release/research-81-100-v4-r2/review-campaign-v1.json"


def preserve_existing_release(clone: Path, request_path: str, quarantine: Path) -> dict | None:
    """Preserve a committed PASS edition in the disposable clone before rebuilding.

    The real build's exclusive reservation stays in force. An incomplete or
    corrupt existing edition is an error, not something the smoke test removes.
    """
    request = json.loads(repository_path(clone, request_path).read_bytes())
    relative = f"releases/agent/{request['id']}"
    target = repository_path(clone, relative)
    if not target.exists():
        return None
    if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != {"manifest.json", "book.md"}:
        raise ValueError("existing release is incomplete or has unexpected files")
    if any(p.is_symlink() or not p.is_file() for p in target.iterdir()):
        raise ValueError("existing release must contain ordinary files")
    stored = json.loads((target / "manifest.json").read_bytes())
    AgentRelease(clone)._validate(stored, "manifest")
    text = (target / "book.md").read_bytes()
    if (stored["status"] != "PASS" or stored["id"] != request["id"]
            or stored["request_sha256"] != record_sha256(request)
            or stored["output"] != {"directory": relative, "manifest_path": f"{relative}/manifest.json",
                                    "text": {"path": f"{relative}/book.md", "sha256": digest(text), "bytes": len(text)}}):
        raise ValueError("existing release manifest/request/book mismatch")
    target.rename(quarantine)
    return stored


def compare_release_manifests(stored: dict, fresh: dict) -> list[str]:
    """Require exact release semantics; disclose only named runtime observations.

    Successful extraction rebuild reports use the same narrow, faithful Python
    normalization as writing compatibility. The compatibility report's list of
    historical runtime observations is retained in the original manifest, while
    the fresh build recomputes it. No review, gate, author or binding is omitted.
    """
    from rcwh.generation.session import _runtime_observations

    differences = []

    def compare(old, new, path=()):
        if old == new:
            return
        label = ".".join(map(str, path))
        if (path[-2:] == ("verification_report", "rebuild")
                and isinstance(old, dict) and isinstance(new, dict)):
            def task(report):
                return {"sources": [{"verification": {"verification_report": {"rebuild": report}}}]}
            normalized, variations = _runtime_observations(task(old), task(new))
            if variations and normalized == task(new):
                differences.append(label)
                return
        if path[-2:] == ("current_writing_inputs", "runtime_observation_variations"):
            # These are historical observations, not admission credentials.
            # The full report's status, changed inputs/records and findings
            # still compare exactly, and fresh compatibility is reverified.
            if isinstance(old, list) and isinstance(new, list):
                differences.append(label)
                return
        if isinstance(old, dict) and isinstance(new, dict) and old.keys() == new.keys():
            for key in old:
                compare(old[key], new[key], path + (key,))
            return
        if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
            for index, (a, b) in enumerate(zip(old, new, strict=True)):
                compare(a, b, path + (index,))
            return
        raise ValueError(f"committed release differs from current rebuild: {label}")

    compare(deepcopy(stored), fresh)
    return differences


def verify(root: Path, request_path: str = REQUEST, plan_path: str = PLAN) -> dict:
    manifest = AgentRelease(root).evaluate(request_path)
    if manifest["status"] == "FAIL" or manifest["findings"]:
        raise ValueError(f"release integrity failed: {manifest['findings']}")
    plan = _load(root, plan_path)
    request = json.loads((root / request_path).read_bytes())
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
            "batch_size": plan["batch_size"],
            "largest_image_bytes": max(j.get("image_bytes", 0) for j in plan["jobs"]),
            "largest_image_count": max(len(j.get("inspect_images", [])) for j in plan["jobs"]),
            "authority_effect": "NONE"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-smoke", action="store_true")
    parser.add_argument("--request", default=REQUEST)
    parser.add_argument("--plan", default=PLAN)
    args = parser.parse_args()
    root = args.root.resolve()
    report = verify(root, args.request, args.plan)
    if args.build_smoke:
        with tempfile.TemporaryDirectory(prefix="rcwh-release-smoke-") as temporary:
            clone = Path(temporary) / "repo"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(root), str(clone)], check=True)
            preserved = preserve_existing_release(clone, args.request, Path(temporary) / "committed-release")
            environment = {**os.environ, "PYTHONPATH": str(clone / "src")}
            result = subprocess.run([sys.executable, "-m", "rcwh.cli", "agent-release", "build", args.request,
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
            if preserved is not None:
                differences = compare_release_manifests(preserved, built)
                if (Path(temporary) / "committed-release/book.md").read_bytes() != (clone / built["output"]["text"]["path"]).read_bytes():
                    raise ValueError("committed research book differs from cloned rebuild")
                report["cloned_build"]["committed_release"] = {
                    "status": "PASS", "book": "EXACT_BYTES", "manifest": "EXACT_EXCEPT_NAMED_RUNTIME_OBSERVATIONS",
                    "runtime_observation_paths": differences, "original_preserved_in_disposable_clone": True}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
