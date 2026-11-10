"""Check real trial custody, revision ancestry and bounded undispatched packets.

This never certifies prose semantics or counts author observations as reviews.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy

from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.lineage import current_compatibility
from rcwh.generation.records import bound_bytes
from rcwh.generation.writing import load_draft


ROOT = Path(__file__).resolve().parents[2]
BASE = Path('artifacts/local-trial-ch86-20261110')


def read(path):
    return json.loads((ROOT / path).read_bytes())


def verify():
    first = read(BASE / 'import.json')
    revised = read(BASE / 'import-v3.json')
    with rebuild_scope():
        draft, text = load_draft(ROOT, revised['draft']['path'])
        assert draft['parent'] == first['draft']
        assert draft['feedback']['path'] == str(BASE / 'local-revision-feedback-v3.json')
        assert text.encode() == (ROOT / BASE / 'ch86-authored-v3.txt').read_bytes()
        assert all(a['principal_id'] == 'session:main-agent:ch86-local-trial:20261110'
                   for a in draft['authors'])
        assert not draft['formal_eligibility'] and draft['qualification'] == 'RESEARCH_ONLY'
        compatibility = current_compatibility(ROOT, revised['draft']['path'])
        assert compatibility['status'] == 'PASS', compatibility
    request = json.loads(bound_bytes(ROOT, draft['prepared_request']))
    assert request['parent'] == first['draft']
    assert request['byte_admission']['status'] == 'PASS'
    assert len(text.encode()) <= request['context']['context_limits']['output_reserve_bytes']
    assert not any(r['path'] == 'data/project/closure_roots.json' for r in draft['inputs'])
    assert read(BASE / 'revision-budget-rejection.json')['admission']['status'] == 'FAIL'
    audit = read(BASE / 'author-selfcheck-v3.json')
    assert audit['candidate'] == draft['candidate']
    assert audit['independent_opinions'] == 0 and not audit['formal_eligibility']
    assert audit['independence'] == 'SAME_AUTHOR_NOT_INDEPENDENT'
    ledger_ref = audit['paragraph_ledger']
    ledger_raw = (ROOT / ledger_ref['path']).read_bytes()
    assert hashlib.sha256(ledger_raw).hexdigest() == ledger_ref['sha256']
    ledger = json.loads(ledger_raw)
    assert ledger['candidate'] == draft['candidate']
    assert '\n\n'.join(p['quote'] for p in ledger['paragraphs']) + '\n' == text
    paragraphs = {p['id'] for p in ledger['paragraphs']}
    for p in ledger['paragraphs']:
        start, end = p['byte_range']
        raw = text.encode()[start:end]
        assert raw.decode() == p['quote'] and hashlib.sha256(raw).hexdigest() == p['sha256']
    scenario = read('data/writing/local-scenarios/ch86-v1/scenario.json')
    assert {e['event'] for e in audit['events']} == {e['id'] for e in scenario['events']}
    assert {m['id'] for m in audit['messages']} == {m['id'] for m in scenario['messages']}
    expected = set()
    for ref in scenario['contracts']:
        contract = json.loads(bound_bytes(ROOT, ref))
        for key in ('required_beats', 'forbidden_beats'):
            expected.update((ref['path'], key, i) for i in range(1, len(contract[key]) + 1))
    assert {(o['contract'], o['type'], o['ordinal']) for o in audit['obligations']} == expected
    for item in [*audit['events'], *audit['obligations']]:
        assert set(item['paragraph_refs']) <= paragraphs
    prepare = runpy.run_path(str(ROOT / BASE / 'prepare_review.py'))['prepare']
    packets = prepare(check=True)
    manifest = read(BASE / 'review-v3/manifest.json')
    assert manifest['candidate']['sha256'] == draft['candidate']['sha256']
    assert len(manifest['tasks']) == 4 and manifest['independent_opinions'] == 0
    for task in manifest['tasks']:
        assert task['status'] == 'NOT_STARTED'
        if task['role'] == 'BLIND_LITERARY':
            assert {r['path'] for r in task['read_inputs']} == {
                str(BASE / f"review-v3/{task['id']}.md"), draft['candidate']['path'], task['scaffold']}
    return {'status': 'PASS', 'scope': 'CUSTODY_CURRENT_COMPATIBILITY_AND_REVIEW_PACKET_BYTES_ONLY',
            'candidate': draft['candidate'], 'draft': revised['draft'],
            'current_compatibility': compatibility,
            'paragraphs': len(paragraphs), 'event_mapping_coverage': len(audit['events']),
            'message_mapping_coverage': len(audit['messages']),
            'obligation_mapping_coverage': len(expected), 'packets': packets,
            'semantic_status': 'PENDING', 'literary_status': 'PENDING',
            'independent_opinions': 0, 'production_admission': 'NOT_GRANTED',
            'authority_effect': 'NONE'}


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
