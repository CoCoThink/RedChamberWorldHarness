"""Adversarial tests of current evidence admission, using only tmp synthetic data."""
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('verify_contract_revision', TOOLS / 'verify_contract_revision.py')
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


def write(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_bytes(data))
    return binding(root, path)


@pytest.fixture
def evidence(tmp_path):
    """Minimal unit fixture, never stored in repository review registries."""
    issues, chapters, reads = [], [], []
    for chapter, name in zip((87, 92, 93), ('MARRIAGE_DECISION', 'DETENTION_CAUSE', 'VERSE_PLACEMENT'), strict=True):
        packet = {'path': f'packet-{chapter}', 'sha256': str(chapter)}
        chapters.append({'chapter': chapter, 'panel': {'packet': packet}})
        rows = []
        for reader in range(2):
            record = {'opinion': {'packet': packet, 'reviewer': {'id': f'r{reader}', 'session_id': f's{reader}'},
                'results': [{'subject_id': f'chapter-{chapter}', 'verdict': 'PASS', 'notes': 'Actual bounded finding.'}]}}
            ref = write(tmp_path, f'record-{chapter}-{reader}.json', record)
            rows.append({'record': ref, 'subject_id': f'chapter-{chapter}', 'quote_from_notes': 'bounded finding', 'interpretation': 'Narrow conclusion.'})
            if chapter == 87:
                write(tmp_path, GUARD.DELIVERY + f'/registration-{reader}.json', {'record': ref})
                reads.append({'record': ref})
        issues.append({'issue_id': name, 'unresolved_same_gap': False, 'fresh_formal_evidence': rows})
    prior = write(tmp_path, 'prior.json', {'issues': deepcopy(issues)})
    write(tmp_path, GUARD.BASE + '/request.json', {'chapters': chapters})
    log = tmp_path / GUARD.DELIVERY / 'coordinator-notes-read.jsonl'
    log.write_text(''.join(json.dumps(r) + '\n' for r in reads))
    core = {'status': 'CLOSED_BY_ACTUAL_NEW_READER_EVIDENCE', 'P9_credit': False, 'issues': issues, 'prior_core': prior}
    return tmp_path, core


def check(root, core):
    write(root, GUARD.DELIVERY + '/core-causal-rulings.json', core)
    return GUARD.verify_core_evidence(root)


def test_actual_current_independent_evidence_is_admitted(evidence):
    root, core = evidence
    assert check(root, core)['P9_credit'] is False


@pytest.mark.parametrize('fault, message', [
    ('unresolved', 'same core gap'),
    ('invented_quote', 'actual reader quotation'),
    ('stale_packet', 'stale packet'),
    ('same_reviewer', 'independent current core readers'),
    ('same_session', 'independent current core readers'),
    ('not_checked', 'incomplete/blocking'),
    ('blocking', 'incomplete/blocking'),
    ('unread', 'registered/root-read'),
    ('rewrite_retained_evidence', 'unchanged core evidence rewritten'),
])
def test_core_cannot_close_from_inadequate_evidence(evidence, fault, message):
    root, core = evidence
    issue = core['issues'][0]
    if fault == 'unresolved':
        issue['unresolved_same_gap'] = True
    elif fault == 'invented_quote':
        issue['fresh_formal_evidence'][0]['quote_from_notes'] = 'Not present in any opinion'
    elif fault == 'unread':
        (root / GUARD.DELIVERY / 'coordinator-notes-read.jsonl').write_text('')
    elif fault == 'rewrite_retained_evidence':
        core['issues'][1]['unresolved_same_gap'] = True
    else:
        item = issue['fresh_formal_evidence'][1]
        record = json.loads((root / item['record']['path']).read_bytes())
        opinion = record['opinion']
        if fault == 'stale_packet':
            opinion['packet']['sha256'] = 'previous packet'
        elif fault == 'same_reviewer':
            opinion['reviewer']['id'] = 'r0'
        elif fault == 'same_session':
            opinion['reviewer']['session_id'] = 's0'
        elif fault == 'not_checked':
            opinion['results'][0]['verdict'] = 'NOT_CHECKED'
        elif fault == 'blocking':
            opinion['results'][0].update(verdict='FAIL', severity='BLOCKING')
        item['record'] = write(root, item['record']['path'], record)
        write(root, GUARD.DELIVERY + '/registration-1.json', {'record': item['record']})
        log = root / GUARD.DELIVERY / 'coordinator-notes-read.jsonl'
        lines = [json.loads(s) for s in log.read_text().splitlines()]
        lines[1]['record'] = item['record']
        log.write_text(''.join(json.dumps(r) + '\n' for r in lines))
    with pytest.raises(ValueError, match=message):
        check(root, core)
