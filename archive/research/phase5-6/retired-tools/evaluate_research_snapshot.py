"""Evaluate once on exact Linux inputs; never build or overwrite old results."""
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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(root: Path, request_path: str, output_directory: str) -> dict:
    from rcwh.assets.paths import repository_path
    from rcwh.candidate_reviews import canonical_bytes
    from rcwh.generation.records import append_bytes

    if sys.platform != 'linux':
        raise ValueError('research snapshot evaluation requires Linux')
    root = root.resolve()
    request = repository_path(root, request_path)
    output = repository_path(root, output_directory)
    if output.exists():
        raise FileExistsError('evaluation results must use a new directory')
    if not request.is_file() or request.is_relative_to(output):
        raise ValueError('evaluation requires an existing request outside output directory')
    request_sha = sha(request)
    files = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root
    ).decode().split('\0')
    inputs = {}
    with tempfile.TemporaryDirectory(prefix='rcwh-final-evaluation-') as directory:
        snapshot = Path(directory) / 'repo'
        snapshot.mkdir()
        for relative in sorted(set(files) - {''}):
            source = repository_path(root, relative)
            if source.is_symlink():
                raise ValueError('symlink in snapshot inputs')
            if not source.is_file():
                continue
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            inputs[relative] = sha(target)
        if inputs.get(request_path) != request_sha:
            raise ValueError('request absent or changed during capture')
        subprocess.run(['git', 'init', '-q', str(snapshot)], check=True)
        subprocess.run(['git', 'add', '.'], cwd=snapshot, check=True, capture_output=True)
        program = '''
from pathlib import Path
import time
from rcwh.workflow.agent_release import AgentRelease
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import append_bytes,binding
root=Path.cwd();engine=AgentRelease(root);before=engine._stable_snapshot();started=time.monotonic()
report=engine.evaluate(REQUEST)
if engine._stable_snapshot()!=before:raise ValueError('stable snapshot changed during evaluation')
append_bytes(root,OUTPUT+'/report.json',canonical_bytes(report))
append_bytes(root,OUTPUT+'/execution.json',canonical_bytes({
 'schema_version':1,'kind':'ACTUAL_RELEASE_EVALUATE_EXECUTION','authority_effect':'NONE',
 'request':binding(root,REQUEST),'report':binding(root,OUTPUT+'/report.json'),'status':report['status'],
 'elapsed_seconds':round(time.monotonic()-started,3),'stable_snapshot_unchanged':True,
 'build_called':False,'execution_scope':'NORMAL_EVALUATOR_ON_BYTE_IDENTICAL_LINUX_SNAPSHOT',
 'literary_acceptance':'NOT_GRANTED'}))
print('evaluation status',report['status'],flush=True)
'''
        program = f'REQUEST={request_path!r}\nOUTPUT={output_directory!r}\n' + program
        env = {**os.environ, 'PYTHONPATH': str(snapshot / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([sys.executable, '-u', '-c', program], cwd=snapshot, env=env, check=True)
        current_files = subprocess.check_output(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root
        ).decode().split('\0')
        current = {p for p in current_files if p and repository_path(root, p).is_file()}
        additions = sorted(current - set(inputs))
        drift = [p for p, value in inputs.items()
                 if not repository_path(root, p).is_file() or sha(repository_path(root, p)) != value]
        if drift or additions:
            raise ValueError(f'input drift; no evaluation copyback: changed={drift}, added={additions}')
        products = {name: (snapshot / output_directory / name).read_bytes()
                    for name in ('report.json', 'execution.json')}
        execution = json.loads(products['execution.json'])
        report = json.loads(products['report.json'])
        if (execution['build_called'] is not False or execution['stable_snapshot_unchanged'] is not True
                or execution['request'] != {'path': request_path, 'sha256': request_sha}
                or execution['report'] != {'path': output_directory + '/report.json',
                                           'sha256': hashlib.sha256(products['report.json']).hexdigest()}
                or execution['status'] != report['status']):
            raise ValueError('evaluation output bindings or execution custody differ')
        for name, raw in products.items():
            append_bytes(root, output_directory + '/' + name, raw)
            if (output / name).read_bytes() != raw:
                raise ValueError('evaluation copyback differs')
        custody = {'schema_version': 1, 'kind': 'RELEASE_EVALUATION_SNAPSHOT_CUSTODY',
                   'authority_effect': 'NONE', 'inputs': inputs, 'input_count': len(inputs),
                   'changed_original_inputs': drift, 'snapshot_removed': True,
                   'output_hashes': {name: hashlib.sha256(raw).hexdigest() for name, raw in products.items()},
                   'limitation': 'Ordinary evaluation only; FAIL/PENDING preserved, no build, source/human/literary qualification.'}
    append_bytes(root, output_directory + '/snapshot-custody.json', canonical_bytes(custody))
    return {'status': report['status'], 'build_called': False, 'snapshot_removed': True,
            'input_count': len(inputs), 'changed_original_inputs': drift}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--request', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.root, args.request, args.output_directory), ensure_ascii=False))
