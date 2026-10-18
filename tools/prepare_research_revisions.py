"""Prepare editorial revisions on a byte-identical disposable Linux snapshot.

Normal fresh request validation remains enabled. Only newly prepared request
bytes are copied back, after all snapshot input bytes are checked for drift.
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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root: Path, inventory_path: str, notes_directory: str, output_directory: str) -> None:
    from rcwh.assets.paths import repository_path
    from rcwh.candidate_reviews import canonical_bytes
    from rcwh.generation.records import append_bytes

    inventory_file = repository_path(root, inventory_path)
    inventory = json.loads(inventory_file.read_bytes())
    notes = repository_path(root, notes_directory)
    output = repository_path(root, output_directory)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite editorial revision requests: {output_directory}")
    rows = inventory['chapters']
    for row in rows:
        path = notes / f"notes-ch{row['chapter']}-v1.txt"
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"editorial notes unavailable: {path.name}")
    files = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root
    ).decode().split('\0')
    before = {}
    with tempfile.TemporaryDirectory(prefix='rcwh-editorial-preparation-') as directory:
        snapshot = Path(directory) / 'repo'
        snapshot.mkdir()
        for relative in sorted(set(files) - {''}):
            source = repository_path(root, relative)
            if not source.is_file():
                continue
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            before[relative] = sha(destination)
        subprocess.run(['git', 'init', '-q', str(snapshot)], check=True)
        subprocess.run(['git', 'add', '.'], cwd=snapshot, check=True, capture_output=True)
        # Run the snapshot's code, not an editable-install import of the original.
        program = '''
import json, time
from pathlib import Path
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding, bound_bytes, append_bytes
from rcwh.generation.session import prepare_request, prepared_request_integrity_report
root=Path.cwd()
inventory=json.loads((root/INVENTORY).read_bytes())
results=[]
for row in inventory['chapters']:
    ch=row['chapter']; started=time.monotonic()
    bound_bytes(root,row['draft']); bound_bytes(root,row['feedback'])
    notes=f'{NOTES}/notes-ch{ch}-v1.txt'
    packet=prepare_request(root,parent_path=row['draft']['path'],feedback_path=row['feedback']['path'],
                           notes_path=notes,revision_template='revise-v2',model='claude-opus-5-5')
    report=prepared_request_integrity_report(root,packet)
    ref=append_bytes(root,f'{OUTPUT}/ch{ch}.json',canonical_bytes(packet))
    results.append({'chapter':ch,'draft':row['draft'],'feedback':row['feedback'],'notes':binding(root,notes),
                    'request':ref,'integrity':report,'elapsed_seconds':round(time.monotonic()-started,3)})
    print(f'chapter {ch}: fresh integrity {report["status"]}',flush=True)
append_bytes(root,f'{OUTPUT}/preparation-report.json',canonical_bytes({
    'schema_version':1,'kind':'EDITORIAL_REVISION_PREPARATION','status':'PASS',
    'scope':'FRESH_RENDERER_ON_BYTE_IDENTICAL_LINUX_SNAPSHOT','authority_effect':'NONE',
    'chapters':results,'limitation':'Prepared custody only, not literary acceptance or input-consumption proof.'}))
'''
        program = (f'INVENTORY={inventory_path!r}\nNOTES={notes_directory!r}\nOUTPUT={output_directory!r}\n' + program)
        env = {**os.environ, 'PYTHONPATH': str(snapshot / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}
        subprocess.run([sys.executable, '-c', program], cwd=snapshot, env=env, check=True)
        drift = [relative for relative, value in before.items()
                 if not repository_path(root, relative).is_file() or sha(repository_path(root, relative)) != value]
        if drift:
            raise ValueError(f'original inputs changed during snapshot preparation: {drift}')
        products = sorted((snapshot / output_directory).glob('*.json'))
        if len(products) != len(rows) + 1:
            raise ValueError('snapshot revision output coverage mismatch')
        for path in products:
            append_bytes(root, path.relative_to(snapshot).as_posix(), path.read_bytes())
        copied = {path.name: sha(path) for path in products}
        if any(sha(output / name) != value for name, value in copied.items()):
            raise ValueError('copyback byte mismatch')
        append_bytes(root, f'{output_directory}/snapshot-custody.json', canonical_bytes({
            'schema_version': 1, 'scope': 'SNAPSHOT_INPUT_AND_COPYBACK_BYTE_IDENTITY',
            'status': 'PASS', 'input_files': len(before), 'inputs': before, 'output_hashes': copied,
            'changed_original_inputs': drift, 'authority_effect': 'NONE',
            'limitation': 'Same-byte snapshot computation, not model execution or literary acceptance.'}))
    print(f'Prepared {len(rows)} editorial revisions; snapshot removed.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--notes-directory', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    prepare(args.root.resolve(), args.inventory, args.notes_directory, args.output_directory)
