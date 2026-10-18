"""Check declared whole-text coverage and literal quotes, not reader cognition."""
from __future__ import annotations

import json
from pathlib import Path

from rcwh.candidate_reviews import digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance


def check(root: Path, packet_ref: dict, submissions: list[dict], author_sessions: set[str]) -> dict:
    packet = json.loads(bound_bytes(root, packet_ref))
    subjects = {row['id']: row for row in packet['subjects']}
    if len(subjects) != 6 or len(packet['subjects']) != 6 or len(submissions) != 2:
        raise ValueError('exactly six subjects and two submissions required')
    texts = {identity: bound_bytes(root, row['binding']).decode('utf-8')
             for identity, row in subjects.items()}
    ids, sessions, rows = set(), set(), []
    for index, submitted in enumerate(submissions):
        opinion = json.loads(bound_bytes(root, submitted['opinion']))
        observation = json.loads(bound_bytes(root, submitted['observations']))
        errors = validate_instance(opinion, root / 'schemas/agent_review.schema.json')
        if errors:
            raise ValueError('invalid opinion: ' + '; '.join(errors))
        if opinion['report_kind'] != 'AGENT_REVIEW_OPINION' or opinion['packet'] != packet_ref:
            raise ValueError('wrong packet or filing envelope')
        reviewer = opinion['reviewer']
        identity, session = reviewer['id'], reviewer['session_id']
        if identity in ids or session in sessions or session in author_sessions | {packet['coordinator_session_id']}:
            raise ValueError('duplicate reader or exposed author/coordinator session')
        ids.add(identity); sessions.add(session)
        if reviewer['context_isolation']['asserted']:
            raise ValueError('shared-workspace pilot does not assert technical isolation')
        results = opinion['results']
        if len(results) != 6 or {row['subject_id'] for row in results} != set(subjects):
            raise ValueError('missing or duplicate opinion subject')
        for result in results:
            if (result['subject_sha256'] != subjects[result['subject_id']]['binding']['sha256']
                    or result['sample_checks'] != []):
                raise ValueError('stale subject or undeclared samples')
        order = list(subjects)
        if observation['actual_read_order'] != (order if index == 0 else list(reversed(order))):
            raise ValueError('actual declared reading order differs from counterbalance')
        scope = observation['read_scope']
        if 'scope_correction' in submitted:
            correction = json.loads(bound_bytes(root, submitted['scope_correction']))
            if correction['raw_observations'] != submitted['observations']:
                raise ValueError('scope correction must bind exact frozen original')
            corrected = {item['subject_id']: item for item in correction['corrections']}
            if len(corrected) != 6 or set(corrected) != set(subjects):
                raise ValueError('scope correction coverage differs')
            scope = []
            for original in observation['read_scope']:
                item = corrected[original['subject_id']]
                text = texts[original['subject_id']]
                count = len(text.splitlines())
                if (item['binding'] != original['binding']
                        or item['original_line_ranges'] != original['line_ranges']
                        or original['line_ranges'] != [[1, count + 1]]
                        or item['corrected_line_ranges'] != [[1, count]]
                        or item['EOF_display_only']['line_ranges'] != [[count + 1, count + 1]]
                        or not text.endswith('\n')):
                    raise ValueError('correction is not solely an extra EOF display line')
                scope.append({**original, 'line_ranges': item['corrected_line_ranges']})
        if len(scope) != 6 or {row['subject_id'] for row in scope} != set(subjects):
            raise ValueError('missing or duplicate declared full-text scope')
        for item in scope:
            if item['binding'] != subjects[item['subject_id']]['binding'] or item['complete'] is not True:
                raise ValueError('stale or incomplete scope')
            count = len(texts[item['subject_id']].splitlines())
            end = 0
            for left, right in sorted(item['line_ranges']):
                if type(left) is not int or type(right) is not int or not 1 <= left <= right <= count:
                    raise ValueError('invalid reading interval')
                if left > end + 1:
                    raise ValueError('gap in declared reading coverage')
                end = max(end, right)
            if end != count:
                raise ValueError('incomplete declared whole-text coverage')
        evidence = observation['evidence']
        if not evidence or len({item['id'] for item in evidence}) != len(evidence):
            raise ValueError('missing or duplicate quote evidence')
        quoted = set()
        for item in evidence:
            subject = subjects[item['subject_id']]
            lines = texts[item['subject_id']].splitlines(keepends=True)
            left, right = item['line_start'], item['line_end']
            if (type(left) is not int or type(right) is not int or not 1 <= left <= right <= len(lines)
                    or item['path'] != subject['binding']['path'] or not item['quote']
                    or item['quote'] not in ''.join(lines[left - 1:right])):
                raise ValueError('quote is not exact within bound lines')
            quoted.add(item['subject_id'])
        if quoted != set(subjects):
            raise ValueError('each full text needs actual quote evidence')
        rows.append({'reviewer': reviewer, 'opinion': submitted['opinion'],
                     'observations': submitted['observations'],
                     **({'scope_correction': submitted['scope_correction']} if 'scope_correction' in submitted else {}),
                     'quote_count': len(evidence),
                     'raw_verdicts': [row['verdict'] for row in results]})
    return {'schema_version': 1, 'kind': 'PILOT_READING_MECHANICAL_CUSTODY',
            'status': 'BYTE_QUOTES_AND_DECLARED_COVERAGE_PASS_NOT_QUALIFICATION',
            'packet': packet_ref, 'readers': rows, 'authority_effect': 'NONE',
            'limitation': 'Exact bytes, literal quotes and declared interval unions only; no proof of cognition, independence, literary adoption or protection semantics.'}
