"""Prepare a pinned research-only review of the unadmitted v0.5 draft."""
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import binding
from prepare_ch86_knowledge_v05_draft import build, OUTPUT
from knowledge_review_evidence import SOURCES

ROOT = Path(__file__).resolve().parents[1]
BASE = 'data/writing/knowledge-v05-draft-review'
TOPICS = ('ENTRY', 'RAPID_DECLINE', 'DEATH_WITNESSED', 'BAOYU_LEARNS',
          'PRECISE_TIME', 'PHYSIOLOGY', 'MEDICAL_CAUSE', 'LEGACY_BOUNDARY')


def documents(root):
    if (root / OUTPUT).read_bytes() != build(root):
        raise ValueError('draft differs from reproducible migration')
    paths = [OUTPUT, 'data/knowledge/v04_ch86.json',
             'tools/prepare_ch86_knowledge_v05_draft.py', *SOURCES.values()]
    refs = [binding(root, path) for path in paths]
    docs = {}
    dispatches = []
    for job in ('semantic-1', 'semantic-2'):
        scaffold_path = f'{BASE}/{job}.scaffold.json'
        scaffold = {'kind': 'CH86_V05_DRAFT_SEMANTIC_OPINION', 'job_id': job,
                    'reviewer': {'principal_id': '', 'session_id': '', 'identity_basis': ''},
                    'reading_status': 'NOT_STARTED', 'declared_read_files': [], 'unread': [],
                    'findings': [{'topic': t, 'assessment': 'PENDING', 'reason': '', 'citations': []} for t in TOPICS],
                    'overall_assessment': 'PENDING', 'authority_effect': 'NONE',
                    'production_admission': 'NOT_GRANTED'}
        docs[scaffold_path] = scaffold
        dispatch = {'kind': 'CH86_V05_DRAFT_SEMANTIC_DISPATCH', 'job_id': job,
                    'read_inputs': refs, 'read_bytes': sum((root / p).stat().st_size for p in paths),
                    'scaffold': {'path': scaffold_path, 'sha256': digest(canonical_bytes(scaffold))},
                    'expected_raw_opinion': f'{BASE}/opinions/{job}.json',
                    'instructions': ('独立全文阅读所有绑定材料，校验摘要；不得读取另一位本轮意见。'
                                     '回放草案各事件，逐项核对各人物知识、信念和未指定状态，尤其入口、突变和知死前后。'
                                     '对候选正文支持给出逐字引文和定位；无依据则标 PENDING，错误标 FAIL。'
                                     '按骨架如实记录任务、会话身份、每份文件摘要、字节数及是否完整阅读；'
                                     '未完成不得声明完整。只写指定原始意见，不覆盖，不提交，不调用外部模型 API。'
                                     '该草案及正文是研究材料，不裁决旧 C1、来源、语料或生产准入。'),
                    'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED'}
        path = f'{BASE}/dispatch/{job}.json'
        docs[path] = dispatch
        dispatches.append({'path': path, 'sha256': digest(canonical_bytes(dispatch))})
    docs[f'{BASE}/plan.json'] = {'kind': 'CH86_V05_DRAFT_REVIEW_PLAN', 'dispatches': dispatches,
        'context_fork': 'none', 'maximum_concurrency': 2, 'token_count': 'NOT_MEASURED',
        'status': 'PENDING', 'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED'}
    return docs


def run(root, check=False):
    for path, doc in documents(root).items():
        target = root / path
        raw = canonical_bytes(doc)
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError('refusing to replace changed review package: ' + path)
        elif check:
            raise ValueError('missing review package: ' + path)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(raw)
    return {'status': 'PENDING', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    print(json.dumps(run(ROOT, parser.parse_args().check), ensure_ascii=False))
