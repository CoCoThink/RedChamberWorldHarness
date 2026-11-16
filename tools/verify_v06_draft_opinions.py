"""Validate submitted raw review records; absence never becomes a pass."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
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
    opinions = []
    candidate_path = SOURCES['candidate']
    for job in JOBS:
        path = root / BASE / 'opinions' / f'{job}.json'
        if not path.exists():
            continue
        task = json.loads((root / BASE / 'dispatch' / f'{job}.json').read_bytes())
        opinion = json.loads(path.read_bytes())
        if (opinion.get('kind') != 'CH86_V06_DRAFT_SEMANTIC_OPINION' or opinion.get('job_id') != job
                or opinion.get('authority_effect') != 'NONE'
                or opinion.get('production_admission') != 'NOT_GRANTED'):
            raise ValueError(f'{job}: invalid opinion identity or authority')
        reviewer = opinion.get('reviewer', {})
        if not reviewer.get('principal_id') or not reviewer.get('session_id') or reviewer.get('identity_basis') != 'NATIVE_TASK_LABEL_NOT_PROVIDER_VERIFIED':
            raise ValueError(f'{job}: reviewer identity missing')
        reads = opinion.get('declared_read_files', [])
        expected = {ref['path']: ref for ref in task['read_inputs']}
        if len(reads) != len(expected) or {r.get('path') for r in reads} != set(expected):
            raise ValueError(f'{job}: declared read set incomplete or duplicated')
        for entry in reads:
            ref = expected[entry['path']]
            raw = bound_bytes(root, ref)
            if entry.get('sha256') != ref['sha256'] or entry.get('bytes') != len(raw) or entry.get('read_complete') is not True:
                raise ValueError(f'{job}: incomplete read declaration')
        if opinion.get('reading_status') != 'COMPLETE' or opinion.get('unread') != []:
            raise ValueError(f'{job}: reading incomplete')
        findings = opinion.get('findings', [])
        if len(findings) != len(TOPICS) or {f.get('topic') for f in findings} != set(TOPICS):
            raise ValueError(f'{job}: missing or duplicate topic')
        statuses = {'PASS', 'FAIL', 'PENDING'}
        if opinion.get('overall_assessment') not in statuses:
            raise ValueError(f'{job}: invalid overall assessment')
        for finding in findings:
            if finding.get('assessment') not in statuses or not str(finding.get('reason', '')).strip() or not finding.get('citations'):
                raise ValueError(f'{job}: incomplete finding')
            for citation in finding['citations']:
                if citation.get('path') not in expected or not str(citation.get('locator', '')).strip():
                    raise ValueError(f'{job}: invalid citation')
                if citation['path'] == candidate_path and not citation.get('quote'):
                    raise ValueError(f'{job}: candidate citation requires a verbatim quote')
                if 'quote' in citation and (not citation['quote'] or citation['quote'] not in bound_bytes(root, expected[citation['path']]).decode('utf-8')):
                    raise ValueError(f'{job}: quote absent from cited material')
        opinions.append(opinion)
    if len(opinions) == 2:
        for field in ('principal_id', 'session_id'):
            if len({o['reviewer'][field] for o in opinions}) != 2:
                raise ValueError('reviewers must declare distinct identities')
    custody_path = root / BASE / 'opinions' / 'custody.json'
    custody_status = 'UNVERIFIED'
    if custody_path.exists():
        custody = json.loads(custody_path.read_bytes())
        attempts = custody.get('attempts', [])
        if (custody.get('kind') != 'CH86_V06_DRAFT_REVIEW_CUSTODY'
                or custody.get('basis') != 'ORCHESTRATOR_RECORDED'
                or custody.get('production_admission') != 'NOT_GRANTED'
                or len(attempts) != len(opinions)
                or {a.get('job_id') for a in attempts} != {o['job_id'] for o in opinions}):
            raise ValueError('invalid custody record')
        for attempt in attempts:
            job = attempt['job_id']
            ref = attempt['opinion']
            if ref.get('path') != f'{BASE}/opinions/{job}.json':
                raise ValueError('custody opinion path mismatch')
            bound_bytes(root, ref)
            if 'dispatch_ticket' in attempt:
                ticket = attempt['dispatch_ticket']
                if ticket.get('path') != f".codex-dispatch/rcwh_ticket_v06_semantic_{job[-1]}.md":
                    raise ValueError('custody ticket path mismatch')
                bound_bytes(root, ticket)
            if attempt.get('context_fork') not in ('none', 'all'):
                raise ValueError('invalid custody context')
        expected_context = json.loads((root / BASE / 'plan.json').read_bytes())['context_fork']
        if any(a['context_fork'] != expected_context for a in attempts):
            custody_status = 'CONTEXT_DEVIATION'
        elif len(attempts) == len(JOBS):
            custody_status = 'CONTEXT_MATCHES_PLAN'
    decision = verify_disposition(root, opinions, custody_status)
    return {'status': 'RECORDS_VALID' if len(opinions) == 2 else 'PENDING',
            'registered_opinions': len(opinions), 'independence': 'SELF_REPORTED_NOT_VERIFIED',
            'custody': custody_status,
            'reviewer_assessments': {o['job_id']: {
                'overall': o['overall_assessment'],
                'topics': {f['topic']: f['assessment'] for f in o['findings']}}
                for o in opinions},
            'coordinator_decision': decision,
            'semantic_verdict': 'NOT_AUTOMATED', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    print(json.dumps(verify(ROOT), ensure_ascii=False, sort_keys=True))
