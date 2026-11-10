"""Verify this native review's custody and coverage, never prose correctness.

Read completion and fresh-context isolation remain self-reported. Original
preparation snapshots retain NOT_STARTED; execution.json owns actual progress.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('artifacts/local-trial-review-20261111')
INPUT_COMMIT = '642540275628ebcccfaab758cf5d9701a7c5ad16'
PLAN_SHA = 'cf6ee9e4eca1f2d59f1c15fc4b99db4485403bf2a0bbda92b5d2b42902f441f0'
ASSESSMENTS = {'PASS', 'PENDING', 'FAIL'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bound(ref, root=ROOT):
    path = (root / ref['path']).resolve()
    require(path.is_relative_to(root.resolve()), 'reference escapes repository')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ref['sha256'], f"changed bytes: {ref['path']}")
    if 'bytes' in ref:
        require(len(raw) == ref['bytes'], f"changed size: {ref['path']}")
    return raw


def research_only(record):
    require(record['qualification'] == 'RESEARCH_ONLY', 'research qualification changed')
    require(record['formal_eligibility'] is False, 'formal eligibility granted')
    require(record['authority_effect'] == 'NONE', 'authority effect granted')


def validate_opinion(opinion, task, agent, candidate, expected, paragraph_count):
    """Validate declared scope, not actual model consumption or literary verdict."""
    require(opinion['job_id'] == task['id'], 'wrong review task')
    require(opinion['candidate'] == {k: candidate[k] for k in ('path', 'sha256')}, 'wrong candidate')
    require(set(opinion['reviewer']) == {'principal_id', 'session_id'}, 'reviewer identity missing')
    require(all(v == agent for v in opinion['reviewer'].values()), 'reviewer identity mismatch')
    require(opinion['status'] == opinion['reading_status'] == 'COMPLETE', 'incomplete opinion')
    declared = opinion['declared_read_files']
    require(len(declared) == len(task['read_inputs']), 'missing/extra read declaration')
    require(all(r['read_complete'] is True for r in declared), 'unread assigned input')
    require(sorted(({k: r[k] for k in ('path', 'sha256', 'bytes')} for r in declared), key=lambda r: r['path'])
            == sorted(task['read_inputs'], key=lambda r: r['path']), 'read declaration binding mismatch')
    require(bool(opinion['unread_files']), 'unassigned scope not disclosed')
    require(opinion['overall_assessment'] in ASSESSMENTS, 'invalid overall assessment')
    research_only(opinion)
    obligations = opinion['obligation_findings']
    actual = [(o['contract_id'], o['type'], o['ordinal']) for o in obligations]
    require(len(actual) == len(set(actual)) and set(actual) == expected, 'contract obligation coverage mismatch')
    require(set(opinion['assigned_contracts']) == {o[0] for o in expected}, 'assigned contracts mismatch')
    ids = [f['id'] for f in opinion['findings']]
    require(len(ids) == len(set(ids)), 'duplicate finding id')
    for finding in opinion['findings']:
        require(finding['severity'] in {'ADVISORY', 'BLOCKING'}, 'invalid severity')
        require(bool(finding['suggestion']), 'missing finding suggestion')
    for item in [*opinion['findings'], *obligations, *opinion['event_and_message_findings']]:
        require(item['assessment'] in ASSESSMENTS and bool(item['reason']) and bool(item['quote']), 'missing review evidence')
        paragraphs = item.get('paragraphs', [])
        require(all(type(p) is int and 1 <= p <= paragraph_count for p in paragraphs), 'paragraph out of range')
        if item in opinion['findings'] or item in obligations:
            require(bool(paragraphs), 'paragraph evidence missing')
    if task['role'] == 'BLIND_LITERARY':
        require(not opinion['event_and_message_findings'], 'blind reader asserts model coverage')


def verify(root=ROOT):
    execution = json.loads((root / BASE / 'execution.json').read_bytes())
    require(execution['input_commit'] == INPUT_COMMIT, 'wrong review baseline')
    require(execution['selected_plan_binding']['sha256'] == PLAN_SHA, 'preparation snapshot changed')
    plan = json.loads(bound(execution['selected_plan_binding'], root))
    require(execution['selected_plan'] == execution['selected_plan_binding']['path'], 'wrong selected plan')
    ci = json.loads(bound(execution['input_ci_binding'], root))
    require(execution['input_ci'] == execution['input_ci_binding']['path'], 'wrong CI receipt')
    require(ci['headSha'] == INPUT_COMMIT and ci['conclusion'] == 'success', 'input CI not successful')
    jobs = {j['name']: j for j in ci['jobs']}
    require(set(jobs) == {'validate (3.12.3)', 'validate (3.12.13)'}, 'missing CI matrix job')
    require(all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs.values()), 'CI job not successful')
    ci_finished = max(datetime.fromisoformat(j['completedAt'].replace('Z', '+00:00')) for j in jobs.values())
    research_only(execution)
    require(execution['provider_consumption_proof'] is False and execution['human_qualification'] is False,
            'review qualification inflated')
    require(execution['production_admission'] == 'NOT_GRANTED', 'production admission inflated')
    require(execution['read_claim_basis'] == 'SELF_REPORTED', 'consumption claim inflated')
    require(execution['status'] == 'COMPLETE' and execution['independent_opinions'] == 4, 'execution incomplete')
    require(execution['maximum_concurrency'] == 3, 'concurrency policy changed')
    require(execution['batch_1'] == ['blind-1', 'blind-2', 'contract-1']
            and execution['batch_2'] == ['contract-2'], 'batch plan changed')
    require(plan['independent_opinions'] == 0 and all(t['status'] == 'NOT_STARTED' for t in plan['tasks']),
            'preparation snapshot rewritten as progress')
    candidate = plan['candidate']
    prose = bound(candidate, root).decode('utf-8')
    paragraphs = prose.strip().split('\n\n')
    tasks = {t['id']: t for t in plan['tasks']}
    attempts = execution['attempts']
    require(len(tasks) == len(attempts) == 4 and {a['job'] for a in attempts} == set(tasks), 'missing/duplicate jobs')
    require(len({a['agent'] for a in attempts}) == 4, 'reader reused')
    require(all(a['agent'] != 'session:main-agent:ch86-local-trial:20261110' for a in attempts), 'author counted as reader')
    events, messages, obligations, findings, verdicts = set(), set(), [], [], {}
    nonpass_obligations, nonpass_model_items = [], []
    for attempt in attempts:
        task = tasks[attempt['job']]
        expected_agent = '/root/trial86_' + task['id'].replace('-', '') + '_20261111'
        require(attempt['agent'] == expected_agent, 'unexpected native reader')
        require(attempt['attempt'] == 1 and attempt['status'] == 'SUBMITTED', 'unexpected attempt/status')
        require(attempt['context_fork'] == 'none' and attempt['read_claim_basis'] == 'SELF_REPORTED', 'context claim changed')
        require(datetime.fromisoformat(attempt['started_at']) >= ci_finished, 'reader started before input CI')
        require(datetime.fromisoformat(attempt['completion_observed_at']) >= datetime.fromisoformat(attempt['started_at']), 'invalid completion order')
        require(attempt['batch'] == (1 if attempt['job'] in execution['batch_1'] else 2), 'wrong batch')
        external = sum(len(bound(attempt[k], root)) for k in ('dispatch', 'bootstrap', 'repository_instructions'))
        external += sum(len(bound(r, root)) for r in attempt.get('additional_instructions', []))
        require(external == attempt['known_external_bytes'] <= task['budget']['instruction_reserve_bytes'], 'external instructions over budget')
        require(attempt['external_context_usage'] == 'UNVERIFIED_RESERVATION', 'unmeasured context claimed as measured')
        read_bytes = sum(len(bound(r, root)) for r in task['read_inputs'])
        budget = task['budget']
        require(read_bytes == budget['read_bytes'] and read_bytes + budget['instruction_reserve_bytes']
                + budget['output_reserve_bytes'] == budget['reserved_total_bytes'] <= budget['maximum_bytes'], 'read budget mismatch')
        require(attempt['raw_opinion']['path'] == task['expected_raw_opinion'], 'wrong raw opinion path')
        raw = bound(attempt['raw_opinion'], root)
        require(len(raw) <= budget['output_reserve_bytes'], 'raw opinion over output budget')
        opinion = json.loads(raw)
        expected = set()
        for ref in task['read_inputs']:
            if '/contracts/' in ref['path']:
                contract = json.loads(bound(ref, root))
                contract_id = Path(ref['path']).name.split('.')[0]
                for kind in ('required_beats', 'forbidden_beats'):
                    expected.update((contract_id, kind, i) for i in range(1, len(contract[kind]) + 1))
        validate_opinion(opinion, task, attempt['agent'], candidate, expected, len(paragraphs))
        verdicts[task['id']] = opinion['overall_assessment']
        obligations.extend((o['contract_id'], o['type'], o['ordinal']) for o in opinion['obligation_findings'])
        nonpass_obligations.extend({'job': task['id'], **o} for o in opinion['obligation_findings'] if o['assessment'] != 'PASS')
        findings.extend((task['id'], f) for f in opinion['findings'])
        for item in opinion['event_and_message_findings']:
            require(item['kind'] in {'event', 'message'}, 'unknown model coverage kind')
            (events if item['kind'] == 'event' else messages).add(item['id'])
            if item['assessment'] != 'PASS':
                nonpass_model_items.append({'job': task['id'], **item})
    first_finished = max(datetime.fromisoformat(a['completion_observed_at']) for a in attempts if a['batch'] == 1)
    second_started = min(datetime.fromisoformat(a['started_at']) for a in attempts if a['batch'] == 2)
    require(first_finished <= second_started, 'second batch started before first batch completion')
    scenario = json.loads((root / 'data/writing/local-scenarios/ch86-v1/scenario.json').read_bytes())
    require(events == {e['id'] for e in scenario['events']}, 'event coverage missing/unknown')
    require(messages == {m['id'] for m in scenario['messages']}, 'message coverage missing/unknown')
    require(len(obligations) == len(set(obligations)) == 40, 'obligation coverage missing/duplicate')
    disposition = json.loads(bound(execution['disposition_binding'], root))
    require(disposition['candidate'] == candidate, 'disposition candidate mismatch')
    research_only(disposition)
    require(disposition['production_admission'] == 'NOT_GRANTED', 'disposition grants production')
    actual_ids = [(r['job'], r['finding_id']) for r in disposition['findings']]
    require(len(actual_ids) == len(set(actual_ids)) and set(actual_ids) == {(job, f['id']) for job, f in findings}, 'finding disposition coverage missing/duplicate')
    require(all(r['disposition'] in {'RETAIN', 'REVISE', 'DEFER', 'CLARIFY_MODEL'} and r['reason'] for r in disposition['findings']), 'missing disposition reason')
    original_findings = {(job, f['id']): f for job, f in findings}
    for item in disposition['findings']:
        original = original_findings[(item['job'], item['finding_id'])]
        require(item['original_assessment'] == original['assessment']
                and item['original_severity'] == original['severity'], 'original finding verdict changed')
    require(disposition['pending_contract_obligations'] == nonpass_obligations, 'pending obligation omitted/changed')
    require(disposition['decision'] == 'REVISE_BEFORE_ANY_SCALE_OUT'
            and disposition['literary_status'] == disposition['semantic_status'] == 'PENDING'
            and disposition['revision_state'] == 'PLANNED_NOT_EXECUTED', 'unverified adoption/revision claim')
    return {'status': 'PASS', 'scope': 'REVIEW_CUSTODY_DECLARED_READS_AND_COVERAGE_ONLY',
            'input_commit': INPUT_COMMIT, 'independent_model_opinions': 4,
            'reader_verdicts': verdicts, 'obligations': len(obligations),
            'events_covered': len(events), 'messages_covered': len(messages),
            'finding_assessments': dict(Counter(f['assessment'] for _, f in findings)),
            'nonpass_contract_obligations': len(nonpass_obligations),
            'nonpass_event_or_message_items': len(nonpass_model_items),
            'literary_status': 'PENDING', 'semantic_status': 'PENDING',
            'source_and_corpus_review': 'NOT_CHECKED',
            'read_claim_basis': 'SELF_REPORTED', 'provider_consumption_proof': False,
            'formal_eligibility': False, 'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
