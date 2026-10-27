"""Freeze selected prose and explicit neighbouring candidates for fresh review."""
from collections import Counter
from pathlib import Path
import json
from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.records import binding
from rcwh.workflow.release_packets import prepare, _write_immutable
from rcwh.workflow.review_campaign import plan, status

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REL = O.relative_to(R).as_posix()
REQUEST = 'data/agent_release/research-81-100-v5/request.json'
PLAN = 'data/agent_release/research-81-100-v5/review-campaign-v1.json'


def main():
    result = prepare(R, 'research-81-100-v5', 'data/agent_release/selection-81-100-v9.json', list(range(81, 101)), coordinator_session_id='coordinator:release-v1', max_book_read_bytes=197 * 1024, reuse_request_path='data/agent_release/research-81-100-v4-r4/request.json')
    _write_immutable(R, REL + '/prepare-output.json', result)
    result = plan(R, REQUEST, PLAN, batch_size=3, max_read_bytes=197 * 1024, max_attempts=3)
    _write_immutable(R, REL + '/campaign-plan.json', result)
    s = status(R, PLAN)
    _write_immutable(R, REL + '/campaign-baseline.json', s)
    document = json.loads((R / PLAN).read_bytes())
    assert all(j['reading_bytes'] <= 197 * 1024 and not j['exceeds_budget'] for j in document['jobs'])
    request = json.loads((R / REQUEST).read_bytes())
    old = json.loads((R / 'data/agent_release/research-81-100-v4-r4/request.json').read_bytes())
    changed_packets = [a['chapter'] for a, b in zip(request['chapters'], old['chapters']) if a['panel'] != b['panel']]
    assert changed_packets == [84, 87, 95, 97]
    for ch, subjects in [(84, ['chapter-84', 'contract-84-3']), (87, ['chapter-87', 'contract-87-1', 'contract-87-3']), (95, ['chapter-95']), (97, ['chapter-97', 'contract-97-1']), (92, ['contract-92-6'])]:
        row = next(row for row in request['chapters'] if row['chapter'] == ch)
        for sid in subjects:
            dependencies = row['review_context_chapters'][sid]
            refs = [next(r for r in request['chapters'] if r['chapter'] == c)['candidate'] for c in dependencies]
            jobs = [j for j in document['jobs'] if j['chapter'] == ch and sid in j['subjects']]
            assert len(jobs) == 2 and all(all(ref in j['read_in_full'] for ref in refs) for j in jobs)
    report = {'status': 'INPUT_PREPARED_NOT_REVIEWED', 'request': binding(R, REQUEST), 'plan': binding(R, PLAN), 'states': dict(Counter(j['status'] for j in s['jobs'])), 'jobs': len(s['jobs']), 'fresh_jobs': [j['id'] for j in s['jobs'] if not j['reused']], 'changed_packets': changed_packets, 'max_reading_bytes': max(j['reading_bytes'] for j in document['jobs']), 'budget_unit': 'UTF8_BYTES_NOT_MEASURED_TOKENS', 'authority_effect': 'NONE'}
    _write_immutable(R, REL + '/preparation-summary.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    with rebuild_scope():
        main()
