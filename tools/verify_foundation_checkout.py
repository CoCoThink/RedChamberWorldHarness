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
            ("project-status", ["project", "status"], 0),
            ("asset-history", ["assets", "history", "--list"], 0),
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
            ("promotion-export", ["promotion", "promotion:ch86:b:v1-5-candidate", "--output", str(base / "candidate.md"), "--json"], 0),
        ]
        results = {}
        for name, args, expected in checks:
            result = subprocess.run(
                [sys.executable, "-c", CLI_CODE, *args], cwd=clean, env=env,
                capture_output=True, text=True, timeout=120,
            )
            payload = json.loads(result.stdout) if result.stdout.lstrip().startswith("{") else {"message": result.stdout.strip()}
            if expected is None:
                if not payload.get("sources") or payload.get("graph_findings") or payload.get("storage_findings"):
                    raise RuntimeError(f"{name}: invalid source closure report: {payload}")
                expected = int(any(s["status"] != "PASS" for s in payload["sources"]))
                if payload.get("status") != ("FAIL" if expected else "PASS"):
                    raise RuntimeError(f"{name}: inconsistent source closure status")
            if result.returncode != expected:
                raise RuntimeError(f"{name}: {result.returncode} != {expected}\n{result.stdout}\n{result.stderr}")
            if name.endswith("-trace") and payload.get("trace_complete") is not True:
                raise RuntimeError(f"{name}: incomplete local asset trace")
            results[name] = {"returncode": result.returncode, "check_status": "PASS", "expected_returncode": expected}
            if "status" in payload:
                results[name]["status"] = payload["status"]
            for key in ("assets", "origins", "roots", "local_containers", "unresolved_sources", "evidence_closure"):
                if key in payload:
                    results[name][key] = payload[key]
            print(name, results[name], flush=True)
        # Exercise the workflow's real shell blocks, including expected nonzero exits.
        # Dependency installation is supplied by this environment; pytest runs below.
        bin_dir = base / "bin"
        bin_dir.mkdir()
        launcher = bin_dir / "rcwh"
        launcher.write_text(f"#!{sys.executable}\n" + CLI_CODE, encoding="utf-8")
        launcher.chmod(0o755)
        workflow = yaml.safe_load((clean / ".github/workflows/validate.yml").read_text(encoding="utf-8"))
        workflow_env = {**env, "PATH": str(bin_dir) + os.pathsep + env["PATH"],
                        "RCWH_ASSET_BASE": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean, text=True).strip()}
        workflow_results = []
        for step in workflow["jobs"]["validate"]["steps"]:
            script = step.get("run", "").strip()
            if not script or script in {"python -m pip install -e '.[dev]'", "pytest -q"}:
                continue
            name = step.get("name", script.splitlines()[0])
            result = subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", script], cwd=clean, env=workflow_env,
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode:
                raise RuntimeError(f"workflow {name} failed\n{result.stdout}\n{result.stderr}")
            workflow_results.append({"name": name, "returncode": result.returncode})
            print("workflow:", name, "PASS", flush=True)
        test = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=clean, env=env,
            capture_output=True, text=True, timeout=180,
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
            "full_self_contained_status": "INCOMPLETE",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    report = verify(root)
    destination = root / REPORT
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verification report written:", REPORT)


if __name__ == "__main__":
    main()
