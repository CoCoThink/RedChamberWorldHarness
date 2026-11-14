"""Bind same-reader amendment follow-up without inflating independent-reader counts."""
import argparse
import json
from pathlib import Path
import subprocess

from rcwh.generation.records import binding, bound_bytes
import prepare_ch86_knowledge_amendment as amendment
import verify_ch86_knowledge_review as initial

ROOT = Path(__file__).resolve().parents[1]
REVIEW = amendment.OUTPUT + '/review'
CONTEXT = 'REUSED_SAME_ORIGINAL_READER'


def prepare(ci_path, root=ROOT):
    initial.verify(root)
    amendment.verify(root)
    ci = json.loads(ci_path.read_bytes())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    assert ci['headSha'] == commit and ci['status'] == 'completed' and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 2 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    manifest_ref = binding(root, amendment.OUTPUT + '/manifest.json')
    manifest = json.loads(bound_bytes(root, manifest_ref))
    execution_ref = manifest['original_review_execution']
    execution = json.loads(bound_bytes(root, execution_ref))
    tasks = []
    for attempt in execution['attempts']:
        job = attempt['job_id']
        original_task = json.loads(bound_bytes(root, attempt['dispatch']))
        scaffold = json.loads(bound_bytes(root, original_task['read_inputs'][-1]))
        scaffold_ref = initial.write(root, REVIEW + f'/{job}.scaffold.json', scaffold)
        read_inputs = [manifest['candidate'], manifest['scenario'], *manifest['contracts'][3:],
                       binding(root, 'data/knowledge/v03_slice2.json'),
                       binding(root, 'data/scenes/ch86_last_night.yaml'),
                       binding(root, 'artifacts/local-trial-revision-ch86-20261111/review/semantic-boundary.md'),
                       attempt['raw_opinion'], manifest_ref, scaffold_ref]
        instructions = ('这是原读者对ch86-v4修订的研究复核，沿用自身上下文，不是新增独立读者。'
                        '只能阅读read_inputs及AGENTS.md，完整阅读全部分配材料并核SHA256，截断必须补读。'
                        '可以读取自己原始意见，不读取另一位读者意见；manifest中的其他文件引用不是追加读集。'
                        '不预设修订成功，独立核对七项，特别核对普通观察/医学生理/医学死因边界、两条新增偏序是否充分且未过度约束、活动指令与合同是否相容。'
                        '候选正文未改，回放及修订说明均不代替正文证据；可质疑新增定义或发现新问题。'
                        'OLD_FINDING旧命题无等值映射，不能替旧读者改判。'
                        '按scaffold填写七项，每项理由/材料定位，必要时逐字正文引句及空行分段段号（含回目，从1起）。'
                        'assessment与overall_assessment限PASS/FAIL/PENDING，允许旧C1仍PENDING；reading_status限COMPLETE/INCOMPLETE。'
                        'declared_read_files列每项path/sha256/bytes/read_complete；阅读是自述非provider消费证明。'
                        'reviewer两个身份字段均填自身实际原任务标签，身份基础限任务标签未provider验证。'
                        '仅保存expected_raw_opinion，禁止覆盖旧意见、建分支、提交、改其他文件或调用外部模型API。'
                        '意见最多16384 UTF-8字节；读不全写INCOMPLETE/unread，不能编造覆盖。研究资格不提升为真人、来源语料或production。')
        read_bytes = sum(len(bound_bytes(root, ref)) for ref in read_inputs)
        assert read_bytes + 32768 <= 201728
        task = {'job_id': job, 'instructions': instructions, 'read_inputs': read_inputs,
                'expected_reader': attempt['agent'], 'context_mode': CONTEXT,
                'expected_raw_opinion': REVIEW + f'/opinions/{job}.json',
                'budget': {'read_bytes': read_bytes, 'instruction_reserve_bytes': 16384,
                           'output_reserve_bytes': 16384, 'maximum_bytes': 201728,
                           'reserved_total_bytes': read_bytes + 32768,
                           'tokens': 'NOT_MEASURED', 'system_context_bytes': 'NOT_MEASURED',
                           'reused_prior_context_bytes': 'NOT_MEASURED'}}
        tasks.append(initial.write(root, REVIEW + f'/dispatch/{job}.json', task))
    initial.write(root, REVIEW + '/plan.json', {
        'kind': 'CH86_KNOWLEDGE_AMENDMENT_FOLLOWUP_PLAN', 'status': 'NOT_STARTED',
        'input_commit': commit, 'input_ci': initial.write(root, REVIEW + '/input-ci.json', ci),
        'manifest': manifest_ref, 'candidate': manifest['candidate'], 'original_execution': execution_ref,
        'repository_instructions': binding(root, 'AGENTS.md'), 'tasks': tasks, 'context_mode': CONTEXT,
        'maximum_concurrency': 2, 'independent_opinions_added': 0,
        'qualification': 'RESEARCH_ONLY', 'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'})
    (root / REVIEW / 'opinions').mkdir(parents=True, exist_ok=True)


def verify(root=ROOT):
    original_result = initial.verify(root)
    amendment.verify(root)
    plan_ref = binding(root, REVIEW + '/plan.json')
    plan = json.loads(bound_bytes(root, plan_ref))
    ci = json.loads(bound_bytes(root, plan['input_ci']))
    assert ci['headSha'] == plan['input_commit'] and ci['status'] == 'completed' and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 2 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    bound_bytes(root, plan['repository_instructions'])
    assert plan['manifest'] == binding(root, amendment.OUTPUT + '/manifest.json')
    manifest = json.loads(bound_bytes(root, plan['manifest']))
    assert plan['candidate'] == manifest['candidate']
    assert plan['original_execution'] == manifest['original_review_execution']
    original = json.loads(bound_bytes(root, plan['original_execution']))
    execution = json.loads((root / REVIEW / 'execution.json').read_bytes())
    assert execution['plan'] == plan_ref and execution['status'] == 'COMPLETE'
    assert execution['context_mode'] == plan['context_mode'] == CONTEXT
    assert execution['maximum_concurrency'] <= plan['maximum_concurrency'] == 2
    assert execution['independent_opinions_added'] == plan['independent_opinions_added'] == 0
    assert execution['human_qualification'] is False and execution['provider_consumption_proof'] is False
    assert execution['qualification'] == plan['qualification'] == 'RESEARCH_ONLY'
    assert execution['production_admission'] == plan['production_admission'] == 'NOT_GRANTED'
    assert execution['authority_effect'] == plan['authority_effect'] == 'NONE'
    assert len(execution['attempts']) == len(plan['tasks']) == 2
    attempts = {a['job_id']: a for a in execution['attempts']}
    originals = {a['job_id']: a for a in original['attempts']}
    assert set(attempts) == set(originals) == set(initial.JOBS)
    opinions = {}
    for task_ref in plan['tasks']:
        task = json.loads(bound_bytes(root, task_ref))
        attempt = attempts[task['job_id']]
        assert attempt['agent'] == task['expected_reader'] == originals[task['job_id']]['agent']
        assert task['context_mode'] == CONTEXT
        assert originals[task['job_id']]['raw_opinion'] in task['read_inputs']
        other = next(a['raw_opinion'] for j, a in originals.items() if j != task['job_id'])
        assert other not in task['read_inputs']
        opinions[task['job_id']] = initial.verify_task(root, task_ref, attempt, plan['candidate'], CONTEXT)
    assert set(opinions) == set(initial.JOBS)
    read = execution['coordinator_read']
    assert read['read_complete'] is True and read['basis'] == 'SELF_REPORTED_AFTER_TOOL_OUTPUT'
    assert read['opinion_bindings'] == [a['raw_opinion'] for a in execution['attempts']]
    return {'status': 'PASS', 'scope': 'CUSTODY_AND_SELF_REPORTED_COVERAGE_ONLY',
            'original_reader_verdicts': original_result['reader_verdicts'],
            'followup_reader_verdicts': {j: o['overall_assessment'] for j, o in opinions.items()},
            'independent_model_readers': 2, 'independent_opinions_added': 0,
            'provider_consumption_proof': False, 'source_and_corpus_review': 'NOT_CHECKED',
            'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', type=Path, metavar='INPUT_CI_JSON')
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare)
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
