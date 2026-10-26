"""Audit all actual v4 rounds, bounded contexts, retained dissent and refusal."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import json
import subprocess

from core_evidence import validate_core
from rcwh.generation.records import binding, bound_bytes
from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.review_campaign import status

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
N = R / 'artifacts/agent_research/v4-risk-revision-20261026'
EARLIER = R / 'artifacts/agent_research/v4-correction-20261026'
REQUEST = 'data/agent_release/research-81-100-v4-r4/request.json'
PLAN = 'data/agent_release/research-81-100-v4-r4/review-campaign-v1.json'


def load(path):
    return json.loads(path.read_bytes())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def phase(directory, expected_records, campaign=None):
    receipts = [load(path) for path in sorted(directory.glob('registration-*.json'))]
    assert len(receipts) == expected_records
    read = lines(directory / 'coordinator-notes-read.jsonl')
    assert len(read) == len(receipts)
    assert all(x['scope'] == 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR'
               and x['peer_credit'] is False for x in read)
    assert {x['record']['sha256'] for x in receipts} == {x['record']['sha256'] for x in read}
    ci = load(directory / 'input-ci.json')
    assert ci['conclusion'] == 'success' and len(ci['jobs']) == 2
    assert all(job['conclusion'] == 'success' for job in ci['jobs'])
    if (directory / 'input-commit.json').exists():
        assert ci['headSha'] == load(directory / 'input-commit.json')['commit']
    completed = max(datetime.fromisoformat(j['completedAt'].replace('Z', '+00:00')) for j in ci['jobs'])
    launches = lines(directory / 'launches.jsonl')
    assert all(x['fork_turns'] == 'none' and datetime.fromisoformat(x['observed_utc']) > completed for x in launches)
    assert len({x['task'] for x in launches}) == len(launches)
    results = []
    for receipt in receipts:
        record = json.loads(bound_bytes(R, receipt['record']))
        assert json.loads(bound_bytes(R, record['raw_output'])) == record['opinion']
        results.extend(record['opinion']['results'])
    failed = []
    if campaign is not None:
        fresh = {j['id'] for j in campaign['jobs'] if not j['reused']}
        assert {r['job_id'] for r in receipts} == fresh
        assert len(receipts) == len(fresh)
        assert {x['job_id'] for x in launches} == fresh
        assert len(launches) == sum(j['attempts'] for j in campaign['jobs'])
        assert len({(x['job_id'], x['attempt']) for x in launches}) == len(launches)
        for launch in launches:
            bound_bytes(R, launch['assignment'])
            event = load(R / campaign['attempt_directory'] / launch['job_id'] / f"attempt-{launch['attempt']}.json")
            assert event['assignment'] == launch['assignment'] and event['attempt'] == launch['attempt']
            if event['status'] == 'FAILED':
                assert event['record'] is None and event['status_code'] in {429, 500, 502, 503, 504}
                assert event['error'].strip() and event['error'] in bound_bytes(R, event['stderr']).decode()
                failed.append({'job': launch['job_id'], 'attempt': launch['attempt'],
                               'task': launch['task'], 'status_code': event['status_code'], 'error': event['error']})
            else:
                assert event['status'] == 'REGISTERED'
                assert any(x['job_id'] == launch['job_id'] and x['record'] == event['record'] for x in receipts)
        assert len(launches) == len(receipts) + len(failed)
    else:
        assert len(launches) == len(receipts)
    return {'directory': directory.relative_to(R).as_posix(), 'registered': len(receipts),
            'launches': len(launches), 'failed_transport_attempts': failed,
            'subject_results': len(results), 'input_ci': {k: ci[k] for k in ('headSha', 'conclusion', 'url')}}, receipts, launches, results


def main():
    current = status(R, PLAN)
    assert len(current['jobs']) == 76
    assert all(j['status'] == 'COMPLETE' and not j['needs_followup'] for j in current['jobs'])
    previous = status(R, 'data/agent_release/research-81-100-v4-r3/review-campaign-v1.json')
    assert len(previous['jobs']) == 74 and all(j['status'] == 'COMPLETE' for j in previous['jobs'])
    assert [j['id'] for j in previous['jobs'] if j['needs_followup']] == ['CHAPTER-92-029-r2']
    rounds = [phase(EARLIER, 7), phase(N, 17, previous), phase(O, 6, current)]
    all_tasks = [x['task'] for _, _, launches, _ in rounds for x in launches]
    assert len(all_tasks) == len(set(all_tasks))
    receipts = [x for _, rs, _, _ in rounds for x in rs]
    all_results = [x for _, _, _, results in rounds for x in results]
    metadata = {j['id']: j for j in load(R / PLAN)['jobs']}
    retained = {r['record']['sha256']: r for r in receipts}
    seams, book = Counter(), []
    for job in current['jobs']:
        if metadata[job['id']]['kind'] != 'BOOK':
            continue
        assert job['record']['sha256'] in retained
        record = json.loads(bound_bytes(R, job['record']))
        notes = '\n'.join(x['notes'] for x in record['opinion']['results'])
        assigned = metadata[job['id']]['continuity']['seams']
        for left, right in assigned:
            assert f'{left}→{right}' in notes
            seams[(left, right)] += 1
        book.append({'job': job['id'], 'record': job['record'], 'seams': assigned,
                     'verdicts': [x['verdict'] for x in record['opinion']['results']]})
    assert len(book) == 8 and len(seams) == 19 and set(seams.values()) == {2}

    comparison = load(N / 'comparison/summary.json')
    assert comparison['status'] == 'COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS' and comparison['P9_credit'] is False
    cl = lines(N / 'comparison/launches.jsonl')
    assert len(cl) == 4 and len({x['task'] for x in cl}) == 4
    assert not {x['task'] for x in cl} & set(all_tasks)
    old_ci = load(N / 'input-ci.json')
    old_completed = max(datetime.fromisoformat(j['completedAt'].replace('Z', '+00:00')) for j in old_ci['jobs'])
    assert all(x['fork_turns'] == 'none' and not x['P9_credit']
               and datetime.fromisoformat(x['observed_utc']) > old_completed for x in cl)
    cr = [load(p) for p in (N / 'comparison/receipts').glob('*.json')]
    cmp_read = lines(N / 'comparison/coordinator-read.jsonl')
    assert len(cr) == len(cmp_read) == 4
    assert {x['opinion']['sha256'] for x in cr} == {x['opinion']['sha256'] for x in cmp_read}
    for receipt in cr:
        bound_bytes(R, receipt['opinion'])

    ledger = load(O / 'coordinator-dispositions.json')
    assert ledger['comparison'] == binding(R, (N / 'comparison/summary.json').relative_to(R).as_posix())
    core, unresolved = validate_core(R, O, unresolved_handoff=True, chapters=ledger['chapters'])
    assert unresolved == {87}
    report = AgentRelease(R).evaluate(REQUEST)
    assert report['status'] == 'PENDING' and not report['findings'] and len(report['chapters']) == 20
    assert {c['chapter'] for c in report['chapters'] if c['gates']['COORDINATOR_DECISION'] == 'PENDING'} == unresolved
    assert all(v == 'PASS' for c in report['chapters'] for name, v in c['gates'].items() if name != 'COORDINATOR_DECISION')
    gates = Counter(v for c in report['chapters'] for v in c['gates'].values())
    assert gates == {'PASS': 239, 'PENDING': 1}
    refusal = load(O / 'normal-build-attempt.json')
    assert refusal['refused'] and not refusal['allow_pending'] and refusal['exit_code'] != 0
    assert 'only explicit pending staging is allowed' in refusal['stdout'] + '\n' + refusal['stderr']
    assert not (R / report['output']['directory']).exists()
    assert not (R / 'releases/agent/research-81-100-v4-r4').exists()

    request = load(R / REQUEST)
    frozen = json.loads(subprocess.check_output(['git', 'show', f"{load(O / 'input-commit.json')['commit']}:{REQUEST}"], cwd=R))
    without_decisions = {**request, 'chapters': [{k: v for k, v in row.items() if k != 'decision'} for row in request['chapters']]}
    assert frozen == without_decisions
    old_request = load(R / 'data/agent_release/research-81-100-v4-r3/request.json')
    for old, new in zip(old_request['chapters'], request['chapters']):
        assert old['candidate'] == new['candidate'] and old['draft'] == new['draft'] and old['writing_package'] == new['writing_package']
        if old['chapter'] != 92:
            assert old['panel'] == new['panel']
    assert old_request['book_review'] == request['book_review']
    old_unread = json.loads(bound_bytes(R, load(N / 'registration-005.json')['record']))
    assert next(x for x in old_unread['opinion']['results'] if x['subject_id'] == 'contract-92-6')['verdict'] == 'NOT_CHECKED'
    row92 = next(x for x in request['chapters'] if x['chapter'] == 92)
    row93 = next(x for x in request['chapters'] if x['chapter'] == 93)
    assert row92['review_context_chapters'] == {'contract-92-6': [93]}
    for job in metadata.values():
        assert job['reading_bytes'] <= load(R / PLAN)['max_read_bytes'] and not job['exceeds_budget']
        if job['chapter'] == 92 and 'contract-92-6' in job['subjects']:
            assert row93['candidate'] in job['read_in_full']

    preserved = ['data/world', 'data/scenes', 'data/provenance', 'sources', 'releases/stable',
                 *[f'releases/agent/research-81-100-v{i}' for i in (1, 2, 3)],
                 *[f'data/agent_release/research-81-100-v{i}' for i in (1, 2, 3)],
                 'data/agent_release/selection-81-100-v4.json']
    subprocess.run(['git', 'diff', '--exit-code', '29a81d5', '--', *preserved], cwd=R, check=True, capture_output=True)
    changes = subprocess.check_output(['git', 'diff', '--name-status', '29a81d5', '--', 'data/planning'], cwd=R, text=True).splitlines()
    assert set(changes) == {'A\tdata/planning/contracts/agent-final-v1/92-S6.v3.json', 'A\tdata/planning/contracts/agent-final-v1/93-S2.v3.json'}
    negatives = [x for x in all_results if x['verdict'] in ('FAIL', 'REJECT')]
    result = {'status': 'PASS', 'scope': 'ACTUAL_EXECUTION_CUSTODY_AND_UNRESOLVED_HANDOFF_NOT_LITERARY_PASS',
              'rounds': [x[0] for x in rounds], 'current_jobs': 76,
              'reused_current_jobs': sum(j['reused'] for j in current['jobs']),
              'new_v4_records_all_rounds': len(receipts), 'new_v4_subject_results': len(all_results),
              'new_negative_results': len(negatives), 'negative_severity': dict(Counter(x.get('severity', 'BLOCKING') for x in negatives)),
              'book_readers': book, 'unique_seams': 19, 'reader_seam_notes': sum(seams.values()),
              'comparison_readers': 4, 'comparison_votes': comparison['votes'],
              'core_status': core['status'], 'release_status': report['status'], 'unresolved_chapters': [87],
              'release_gates': dict(gates), 'request': binding(R, REQUEST),
              'evaluation': binding(R, (O / 'final-release-evaluation.json').relative_to(R).as_posix()),
              'reading_book': binding(R, 'data/agent_release/research-81-100-v4-r3/reading/book.md'),
              'published_book': None, 'published_manifest': None, 'preserved_trees': preserved,
              'resource_parity': 'NOT_VERIFIED', 'reading_declarations': 'DECLARED_NOT_MACHINE_PROOF',
              'P9_credit': False, 'authority_effect': 'NONE'}
    target = O / 'actual-execution-verification.json'
    assert not target.exists()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('book_readers', 'comparison_votes')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
