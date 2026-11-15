"""Validate submitted raw review records; absence never becomes a pass."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes
from prepare_v04_knowledge_review import BASE, JOBS, ROOT, TOPICS, run


def verify(root):
    run(root, True)
    opinions = []
    for job in JOBS:
        path = root / BASE / 'opinions' / f'{job}.json'
        if not path.exists():
            continue
        task = json.loads((root / BASE / 'dispatch' / f'{job}.json').read_bytes())
        opinion = json.loads(path.read_bytes())
        if (opinion.get('kind') != 'CH86_V04_SEMANTIC_OPINION' or opinion.get('job_id') != job
                or opinion.get('evidence') != json.loads((root / BASE / 'plan.json').read_bytes())['evidence']
                or opinion.get('qualification') != 'RESEARCH_ONLY'
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
                if 'quote' in citation and (not citation['quote'] or citation['quote'] not in bound_bytes(root, expected[citation['path']]).decode('utf-8')):
                    raise ValueError(f'{job}: quote absent from cited material')
        opinions.append(opinion)
    if len(opinions) == 2:
        for field in ('principal_id', 'session_id'):
            if len({o['reviewer'][field] for o in opinions}) != 2:
                raise ValueError('reviewers must declare distinct identities')
    return {'status': 'RECORDS_VALID' if len(opinions) == 2 else 'PENDING',
            'registered_opinions': len(opinions), 'independence': 'SELF_REPORTED_NOT_VERIFIED',
            'semantic_verdict': 'NOT_AUTOMATED', 'production_admission': 'NOT_GRANTED'}


if __name__ == '__main__':
    print(json.dumps(verify(ROOT), ensure_ascii=False, sort_keys=True))
