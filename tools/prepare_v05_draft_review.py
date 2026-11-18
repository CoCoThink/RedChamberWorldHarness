"""Prepare a pinned research-only review of the unadmitted v0.5 draft."""
import json
from pathlib import Path

from rcwh.workflow import knowledge_draft_review as draft_review
from prepare_ch86_knowledge_v05_draft import build, OUTPUT
from knowledge_review_evidence import SOURCES

ROOT = Path(__file__).resolve().parents[1]
BASE = 'data/writing/knowledge-v05-draft-review'
KIND = 'CH86_V05_DRAFT'
TOPICS = draft_review.TOPICS
INSTRUCTIONS = (
    '独立全文阅读所有绑定材料，校验摘要；不得读取另一位本轮意见。'
    '回放草案各事件，逐项核对各人物知识、信念和未指定状态，尤其入口、突变和知死前后。'
    '对候选正文支持给出逐字引文和定位；无依据则标 PENDING，错误标 FAIL。'
    '按骨架如实记录任务、会话身份、每份文件摘要、字节数及是否完整阅读；'
    '未完成不得声明完整。只写指定原始意见，不覆盖，不提交，不调用外部模型 API。'
    '该草案及正文是研究材料，不裁决旧 C1、来源、语料或生产准入。'
)


def documents(root):
    if (root / OUTPUT).read_bytes() != build(root):
        raise ValueError('draft differs from reproducible migration')
    paths = [OUTPUT, 'data/knowledge/v04_ch86.json',
             'tools/prepare_ch86_knowledge_v05_draft.py', *SOURCES.values()]
    return draft_review.documents(root, BASE, KIND, paths, INSTRUCTIONS)


def run(root, check=False):
    return draft_review.publish(root, documents(root), check=check)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    print(json.dumps(run(ROOT, parser.parse_args().check), ensure_ascii=False))
