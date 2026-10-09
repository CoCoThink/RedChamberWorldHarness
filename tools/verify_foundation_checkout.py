"""Verify intended changes in an isolated Git checkout, including CRLF handling.

This materializes tracked and non-ignored files without staging or committing
the user's repository. Dependencies must already be installed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml


REPORT = "artifacts/migration/handover-20261008/verification_report.json"
CLI_CODE = '''import socket, sys
from rcwh.cli import main
attempts=[]
def denied(*args, **kwargs):
    attempts.append(True)
    raise RuntimeError("Network is disabled for checkout verification")
socket.create_connection=denied
socket.getaddrinfo=denied
socket.socket.connect=denied
socket.socket.connect_ex=denied
sys.argv=["rcwh", *sys.argv[1:]]
try:
    main()
finally:
    if attempts:
        raise RuntimeError("Unexpected network access during local verification")
'''


def verify(root: Path) -> dict:
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
    ).decode("utf-8").split("\0")
    files = sorted({p for p in tracked if p and p != REPORT and (root / p).is_file()})
    with tempfile.TemporaryDirectory(prefix="rcwh-foundation-") as task_dir:
        base = Path(task_dir)
        staging = base / "staging"
        staging.mkdir()
        for relative in files:
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        subprocess.run(["git", "init", "-q", str(staging)], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=staging, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=Verification", "-c", "user.email=verification@example.invalid",
             "commit", "-qm", "Materialize intended foundation worktree"],
            cwd=staging, check=True, capture_output=True,
        )
        clean = base / "checkout"
        subprocess.run(
            ["git", "-c", "core.autocrlf=true", "clone", "--quiet", "--no-local", str(staging), str(clean)],
            check=True, capture_output=True,
        )
        if any(clean.glob("RCWH_Repository_Consolidation_Handover_*")):
            raise RuntimeError("checkout contains a handover package or nested repository")
        env = {**os.environ, "PYTHONPATH": str(clean / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        checks = [
            ("asset-storage", ["self-contained", "check", "--profile", "asset-storage", "--require-tracked"], 0),
            ("release-storage", ["self-contained", "check", "--profile", "release-storage", "--require-tracked"], 0),
            ("source-content", ["self-contained", "check", "--profile", "source-content", "--require-tracked"], None),
            ("source-locators", ["self-contained", "check", "--profile", "source-locators", "--require-tracked"], None),
            ("sources-verify-all", ["sources", "verify-all", "--require-tracked"], 0),
            ("source-gap-regression", ["sources", "gap-check", "--require-tracked"], 0),
            ("declared-input-regression", ["self-contained", "check", "--profile", "declared-inputs-regression", "--require-tracked"], 0),
            ("declared-input-closure", ["self-contained", "check", "--profile", "declared-inputs", "--require-tracked"], None),
            ("project-acceptance", ["project", "acceptance", "--require-tracked"], 0),
            ("project-acceptance-strict", ["project", "acceptance", "--require-tracked", "--require-complete"], None),
            ("project-status", ["project", "status"], 0),
            ("asset-history", ["assets", "history", "--list"], 0),
            ("asset-collections", ["assets", "collections"], 0),
            ("catalog-index", ["assets", "index"], 0),
            ("chapter-asset-discovery", ["assets", "list", "--role", "CHAPTER_CARD", "--chapter", "92"], 0),
            ("corpus-inputs", ["corpus", "inputs", "data/corpus/inputs/front80-pilot-v1.json", "--require-tracked"], 0),
            ("corpus-pilot", ["corpus", "verify", "corpus:front80:pilot:v1", "--require-tracked", "--rebuild"], 0),
            ("corpus-front80-candidate", ["corpus", "verify", "corpus:front80:v1-candidate", "--require-tracked", "--rebuild"], 0),
            ("frozen-writing-inputs", ["literary-inputs", "package", "data/writing/packages/ch89-research-v4.json", "--require-tracked"], 0),
            ("paired-review-submissions", ["paired-review", "summary"], 0),
            ("repository-validation", ["validate"], 0),
            ("literary-production", ["literary-production", "summary", "--json"], 0),
            ("prewrite-summary", ["prewrite", "summary", "--json"], 0),
            ("implementation-summary", ["implementation", "summary", "--json"], 0),
            ("implementation-stable", ["implementation", "stable", "--json"], 0),
            ("evidence-regression", ["regression", "--json"], 0),
            ("microdraft-summary", ["microdraft", "summary"], 0),
            ("review-summary", ["blind-microdraft-review", "summary"], 0),
            ("revision-summary", ["revision-ablation", "summary"], 0),
            ("world-summary-text", ["world", "summary"], 0),
            ("object-summary-text", ["object", "summary"], 0),
            ("ecology-summary-text", ["literary-ecology", "summary"], 0),
            ("adapter-summary-text", ["historical-adapter", "summary"], 0),
            ("suite-summary-text", ["literary-suite", "summary"], 0),
            ("knowledge-summary-text", ["knowledge", "summary"], 0),
            ("object-trace", ["object", "trace", "OBJ-TONGLING-JADE", "--json"], 0),
            ("literary-trace", ["literary-ecology", "trace", "evidence", "A01", "--json"], 0),
            ("implementation-trace", ["implementation", "trace", "source", "asset:release:stable:v1.4:readable", "--json"], 0),
            ("blind-export", ["literary-suite", "blind", "comp:43-0:ch89:pressure-test", "--output-dir", str(base / "blind-review"), "--json"], 0),
            ("promotion-export", ["promotion", "promotion:ch86:b:v1-5-candidate", "--output", str(base / "candidate.md"), "--json"], 2),
        ]
        results = {}
        acceptance_report = None
        for name, args, expected in checks:
            result = subprocess.run(
                [sys.executable, "-c", CLI_CODE, *args], cwd=clean, env=env,
                capture_output=True, text=True, timeout=240 if name.startswith("project-acceptance") else 120,
            )
            payload = json.loads(result.stdout) if result.stdout.lstrip().startswith("{") else {"message": result.stdout.strip()}
            if expected is None:
                if name == "project-acceptance-strict":
                    if payload.get("scope") != "REVIEW_FOLLOWUP_INPUT_ACCEPTANCE":
                        raise RuntimeError("Invalid project acceptance scope")
                    expected = int(payload["status"] != "PASS")
                elif name == "declared-input-closure":
                    if payload.get("profile") != "declared-inputs" or payload.get("status") not in {"PASS", "FAIL"}:
                        raise RuntimeError("Invalid strict declared-input closure report")
                    expected = int(payload["status"] != "PASS")
                else:
                    if not payload.get("sources") or payload.get("graph_findings") or payload.get("storage_findings"):
                        raise RuntimeError(f"{name}: invalid source closure report: {payload}")
                    expected = int(any(s["status"] != "PASS" for s in payload["sources"]))
                    if payload.get("status") != ("FAIL" if expected else "PASS"):
                        raise RuntimeError(f"{name}: inconsistent source closure status")
            if result.returncode != expected:
                raise RuntimeError(f"{name}: {result.returncode} != {expected}\n{result.stdout}\n{result.stderr}")
            if name.endswith("-trace") and payload.get("trace_complete") is not True:
                raise RuntimeError(f"{name}: incomplete local asset trace")
            if name == "project-acceptance":
                acceptance_report = payload
            if name == "promotion-export" and (payload.get("overall") != "PENDING"
                    or payload.get("pending_checks") != ["COMPETITION_ELIGIBILITY"]
                    or payload.get("findings")):
                raise RuntimeError("Historical promotion must await independent reviews")
            results[name] = {"returncode": result.returncode, "check_status": "PASS", "expected_returncode": expected}
            if "status" in payload:
                results[name]["status"] = payload["status"]
            for key in ("assets", "origins", "roots", "local_containers", "unresolved_sources", "evidence_closure"):
                if key in payload:
                    results[name][key] = payload[key]
            for key in ("closure_status", "readiness", "human_acceptance", "review_count", "scope", "engineering_status", "pending_checks", "failed_checks"):
                if key in payload: results[name][key] = payload[key]
            print(name, results[name], flush=True)
        # Exercise the workflow's real shell blocks, including expected nonzero exits.
        # Dependency installation is supplied by this environment; pytest runs below.
        bin_dir = base / "bin"
        bin_dir.mkdir()
        launcher = bin_dir / "rcwh"
        launcher.write_text(f"#!{sys.executable}\n" + CLI_CODE, encoding="utf-8")
        launcher.chmod(0o755)
        workflow = yaml.safe_load((clean / ".github/workflows/validate.yml").read_text(encoding="utf-8"))
        workflow_env = {**env, "PATH": os.pathsep.join((str(bin_dir), str(Path(sys.executable).parent), env["PATH"])),
                        "RCWH_ASSET_BASE": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean, text=True).strip()}
        workflow_results = []
        for step in workflow["jobs"]["validate"]["steps"]:
            script = step.get("run", "").strip()
            if not script or script in {"python -m pip install -e '.[dev]'", "pytest -q"}:
                continue
            name = step.get("name", script.splitlines()[0])
            result = subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", script], cwd=clean, env=workflow_env,
                capture_output=True, text=True, timeout=600 if "verify_corpus_candidates" in script else 180,
            )
            if result.returncode:
                raise RuntimeError(f"workflow {name} failed\n{result.stdout}\n{result.stderr}")
            workflow_results.append({"name": name, "returncode": result.returncode})
            print("workflow:", name, "PASS", flush=True)
        test = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=clean, env=env,
            capture_output=True, text=True, timeout=600,
        )
        summary = next((line for line in reversed(test.stdout.splitlines()) if "passed" in line or "failed" in line), "")
        print("clean checkout tests:", summary, flush=True)
        if test.returncode:
            raise RuntimeError(f"clean checkout tests failed\n{test.stdout}\n{test.stderr}")
        return {
            "schema_version": 1,
            "verification_kind": "TEMPORARY_GIT_CHECKOUT_OF_INTENDED_WORKTREE",
            "source_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "materialized_tree_sha": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=staging, text=True).strip(),
            "materialized_files": len(files), "excluded_from_materialization": [REPORT],
            "handover_package_present": False, "checkout_autocrlf": True,
            "network_policy": "Socket connection and DNS calls forbidden during CLI validation; dependencies preinstalled",
            "python_version": sys.version.split()[0], "checks": results,
            "workflow_checks": workflow_results,
            "workflow_scope": "All validation shell steps; preinstalled dependencies; pytest executed separately below",
            "tests": {"returncode": test.returncode, "summary": summary},
            "full_self_contained_status": "COMPLETE" if results["declared-input-closure"]["status"] == "PASS" else "INCOMPLETE",
            "review_followup_acceptance": results["project-acceptance"]["status"],
            "input_acceptance": acceptance_report,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", default=REPORT, help="New report path; existing audit reports are never overwritten")
    args = parser.parse_args()
    root = args.root.resolve()
    from rcwh.assets.paths import repository_path
    destination = repository_path(root, args.output)
    if destination.exists(): raise FileExistsError(f"Audit report already exists: {args.output}")
    report = verify(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Verification report written:", args.output)


if __name__ == "__main__":
    main()
