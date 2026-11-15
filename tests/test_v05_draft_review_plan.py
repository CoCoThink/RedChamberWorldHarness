import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prepare_v05_draft_review import BASE, ROOT, documents, run


def test_package_is_reproducible_and_binds_inputs(tmp_path):
    docs = documents(ROOT)
    dispatch = docs[f'{BASE}/dispatch/semantic-1.json']
    for ref in dispatch['read_inputs']:
        source = ROOT / ref['path']
        target = tmp_path / ref['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == ref['sha256']
    assert run(tmp_path)['production_admission'] == 'NOT_GRANTED'
    assert run(tmp_path, check=True)['status'] == 'PENDING'
    assert documents(tmp_path) == docs
    (tmp_path / dispatch['read_inputs'][0]['path']).write_text('{}')
    with pytest.raises(ValueError, match='draft differs'):
        run(tmp_path, check=True)


def test_package_refuses_modified_existing_records(tmp_path):
    docs = documents(ROOT)
    for ref in docs[f'{BASE}/dispatch/semantic-1.json']['read_inputs']:
        target = tmp_path / ref['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref['path'], target)
    run(tmp_path)
    target = tmp_path / BASE / 'semantic-1.scaffold.json'
    target.write_text(json.dumps({'changed': True}))
    with pytest.raises(ValueError, match='refusing to replace'):
        run(tmp_path)
    assert json.loads(target.read_text()) == {'changed': True}
