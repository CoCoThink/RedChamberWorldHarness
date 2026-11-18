"""Shared preparation and custody checks for versioned knowledge draft reviews."""
import json
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..generation.records import append_bytes, bound_bytes

JOBS = ('semantic-1', 'semantic-2')
TOPICS = ('ENTRY', 'RAPID_DECLINE', 'DEATH_WITNESSED', 'BAOYU_LEARNS',
          'PRECISE_TIME', 'PHYSIOLOGY', 'MEDICAL_CAUSE', 'LEGACY_BOUNDARY')


def documents(root: Path, directory: str, kind: str, paths: list[str], instructions: str) -> dict:
    refs = []
    byte_count = 0
    for path in paths:
        raw = repository_path(root, path).read_bytes()
        refs.append({'path': path, 'sha256': digest(raw)})
        byte_count += len(raw)
    docs = {}
    dispatches = []
    for job in JOBS:
        scaffold_path = f'{directory}/{job}.scaffold.json'
        scaffold = {'kind': f'{kind}_SEMANTIC_OPINION', 'job_id': job,
                    'reviewer': {'principal_id': '', 'session_id': '', 'identity_basis': ''},
                    'reading_status': 'NOT_STARTED', 'declared_read_files': [], 'unread': [],
                    'findings': [{'topic': topic, 'assessment': 'PENDING', 'reason': '', 'citations': []}
                                 for topic in TOPICS],
                    'overall_assessment': 'PENDING', 'authority_effect': 'NONE',
                    'production_admission': 'NOT_GRANTED'}
        docs[scaffold_path] = scaffold
        dispatch = {'kind': f'{kind}_SEMANTIC_DISPATCH', 'job_id': job,
                    'read_inputs': refs, 'read_bytes': byte_count,
                    'scaffold': {'path': scaffold_path, 'sha256': digest(canonical_bytes(scaffold))},
                    'expected_raw_opinion': f'{directory}/opinions/{job}.json',
                    'instructions': instructions, 'authority_effect': 'NONE',
                    'production_admission': 'NOT_GRANTED'}
        path = f'{directory}/dispatch/{job}.json'
        docs[path] = dispatch
        dispatches.append({'path': path, 'sha256': digest(canonical_bytes(dispatch))})
    docs[f'{directory}/plan.json'] = {'kind': f'{kind}_REVIEW_PLAN', 'dispatches': dispatches,
        'context_fork': 'none', 'maximum_concurrency': 2, 'token_count': 'NOT_MEASURED',
        'status': 'PENDING', 'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED'}
    return docs


def publish(root: Path, docs: dict, *, check: bool = False) -> dict:
    missing = {}
    for path, doc in docs.items():
        target = repository_path(root, path)
        raw = canonical_bytes(doc)
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError('refusing to replace changed review package: ' + path)
        elif check:
            raise ValueError('missing review package: ' + path)
        else:
            missing[path] = raw

    for path, raw in missing.items():
        try:
            append_bytes(root, path, raw)
        except FileExistsError:
            if repository_path(root, path).read_bytes() != raw:
                raise ValueError('refusing to replace changed review package: ' + path) from None
    return {'status': 'PENDING', 'production_admission': 'NOT_GRANTED'}


def verify_opinions(root: Path, directory: str, kind: str, version: str,
                    candidate_path: str) -> tuple[dict, list[dict]]:
    opinions = []
    for job in JOBS:
        path = root / directory / 'opinions' / f'{job}.json'
        if not path.exists():
            continue
        task = json.loads((root / directory / 'dispatch' / f'{job}.json').read_bytes())
        opinion = json.loads(path.read_bytes())
        if (opinion.get('kind') != f'{kind}_SEMANTIC_OPINION' or opinion.get('job_id') != job
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
    custody_path = root / directory / 'opinions' / 'custody.json'
    custody_status = 'UNVERIFIED'
    if custody_path.exists():
        custody = json.loads(custody_path.read_bytes())
        attempts = custody.get('attempts', [])
        if (custody.get('kind') != f'{kind}_REVIEW_CUSTODY'
                or custody.get('basis') != 'ORCHESTRATOR_RECORDED'
                or custody.get('production_admission') != 'NOT_GRANTED'
                or len(attempts) != len(opinions)
                or {a.get('job_id') for a in attempts} != {o['job_id'] for o in opinions}):
            raise ValueError('invalid custody record')
        for attempt in attempts:
            job = attempt['job_id']
            ref = attempt['opinion']
            if ref.get('path') != f'{directory}/opinions/{job}.json':
                raise ValueError('custody opinion path mismatch')
            bound_bytes(root, ref)
            if 'dispatch_ticket' in attempt:
                ticket = attempt['dispatch_ticket']
                if ticket.get('path') != f".codex-dispatch/rcwh_ticket_{version}_semantic_{job[-1]}.md":
                    raise ValueError('custody ticket path mismatch')
                bound_bytes(root, ticket)
            if attempt.get('context_fork') not in ('none', 'all'):
                raise ValueError('invalid custody context')
        expected_context = json.loads((root / directory / 'plan.json').read_bytes())['context_fork']
        if any(a['context_fork'] != expected_context for a in attempts):
            custody_status = 'CONTEXT_DEVIATION'
        elif len(attempts) == len(JOBS):
            custody_status = 'CONTEXT_MATCHES_PLAN'
    report = {'status': 'RECORDS_VALID' if len(opinions) == len(JOBS) else 'PENDING',
            'registered_opinions': len(opinions), 'independence': 'SELF_REPORTED_NOT_VERIFIED',
            'custody': custody_status,
            'semantic_verdict': 'NOT_AUTOMATED', 'production_admission': 'NOT_GRANTED'}
    return report, opinions
