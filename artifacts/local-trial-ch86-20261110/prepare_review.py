"""Freeze this trial's bounded research reading packets; never start readers.

This is separate from agent-panel release qualification: local v3 contracts
have not been admitted as formal executable scene contracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = 'artifacts/local-trial-ch86-20261110'
SCENARIO = 'data/writing/local-scenarios/ch86-v1/scenario.json'
CONTRACTS = 'data/writing/local-scenarios/ch86-v1/contracts'
CAP = 131072
OVERHEAD = 16384
OUTPUT = 16384


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def binding(path):
    raw = (ROOT / path).read_bytes()
    return {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def write_once(path, raw, *, check):
    target = ROOT / path
    if target.exists():
        if target.read_bytes() != raw:
            raise ValueError(f'immutable trial file differs: {path}')
    elif check:
        raise ValueError(f'missing trial file: {path}')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def prepare(*, check=False, import_receipt=f'{BASE}/import-v3.json', output=f'{BASE}/review-v3', scenario=SCENARIO, contracts=CONTRACTS):
    imported = json.loads((ROOT / import_receipt).read_bytes())
    candidate = binding(imported['candidate']['path'])
    if candidate['sha256'] != imported['candidate']['sha256']:
        raise ValueError('import candidate has changed')
    tasks = []
    for job, role, scenes in [
        ('blind-1', 'BLIND_LITERARY', []), ('blind-2', 'BLIND_LITERARY', []),
        ('contract-1', 'LOCAL_CONTRACT_AND_STATE', [1, 2, 3]),
        ('contract-2', 'LOCAL_CONTRACT_AND_STATE', [4, 5, 6]),
    ]:
        protocol = (
            '# 独立研究审读\n\n'
            '完整读取且仅评价本任务read_inputs列出的原件，不读作者自查、旧正文、其他读者意见。'
            '这是单回研究审读，无人类、供应商或production资格。'
            '先从未启动骨架另存自己的原始意见；不得覆盖骨架。'
            '给出原文引句、问题与理由，明确未读材料和不能确认之处。'
            '若任一文件未能读完、工具输出截断或输出预算不足，记录INCOMPLETE，不写COMPLETE。'
            '读完是本人声明，不能作为上下文隔离或实际消费的外部证明。\n\n'
        )
        if scenes:
            protocol += (
                '本任务通读完整候选、完整局部模型和所分配的完整合同。逐项核对必写/禁写、'
                '本组checkpoint涉及的事件与消息、角色身份与到场、药碗/药吊子/稿夹/炉火。'
                '以正文引句判定，不能以模型重放PASS代替正文支持。'
                '参与者表是否穷尽、动作未成的识别、实际死时知识边界如有歧义须保留。'
                '原UNKNOWN与新增编辑模型分开，不能将局部叙事补成全局证据。'
                '本任务没有分配原史料或语料，不评价其独立资格；其他三份合同未读，不宣称整回合同全通过。'
                '两组结果需要协调汇总才能判断全部24个事件/5条消息；不要假定另一组已读或已通过。\n'
            )
        else:
            protocol += (
                '本任务只通读候选正文，评价人物声音、动作与信息的可理解性、叙事节奏、'
                '是否以重复动作填充、情感是否成立及结尾效果。请先独立形成意见，'
                '不要猜作者、检索其他版本或把未提供的合同当作事实。'
                '没有分配合同/史料/语料，因此不作其资格判断。\n'
            )
        protocol_path = f'{output}/{job}.md'
        write_once(protocol_path, protocol.encode(), check=check)
        paths = [protocol_path, candidate['path']]
        if scenes:
            paths += [scenario] + [f'{contracts}/86-S{i}.v3.json' for i in scenes]
        scaffold_path = f'{output}/{job}.scaffold.json'
        scaffold = {
            'kind': 'LOCAL_TRIAL_REVIEW_SCAFFOLD', 'job_id': job,
            'candidate': {k: candidate[k] for k in ['path', 'sha256']},
            'reviewer': {'principal_id': None, 'session_id': None},
            'status': 'NOT_STARTED', 'reading_status': 'NOT_STARTED',
            'declared_read_files': [], 'unread_files': [], 'findings': [],
            'assigned_contracts': [f'86-S{i}' for i in scenes],
            'event_and_message_findings': [], 'obligation_findings': [],
            'overall_assessment': 'NOT_CHECKED', 'qualification': 'RESEARCH_ONLY',
            'formal_eligibility': False, 'authority_effect': 'NONE',
        }
        write_once(scaffold_path, encode(scaffold), check=check)
        refs = [binding(p) for p in paths + [scaffold_path]]
        size = sum(r['bytes'] for r in refs)
        total = size + OVERHEAD + OUTPUT
        if total > CAP:
            raise ValueError(f'{job}: complete files + reservations exceed cap: {total}')
        tasks.append({
            'id': job, 'role': role, 'status': 'NOT_STARTED',
            'read_inputs': refs, 'scaffold': scaffold_path,
            'expected_raw_opinion': f'{output}/opinions/{job}.json',
            'budget': {'read_bytes': size, 'instruction_reserve_bytes': OVERHEAD,
                       'output_reserve_bytes': OUTPUT, 'reserved_total_bytes': total,
                       'maximum_bytes': CAP, 'token_capacity': 'NOT_MEASURED'},
        })
    manifest = {
        'schema_version': 1, 'kind': 'LOCAL_TRIAL_REVIEW_PLAN',
        'candidate': candidate, 'import_receipt': binding(import_receipt),
        'tasks': tasks, 'independent_opinions': 0, 'scope_status': 'PENDING',
        'literary_status': 'PENDING', 'source_and_corpus_review': 'NOT_CHECKED',
        'dispatch': {'mode': 'NATIVE_SUBAGENT_ONLY_AFTER_INPUT_CI_AND_AUTHORIZATION',
                     'maximum_concurrency': 3, 'attempts': 0,
                     'adapter_command': None,
                     'retry_policy': 'Preserve incomplete/failed originals; retry sequentially up to 2 times; no replacement opinion by coordinator'},
        'qualification': 'RESEARCH_ONLY', 'formal_eligibility': False,
        'human_qualification': False, 'authority_effect': 'NONE',
    }
    write_once(f'{output}/manifest.json', encode(manifest), check=check)
    return {'status': 'PASS', 'scope': 'PACKET_BYTES_AND_BUDGET_ONLY',
            'jobs': [{ 'id': t['id'], **t['budget']} for t in tasks],
            'independent_opinions': 0, 'authority_effect': 'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--import-receipt', default=f'{BASE}/import-v3.json')
    parser.add_argument('--output-directory', default=f'{BASE}/review-v3')
    parser.add_argument('--scenario', default=SCENARIO)
    parser.add_argument('--contracts-directory', default=CONTRACTS)
    args = parser.parse_args()
    print(json.dumps(prepare(check=args.check, import_receipt=args.import_receipt,
                             output=args.output_directory, scenario=args.scenario,
                             contracts=args.contracts_directory), ensure_ascii=False, indent=2))
