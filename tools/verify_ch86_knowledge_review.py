"""Prepare/check bounded native review custody; opinions remain semantic judgments."""
import argparse
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.local_scenario import checkpoint_view, compile_scenario, verify_material
from rcwh.generation.records import binding, bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/local-scenario-ch86-knowledge-split'
REVIEW = BASE + '/review'
ITEMS = ['WITNESS', 'RECIPIENT', 'PRECISE_TIME', 'PHYSIOLOGY', 'CAUSAL_ORDER', 'CONTRACT_COMPATIBILITY', 'OLD_FINDING']
JOBS = {'semantic-1': '独立核对正文对四类知识命题的支持及其取得边界。',
        'semantic-2': '独立核对偏序/消息传播与原合同声明的相容性、旧命题没有等值映射的影响。'}


def write(root, path, value):
    target = root / path
    raw = canonical_bytes(value)
    if target.exists() and target.read_bytes() != raw:
        raise ValueError('refusing to replace original: ' + path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return binding(root, path)


def prepare(ci_path, root=ROOT):
    manifest = json.loads((root / BASE / 'manifest.json').read_bytes())
    for value in manifest.values():
        for ref in value if isinstance(value, list) else [value]:
            if isinstance(ref, dict) and 'path' in ref:
                bound_bytes(root, ref)
    ci = json.loads(ci_path.read_bytes())
    if ci['headSha'] != '716755d58cb87148fe7cb6522db4f6ac641fca0f' or ci['status'] != 'completed' or ci['conclusion'] != 'success':
        raise ValueError('review input CI is not successful')
    if len(ci['jobs']) != 2 or any(j['conclusion'] != 'success' for j in ci['jobs']):
        raise ValueError('both input CI jobs required')
    ci_ref = write(root, REVIEW + '/input-ci.json', ci)
    imported = json.loads(bound_bytes(root, manifest['candidate_import']))
    candidate = imported['candidate']
    bound_bytes(root, candidate)
    compiled = json.loads(bound_bytes(root, manifest['checkpoints']))
    view_ref = write(root, REVIEW + '/checkpoint-view.json', checkpoint_view(compiled))
    inputs = [candidate, manifest['scenario'], *manifest['contracts'][3:], view_ref,
              manifest['semantic_boundary'], binding(root, BASE + '/REVIEW.md'),
              binding(root, 'data/knowledge/v03_slice2.json'), binding(root, 'data/scenes/ch86_last_night.yaml')]
    tasks = []
    for job, focus in JOBS.items():
        scaffold = {'kind': 'CH86_KNOWLEDGE_REVIEW_OPINION', 'job_id': job,
                    'reviewer': {'principal_id': '', 'session_id': '', 'identity_basis': 'NATIVE_TASK_LABEL_NOT_PROVIDER_VERIFIED'},
                    'candidate': candidate, 'reading_status': 'NOT_STARTED', 'declared_read_files': [],
                    'unread': [], 'findings': [{'id': i, 'assessment': 'PENDING', 'reason': '',
                                               'prose_quotes': [], 'material_citations': []} for i in ITEMS],
                    'overall_assessment': 'PENDING', 'qualification': 'RESEARCH_ONLY',
                    'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}
        scaffold_ref = write(root, REVIEW + f'/{job}.scaffold.json', scaffold)
        read_inputs = inputs + [scaffold_ref]
        read_bytes = sum(len(bound_bytes(root, r)) for r in read_inputs)
        instructions = ('在 /mnt/d/code/redchamberworldharness 做独立研究语义审读。只读本 dispatch 的 read_inputs 和仓库 AGENTS.md。'
                        '全文阅读正文，逐份美化 JSON 并分块读完所有分配内容，截断必须补读；完整读集核 SHA256。'
                        'checkpoint-view 是精确 ENTRY 加 overrides 的无损视图，不是删节；模型回放不是正文证据。'
                        '重点：' + focus + ' 仍须独立评价所有七项，允许挑战边界说明及新模型。'
                        'OLD_FINDING 指 C1-DEATH-KNOWLEDGE 的旧歧义命题，判断新拆分能否解决及为何；旧审阅意见不提供，不能替旧读者改判。'
                        '按 scaffold 填意见；assessment/overall_assessment 只用 PASS/FAIL/PENDING。reading_status 用 COMPLETE/INCOMPLETE。'
                        'declared_read_files 每行 path/sha256/bytes/read_complete，必须列全部读集；这是自述，不是消费证明。'
                        'prose_quotes 每行 quote 和 paragraphs（空行分段从1起，含回目）；引句必须逐字一致。'
                        'material_citations 每行 path/locator，明确 JSON 字段或上游行。每项必须有理由、材料定位，有正文支持时给引句。'
                        'reviewer principal_id/session_id 填当前实际任务标签，底层会话身份未知如实说明。'
                        '仅把原始 JSON 写入 expected_raw_opinion（已存在则拒绝覆盖），不要写其他文件、提交或建分支；最终返回路径及摘要。'
                        '不读旧稿/作者自查/其他意见，不调用外部模型 API。不提升为真人、来源语料或 production 资格。'
                        '不能读全则 INCOMPLETE 并列 unread，不能编造覆盖。原始 JSON 最多 16384 UTF-8 字节。')
        task = {'job_id': job, 'instructions': instructions, 'read_inputs': read_inputs,
                'expected_raw_opinion': REVIEW + f'/opinions/{job}.json',
                'budget': {'read_bytes': read_bytes, 'instruction_reserve_bytes': 16384,
                           'output_reserve_bytes': 16384, 'maximum_bytes': 201728,
                           'reserved_total_bytes': read_bytes + 32768,
                           'tokens': 'NOT_MEASURED', 'system_context_bytes': 'NOT_MEASURED'}}
        if task['budget']['reserved_total_bytes'] > task['budget']['maximum_bytes']:
            raise ValueError('task exceeds byte reservation')
        tasks.append(write(root, REVIEW + f'/dispatch/{job}.json', task))
    write(root, REVIEW + '/plan.json', {'kind': 'CH86_KNOWLEDGE_REVIEW_PLAN', 'status': 'NOT_STARTED',
           'independent_opinions': 0, 'input_ci': ci_ref, 'input_commit': ci['headSha'],
           'manifest': binding(root, BASE + '/manifest.json'), 'candidate': candidate,
           'repository_instructions': binding(root, 'AGENTS.md'), 'tasks': tasks,
           'context_fork': 'none', 'maximum_concurrency': 2,
           'qualification': 'RESEARCH_ONLY', 'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'})


def verify(root=ROOT):
    plan = json.loads((root / REVIEW / 'plan.json').read_bytes())
    ci = json.loads(bound_bytes(root, plan['input_ci']))
    assert ci['headSha'] == plan['input_commit'] and ci['status'] == 'completed' and ci['conclusion'] == 'success'
    assert len(ci['jobs']) == 2 and all(j['conclusion'] == 'success' for j in ci['jobs'])
    bound_bytes(root, plan['repository_instructions'])
    manifest = json.loads(bound_bytes(root, plan['manifest']))
    for value in manifest.values():
        for ref in value if isinstance(value, list) else [value]:
            if isinstance(ref, dict) and 'path' in ref:
                bound_bytes(root, ref)
    package = json.loads(bound_bytes(root, manifest['package']))
    scenario, compiled, _ = verify_material(root, package)
    assert compiled == json.loads(bound_bytes(root, manifest['checkpoints']))
    assert checkpoint_view(compiled) == json.loads((root / REVIEW / 'checkpoint-view.json').read_bytes())
    execution = json.loads((root / REVIEW / 'execution.json').read_bytes())
    assert execution['plan'] == binding(root, REVIEW + '/plan.json')
    assert execution['status'] == 'COMPLETE' and execution['context_fork'] == 'none'
    assert execution['maximum_concurrency'] <= plan['maximum_concurrency'] == 2
    assert execution['provider_consumption_proof'] is False and execution['human_qualification'] is False
    attempts = execution['attempts']
    assert len(attempts) == len(plan['tasks']) == 2 and len({a['agent'] for a in attempts}) == 2
    assert {a['job_id'] for a in attempts} == set(JOBS)
    assert {json.loads(bound_bytes(root, ref))['job_id'] for ref in plan['tasks']} == set(JOBS)
    assert execution['qualification'] == 'RESEARCH_ONLY' and execution['production_admission'] == 'NOT_GRANTED' and execution['authority_effect'] == 'NONE'
    read = execution['coordinator_read']
    assert read['read_complete'] is True and read['basis'] == 'SELF_REPORTED_AFTER_TOOL_OUTPUT'
    assert read['opinion_bindings'] == [a['raw_opinion'] for a in attempts]
    verdicts = {}
    for task_ref in plan['tasks']:
        task = json.loads(bound_bytes(root, task_ref))
        attempt = next(a for a in attempts if a['job_id'] == task['job_id'])
        opinion = verify_task(root, task_ref, attempt, plan['candidate'])
        verdicts[task['job_id']] = opinion['overall_assessment']
    return {'status': 'PASS', 'scope': 'CUSTODY_AND_SELF_REPORTED_COVERAGE_ONLY',
            'independent_model_opinions': len(verdicts), 'reader_verdicts': verdicts,
            'provider_consumption_proof': False, 'source_and_corpus_review': 'NOT_CHECKED',
            'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}


def verify_task(root, task_ref, attempt, candidate, expected_context='none'):
    paragraphs = bound_bytes(root, candidate).decode().strip().split('\n\n')
    task = json.loads(bound_bytes(root, task_ref))
    read_bytes = sum(len(bound_bytes(root, r)) for r in task['read_inputs'])
    b = task['budget']
    assert read_bytes == b['read_bytes'] and read_bytes + b['instruction_reserve_bytes'] + b['output_reserve_bytes'] == b['reserved_total_bytes'] <= b['maximum_bytes']
    assert len(task['instructions'].encode()) + len((root / 'AGENTS.md').read_bytes()) <= b['instruction_reserve_bytes']
    assert attempt['dispatch'] == task_ref and attempt['status'] == 'SUBMITTED' and attempt['context_fork'] == expected_context
    assert attempt['raw_opinion']['path'] == task['expected_raw_opinion']
    raw = bound_bytes(root, attempt['raw_opinion'])
    assert len(raw) <= b['output_reserve_bytes']
    opinion = json.loads(raw)
    assert opinion['kind'] == 'CH86_KNOWLEDGE_REVIEW_OPINION' and opinion['job_id'] == task['job_id']
    assert opinion['candidate'] == candidate
    assert opinion['reviewer']['principal_id'] == opinion['reviewer']['session_id'] == attempt['agent']
    assert opinion['reading_status'] == 'COMPLETE' and not opinion['unread']
    expected_reads = {r['path']: r for r in task['read_inputs']}
    claims = opinion['declared_read_files']
    assert len(claims) == len(expected_reads) and {c['path'] for c in claims} == set(expected_reads)
    for claim in claims:
        ref = expected_reads[claim['path']]
        assert claim['read_complete'] is True and claim['sha256'] == ref['sha256'] and claim['bytes'] == len(bound_bytes(root, ref))
    assert len(opinion['findings']) == len(ITEMS) and {f['id'] for f in opinion['findings']} == set(ITEMS)
    for finding in opinion['findings']:
        assert finding['assessment'] in {'PASS', 'FAIL', 'PENDING'} and finding['reason'] and finding['material_citations']
        for citation in finding['material_citations']:
            assert citation['path'] in expected_reads and citation['locator']
        for quote in finding['prose_quotes']:
            assert quote['quote'] and quote['paragraphs']
            assert all(type(n) is int and 1 <= n <= len(paragraphs) and quote['quote'] in paragraphs[n-1] for n in quote['paragraphs'])
    assert opinion['overall_assessment'] in {'PASS', 'FAIL', 'PENDING'}
    assert opinion['qualification'] == 'RESEARCH_ONLY' and opinion['production_admission'] == 'NOT_GRANTED' and opinion['authority_effect'] == 'NONE'
    return opinion


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', type=Path, metavar='INPUT_CI_JSON')
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare)
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
