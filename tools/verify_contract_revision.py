"""Verify v6 contract custody, exact book reuse, and phase-specific evidence."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from rcwh.assets import AssetError
from rcwh.generation.records import bound_bytes
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.planning.contracts import inspect_contract
from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.attribution import release_attribution
from rcwh.workflow.release_packets import _write_immutable
from rcwh.workflow.review_campaign import status
from verify_agent_release import verify as verify_release

OLD = 'data/agent_release/research-81-100-v5/request.json'
BASE = 'data/agent_release/research-81-100-v6-r2'
REL = 'artifacts/agent_research/v6-contract-20261028'
DELIVERY = 'artifacts/agent_research/v6-review-20261029'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_core_evidence(root: Path) -> dict:
    """Require actual current two-reader evidence; preserve unchanged 92/93 proofs."""
    def load(path):
        return json.loads((root / path).read_bytes())
    core = load(DELIVERY + '/core-causal-rulings.json')
    prior = json.loads(bound_bytes(root, core['prior_core']))
    require(core['status'] == 'CLOSED_BY_ACTUAL_NEW_READER_EVIDENCE' and core['P9_credit'] is False,
            'unresolved core cannot authorize adoption')
    require([i['issue_id'] for i in core['issues']] == ['MARRIAGE_DECISION', 'DETENTION_CAUSE', 'VERSE_PLACEMENT'], 'missing core obligations')
    require(core['issues'][1:] == prior['issues'][1:], 'unchanged core evidence rewritten')
    current = {r['chapter']: r for r in load(BASE + '/request.json')['chapters']}
    registration = {json.loads(p.read_bytes())['record']['sha256'] for p in (root / DELIVERY).glob('registration-*.json')}
    read = {json.loads(s)['record']['sha256'] for s in (root / DELIVERY / 'coordinator-notes-read.jsonl').read_text().splitlines()}
    for issue, chapter in zip(core['issues'], (87, 92, 93), strict=True):
        require(issue['unresolved_same_gap'] is False, 'same core gap remains unresolved')
        readers, sessions = set(), set()
        for evidence in issue['fresh_formal_evidence']:
            ref = evidence['record']
            if chapter == 87:
                require(ref['sha256'] in registration & read, 'new core evidence not actually registered/root-read')
            record = json.loads(bound_bytes(root, ref))
            opinion = record['opinion']
            require(opinion['packet'] == current[chapter]['panel']['packet'], 'core opinion has stale packet')
            result = next(r for r in opinion['results'] if r['subject_id'] == evidence['subject_id'])
            require(result['verdict'] == 'PASS' or result['verdict'] == 'FAIL' and result.get('severity') == 'ADVISORY', 'incomplete/blocking core evidence')
            require(evidence['quote_from_notes'].strip() and evidence['quote_from_notes'] in result['notes'] and evidence['interpretation'].strip(), 'missing actual reader quotation')
            readers.add(opinion['reviewer']['id']); sessions.add(opinion['reviewer']['session_id'])
        require(len(readers) >= 2 and len(sessions) >= 2, 'two independent current core readers required')
    return core


def verify_reviewed_delivery(root: Path, request: dict, observed: dict, release: dict) -> dict:
    def load(path):
        return json.loads((root / path).read_bytes())
    require(release['release_status'] == 'PASS', 'reviewed delivery must independently pass release gates')
    require(len(observed['jobs']) == 82 and all(j['status'] == 'COMPLETE' and not j['needs_followup'] for j in observed['jobs']), 'actual review campaign incomplete')
    freeze = load(DELIVERY + '/input-commit.json'); ci = load(DELIVERY + '/input-ci.json')
    require(freeze['commit'] == ci['headSha'] == 'af22429cd437982c32565026d546a2397ecabd42', 'wrong input freeze/CI')
    require(ci['conclusion'] == 'success' and {j['name'] for j in ci['jobs']} == {'validate (3.12.3)', 'validate (3.12.13)'}
            and all(j['conclusion'] == 'success' for j in ci['jobs']), 'frozen input dual CI not successful')
    frozen = load(BASE + '/review-campaign-v1.json')['request']
    original = json.loads(bound_bytes(root, frozen))
    stripped = {**request, 'chapters': [{k: v for k, v in row.items() if k != 'decision'} for row in request['chapters']]}
    require(stripped == original and digest(canonical_bytes(original)) == freeze['request']['sha256'], 'reader inputs changed after freeze')
    historical = load(REL + '/verification.json')
    require(historical['release_status'] == 'PENDING' and historical['states'] == {'COMPLETE': 80, 'PENDING': 2}
            and historical['normal_build_refusal'] == 'agent release PENDING; only explicit pending staging is allowed', 'original pending evidence lost')
    ledger = load(DELIVERY + '/coordinator-dispositions.json')
    prior = json.loads(bound_bytes(root, ledger['prior_ledger']))
    require(ledger['records'][:len(prior['records'])] == prior['records'] and ledger['issues'][:len(prior['issues'])] == prior['issues'], 'historical record/disposition prefix changed')
    require(len(ledger['records']) == len(prior['records']) + 2, 'unexpected actual new opinion count')
    read = [json.loads(s) for s in (root / DELIVERY / 'coordinator-notes-read.jsonl').read_text().splitlines()]
    read_shas = {r['record']['sha256'] for r in read if r['scope'] == 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR' and r['peer_credit'] is False}
    launches = [json.loads(s) for s in (root / DELIVERY / 'launches.jsonl').read_text().splitlines()]
    require(len(launches) == 2 and len(read) == 2, 'unexpected launches or reading declarations')
    completion = max(datetime.fromisoformat(j['completedAt'].replace('Z', '+00:00')) for j in ci['jobs'])
    require(all(datetime.fromisoformat(x['observed_utc']) > completion and x['fork_turns'] == 'none' for x in launches), 'readers started before frozen CI')
    receipts = [json.loads(p.read_bytes()) for p in sorted((root / DELIVERY).glob('registration-*.json'))]
    require(len(receipts) == 2 and {x['record']['sha256'] for x in receipts} == read_shas, 'new opinions were not all actually root-read')
    new_refs = {x['record']['sha256'] for x in receipts}
    require(new_refs == {j['record']['sha256'] for j in observed['jobs'] if not j['reused']}, 'registered opinions not current campaign results')
    issues = {(i['record']['sha256'], i['subject_id']): i for i in ledger['issues']}
    for row in ledger['records']:
        record = json.loads(bound_bytes(root, row['record']))
        require(json.loads(bound_bytes(root, record['raw_output'])) == record['opinion'], 'original opinion rewritten')
        for result in record['opinion']['results']:
            if result['verdict'] in {'FAIL', 'REJECT'}:
                issue = issues.get((row['record']['sha256'], result['subject_id']))
                require(issue and issue['original_result'] == result and issue['rationale'].strip(), 'historical negative lost')
    verify_core_evidence(root)
    # Even with completed reviews, the original no-decision input cannot publish.
    runtime = AgentRelease(root)
    try:
        runtime.build(original)
    except AssetError as exc:
        require(str(exc) == 'agent release PENDING; only explicit pending staging is allowed', 'wrong frozen-input refusal')
    else:
        raise ValueError('original input without coordinator decisions was published')
    built = load(DELIVERY + '/normal-build-attempt.json')
    require(built['exit_code'] == 0 and built['allow_pending'] is False and built['release_status'] == 'PASS', 'actual normal build missing')
    manifest = load('releases/agent/research-81-100-v6-r2/manifest.json')
    require(manifest == json.loads(built['stdout']) and manifest['status'] == 'PASS', 'normal build/manifest mismatch')
    text = manifest['output']['text']
    require(bound_bytes(root, {'path': text['path'], 'sha256': text['sha256']}) == (root / (BASE + '/reading/book.md')).read_bytes(), 'published prose differs from bound reading book')
    return {'new_actual_records': 2, 'all_history_records': len(ledger['records']), 'core': 'CURRENT_TWO_READER_EVIDENCE',
            'frozen_no_decision_build': 'REFUSED_PENDING', 'normal_build': 'PASS_NO_ALLOW_PENDING', 'human_credit': False, 'P9_credit': False}


def verify(root: Path, *, expect_pending: bool = False, expect_reviewed: bool = False) -> dict:
    require(not (expect_pending and expect_reviewed), 'select one review phase')
    def load(path):
        return json.loads((root / path).read_bytes())
    request, old = load(BASE + '/request.json'), load(OLD)
    ledger = load(REL + '/contract-changes.json')
    design = json.loads(bound_bytes(root, ledger['design']))
    bound_bytes(root, design['plan'])
    require(design['baseline_request']['path'] == OLD, 'wrong previous edition')
    bound_bytes(root, design['baseline_request'])
    for ref in design['review_basis']:
        bound_bytes(root, ref)
    contracts = []
    for index, pair in enumerate(ledger['contracts']):
        before, after = (json.loads(bound_bytes(root, pair[k])) for k in ('previous', 'current'))
        reconstructed = deepcopy(before)
        changes = [c for c in ledger['changes'] if c['contract_id'] == before['id']]
        require(len({c['field'] for c in changes}) == len(changes), 'duplicate ledger field')
        for c in changes:
            require(reconstructed[c['field']] == c['before'], 'incorrect before value in ledger')
            reconstructed[c['field']] = c['after']
        require(reconstructed == after, 'unrecorded contract changes')
        permitted = {'revision', 'entry_from', 'function', 'unresolved', 'notes'}
        if index == 1:
            permitted.add('required_beats')
            require(len(before['required_beats']) == len(after['required_beats']), 'removed beat')
            for i, (a, b) in enumerate(zip(before['required_beats'], after['required_beats'], strict=True)):
                changed = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
                require(changed <= ({'description', 'editorial_override'} if i in (2, 3) else set()), 'lost beat evidence or unrelated requirement change')
        require({c['field'] for c in changes} <= permitted, 'changed state/evidence/forbidden obligations')
        if index:
            require(after['entry_from'] == ledger['contracts'][index - 1]['current']['path'], 'selected predecessor mismatch')
            require(after['entry_checkpoint'] == {'kind': 'UNKNOWN', 'chapter': None}, 'invented scene checkpoint')
        report = inspect_contract(root, after, pair['current']['path'], seed_ref=after['bindings']['seed']['path'], plan_ref=after['chapter_plan_ref'])
        require(all(tier['status'] != 'FAIL' for tier in (report['declared_compatibility'], report['deterministic_world_state_replay'])), 'contract integrity/state replay failed')
        require(report['prose_supported_semantic_replay']['status'] == 'NOT_CHECKED', 'technical check claimed prose verification')
        contracts.append({'contract': pair['current'], 'declared_compatibility': report['declared_compatibility']['status'],
                          'world_state_replay': report['deterministic_world_state_replay']['status'], 'prose_semantics': 'NOT_CHECKED'})
    require(len(contracts) == 5, 'expected exactly five alternate contracts')
    changed = []
    for a, b in zip(request['chapters'], old['chapters'], strict=True):
        require(a['chapter'] == b['chapter'] and a['candidate'] == b['candidate'], 'unexpected prose change')
        if a['panel'] != b['panel']:
            changed.append(a['chapter'])
        if a['chapter'] == 87:
            now, prior = release_attribution(root, a), release_attribution(root, b)
            require(now['contributors'] == prior['contributors'], 'custodian received author credit')
            require(now['receipt_chain'][:-1] == prior['receipt_chain'], 'lost prior receipts')
            require(now['prose_identical_to_previous'], 'false identical-prose disclosure')
    require(changed == [87], 'unrelated chapter packet changed')
    require(request['book_review'] == old['book_review'], 'not retaining actual original book packet')
    descriptor = load(BASE + '/reading/book-segments-v2.json')
    require(descriptor['packet'] == request['book_review']['packet'], 'reading index and request disagree')
    require((root / (BASE + '/reading/book.md')).read_bytes() == (root / 'data/agent_release/research-81-100-v5/reading/book.md').read_bytes(), 'assembled book changed')
    release = verify_release(root, BASE + '/request.json', BASE + '/review-campaign-v1.json')
    observed = status(root, BASE + '/review-campaign-v1.json')
    plan = load(BASE + '/review-campaign-v1.json')
    jobs = {j['id']: j for j in plan['jobs']}
    book = [j for j in observed['jobs'] if jobs[j['id']]['kind'] == 'BOOK']
    require(len(book) == 8 and all(j['status'] == 'COMPLETE' and j['reused'] for j in book), 'actual original continuity opinions not reused')
    seams = Counter(tuple(s) for j in book for s in jobs[j['id']]['continuity']['seams'])
    require(len(seams) == 19 and set(seams.values()) == {2}, 'seam coverage not double read')
    refusal = None
    if expect_pending:
        require(release['release_status'] == 'PENDING', 'unreviewed edition must be pending')
        fresh = [j for j in observed['jobs'] if not j['reused']]
        require(len(fresh) == 2 and all(j['status'] == 'PENDING' and jobs[j['id']]['chapter'] == 87 for j in fresh), 'unexpected fresh review completion/scope')
        require(not any('decision' in r for r in request['chapters']), 'input freeze must not invent coordinator decisions')
        try:
            AgentRelease(root).build(BASE + '/request.json')
        except AssetError as exc:
            refusal = str(exc)
        require(refusal == 'agent release PENDING; only explicit pending staging is allowed', 'normal build did not refuse unreviewed edition')
        require(not (root / 'releases/agent/research-81-100-v6-r2').exists(), 'pending edition published output')
    reviewed = verify_reviewed_delivery(root, request, observed, release) if expect_reviewed else None
    return {'status': 'PASS', 'scope': 'CONTRACT_CUSTODY_AND_BOOK_REUSE_NOT_PEER_ADMISSION',
        'release_status': release['release_status'], 'contracts': contracts,
        'states': dict(Counter(j['status'] for j in observed['jobs'])),
        'book_jobs_reused': len(book), 'double_read_seams': len(seams),
        'largest_reading_bytes': release['largest_reading_bytes'], 'normal_build_refusal': refusal,
        'prose_changed_chapters': [], 'reviewed_delivery': reviewed, 'authority_effect': 'NONE', 'human_credit': False, 'P9_credit': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expect-pending', action='store_true')
    parser.add_argument('--expect-reviewed', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify(root, expect_pending=args.expect_pending, expect_reviewed=args.expect_reviewed)
    if args.output:
        _write_immutable(root, args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
