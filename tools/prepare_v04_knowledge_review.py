"""Prepare reproducible independent-review dispatches without asserting a verdict."""
import argparse
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding, bound_bytes
from knowledge_review_evidence import ROOT, verify as verify_evidence

BASE = 'data/writing/knowledge-v04-review'
EVIDENCE = 'data/writing/knowledge-review-evidence/95494597384adfed238a0d0684a511011586b46bb0e5f02041b38579b36f4889.json'
PROJECTION = 'data/writing/knowledge-projections/525e22f2b1c8af7a71bafd4fb021f4bfbf40f89e2d2c34e8f676b2ccf966cf7a.json'
JOBS = ('semantic-1', 'semantic-2')
TOPICS = ('ENTRY', 'RAPID_DECLINE', 'DEATH_WITNESSED', 'BAOYU_LEARNS',
          'PRECISE_TIME', 'PHYSIOLOGY', 'MEDICAL_CAUSE', 'LEGACY_BOUNDARY')


def documents(root):
    evidence = verify_evidence(root, EVIDENCE)
    request = json.loads(bound_bytes(root, evidence['request']))
    projection = request['knowledge_projection']
    if projection != binding(root, PROJECTION):
        raise ValueError('unexpected review projection')
    read = [binding(root, EVIDENCE), evidence['request'], projection,
            *evidence['materials'].values()]
    byte_count = sum(len(bound_bytes(root, ref)) for ref in read)
    docs = {}
    dispatches = []
    for job in JOBS:
        scaffold_path = f'{BASE}/{job}.scaffold.json'
        scaffold = {'kind': 'CH86_V04_SEMANTIC_OPINION', 'job_id': job,
                    'reviewer': {'principal_id': '', 'session_id': '',
                                 'identity_basis': 'NATIVE_TASK_LABEL_NOT_PROVIDER_VERIFIED'},
                    'evidence': binding(root, EVIDENCE), 'reading_status': 'NOT_STARTED',
                    'declared_read_files': [], 'unread': [],
                    'findings': [{'topic': topic, 'assessment': 'PENDING', 'reason': '',
                                  'citations': []} for topic in TOPICS],
                    'overall_assessment': 'PENDING', 'qualification': 'RESEARCH_ONLY',
                    'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}
        docs[scaffold_path] = scaffold
        scaffold_raw = canonical_bytes(scaffold)
        from rcwh.candidate_reviews import digest
        scaffold_ref = {'path': scaffold_path, 'sha256': digest(scaffold_raw)}
        task = {'kind': 'CH86_V04_SEMANTIC_DISPATCH', 'job_id': job,
                'read_inputs': read, 'scaffold': scaffold_ref,
                'expected_raw_opinion': f'{BASE}/opinions/{job}.json',
                'read_bytes': byte_count, 'token_count': 'NOT_MEASURED',
                'instructions': ('独立全文阅读全部 read_inputs，核对各文件摘要；不得阅读另一位读者意见。'
                                 '投影 runtime 包含所有事件，除所列快照外须回放 RAPID_DECLINE；逐项核对命题、各人物及顺序，'
                                 '用候选正文和局部场景具体定位材料支持或缺口；可质疑先前分析。'
                                 '按骨架填写每项 PASS、FAIL 或 PENDING 及理由、文件路径与定位；正文支持须逐字引用。'
                                 'declared_read_files 列出每份 read_inputs 的 path、sha256、bytes 和 read_complete；'
                                 '无法全文读完须标 INCOMPLETE 并列 unread，不得假称完成。'
                                 '如实填写实际任务和会话身份；该自述不是提供者消费证明或真人资格。'
                                 '仅保存原始意见到 expected_raw_opinion，禁止覆盖、修改其他文件、提交或调用外部模型 API。'
                                 '不判旧 C1、来源语料资格或 production。'),
                'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED'}
        path = f'{BASE}/dispatch/{job}.json'
        docs[path] = task
        dispatches.append({'path': path, 'sha256': digest(canonical_bytes(task))})
    docs[f'{BASE}/plan.json'] = {'kind': 'CH86_V04_SEMANTIC_REVIEW_PLAN',
        'evidence': binding(root, EVIDENCE), 'dispatches': dispatches,
        'independent_opinions': 0, 'status': 'NOT_STARTED', 'maximum_concurrency': 2,
        'context_fork': 'none', 'token_count': 'NOT_MEASURED',
        'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED'}
    return docs


def run(root, check):
    for path, data in documents(root).items():
        dest = root / path
        raw = canonical_bytes(data)
        if dest.exists():
            if dest.read_bytes() != raw:
                raise ValueError('refusing to replace changed dispatch: ' + path)
        elif check:
            raise ValueError('missing dispatch: ' + path)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as handle:
                handle.write(raw)
    return {'status': 'PASS', 'review_status': 'NOT_STARTED', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(ROOT, args.check), ensure_ascii=False))
