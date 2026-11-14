"""Prepare and verify the same-reader follow-up for the v6 care-order edge."""
import argparse
import json
from pathlib import Path
import subprocess

from rcwh.generation.records import binding, bound_bytes
import prepare_ch86_care_order_v6 as amendment
import verify_ch86_care_order_review as previous
import verify_ch86_knowledge_review as initial

ROOT = Path(__file__).resolve().parents[1]
REVIEW = amendment.OUTPUT + '/review'
CONTEXT = 'REUSED_SAME_ORIGINAL_READER'


def prepare(ci_path, root=ROOT):
    amendment.verify(root)
    previous.verify(root)
    ci = json.loads(Path(ci_path).read_bytes())
    if ci.get('status') != 'completed' or ci.get('conclusion') != 'success':
        raise ValueError('v6 review requires completed successful CI')
    if len(ci.get('jobs', [])) != 2 or any(job.get('conclusion') != 'success' for job in ci['jobs']):
        raise ValueError('both Python CI jobs are required')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if ci.get('headSha') != head:
        raise ValueError('CI SHA must match the review preparation HEAD')
    ci_ref = initial.write(root, REVIEW + '/input-ci.json', ci)
    manifest_ref = binding(root, amendment.OUTPUT + '/manifest.json')
    manifest = json.loads(bound_bytes(root, manifest_ref))
    previous_plan_ref = binding(root, previous.REVIEW + '/plan.json')
    previous_execution_ref = binding(root, previous.REVIEW + '/execution.json')
    previous_plan = json.loads(bound_bytes(root, previous_plan_ref))
    previous_execution = json.loads(bound_bytes(root, previous_execution_ref))
    previous_attempts = {attempt['job_id']: attempt for attempt in previous_execution['attempts']}
    tasks = []
    for job in initial.JOBS:
        previous_task_ref = next(ref for ref in previous_plan['tasks']
                                 if json.loads(bound_bytes(root, ref))['job_id'] == job)
        previous_task = json.loads(bound_bytes(root, previous_task_ref))
        scaffold = json.loads(bound_bytes(root, previous_task['read_inputs'][-1]))
        scaffold_ref = initial.write(root, REVIEW + f'/{job}.scaffold.json', scaffold)
        reads = [manifest['candidate'], manifest['scenario'], *manifest['contracts'][3:],
                 binding(root, 'data/knowledge/v03_slice2.json'),
                 binding(root, 'data/scenes/ch86_last_night.yaml'),
                 binding(root, 'artifacts/local-trial-revision-ch86-20261111/review/semantic-boundary.md'),
                 previous_attempts[job]['raw_opinion'], scaffold_ref]
        read_bytes = sum(len(bound_bytes(root, ref)) for ref in reads)
        instructions = ('这是ch86-v6单边偏序修订复核。沿用同一原读者上下文，不增加独立读者数。'
                        '只读本dispatch的read_inputs和仓库AGENTS.md；全文逐项读完并核SHA，截断须补读。'
                        '只可读自己的v5原意见，不读另一位读者意见或协调者的审阅处置。'
                        '核对候选正文与完整场景、S4-S6合同、回放边界；回放不是正文证据。'
                        '重点判断liwan_takes_care < baoyu_departs是否受正文支持且粒度合适，'
                        '是否应从unconstrained_pairs移除；同时复核保留的两处宝玉收信与死亡/身体料理无序是否合理。'
                        '旧C1仍无等值映射，不得替旧读者改判。按scaffold逐项写判断、理由、材料定位；正文引句须逐字匹配，段号从正文第一段=1且不计标题。'
                        'declared_read_files列齐全部path/sha256/bytes/read_complete；自述不等于provider消费证明。'
                        '身份如实使用原任务标签。仅写expected_raw_opinion，不覆盖历史意见、不改其他文件、不提交、不建分支、不调用外部模型API。'
                        '最多16384字节；读不完须列unread。RESEARCH_ONLY，authority NONE，production NOT_GRANTED。')
        task = {'job_id': job, 'instructions': instructions, 'read_inputs': reads,
                'expected_reader': previous_attempts[job]['agent'], 'context_mode': CONTEXT,
                'expected_raw_opinion': REVIEW + f'/opinions/{job}.json',
                'budget': {'read_bytes': read_bytes, 'instruction_reserve_bytes': 16384,
                           'output_reserve_bytes': 16384, 'maximum_bytes': 201728,
                           'reserved_total_bytes': read_bytes + 32768, 'tokens': 'NOT_MEASURED',
                           'system_context_bytes': 'NOT_MEASURED', 'reused_prior_context_bytes': 'NOT_MEASURED'}}
        if task['budget']['reserved_total_bytes'] > task['budget']['maximum_bytes']:
            raise ValueError(f'{job} exceeds task byte reservation')
        tasks.append(initial.write(root, REVIEW + f'/dispatch/{job}.json', task))
    plan = {'kind': 'CH86_CARE_ORDER_V6_REVIEW_PLAN', 'status': 'NOT_STARTED',
            'input_commit': head, 'input_ci': ci_ref, 'manifest': manifest_ref,
            'candidate': manifest['candidate'], 'previous_plan': previous_plan_ref,
            'previous_execution': previous_execution_ref, 'repository_instructions': binding(root, 'AGENTS.md'),
            'tasks': tasks, 'context_mode': CONTEXT, 'maximum_concurrency': 2,
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
    assert len(ci['jobs']) == 2 and all(job['conclusion'] == 'success' for job in ci['jobs'])
    assert plan['manifest'] == binding(root, amendment.OUTPUT + '/manifest.json')
    manifest = json.loads(bound_bytes(root, plan['manifest']))
    assert plan['candidate'] == manifest['candidate']
    assert plan['previous_plan'] == binding(root, previous.REVIEW + '/plan.json')
    assert plan['previous_execution'] == binding(root, previous.REVIEW + '/execution.json')
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
    attempts = {attempt['job_id']: attempt for attempt in execution['attempts']}
    prior_execution = json.loads(bound_bytes(root, plan['previous_execution']))
    prior_attempts = {attempt['job_id']: attempt for attempt in prior_execution['attempts']}
    opinions = {}
    for task_ref in plan['tasks']:
        task = json.loads(bound_bytes(root, task_ref))
        attempt = attempts[task['job_id']]
        assert attempt['agent'] == task['expected_reader'] == prior_attempts[task['job_id']]['agent']
        assert attempt['context_fork'] == CONTEXT
        peer = next(job for job in prior_attempts if job != task['job_id'])
        assert prior_attempts[peer]['raw_opinion'] not in task['read_inputs']
        assert binding(root, previous.REVIEW + '/disposition.json') not in task['read_inputs']
        assert plan['manifest'] not in task['read_inputs']
        opinion = initial.verify_task(root, task_ref, attempt, plan['candidate'], CONTEXT)
        opinions[task['job_id']] = opinion
    read = execution['coordinator_read']
    assert read['read_complete'] is True and read['basis'] == 'SELF_REPORTED_AFTER_TOOL_OUTPUT'
    assert read['opinion_bindings'] == [attempt['raw_opinion'] for attempt in execution['attempts']]
    return {'status': 'PASS', 'scope': 'CUSTODY_AND_SELF_REPORTED_COVERAGE_ONLY',
            'reader_verdicts': {job: opinion['overall_assessment'] for job, opinion in opinions.items()},
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
