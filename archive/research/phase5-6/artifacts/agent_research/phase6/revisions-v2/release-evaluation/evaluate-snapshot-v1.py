"""Run the unchanged evaluator in one byte-identical Linux snapshot."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

root = Path(sys.argv[1]).resolve()
base = 'artifacts/agent_research/phase6/revisions-v2'
output = root / base / 'release-evaluation'
request = f'{base}/release-evaluation/request-v1.json'
for name in ('report-v1.json', 'execution-v1.json'):
    if (output / name).exists():
        raise FileExistsError(name)
files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root).decode().split('\0')
inputs = {}
started = time.monotonic()
with tempfile.TemporaryDirectory(prefix='rcwh-release-evaluate-') as directory:
    snapshot = Path(directory) / 'repo'
    snapshot.mkdir()
    for relative in sorted(set(files) - {''}):
        source = root / relative
        if source.is_symlink():
            raise ValueError(f'symlink: {relative}')
        if not source.is_file():
            continue
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        inputs[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
    subprocess.run(['git', 'init', '-q', str(snapshot)], check=True)
    subprocess.run(['git', 'add', '.'], cwd=snapshot, check=True, capture_output=True)
    program = '''
from pathlib import Path
import json,time
from rcwh.workflow.agent_release import AgentRelease
from rcwh.generation.records import append_bytes,binding
from rcwh.candidate_reviews import canonical_bytes
root=Path.cwd();base='artifacts/agent_research/phase6/revisions-v2'
engine=AgentRelease(root);before=engine._stable_snapshot();started=time.monotonic()
report=engine.evaluate(base+'/release-evaluation/request-v1.json')
assert engine._stable_snapshot()==before
append_bytes(root,base+'/release-evaluation/report-v1.json',canonical_bytes(report))
append_bytes(root,base+'/release-evaluation/execution-v1.json',canonical_bytes({
 'schema_version':1,'kind':'ACTUAL_RELEASE_EVALUATE_EXECUTION','authority_effect':'NONE',
 'request':binding(root,base+'/release-evaluation/request-v1.json'),
 'report':binding(root,base+'/release-evaluation/report-v1.json'),'status':report['status'],
 'elapsed_seconds':round(time.monotonic()-started,3),'stable_snapshot_unchanged':True,
 'build_called':False,'execution_scope':'UNCHANGED_NORMAL_EVALUATOR_ON_BYTE_IDENTICAL_LINUX_SNAPSHOT',
 'literary_acceptance':'NOT_GRANTED','limitation':'Normal fresh author and input checks, no memoization or bypass. No build called; all FAIL/PENDING retained.'}))
print('evaluation status',report['status'],flush=True)
'''
    env = {**os.environ, 'PYTHONPATH': str(snapshot / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
    subprocess.run([sys.executable, '-u', '-c', program], cwd=snapshot, env=env, check=True)
    drift = [relative for relative, digest in inputs.items()
             if not (root / relative).is_file() or hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest]
    if drift:
        raise ValueError(f'input drift, no copyback: {drift}')
    for name in ('report-v1.json', 'execution-v1.json'):
        raw = (snapshot / base / 'release-evaluation' / name).read_bytes()
        with (output / name).open('xb') as target:
            target.write(raw)
        assert (output / name).read_bytes() == raw
    custody = {'schema_version': 1, 'kind': 'RELEASE_EVALUATION_SNAPSHOT_CUSTODY',
               'authority_effect': 'NONE', 'inputs': inputs, 'input_count': len(inputs),
               'changed_original_inputs': drift, 'snapshot_removed': True,
               'elapsed_seconds': round(time.monotonic()-started, 3),
               'output_hashes': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                 for name in ('report-v1.json', 'execution-v1.json')},
               'limitation': 'Same-byte normal evaluation only; no build or source/human/literary qualification.'}
    with (output / 'snapshot-custody-v1.json').open('x') as target:
        json.dump(custody, target, ensure_ascii=False, sort_keys=True, indent=2)
        target.write('\n')
print('Evaluation reports copied byte-exact; disposable snapshot removed.', flush=True)
