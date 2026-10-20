"""Import one frozen editorial revision on a byte-identical Linux snapshot.

No custody checks are skipped. This is a computational staging convenience,
not a provider attestation or a proof of model input consumption.
"""
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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_revision(root: Path, text_path: str, request_path: str, *, session_id: str,
                    model_label: str, receipt_path: str) -> dict:
    from rcwh.assets.paths import repository_path
    from rcwh.candidate_reviews import canonical_bytes
    from rcwh.generation.records import append_bytes

    text = repository_path(root, text_path)
    request = repository_path(root, request_path)
    receipt = repository_path(root, receipt_path)
    if receipt.exists():
        raise FileExistsError(f'refusing to overwrite revision receipt: {receipt_path}')
    raw_text, raw_request = text.read_bytes(), request.read_bytes()
    prepared = json.loads(raw_request)
    if (prepared['context']['operation'] != 'revise'
            or prepared['context'].get('revision_template') != 'revise-v2'
            or prepared['parent'] is None or prepared['feedback'] is None):
        raise ValueError('revision import requires an actual revise-v2 parent and feedback')
    files = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root
    ).decode().split('\0')
    before = {}
    with tempfile.TemporaryDirectory(prefix='rcwh-revision-import-') as directory:
        snapshot = Path(directory) / 'repo'
        snapshot.mkdir()
        for relative in sorted(set(files) - {''}):
            source = repository_path(root, relative)
            if not source.is_file():
                continue
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            before[relative] = digest(destination)
        if text_path not in before or request_path not in before:
            raise ValueError('revision text/request absent from snapshot input set')
        if before[text_path] != hashlib.sha256(raw_text).hexdigest() or before[request_path] != hashlib.sha256(raw_request).hexdigest():
            raise ValueError('revision bytes changed while snapshot was captured')
        subprocess.run(['git', 'init', '-q', str(snapshot)], check=True)
        subprocess.run(['git', 'add', '.'], cwd=snapshot, check=True, capture_output=True)
        program = '''
import json
from pathlib import Path
from rcwh.generation.session import import_draft
root=Path.cwd()
result=import_draft(root,TEXT,REQUEST,session_id=SESSION,session_model_label=MODEL)
(root/'snapshot-import-result.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
'''
        program = (f'TEXT={text_path!r}\nREQUEST={request_path!r}\nSESSION={session_id!r}\nMODEL={model_label!r}\n' + program)
        env = {**os.environ, 'PYTHONPATH': str(snapshot / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([sys.executable, '-c', program], cwd=snapshot, env=env, check=True)
        result = json.loads((snapshot / 'snapshot-import-result.json').read_bytes())
        if result['status'] != 'PASS':
            raise ValueError('snapshot session import did not pass')
        changed = [relative for relative, value in before.items()
                   if not repository_path(root, relative).is_file() or digest(repository_path(root, relative)) != value]
        if changed:
            raise ValueError(f'original inputs changed during revision import: {changed}')
        products = {}
        for field in ('candidate', 'prepared_request', 'run', 'draft'):
            binding = result[field]
            path = repository_path(snapshot, binding['path'])
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != binding['sha256']:
                raise ValueError(f'snapshot import output hash mismatch: {field}')
            products[binding['path']] = raw
        if 'input_snapshot' in result:
            from rcwh.generation.snapshots import InputSnapshot
            frozen = InputSnapshot(snapshot, result['input_snapshot'])
            frozen.verify()
            refs = [result['input_snapshot'], *frozen.entries.values()]
            for ref in refs:
                products[ref['path']] = repository_path(snapshot, ref['path']).read_bytes()
        for relative, raw in products.items():
            path = repository_path(root, relative)
            if path.exists():
                if not path.is_file() or path.read_bytes() != raw:
                    raise ValueError(f'conflicting original revision output: {relative}')
        for relative, raw in products.items():
            path = repository_path(root, relative)
            if not path.exists():
                append_bytes(root, relative, raw)
            if path.read_bytes() != raw:
                raise ValueError(f'revision copyback byte mismatch: {relative}')
        record = {'schema_version': 1, 'kind': 'REVISION_IMPORT_SNAPSHOT_CUSTODY',
                  'status': 'PASS', 'authority_effect': 'NONE',
                  'scope': 'FRESH_SESSION_IMPORT_ON_BYTE_IDENTICAL_LINUX_SNAPSHOT',
                  'text': {'path': text_path, 'sha256': before[text_path]},
                  'request': {'path': request_path, 'sha256': before[request_path]},
                  'inputs': before, 'changed_original_inputs': changed, 'result': result,
                  'output_hashes': {path: hashlib.sha256(raw).hexdigest() for path, raw in products.items()},
                  'limitation': 'Custody only; length, literary quality, semantics and provider identity are not qualified.'}
        append_bytes(root, receipt_path, canonical_bytes(record))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--text', required=True)
    parser.add_argument('--request', required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--model-label', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    result = import_revision(args.root.resolve(), args.text, args.request,
                             session_id=args.session_id, model_label=args.model_label,
                             receipt_path=args.receipt)
    print(json.dumps({'status': result['status'], 'draft': result['draft'],
                      'candidate': result['candidate']}, ensure_ascii=False))
