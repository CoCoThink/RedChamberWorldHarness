import hashlib
import json
import shutil
from pathlib import Path

import pytest

from prepare_v06_draft_review import BASE, ROOT, documents, run
from verify_v06_draft_opinions import verify


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
            'path': path.relative_to(tmp_path).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}})
    custody = tmp_path / BASE / 'opinions' / 'custody.json'
    custody.write_text(json.dumps({'kind': 'CH86_V06_DRAFT_REVIEW_CUSTODY',
        'basis': 'ORCHESTRATOR_RECORDED', 'attempts': attempts, 'production_admission': 'NOT_GRANTED'}))
    result = verify(tmp_path)
    assert result['custody'] == 'CONTEXT_DEVIATION'
    assert result['production_admission'] == 'NOT_GRANTED'
    assert result['reviewer_assessments']['semantic-1']['overall'] == 'PENDING'
    assert result['coordinator_decision'] == 'NOT_RECORDED'
    (tmp_path / attempts[0]['opinion']['path']).write_text('{}')
    with pytest.raises(ValueError):
        verify(tmp_path)


@pytest.fixture
def submitted_review(tmp_path):
    docs = documents(ROOT)
    paths = {ref['path'] for ref in docs[f'{BASE}/dispatch/semantic-1.json']['read_inputs']}
    paths.update(docs)
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / BASE / 'opinions').glob('*.json'))
    paths.add(f'{BASE}/disposition.json')
    paths.update(f'.codex-dispatch/rcwh_ticket_v06_semantic_{i}.md' for i in (1, 2))
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    return tmp_path


def test_qualified_closeout_does_not_grant_legacy_or_production_admission(submitted_review):
    result = verify(submitted_review)
    assert result['custody'] == 'CONTEXT_MATCHES_PLAN'
    assert result['coordinator_decision'] == 'ACCEPT_FOR_RESEARCH_WITH_LIMITS'
    assert result['semantic_verdict'] == 'NOT_AUTOMATED'
    assert result['production_admission'] == 'NOT_GRANTED'


@pytest.mark.parametrize('field,value', [
    ('legacy_c1', 'PASS'), ('production_admission', 'GRANTED'),
    ('strict_understanding', 'ESTABLISHED'), ('limitations', []),
    ('recorded_assessments', {'semantic-1': 'FAIL', 'semantic-2': 'PASS'}),
])
def test_closeout_rejects_expanded_claims(submitted_review, field, value):
    path = submitted_review / BASE / 'disposition.json'
    doc = json.loads(path.read_bytes())
    doc[field] = value
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        verify(submitted_review)


def test_closeout_preserves_qualified_reason_and_exact_draft(submitted_review):
    path = submitted_review / BASE / 'disposition.json'
    raw = path.read_bytes()
    doc = json.loads(raw)
    doc['limitations'][0]['reviewer_reason'] = 'An unconditional pass'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='original reason'):
        verify(submitted_review)
    path.write_bytes(raw)
    draft = submitted_review / doc['draft']['path']
    draft.write_bytes(draft.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='draft differs'):
        verify(submitted_review)
