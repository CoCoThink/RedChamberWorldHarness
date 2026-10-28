"""Prepare the final contract-only request with verified whole-book reuse."""
from collections import Counter
from pathlib import Path
import json

from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.records import binding
from rcwh.workflow.release_packets import prepare, _write_immutable
from rcwh.workflow.review_campaign import plan, status

R = Path(__file__).resolve().parents[3]
REL = 'artifacts/agent_research/v6-contract-20261028/book-reuse'
BASE = 'data/agent_release/research-81-100-v6-r2'


def main():
    result = prepare(R, 'research-81-100-v6-r2', 'data/agent_release/selection-81-100-v10.json',
        list(range(81, 101)), coordinator_session_id='coordinator:release-v1',
        max_book_read_bytes=197 * 1024,
        reuse_request_path='data/agent_release/research-81-100-v5/request.json')
    _write_immutable(R, REL + '/prepare-output.json', result)
    planned = plan(R, BASE + '/request.json', BASE + '/review-campaign-v1.json',
                   batch_size=3, max_read_bytes=197 * 1024, max_attempts=3)
    _write_immutable(R, REL + '/campaign-plan.json', planned)
    observed = status(R, BASE + '/review-campaign-v1.json')
    _write_immutable(R, REL + '/campaign-baseline.json', observed)
    jobs = {j['id']: j for j in json.loads((R / (BASE + '/review-campaign-v1.json')).read_bytes())['jobs']}
    fresh = [j for j in observed['jobs'] if not j['reused']]
    if len(fresh) != 2 or any(jobs[j['id']]['kind'] != 'CHAPTER' or jobs[j['id']]['chapter'] != 87 or j['status'] != 'PENDING' for j in fresh):
        raise ValueError('expected exactly two new chapter-87 readers, without invented completion')
    summary = {'status': 'PREPARED_PENDING_TWO_INDEPENDENT_READERS',
        'request': binding(R, BASE + '/request.json'), 'plan': planned['plan'],
        'jobs': len(observed['jobs']), 'states': dict(Counter(j['status'] for j in observed['jobs'])),
        'fresh_jobs': [j['id'] for j in fresh], 'prose_changed_chapters': [],
        'book_jobs_reused': [j['id'] for j in observed['jobs'] if jobs[j['id']]['kind'] == 'BOOK' and j['reused']],
        'new_peer_opinions': 0, 'authority_effect': 'NONE'}
    _write_immutable(R, REL + '/preparation-summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    with rebuild_scope():
        main()
