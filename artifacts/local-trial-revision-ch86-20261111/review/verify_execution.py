"""Check review custody and declared coverage; never certify prose or consumption."""
from copy import deepcopy
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('artifacts/local-trial-revision-ch86-20261111/review')


def verify():
    helpers = runpy.run_path(str(ROOT / 'artifacts/local-trial-review-20261111/verify.py'))
    bound = lambda ref: helpers['bound'](ref, ROOT)
    execution = json.loads((ROOT / BASE / 'execution.json').read_bytes())
    plan = json.loads(bound(execution['plan_binding']))
    ci = json.loads(bound(execution['ci_binding']))
    assert ci['headSha'] == execution['input_commit'] == '61f647a60b150a6e9d471467926f107a8b653b81'
    assert ci['status'] == 'completed' and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 2 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    assert execution['status'] == 'COMPLETE' and execution['maximum_concurrency'] == 3
    helpers['research_only'](execution)
    assert not execution['provider_consumption_proof'] and not execution['human_qualification']
    assert execution['production_admission'] == 'NOT_GRANTED'
    assert plan['independent_opinions'] == 0 and all(t['status'] == 'NOT_STARTED' for t in plan['tasks'])
    prose = bound(plan['candidate']).decode()
    paragraphs = prose.strip().split('\n\n')
    followup = execution['citation_followup']
    addendum = json.loads(bound(followup['output']))
    bound(addendum['original_review'])
    assert addendum['original_review']['sha256'] == next(a for a in execution['attempts'] if a['job'] == 'blind-1')['raw_opinion']['sha256']
    assert addendum['candidate'] == {k: plan['candidate'][k] for k in ('path', 'sha256')}
    for correction in addendum['corrections']:
        assert correction['accurate_literal_quote'] in prose
        for quote in correction['all_quotes_with_paragraphs']:
            assert any(quote['literal_quote'] in paragraphs[n-1] for n in quote['paragraphs'])
    assert sum(len(bound(r)) for r in followup['read_inputs']) + 32768 == followup['reserved_total_bytes'] <= followup['maximum_bytes']
    assert len(bound(followup['output'])) <= followup['output_reserve_bytes']
    bound(followup['dispatch'])
    attempts = execution['attempts']
    assert len(attempts) == 4 and len({a['agent'] for a in attempts}) == 4
    assert {a['job'] for a in attempts} == {t['id'] for t in plan['tasks']}
    events, messages, obligations, findings = set(), set(), [], []
    verdicts, nonpass = {}, []
    for task in plan['tasks']:
        attempt = next(a for a in attempts if a['job'] == task['id'])
        assert attempt['status'] == 'SUBMITTED' and attempt['context_fork'] == 'none'
        expected = set()
        for ref in task['read_inputs']:
            raw = bound(ref)
            if '/contracts/' in ref['path']:
                contract = json.loads(raw)
                for key in ('required_beats', 'forbidden_beats'):
                    expected.update((contract['id'], key, n) for n in range(1, len(contract[key])+1))
        budget = task['budget']
        dispatch = json.loads(bound(attempt['dispatch']))
        known = sum(len(m.encode()) for m in dispatch['messages']) + len(bound(execution['repository_instructions']))
        assert known == attempt['known_instruction_bytes'] <= budget['instruction_reserve_bytes']
        assert sum(len(bound(r)) for r in task['read_inputs']) == budget['read_bytes']
        assert budget['read_bytes'] + budget['instruction_reserve_bytes'] + budget['output_reserve_bytes'] == budget['reserved_total_bytes'] <= budget['maximum_bytes']
        raw = bound(attempt['raw_opinion'])
        assert attempt['raw_opinion']['path'] == task['expected_raw_opinion']
        assert len(raw) <= budget['output_reserve_bytes']
        opinion = json.loads(raw)
        # Extra identity disclaimers remain in the immutable original. The old
        # shared validator accepts only the two identity fields in this view.
        validation_view = deepcopy(opinion)
        validation_view['reviewer'] = {k: opinion['reviewer'][k] for k in ('principal_id', 'session_id')}
        helpers['validate_opinion'](validation_view, task, attempt['agent'], plan['candidate'], expected, len(paragraphs))
        verdicts[task['id']] = opinion['overall_assessment']
        obligations.extend((o['contract_id'], o['type'], o['ordinal']) for o in opinion['obligation_findings'])
        findings.extend({'job':task['id'], **f} for f in opinion['findings'])
        for row in opinion['event_and_message_findings']:
            assert row['kind'] in ('event', 'message')
            (events if row['kind'] == 'event' else messages).add(row['id'])
        nonpass.extend({'job':task['id'], **o} for o in opinion['obligation_findings'] + opinion['event_and_message_findings'] if o['assessment'] != 'PASS')
    scenario = json.loads((ROOT / BASE.parent / 'reading-inputs/scenario.json').read_bytes())
    assert events == {e['id'] for e in scenario['events']}
    assert messages == {m['id'] for m in scenario['messages']}
    assert len(obligations) == len(set(obligations)) == 40
    disposition = json.loads(bound(execution['disposition_binding']))
    helpers['research_only'](disposition)
    assert disposition['candidate'] == plan['candidate']
    assert disposition['production_admission'] == 'NOT_GRANTED'
    assert disposition['semantic_status'] == 'PENDING' and disposition['source_and_corpus_review'] == 'NOT_CHECKED'
    assert disposition['nonpass_contract_and_model_items'] == nonpass
    original = {(f['job'], f['id']): f for f in findings}
    assert len(disposition['findings']) == len(original)
    assert {(f['job'], f['finding_id']) for f in disposition['findings']} == set(original)
    for row in disposition['findings']:
        source = original[row['job'], row['finding_id']]
        assert row['original_assessment'] == source['assessment']
        assert row['original_severity'] == source['severity'] and row['reason']
    return {'status':'PASS', 'scope':'CUSTODY_AND_SELF_REPORTED_COVERAGE_ONLY',
            'independent_model_opinions':4, 'reader_verdicts':verdicts,
            'obligations':len(obligations), 'events':len(events), 'messages':len(messages),
            'nonpass_contract_and_model_items':len(nonpass), 'findings':len(findings),
            'source_and_corpus_review':'NOT_CHECKED', 'production_admission':'NOT_GRANTED',
            'provider_consumption_proof':False, 'authority_effect':'NONE'}


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
