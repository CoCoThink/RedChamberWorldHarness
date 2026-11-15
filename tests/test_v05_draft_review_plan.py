import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prepare_v05_draft_review import BASE, ROOT, documents, run
from verify_v05_draft_opinions import verify


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


def test_opinion_validation_fails_closed_and_checks_custody(tmp_path):
    docs = documents(ROOT)
    for ref in docs[f'{BASE}/dispatch/semantic-1.json']['read_inputs']:
        target = tmp_path / ref['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref['path'], target)
    run(tmp_path)
    assert verify(tmp_path)['status'] == 'PENDING'
    attempts = []
    for job in ('semantic-1', 'semantic-2'):
        dispatch = docs[f'{BASE}/dispatch/{job}.json']
        record = docs[f'{BASE}/{job}.scaffold.json']
        record.update(reading_status='COMPLETE', unread=[], overall_assessment='PENDING',
                      reviewer={'principal_id': job, 'session_id': job,
                                'identity_basis': 'NATIVE_TASK_LABEL_NOT_PROVIDER_VERIFIED'},
                      declared_read_files=[{**ref, 'bytes': (tmp_path / ref['path']).stat().st_size,
                                            'read_complete': True} for ref in dispatch['read_inputs']])
        for finding in record['findings']:
            finding.update(assessment='PENDING', reason='unresolved', citations=[{
                'path': dispatch['read_inputs'][0]['path'], 'locator': 'draft'}])
        path = tmp_path / BASE / 'opinions' / f'{job}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))
        attempts.append({'job_id': job, 'context_fork': 'all', 'opinion': {
            'path': str(path.relative_to(tmp_path)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}})
    custody = tmp_path / BASE / 'opinions' / 'custody.json'
    custody.write_text(json.dumps({'kind': 'CH86_V05_DRAFT_REVIEW_CUSTODY',
        'basis': 'ORCHESTRATOR_RECORDED', 'attempts': attempts, 'production_admission': 'NOT_GRANTED'}))
    result = verify(tmp_path)
    assert result['custody'] == 'CONTEXT_DEVIATION'
    assert result['production_admission'] == 'NOT_GRANTED'
    (tmp_path / attempts[0]['opinion']['path']).write_text('{}')
    with pytest.raises(ValueError):
        verify(tmp_path)
