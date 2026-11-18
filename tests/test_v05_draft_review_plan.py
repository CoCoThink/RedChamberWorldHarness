import hashlib
import json
import shutil
from pathlib import Path

import pytest

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


def test_package_preflights_all_outputs_and_recovers_after_interruption(tmp_path, monkeypatch):
    from rcwh.candidate_reviews import canonical_bytes
    from rcwh.workflow import knowledge_draft_review as draft_review

    docs = {'first.json': {'value': 1}, 'second.json': {'value': 2}}
    second = tmp_path / 'second.json'
    second.write_bytes(b'changed')
    with pytest.raises(ValueError, match='refusing to replace'):
        draft_review.publish(tmp_path, docs)
    assert not (tmp_path / 'first.json').exists()
    second.unlink()

    append = draft_review.append_bytes

    def interrupted(root, path, raw):
        if path == 'second.json':
            raise OSError('interrupted publication')
        return append(root, path, raw)

    monkeypatch.setattr(draft_review, 'append_bytes', interrupted)
    with pytest.raises(OSError, match='interrupted publication'):
        draft_review.publish(tmp_path, docs)
    assert (tmp_path / 'first.json').read_bytes() == canonical_bytes(docs['first.json'])
    monkeypatch.setattr(draft_review, 'append_bytes', append)
    assert draft_review.publish(tmp_path, docs)['status'] == 'PENDING'
    assert draft_review.publish(tmp_path, docs, check=True)['status'] == 'PENDING'


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
            'path': path.relative_to(tmp_path).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}})
    custody = tmp_path / BASE / 'opinions' / 'custody.json'
    custody.write_text(json.dumps({'kind': 'CH86_V05_DRAFT_REVIEW_CUSTODY',
        'basis': 'ORCHESTRATOR_RECORDED', 'attempts': attempts, 'production_admission': 'NOT_GRANTED'}))
    result = verify(tmp_path)
    assert result['custody'] == 'CONTEXT_DEVIATION'
    assert result['production_admission'] == 'NOT_GRANTED'
    (tmp_path / attempts[0]['opinion']['path']).write_text('{}')
    with pytest.raises(ValueError):
        verify(tmp_path)
