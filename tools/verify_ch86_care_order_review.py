"""Prepare and verify same-reader follow-up of the versioned care-order repair."""
import argparse
import json
from pathlib import Path
import subprocess

from rcwh.generation.records import binding, bound_bytes
import prepare_ch86_care_order as amendment
import verify_ch86_knowledge_followup as previous
import verify_ch86_knowledge_review as initial

ROOT = Path(__file__).resolve().parents[1]
REVIEW = amendment.OUTPUT + '/review'
CONTEXT = 'REUSED_SAME_ORIGINAL_READER'


def prepare(ci_path, root=ROOT):
    amendment.verify(root)
    previous.verify(root)
    ci = json.loads(ci_path.read_bytes())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if ci['headSha'] != head or ci['status'] != 'completed' or ci['conclusion'] != 'success':
        raise ValueError('care-order review requires successful CI on current HEAD')
    if len(ci['jobs']) != 2 or any(j['conclusion'] != 'success' for j in ci['jobs']):
        raise ValueError('both Python CI jobs are required')
    ci_ref = initial.write(root, REVIEW + '/input-ci.json', ci)
    manifest_ref = binding(root, amendment.OUTPUT + '/manifest.json')
    manifest = json.loads(bound_bytes(root, manifest_ref))
    prior_plan_ref = binding(root, previous.REVIEW + '/plan.json')
    prior_plan = json.loads(bound_bytes(root, prior_plan_ref))
    prior_execution_ref = binding(root, previous.REVIEW + '/execution.json')
    prior_execution = json.loads(bound_bytes(root, prior_execution_ref))
    prior_attempts = {a['job_id']: a for a in prior_execution['attempts']}
    tasks, scaffolds = [], {}
    for job in initial.JOBS:
        old_task_ref = next(r for r in prior_plan['tasks'] if json.loads(bound_bytes(root, r))['job_id'] == job)
        old_task = json.loads(bound_bytes(root, old_task_ref))
        old_opinion = prior_attempts[job]['raw_opinion']
        scaffold = json.loads(bound_bytes(root, old_task['read_inputs'][-1]))
        scaffold_ref = initial.write(root, REVIEW + f'/{job}.scaffold.json', scaffold)
        reads = [manifest['candidate'], manifest['scenario'], *manifest['contracts'][3:],
                 binding(root, 'data/knowledge/v03_slice2.json'),
                 binding(root, 'data/scenes/ch86_last_night.yaml'),
                 binding(root, 'artifacts/local-trial-revision-ch86-20261111/review/semantic-boundary.md'),
                 old_opinion, manifest_ref, scaffold_ref]
        read_bytes = sum(len(bound_bytes(root, r)) for r in reads)
        instructions = ('这是ch86-v5照护顺序修订复核。沿用同一原读者上下文，不增加独立读者数。'
                        '只读本dispatch的read_inputs和仓库AGENTS.md；全文逐项读完并核SHA，截断须补读。'
                        '允许读取自己的v4复核，不读另一位读者的任何意见；manifest里的意见路径/摘要不构成读集。'
                        '独立复核七项，重点评价body_care_started < runner_observes_death与liwan_takes_care < baoyu_arrives是否由正文支持、事件粒度是否恰当、是否遗漏其他必要偏序或过度约束。'
                        '检查完整候选和六份合同、新旧状态回放边界。回放不是正文证据。旧C1无等值映射，不得代旧读者改判。'
                        '按scaffold填写，每项提供理由和材料定位；若有正文依据给逐字引句及段号。assessment和overall只用PASS/FAIL/PENDING；reading_status填COMPLETE/INCOMPLETE。'
                        'declared_read_files列齐全部path/sha256/bytes/read_complete；自述不等于provider消费证明。身份如实使用原任务标签。'
                        '仅写expected_raw_opinion，不覆盖旧件、不改其他文件、不提交、不建分支、不调用外部模型API。可如实判FAIL/PENDING。'
                        '最多16384字节；读不完须列unread。RESEARCH_ONLY，authority NONE，production NOT_GRANTED。')
        task = {'job_id': job, 'instructions': instructions, 'read_inputs': reads,
                'expected_reader': prior_attempts[job]['agent'], 'context_mode': CONTEXT,
                'expected_raw_opinion': REVIEW + f'/opinions/{job}.json',
                'budget': {'read_bytes': read_bytes, 'instruction_reserve_bytes': 16384,
                           'output_reserve_bytes': 16384, 'maximum_bytes': 201728,
                           'reserved_total_bytes': read_bytes + 32768, 'tokens': 'NOT_MEASURED',
                           'system_context_bytes': 'NOT_MEASURED',
                           'reused_prior_context_bytes': 'NOT_MEASURED'}}
        if task['budget']['reserved_total_bytes'] > task['budget']['maximum_bytes']:
            raise ValueError(f'{job} exceeds task byte reservation')
        task_ref = initial.write(root, REVIEW + f'/dispatch/{job}.json', task)
        tasks.append(task_ref)
        scaffolds[job] = scaffold_ref
    plan = {'kind': 'CH86_CARE_ORDER_REVIEW_PLAN', 'status': 'NOT_STARTED', 'input_commit': head,
            'input_ci': ci_ref, 'manifest': manifest_ref, 'candidate': manifest['candidate'],
            'prior_plan': prior_plan_ref, 'prior_execution': prior_execution_ref,
            'repository_instructions': binding(root, 'AGENTS.md'), 'tasks': tasks,
            'context_mode': CONTEXT, 'maximum_concurrency': 2,
            'independent_opinions_added': 0, 'independent_model_readers_total': 2,
            'qualification': 'RESEARCH_ONLY', 'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}
    initial.write(root, REVIEW + '/plan.json', plan)
    (root / REVIEW / 'opinions').mkdir(parents=True, exist_ok=True)


def verify(root=ROOT):
    amendment.verify(root)
    previous.verify(root)
    plan_ref = binding(root, REVIEW + '/plan.json')
    plan = json.loads(bound_bytes(root, plan_ref))
    ci = json.loads(bound_bytes(root, plan['input_ci']))
    assert ci['headSha'] == plan['input_commit'] and ci['status'] == 'completed' and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 2 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    assert plan['manifest'] == binding(root, amendment.OUTPUT + '/manifest.json')
    manifest = json.loads(bound_bytes(root, plan['manifest']))
    assert plan['candidate'] == manifest['candidate']
    assert plan['prior_plan'] == binding(root, previous.REVIEW + '/plan.json')
    assert plan['prior_execution'] == binding(root, previous.REVIEW + '/execution.json')
    execution = json.loads((root / REVIEW / 'execution.json').read_bytes())
    assert execution['plan'] == plan_ref and execution['status'] == 'COMPLETE'
    assert execution['context_mode'] == plan['context_mode'] == CONTEXT
    assert execution['independent_opinions_added'] == plan['independent_opinions_added'] == 0
    assert execution['independent_model_readers_total'] == plan['independent_model_readers_total'] == 2
    assert execution['human_qualification'] is False and execution['provider_consumption_proof'] is False
    assert execution['qualification'] == plan['qualification'] == 'RESEARCH_ONLY'
    assert execution['production_admission'] == plan['production_admission'] == 'NOT_GRANTED'
    assert execution['authority_effect'] == plan['authority_effect'] == 'NONE'
    assert len(execution['attempts']) == len(plan['tasks']) == 2
    attempts = {a['job_id']: a for a in execution['attempts']}
    prior_execution = json.loads(bound_bytes(root, plan['prior_execution']))
    prior_attempts = {a['job_id']: a for a in prior_execution['attempts']}
    opinions = {}
    for task_ref in plan['tasks']:
        task = json.loads(bound_bytes(root, task_ref))
        attempt = attempts[task['job_id']]
        assert attempt['agent'] == task['expected_reader'] == prior_attempts[task['job_id']]['agent']
        assert attempt['context_fork'] == CONTEXT
        # The initial submissions are immutable; their quote strings are checked against
        # reader-authored, separately bound errata below.
        opinion = initial.verify_task(root, task_ref, attempt, plan['candidate'], CONTEXT,
                                      verify_quotes=False)
        opinions[task['job_id']] = opinion
        prior = json.loads(bound_bytes(root, prior_attempts[task['job_id']]['raw_opinion']))
        assert prior['overall_assessment'] in {'FAIL', 'PENDING'}
        assert prior['candidate'] == plan['candidate']
        assert prior_attempts[next(j for j in prior_attempts if j != task['job_id'])]['raw_opinion'] not in task['read_inputs']
    assert len(opinions) == 2
    read = execution['coordinator_read']
    assert read['read_complete'] is True and read['basis'] == 'SELF_REPORTED_AFTER_TOOL_OUTPUT'
    assert read['opinion_bindings'] == [a['raw_opinion'] for a in execution['attempts']]
    errata_manifest_ref = binding(root, REVIEW + '/citation-errata/manifest.json')
    errata_manifest = json.loads(bound_bytes(root, errata_manifest_ref))
    assert errata_manifest['kind'] == 'CH86_CITATION_ERRATA_MANIFEST'
    assert errata_manifest['plan'] == plan_ref and errata_manifest['execution'] == binding(root, REVIEW + '/execution.json')
    assert len(errata_manifest['entries']) == 2
    body = bound_bytes(root, plan['candidate']).decode().strip().split('\n\n')
    if body and body[0].startswith('第八十六回'):
        body = body[1:]
    discrepancies = []
    for entry in errata_manifest['entries']:
        job = entry['job_id']
        assert job in opinions
        erratum = json.loads(bound_bytes(root, entry['erratum']))
        attempt = attempts[job]
        original_ref = attempt['raw_opinion']
        assert erratum['kind'] == 'CH86_PROSE_QUOTE_ERRATUM'
        assert erratum['original_opinion'] == original_ref and erratum['candidate'] == plan['candidate']
        assert erratum['reader'] == attempt['agent']
        opinion = opinions[job]
        by_id = {f['id']: f for f in opinion['findings']}
        corrected = {f['id']: f for f in erratum['findings']}
        assert set(corrected) == set(by_id) == set(initial.ITEMS)
        for finding_id, correction in corrected.items():
            assert correction['original_prose_quotes'] == by_id[finding_id]['prose_quotes']
            assert isinstance(correction['corrected_prose_quotes'], list)
            for quote in correction['corrected_prose_quotes']:
                assert quote['quote'] and quote['paragraphs']
                assert all(type(n) is int and 1 <= n <= len(body) and quote['quote'] in body[n-1]
                           for n in quote['paragraphs'])
            if correction.get('discrepancy'):
                discrepancies.append({'job_id': job, 'finding_id': finding_id,
                                      'discrepancy': correction['discrepancy']})
    disposition_ref = binding(root, REVIEW + '/disposition.json')
    disposition = json.loads(bound_bytes(root, disposition_ref))
    assert disposition['kind'] == 'CH86_CARE_ORDER_REVIEW_DISPOSITION'
    assert disposition['plan'] == plan_ref and disposition['execution'] == binding(root, REVIEW + '/execution.json')
    assert disposition['citation_errata_manifest'] == errata_manifest_ref
    assert disposition['candidate'] == plan['candidate']
    assert disposition['reviewer_verdicts'] == {job: o['overall_assessment'] for job, o in opinions.items()}
    expected_findings = {(job, finding['id']): finding['assessment']
                         for job, opinion in opinions.items() for finding in opinion['findings']}
    disposition_findings = {(row['job_id'], row['finding_id']): row['original_assessment']
                            for row in disposition['findings']}
    assert disposition_findings == expected_findings
    assert disposition['causal_order_decision']['next_edge'] == ['liwan_takes_care', 'baoyu_departs']
    assert disposition['old_C1'] == 'PENDING_NO_EQUIVALENT_LOCAL_MAPPING'
    assert disposition['semantic_status'] == 'PENDING'
    assert disposition['production_admission'] == 'NOT_GRANTED' and disposition['authority_effect'] == 'NONE'
    return {'status': 'PASS', 'scope': 'CUSTODY_AND_SELF_REPORTED_COVERAGE_ONLY',
            'reader_verdicts': {j: o['overall_assessment'] for j, o in opinions.items()},
            'citation_errata_verified': True, 'citation_discrepancies': discrepancies,
            'coordinator_decision': disposition['decision'],
            'independent_model_readers': 2, 'independent_opinions_added': 0,
            'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', type=Path, metavar='INPUT_CI_JSON')
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare)
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
