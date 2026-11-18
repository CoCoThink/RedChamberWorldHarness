"""Validate submitted raw review records; absence never becomes a pass."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from rcwh.workflow import knowledge_draft_review as draft_review
from prepare_v06_draft_review import BASE, ROOT, TOPICS, run
from knowledge_review_evidence import SOURCES
from prepare_ch86_knowledge_v06_draft import OUTPUT

JOBS = ('semantic-1', 'semantic-2')


def verify_disposition(root, opinions, custody_status):
    """Check a coordinator's bounded decision, never derive it from PASS counts."""
    path = root / BASE / 'disposition.json'
    if not path.exists():
        return 'NOT_RECORDED'
    disposition = json.loads(path.read_bytes())
    if (disposition.get('kind') != 'CH86_V06_DRAFT_COORDINATOR_DISPOSITION'
            or disposition.get('decision') != 'ACCEPT_FOR_RESEARCH_WITH_LIMITS'
            or disposition.get('authority_effect') != 'NONE'
            or disposition.get('production_admission') != 'NOT_GRANTED'
            or disposition.get('legacy_c1') != 'PENDING'
            or disposition.get('runtime_default') != 'UNCHANGED'
            or disposition.get('strict_understanding') != 'NOT_ESTABLISHED'):
        raise ValueError('invalid or authority-bearing coordinator disposition')
    if len(opinions) != len(JOBS) or custody_status != 'CONTEXT_MATCHES_PLAN':
        raise ValueError('coordinator disposition requires complete review custody')
    draft = disposition.get('draft', {})
    if draft.get('path') != OUTPUT:
        raise ValueError('coordinator disposition draft mismatch')
    bound_bytes(root, draft)
    refs = disposition.get('opinions', [])
    expected = {f'{BASE}/opinions/{job}.json' for job in JOBS}
    if len(refs) != len(JOBS) or {ref.get('path') for ref in refs} != expected:
        raise ValueError('coordinator disposition opinion set mismatch')
    for ref in refs:
        bound_bytes(root, ref)
    if disposition.get('recorded_assessments') != {o['job_id']: o['overall_assessment'] for o in opinions}:
        raise ValueError('coordinator disposition misstates original assessments')
    limits = disposition.get('limitations', [])
    if len(limits) != 3 or {item.get('id') for item in limits} != {
            'RECEIPT_NOT_UNDERSTANDING', 'LEGACY_NOT_EQUIVALENT', 'QUALIFICATION_SEPARATE'}:
        raise ValueError('coordinator disposition omits required limitations')
    expected_topics = {
        'RECEIPT_NOT_UNDERSTANDING': ('semantic-2', 'BAOYU_LEARNS'),
        'LEGACY_NOT_EQUIVALENT': ('semantic-2', 'LEGACY_BOUNDARY'),
        'QUALIFICATION_SEPARATE': ('semantic-1', 'LEGACY_BOUNDARY'),
    }
    by_job = {o['job_id']: o for o in opinions}
    for item in limits:
        if not str(item.get('decision', '')).strip():
            raise ValueError('coordinator limitation needs an explicit decision')
        job, topic = expected_topics[item['id']]
        if item.get('opinion_job') != job or item.get('topic') != topic:
            raise ValueError('coordinator limitation source mismatch')
        finding = next(f for f in by_job[job]['findings'] if f['topic'] == topic)
        if item.get('reviewer_reason') != finding['reason']:
            raise ValueError('coordinator limitation must preserve the original reason')
    return disposition['decision']


def verify(root):
    run(root, True)
    report, opinions = draft_review.verify_opinions(root, BASE, 'CH86_V06_DRAFT', 'v06', SOURCES['candidate'])
    decision = verify_disposition(root, opinions, report['custody'])
    report['reviewer_assessments'] = {opinion['job_id']: {
        'overall': opinion['overall_assessment'],
        'topics': {finding['topic']: finding['assessment'] for finding in opinion['findings']}}
        for opinion in opinions}
    report['coordinator_decision'] = decision
    return report


if __name__ == '__main__':
    print(json.dumps(verify(ROOT), ensure_ascii=False, sort_keys=True))
