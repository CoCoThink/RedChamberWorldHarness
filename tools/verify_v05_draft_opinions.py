"""Validate submitted raw review records; absence never becomes a pass."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.workflow import knowledge_draft_review as draft_review
from prepare_v05_draft_review import BASE, ROOT, TOPICS, run
from knowledge_review_evidence import SOURCES

JOBS = ('semantic-1', 'semantic-2')


def verify(root):
    run(root, True)
    report, _ = draft_review.verify_opinions(root, BASE, 'CH86_V05_DRAFT', 'v05', SOURCES['candidate'])
    return report


if __name__ == '__main__':
    print(json.dumps(verify(ROOT), ensure_ascii=False, sort_keys=True))
