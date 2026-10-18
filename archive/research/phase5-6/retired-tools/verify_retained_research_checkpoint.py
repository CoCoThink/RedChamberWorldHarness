"""Verify a new Linux snapshot without deleting it or copying products back."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(root: Path, expected: dict) -> list[str]:
    return [path for path, digest in expected.items()
            if not (root / path).is_file() or sha(root / path) != digest]


def verify(root: Path, output: Path) -> int:
    if sys.version_info[:2] != (3, 12):
        raise ValueError("formal verification requires Python3.12")
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite checkpoint: {output}")
    if not output.is_relative_to(root):
        raise ValueError("checkpoint output must be within repository")
    protected = json.loads((root / "artifacts/agent_research/phase5/verification/protected-originals-final.json").read_bytes())["checked_files"]
    changed = differences(root, protected)
    if changed:
        raise ValueError(f"protected originals changed: {changed}")
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).decode().split("\0")
    # This snapshot is deliberately retained. There is no cleanup branch.
    clean = Path(tempfile.mkdtemp(prefix="rcwh-retained-checkpoint-")) / "repo"
    clean.mkdir()
    output.mkdir(parents=True)
    snapshot_inputs = {}
    for relative in sorted(set(paths) - {""}):
        source = root / relative
        if source.is_relative_to(output):
            continue
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"invalid snapshot input: {relative}")
        raw = source.read_bytes()
        destination = clean / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(raw)
        snapshot_inputs[relative] = hashlib.sha256(raw).hexdigest()
    with (output / "snapshot-inputs.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(snapshot_inputs, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    with (output / "retained-snapshot.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps({"snapshot": str(clean), "cleanup": "NOT_PERFORMED",
                                 "copyback": "NONE", "authority_effect": "NONE"}, indent=2) + "\n")
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
    for name, raw in (("validate.json", validation.stdout), ("validate-stderr.log", validation.stderr)):
        with (output / name).open("xb") as stream:
            stream.write(raw)
    changed = differences(root, protected)
    drift = differences(root, snapshot_inputs)
    failed = bool(tests.returncode or validation.returncode or changed or drift)
    result = {"status": "FAIL" if failed else "PASS", "python": sys.version,
              "pytest_exit_code": tests.returncode, "validate_exit_code": validation.returncode,
              "protected_files": len(protected), "protected_changed": changed,
              "snapshot_input_files": len(snapshot_inputs), "snapshot_changed_during_check": drift,
              "snapshot_removed": False, "retained_snapshot": str(clean), "copyback": "NONE",
              "authority_effect": "NONE", "limitation": "Engineering only; snapshot retained, no release or authority granted."}
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(verify(args.root, args.output))
