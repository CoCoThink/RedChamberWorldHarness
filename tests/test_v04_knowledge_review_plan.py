import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prepare_v04_knowledge_review import BASE, EVIDENCE, JOBS, PROJECTION, ROOT, TOPICS, run
from verify_v04_knowledge_opinions import verify


def setup_repo(tmp_path):
    envelope = json.loads((ROOT / EVIDENCE).read_bytes())
    files = [EVIDENCE, PROJECTION, envelope['request']['path'],
             *(r['path'] for r in envelope['materials'].values()),
             'data/knowledge/v04_ch86.json', 'src/rcwh/knowledge.py',
             'src/rcwh/knowledge_versions.py', 'src/rcwh/generation/knowledge_projection.py']
    for name in files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    run(tmp_path, False)


def opinion(root, job):
    task = json.loads((root / BASE / 'dispatch' / f'{job}.json').read_bytes())
    result = json.loads((root / BASE / f'{job}.scaffold.json').read_bytes())
    result.update(reading_status='COMPLETE', overall_assessment='PENDING',
                  reviewer={'principal_id': job, 'session_id': job,
                            'identity_basis': 'NATIVE_TASK_LABEL_NOT_PROVIDER_VERIFIED'})
    result['declared_read_files'] = [{**r, 'bytes': (root / r['path']).stat().st_size,
                                     'read_complete': True} for r in task['read_inputs']]
    result['findings'] = [{'topic': topic, 'assessment': 'PENDING', 'reason': 'unresolved',
                           'citations': [{'path': task['read_inputs'][0]['path'], 'locator': 'instructions'}]}
                          for topic in TOPICS]
    return result


def save(root, job, value):
    path = root / BASE / 'opinions' / f'{job}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_review_records_remain_pending_and_validate_real_custody_fields(tmp_path):
    setup_repo(tmp_path)
    assert verify(tmp_path)['status'] == 'PENDING'
    first, second = (opinion(tmp_path, job) for job in JOBS)
    save(tmp_path, JOBS[0], first)
    assert verify(tmp_path)['registered_opinions'] == 1
    save(tmp_path, JOBS[1], second)
    result = verify(tmp_path)
    assert result['status'] == 'RECORDS_VALID'
    assert result['semantic_verdict'] == 'NOT_AUTOMATED'
    second['reviewer']['session_id'] = first['reviewer']['session_id']
    save(tmp_path, JOBS[1], second)
    with pytest.raises(ValueError, match='distinct identities'):
        verify(tmp_path)
    second['reviewer']['session_id'] = JOBS[1]
    second['findings'][0]['citations'][0]['quote'] = '不存在的引文'
    save(tmp_path, JOBS[1], second)
    with pytest.raises(ValueError, match='quote absent'):
        verify(tmp_path)


def test_candidate_citations_require_verbatim_text(tmp_path):
    setup_repo(tmp_path)
    record = opinion(tmp_path, JOBS[0])
    envelope = json.loads((tmp_path / EVIDENCE).read_bytes())
    candidate = envelope['materials']['candidate']['path']
    citation = {'path': candidate, 'locator': 'paragraph'}
    record['findings'][0]['citations'] = [citation]
    save(tmp_path, JOBS[0], record)
    with pytest.raises(ValueError, match='requires a verbatim quote'):
        verify(tmp_path)
    citation['quote'] = '不存在的引文'
    save(tmp_path, JOBS[0], record)
    with pytest.raises(ValueError, match='quote absent'):
        verify(tmp_path)
    citation['quote'] = (tmp_path / candidate).read_text(encoding='utf-8')[:20]
    save(tmp_path, JOBS[0], record)
    assert verify(tmp_path)['registered_opinions'] == 1
