"""Verify v6 contract custody and exact book reuse without granting review credit."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from rcwh.assets import AssetError
from rcwh.generation.records import bound_bytes
from rcwh.planning.contracts import inspect_contract
from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.attribution import release_attribution
from rcwh.workflow.release_packets import _write_immutable
from rcwh.workflow.review_campaign import status
from verify_agent_release import verify as verify_release

OLD = 'data/agent_release/research-81-100-v5/request.json'
BASE = 'data/agent_release/research-81-100-v6-r2'
REL = 'artifacts/agent_research/v6-contract-20261028'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root: Path, *, expect_pending: bool = False) -> dict:
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
    return {'status': 'PASS', 'scope': 'CONTRACT_CUSTODY_AND_BOOK_REUSE_NOT_PEER_ADMISSION',
        'release_status': release['release_status'], 'contracts': contracts,
        'states': dict(Counter(j['status'] for j in observed['jobs'])),
        'book_jobs_reused': len(book), 'double_read_seams': len(seams),
        'largest_reading_bytes': release['largest_reading_bytes'], 'normal_build_refusal': refusal,
        'prose_changed_chapters': [], 'authority_effect': 'NONE', 'human_credit': False, 'P9_credit': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expect-pending', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify(root, expect_pending=args.expect_pending)
    if args.output:
        _write_immutable(root, args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
