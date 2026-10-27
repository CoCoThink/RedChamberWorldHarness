"""Verify actual review custody and the real build, without granting literary credit."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import json
import subprocess

from core_evidence import validate_core
from rcwh.generation.records import binding, bound_bytes
from rcwh.workflow.review_campaign import status
from rcwh.workflow.release_packets import _write_immutable

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REQUEST = 'data/agent_release/research-81-100-v5/request.json'
PLAN = 'data/agent_release/research-81-100-v5/review-campaign-v1.json'


def load(path):
    return json.loads(path.read_bytes())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    current = status(R, PLAN)
    metadata = {j['id']: j for j in load(R / PLAN)['jobs']}
    baseline = load(O / 'campaign-baseline.json')
    fresh = {j['id'] for j in baseline['jobs'] if not j['reused']}
    assert len(current['jobs']) == 82 and len(fresh) == 22
    assert all(j['status'] == 'COMPLETE' and not j['needs_followup'] for j in current['jobs'])
    receipts = [load(path) for path in sorted(O.glob('registration-*.json'))]
    read = lines(O / 'coordinator-notes-read.jsonl')
    assert len(receipts) == len(read) == 22
    assert {r['job_id'] for r in receipts} == fresh
    assert {r['record']['sha256'] for r in receipts} == {r['record']['sha256'] for r in read}
    assert all(r['scope'] == 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR' and r['peer_credit'] is False for r in read)
    ci = load(O / 'input-ci.json')
    frozen = load(O / 'input-commit.json')
    assert ci['headSha'] == frozen['commit'] and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 2 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    completed = max(datetime.fromisoformat(j['completedAt'].replace('Z', '+00:00')) for j in ci['jobs'])
    launches = lines(O / 'launches.jsonl')
    assert {x['job_id'] for x in launches} == fresh
    assert len({(x['job_id'], x['attempt']) for x in launches}) == len(launches)
    assert len({x['task'] for x in launches}) == len(launches)
    assert all(x['fork_turns'] == 'none' and datetime.fromisoformat(x['observed_utc']) > completed for x in launches)
    failed = []
    for launch in launches:
        bound_bytes(R, launch['assignment'])
        event = load(R / current['attempt_directory'] / launch['job_id'] / f"attempt-{launch['attempt']}.json")
        assert event['assignment'] == launch['assignment']
        if event['status'] == 'FAILED':
            assert event['record'] is None and event['error'].strip()
            assert event['error'] in bound_bytes(R, event['stderr']).decode()
            failed.append({'job': launch['job_id'], 'attempt': launch['attempt'], 'error': event['error'], 'status_code': event['status_code']})
        else:
            assert event['status'] == 'REGISTERED'
            assert any(r['job_id'] == launch['job_id'] and r['record'] == event['record'] for r in receipts)
    assert len(launches) == len(receipts) + len(failed)
    new_results = []
    for receipt in receipts:
        record = json.loads(bound_bytes(R, receipt['record']))
        assert json.loads(bound_bytes(R, record['raw_output'])) == record['opinion']
        new_results.extend(record['opinion']['results'])
    seams = Counter()
    for job in current['jobs']:
        meta = metadata[job['id']]
        assert not meta['exceeds_budget'] and meta['reading_bytes'] <= 197 * 1024
        if meta['kind'] == 'BOOK':
            opinion = json.loads(bound_bytes(R, job['record']))['opinion']
            notes = '\n'.join(r['notes'] for r in opinion['results'])
            for left, right in meta['continuity']['seams']:
                assert f'{left}→{right}' in notes
                seams[(left, right)] += 1
    assert len(seams) == 19 and set(seams.values()) == {2}
    comparison = load(O / 'comparison/summary.json')
    assert comparison['status'] == 'COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS'
    assert set(comparison['votes']) == {'84', '87', '95', '97'}
    assert all(sum(v.values()) == 2 for v in comparison['votes'].values())
    comparison_launches = lines(O / 'comparison/launches.jsonl')
    comparison_read = lines(O / 'comparison/coordinator-read.jsonl')
    comparison_receipts = [load(p) for p in (O / 'comparison/receipts').glob('*.json')]
    assert len(comparison_launches) == len(comparison_read) == len(comparison_receipts) == 4
    assert all(x['fork_turns'] == 'none' and not x['P9_credit'] and datetime.fromisoformat(x['observed_utc']) > completed for x in comparison_launches)
    assert {x['opinion']['sha256'] for x in comparison_receipts} == {x['opinion']['sha256'] for x in comparison_read}
    assert not {x['task'] for x in comparison_launches} & {x['task'] for x in launches}
    ledger = load(O / 'coordinator-dispositions.json')
    prior = json.loads(bound_bytes(R, ledger['prior_ledger']))
    assert ledger['records'][:len(prior['records'])] == prior['records']
    assert ledger['issues'][:len(prior['issues'])] == prior['issues']
    assert ledger['counts']['new_v5_records'] == 22
    evidence = load(O / 'core-causal-rulings.json')
    core_pending = evidence['status'] == 'UNRESOLVED_RESEARCH_HANDOFF'
    core, core_unresolved = validate_core(R, O, unresolved_handoff=core_pending, chapters=ledger['chapters'])
    unresolved = {int(ch) for ch, ruling in ledger['chapters'].items() if ruling['outcome'] == 'PENDING'}
    assert core_unresolved <= unresolved
    pending = bool(unresolved)
    attempt = load(O / 'normal-build-attempt.json')
    report = load(O / 'final-release-evaluation.json')
    assert not report['findings'] and report['status'] in ['PASS', 'PENDING']
    assert attempt['allow_pending'] is False and '--allow-pending' not in attempt['command']
    directory = R / report['output']['directory']
    if pending:
        assert report['status'] == 'PENDING' and attempt['refused'] and attempt['exit_code'] != 0
        assert 'only explicit pending staging is allowed' in attempt['stdout'] + '\n' + attempt['stderr']
        assert not directory.exists()
    else:
        assert report['status'] == 'PASS' and not attempt['refused'] and attempt['exit_code'] == 0
        manifest = load(directory / 'manifest.json')
        assert manifest['status'] == 'PASS' and manifest['request_sha256'] == report['request_sha256']
        assert (directory / 'book.md').read_bytes() == (R / 'data/agent_release/research-81-100-v5/reading/book.md').read_bytes()
    assert {c['chapter'] for c in report['chapters'] if c['gates']['COORDINATOR_DECISION'] == 'PENDING'} == unresolved
    assert all(value == 'PASS' for c in report['chapters'] for name, value in c['gates'].items() if name != 'COORDINATOR_DECISION')
    request = load(R / REQUEST)
    before = json.loads(subprocess.check_output(['git', 'show', f"{frozen['commit']}:{REQUEST}"], cwd=R))
    assert before == {**request, 'chapters': [{k: v for k, v in row.items() if k != 'decision'} for row in request['chapters']]}
    old = load(R / 'data/agent_release/research-81-100-v4-r4/request.json')
    assert [a['chapter'] for a, b in zip(old['chapters'], request['chapters']) if a['candidate'] != b['candidate']] == [84, 87, 95, 97]
    preserved = ['data/world', 'data/scenes', 'data/provenance', 'sources', 'releases/stable', 'data/agent_release/research-81-100-v4-r4', 'data/agent_release/selection-81-100-v8.json']
    subprocess.run(['git', 'diff', '--exit-code', 'ed403cc', '--', *preserved], cwd=R, check=True, capture_output=True)
    result = {'status': 'PASS', 'scope': 'ACTUAL_V5_EXECUTION_CUSTODY_NOT_LITERARY_OR_HUMAN_PASS', 'input_commit': frozen['commit'], 'input_ci': {k: ci[k] for k in ['headSha', 'conclusion', 'url']}, 'current_jobs': 82, 'fresh_registered_records': 22, 'fresh_subject_results': len(new_results), 'fresh_negative_results': sum(r['verdict'] in ['FAIL', 'REJECT'] for r in new_results), 'transport_failures': failed, 'seams_each_read_twice': 19, 'comparison': comparison['votes'], 'core_status': core['status'], 'unresolved_chapters': sorted(unresolved), 'actual_normal_build_status': report['status'], 'release_status': report['status'], 'release_gates': dict(Counter(v for c in report['chapters'] for v in c['gates'].values())), 'all_history_counts': ledger['counts'], 'authority_effect': 'NONE', 'P9_credit': False}
    _write_immutable(R, (O / 'actual-execution-verification.json').relative_to(R).as_posix(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
