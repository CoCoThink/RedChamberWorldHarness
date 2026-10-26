"""Adversarial guard tests. Synthetic fixtures live only in pytest tmp_path."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core_evidence import validate_core
from rcwh.generation.records import binding


def fixture(root):
    current = root / 'execution'
    current.mkdir()
    refs = []
    for i in range(2):
        path = root / f'synthetic-{i}.json'
        path.write_text(json.dumps({'opinion': {
            'reviewer': {'id': f'SYNTHETIC-TEST-{i}'},
            'results': [{'subject_id': 'test-only', 'verdict': 'FAIL',
                         'severity': 'ADVISORY', 'notes': 'SYNTHETIC evidence: unresolved.'}]}}))
        ref = binding(root, path.name)
        refs.append(ref)
        (current / f'registration-{i:03d}.json').write_text(json.dumps({'record': ref}))
    (current / 'coordinator-notes-read.jsonl').write_text(''.join(json.dumps({
        'record': ref, 'scope': 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR'}) + '\n'
        for ref in refs))
    core = {'status': 'UNRESOLVED_RESEARCH_HANDOFF', 'issues': [
        {'issue_id': issue, 'unresolved_same_gap': issue == 'MARRIAGE_DECISION',
         'fresh_formal_evidence': [{'record': ref, 'subject_id': 'test-only',
             'quote_from_notes': 'SYNTHETIC evidence', 'interpretation': 'TEST ONLY'} for ref in refs]}
        for issue in ('MARRIAGE_DECISION', 'DETENTION_CAUSE', 'VERSE_PLACEMENT')]}
    save(current, core)
    return current, core


def save(current, core):
    (current / 'core-causal-rulings.json').write_text(json.dumps(core))


def test_unresolved_cannot_enter_normal_closure(tmp_path):
    current, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match='no coordinator override'):
        validate_core(tmp_path, current)


def test_explicit_handoff_still_forbids_adoption(tmp_path):
    current, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match='adoption forbidden'):
        validate_core(tmp_path, current, unresolved_handoff=True, chapters={'87': {'outcome': 'ADOPT'}})
    _, unresolved = validate_core(tmp_path, current, unresolved_handoff=True,
                                  chapters={'87': {'outcome': 'PENDING'}})
    assert unresolved == {87}


def test_two_citations_from_one_reader_are_insufficient(tmp_path):
    current, core = fixture(tmp_path)
    core['issues'][0]['fresh_formal_evidence'][1] = core['issues'][0]['fresh_formal_evidence'][0]
    save(current, core)
    with pytest.raises(ValueError, match='two distinct'):
        validate_core(tmp_path, current, unresolved_handoff=True)


def test_unread_record_cannot_close_core(tmp_path):
    current, _ = fixture(tmp_path)
    (current / 'coordinator-notes-read.jsonl').write_text('')
    with pytest.raises(ValueError, match='root-read'):
        validate_core(tmp_path, current, unresolved_handoff=True)


def test_paraphrase_cannot_replace_actual_reader_quote(tmp_path):
    current, core = fixture(tmp_path)
    core['issues'][0]['fresh_formal_evidence'][0]['quote_from_notes'] = 'fabricated quote'
    save(current, core)
    with pytest.raises(ValueError, match='exact reader quotation'):
        validate_core(tmp_path, current, unresolved_handoff=True)


def test_pending_route_cannot_mislabel_all_closed(tmp_path):
    current, core = fixture(tmp_path)
    for issue in core['issues']:
        issue['unresolved_same_gap'] = False
    save(current, core)
    with pytest.raises(ValueError, match='actual unresolved'):
        validate_core(tmp_path, current, unresolved_handoff=True)
