"""Run one disposable Linux research snapshot; preserve results in the repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def verify(root: Path, output: Path) -> int:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite checkpoint results: {output}")
    output.mkdir(parents=True)
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).decode().split("\0")
    frozen = json.loads((root / "artifacts/agent_research/phase5/verification/protected-originals-final.json").read_bytes())
    protected = frozen["checked_files"]
    changed = [p for p, sha in protected.items() if hashlib.sha256((root / p).read_bytes()).hexdigest() != sha]
    if changed:
        raise ValueError(f"protected originals changed: {changed}")
    snapshot_inputs = {}
    with tempfile.TemporaryDirectory(prefix="rcwh-research-checkpoint-") as directory:
        clean = Path(directory) / "repo"
        clean.mkdir()
        for relative in sorted(set(files) - {""}):
            source = root / relative
            if source.is_symlink():
                raise ValueError(f"snapshot input is a symlink: {relative}")
            if not source.is_file() or source.is_relative_to(output):
                continue
            destination = clean / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            snapshot_inputs[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()
        (output / "snapshot-inputs.json").write_text(
            json.dumps(snapshot_inputs, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(clean)], check=True)
        subprocess.run(["git", "add", "."], cwd=clean, check=True, capture_output=True)
        env = {**os.environ, "PYTHONPATH": str(clean / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
               "PYTHONDONTWRITEBYTECODE": "1"}
        with (output / "pytest.log").open("xb") as log:
            tests = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=clean, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        validation = subprocess.run([sys.executable, "-c",
            "import json; from pathlib import Path; from rcwh.validate import validate_repository; "
            "errors=validate_repository(Path.cwd()); print(json.dumps({'status':'FAIL' if errors else 'PASS',"
            "'findings':errors},ensure_ascii=False,indent=2)); raise SystemExit(bool(errors))"],
            cwd=clean, env=env, capture_output=True)
        (output / "validate.json").write_bytes(validation.stdout)
        (output / "validate-stderr.log").write_bytes(validation.stderr)
    changed = [p for p, sha in protected.items() if hashlib.sha256((root / p).read_bytes()).hexdigest() != sha]
    snapshot_changed = [p for p, sha in snapshot_inputs.items()
                        if not (root / p).is_file() or hashlib.sha256((root / p).read_bytes()).hexdigest() != sha]
    result = {"python": sys.version, "pytest_exit_code": tests.returncode,
              "validate_exit_code": validation.returncode, "protected_files": len(protected),
              "protected_changed": changed, "snapshot_input_files": len(snapshot_inputs),
              "snapshot_changed_during_check": snapshot_changed,
              "snapshot_removed": True, "authority_effect": "NONE",
              "limitation": "Engineering checks only, not source authority or literary acceptance."}
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(tests.returncode or validation.returncode or changed or snapshot_changed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(verify(args.root.resolve(), args.output.resolve()))
