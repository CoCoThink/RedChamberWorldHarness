"""Actual reader output keeps local scope, negative verdicts and isolation limits."""
import json
from pathlib import Path

import pytest

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def _quotes(value):
    if isinstance(value, dict):
        if {'path', 'line_start', 'line_end', 'quote'} <= value.keys():
            yield value
        for child in value.values():
            yield from _quotes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _quotes(child)


def _verify_quotes(report):
    rows = list(_quotes(report))
    for row in rows:
        path = ROOT / row['path']
        assert path.resolve().is_relative_to(ROOT)
        text = path.read_text(encoding='utf-8')
        assert row['quote'] in '\n'.join(text.splitlines()[row['line_start'] - 1:row['line_end']])
    return len(rows)


def test_all_twenty_native_long_imports_keep_real_short_lineage():
    inventory = json.loads((BASE / 'frozen-revisions-inventory-v10.json').read_bytes())
    assert inventory['registered_v1_count'] == 20
    assert inventory['registered_narrow_v2_count'] == 1
    assert [row['chapter'] for row in inventory['frozen_v1_chapters']] == list(range(81, 101))
    for row in inventory['frozen_v1_chapters']:
        receipt = json.loads(bound_bytes(ROOT, row['import_receipt']))
        assert receipt['status'] == 'PASS' and receipt['literary_acceptance'] == 'NOT_GRANTED'
        assert receipt['result']['draft'] == row['registered_draft']
        draft = json.loads(bound_bytes(ROOT, row['registered_draft']))
        assert draft['parent'] == row['parent']
        assert bound_bytes(ROOT, draft['candidate']) == bound_bytes(ROOT, row['candidate'])
        assert draft['formal_eligibility'] is False and draft['human_qualification'] is False
        parent = json.loads(bound_bytes(ROOT, draft['parent']))
        assert parent['parent'] is None
        assert parent['package'] == draft['package']
        assert len(bound_bytes(ROOT, parent['candidate']).decode('utf-8')) < 3000


def test_independent_two_query_check_preserves_ambiguity_without_clean_bill():
    custody = json.loads((BASE / 'continuity/independent-two-queries-custody-v1.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert _verify_quotes(report) == custody['verified_quotes'] == 31
    assert report['summary']['query_statuses'] == {
        'Q1_CH94_TIME_ORDER': 'AMBIGUOUS',
        'Q2_CH95_CH96_TWO_AND_HALF': 'AMBIGUOUS',
    }
    assert report['summary']['confirmed_fail_count'] == 0
    assert report['summary']['no_defect_certification'] is False
    assert report['authority']['human_independent_certification'] is False
    assert report['exposure_and_limits']['prior_reader_reports_read'] is False
    assert len(report['reading_record']['sources']) == 3
    for row in report['reading_record']['sources']:
        text = bound_bytes(ROOT, {'path': row['path'], 'sha256': row['sha256']}).decode('utf-8')
        assert row['complete_body_read'] is True
        assert len(text.splitlines()) == row['physical_line_count']


def test_completed_wholebook_is_one_reader_with_retained_risks_not_adoption():
    custody = json.loads((BASE / 'continuity/fullbook-reader1-final-custody-v1.json').read_bytes())
    final, synthesis = [json.loads(bound_bytes(ROOT, row['report'])) for row in custody['reports']]
    assert [_verify_quotes(report) for report in (final, synthesis)] == [106, 17]
    assert final['confirmed_failures'] == []
    assert synthesis['reader']['chapter_count'] == 20
    assert synthesis['reader']['independent_reader_count_claimed'] == 1
    assert synthesis['status'] == 'NOT_ADOPTED_NOT_RELEASED'
    assert synthesis['actual_scope']['unread_selected_chapters'] == []
    assert synthesis['actual_scope']['segment_quote_count'] == 404
    assert synthesis['actual_scope']['complete_body_lines'] == 2211
    total = 0
    for ref in synthesis['bound_segment_reports']:
        report = json.loads(bound_bytes(ROOT, {'path': ref['path'], 'sha256': ref['sha256']}))
        assert _verify_quotes(report) == ref['validated_quote_count']
        total += ref['validated_quote_count']
        for row in report['actual_coverage']:
            text = bound_bytes(ROOT, {'path': row['path'], 'sha256': row['sha256']}).decode('utf-8')
            assert row['complete'] is True
            assert row['line_end'] == len(text.splitlines())
            if row['chapter'] == 91:
                assert row['revision'] == 'v2'
    assert total == 404
    assert len(synthesis['risk_register']['strongest_unresolved_cross_segment_queries']) == 2
    assert synthesis['risk_register']['confirmed_failures_in_this_synthesis'] == []
    assert synthesis['risk_register']['other_retained_unknowns']


@pytest.mark.parametrize('first,last,quotes,unknowns', [(81, 85, 86, 4), (86, 90, 103, 5), (91, 95, 109, 5)])
def test_continuity_segments_are_not_whole_book_pass(first, last, quotes, unknowns):
    report = json.loads((BASE / f'continuity/reader1-ch{first}-{last}-v1.json').read_bytes())
    custody = json.loads((BASE / f'continuity/reader1-ch{first}-{last}-custody-v1.json').read_bytes())
    assert json.loads(bound_bytes(ROOT, custody['report'])) == report
    assert report['status'] == 'NOT_ADOPTED_NOT_RELEASED'
    assert report['authority_effect'] == 'NONE'
    assert report['confirmed_failures'] == []
    assert len(report['uncertainties']) == unknowns
    assert [row['chapter'] for row in report['actual_coverage']] == list(range(first, last + 1))
    for row in report['actual_coverage']:
        text = bound_bytes(ROOT, {'path': row['path'], 'sha256': row['sha256']}).decode('utf-8')
        assert row['complete'] is True
        assert row['line_start'] == 1 and row['line_end'] == len(text.splitlines())
    assert _verify_quotes(report) == custody['verified_quotes'] == quotes


def test_late_first_stage_resolves_interface_quotes_without_claiming_threeway():
    directory = BASE / 'comparison/coordinator'
    custody = json.loads((directory / 'late-reader-one-stage-one-custody-v1.json').read_bytes())
    interfaces = json.loads((directory / 'late-reader-one-stage-one-interface-custody-v1.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert _verify_quotes(report) == custody['quote_checks'] == interfaces['path_line_quote_checks'] == 52
    assert interfaces['additional_evidence_id_resolved_checks'] == 28
    assert interfaces['total_checks'] == 80
    assert report['not_final_three_subject_opinion'] is True
    evidence = {row['id']: row for row in report['evidence']}
    count = 0
    for interface in report['interfaces']:
        for side in ('side_a', 'side_b'):
            quoted = interface[side]
            matches = []
            for ref in quoted['evidence_ids']:
                row = evidence[ref]
                text = (ROOT / row['path']).read_text(encoding='utf-8')
                matches.append(quoted['quote'] in '\n'.join(text.splitlines()[row['line_start'] - 1:row['line_end']]))
            assert any(matches)
            count += 1
    assert count == 28
    assert custody['is_final_threeway_opinion'] is False


def test_late_second_stage_retains_sock_timeline_failure():
    custody = json.loads((BASE / 'comparison/coordinator/late-reader-one-stage-two-custody-v1.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert _verify_quotes(report) == custody['path_line_quote_checks'] == 52
    assert custody['additional_interface_checks'] == 26 and custody['total_checks'] == 78
    assert custody['is_final_threeway_opinion'] is False
    assert report['not_final_three_subject_opinion'] is True
    failure = report['hard_failures'][0]
    assert failure['id'] == 'F01' and failure['status'] == 'CONFIRMED_LOCAL_FAIL'
    assert failure['side_a']['line_start'] == 77
    assert failure['side_b']['line_start'] == 95
    evidence = {row['id']: row for row in report['evidence']}
    for interface in report['interfaces']:
        for key in ('side_a', 'side_b'):
            side = interface[key]
            assert any(side['quote'] in '\n'.join((ROOT / evidence[ref]['path']).read_text(encoding='utf-8').splitlines()[evidence[ref]['line_start'] - 1:evidence[ref]['line_end']])
                       for ref in side['evidence_ids'])


@pytest.mark.parametrize('name,quotes', [('one', 91), ('two', 85)])
def test_middle_second_stage_keeps_partial_scope_and_exact_evidence(name, quotes):
    ref = BASE / f'comparison/coordinator/middle-reader-{name}-stage-two-custody-v1.json'
    custody = json.loads(ref.read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert _verify_quotes(report) == custody['quote_checks'] == quotes
    assert custody['is_final_threeway_opinion'] is False
    assert custody['registration'] == 'NOT_ATTEMPTED_STAGE_OBSERVATIONS_ONLY'
    assert report['authority_effect'] == 'NONE'


@pytest.mark.parametrize('name,quotes', [('one', 94), ('two', 58)])
def test_middle_first_stage_observations_do_not_claim_completed_threeway(name, quotes):
    ref = BASE / f'comparison/coordinator/middle-reader-{name}-stage-one-custody-v1.json'
    custody = json.loads(ref.read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert _verify_quotes(report) == custody['quote_checks'] == quotes
    assert custody['is_final_threeway_opinion'] is False
    assert custody['registration'] == 'NOT_ATTEMPTED_STAGE_OBSERVATIONS_ONLY'
    assert report['authority_effect'] == 'NONE'
    if name == 'one':
        assert report['is_final_opinion'] is False
        assert report['is_three_way_comparison'] is False
        assert report['provisional_local_verdict']['verdict'] == 'PENDING'
        assert report['confirmed_mutual_exclusions'][0]['id'] == 'M1-86-SNOW-ROUNDTRIP'
    else:
        assert report['subject_index_zero_based'] == 2
        assert report['hard_failures']['count'] == 0
        assert report['hard_failures']['findings'] == []


def test_completed_four_segment_threeway_is_not_automatic_winner_or_adoption():
    report = json.loads((BASE / 'comparison/coordinator/threeway-full-reading-synthesis-v1.json').read_bytes())
    assert report['coverage'] == {
        'segments': 4, 'declared_reader_contexts': 8,
        'complete_subject_sequences_read': 24, 'chapter_version_readings': 120,
        'qualification': 'Actual bounded model full-sequence reading, not human independent admission or controlled causal trial',
    }
    assert report['automatic_winner'] is None and report['adoption'] == 'NOT_GRANTED'
    assert report['formal_eligibility'] is False and report['human_qualification'] is False
    covered = []
    for row in report['segments']:
        covered.extend(row['chapters'])
        summary = json.loads(bound_bytes(ROOT, row['summary']))
        assert summary['decoded'] == row['decoded']
        assert len(row['registrations']) == 2
        current = next(item for item in row['decoded'] if item['research_identity'].startswith('research-current-'))
        assert current['panel_status'] == 'PENDING'
    assert covered == list(range(81, 101))
    assert report['retained_negatives'] and report['raw_opinion_disagreements']


def test_late_completed_opinions_do_not_vote_away_sock_fail_or_pending():
    report = json.loads((BASE / 'comparison/coordinator/late-reading-summary-v1.json').read_bytes())
    assert report['automatic_winner'] is None and report['adoption'] == 'NOT_GRANTED'
    decoded = {row['research_identity']: row for row in report['decoded']}
    assert sorted(decoded['reference-copy-late']['raw_verdicts']) == ['FAIL', 'PENDING']
    assert decoded['reference-copy-late']['panel_status'] == 'FAIL'
    for identity in ('research-current-late', 'research-prior-late'):
        assert sorted(decoded[identity]['raw_verdicts']) == ['PASS', 'PENDING']
        assert decoded[identity]['panel_status'] == 'PENDING'
        assert decoded[identity]['distinct_full_reviewer_count'] == 0
    counts = ([52, 52, 48], [57, 71, 59])
    for ref, expected in zip(report['registrations'], counts, strict=True):
        registration = json.loads(bound_bytes(ROOT, ref))
        opinion = json.loads(bound_bytes(ROOT, registration['opinion']))
        assert opinion['reviewer']['context_isolation']['asserted'] is False
        assert all(row['sample_checks'] == [] for row in opinion['results'])
        assert [_verify_quotes(json.loads(bound_bytes(ROOT, stage))) for stage in registration['stage_observations']] == expected
        bound_bytes(ROOT, registration['comparison'])


def test_middle_complete_comparison_retains_mourning_pending_and_original_fail():
    report = json.loads((BASE / 'comparison/coordinator/middle-reading-summary-v1.json').read_bytes())
    assert report['automatic_winner'] is None and report['adoption'] == 'NOT_GRANTED'
    decoded = {row['research_identity']: row for row in report['decoded']}
    assert sorted(decoded['research-current-middle']['raw_verdicts']) == ['PASS', 'PENDING']
    assert decoded['research-prior-middle']['raw_verdicts'] == ['PASS', 'PASS']
    assert decoded['reference-copy-middle']['raw_verdicts'] == ['FAIL', 'FAIL']
    assert decoded['reference-copy-middle']['panel_status'] == 'FAIL'
    for row in decoded.values():
        assert row['distinct_full_reviewer_count'] == 0
    for ref, expected in zip(report['registrations'], ([94, 91, 84], [66, 85, 58]), strict=True):
        registration = json.loads(bound_bytes(ROOT, ref))
        opinion = json.loads(bound_bytes(ROOT, registration['opinion']))
        assert opinion['reviewer']['context_isolation']['asserted'] is False
        assert all(row['sample_checks'] == [] for row in opinion['results'])
        assert [_verify_quotes(json.loads(bound_bytes(ROOT, stage))) for stage in registration['stage_observations']] == expected
        bound_bytes(ROOT, registration['comparison'])


@pytest.mark.parametrize('stage,count', [('one', 59), ('two', 71)])
def test_late_reverse_reader_partial_evidence_does_not_override_other_reader(stage, count):
    custody = json.loads((BASE / f'comparison/coordinator/late-reader-two-stage-{stage}-custody-v1.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert _verify_quotes(report) == custody['quote_checks'] == count
    assert custody['is_final_threeway_opinion'] is False
    assert custody['registration'] == 'NOT_ATTEMPTED_STAGE_OBSERVATIONS_ONLY'
    assert report['authority_effect'] == 'NONE'


def test_tail_threeway_keeps_scroll_fail_and_zero_qualifying_isolated_reviewers():
    report = json.loads((BASE / 'comparison/coordinator/tail-reading-summary-v1.json').read_bytes())
    assert report['automatic_winner'] is None and report['adoption'] == 'NOT_GRANTED'
    decoded = {row['research_identity']: row for row in report['decoded']}
    assert decoded['reference-copy-tail']['raw_verdicts'] == ['FAIL', 'FAIL']
    assert decoded['reference-copy-tail']['panel_status'] == 'FAIL'
    for identity in ('research-current-tail', 'research-prior-tail'):
        assert decoded[identity]['raw_verdicts'] == ['PASS', 'PASS']
        assert decoded[identity]['panel_status'] == 'PENDING'
        assert decoded[identity]['distinct_full_reviewer_count'] == 0
    for ref, count in zip(report['registrations'], (57, 40), strict=True):
        registration = json.loads(bound_bytes(ROOT, ref))
        opinion = json.loads(bound_bytes(ROOT, registration['opinion']))
        observation = json.loads(bound_bytes(ROOT, registration['observations']))
        assert _verify_quotes(observation) == registration['coordinator_exact_quote_checks'] == count
        assert opinion['reviewer']['context_isolation']['asserted'] is False
        assert opinion['independent_human_admission'] is False
        assert all(row['sample_checks'] == [] for row in opinion['results'])
    assert any('not a fifth automatic' in item for item in report['limitations'])


def test_early_threeway_keeps_two_fail_opinions_and_unproven_isolation():
    report = json.loads((BASE / 'comparison/coordinator/early-reading-summary-v1.json').read_bytes())
    assert report['automatic_winner'] is None and report['adoption'] == 'NOT_GRANTED'
    decoded = {row['research_identity']: row for row in report['decoded']}
    assert decoded['reference-copy-early']['raw_verdicts'] == ['FAIL', 'FAIL']
    assert decoded['reference-copy-early']['panel_status'] == 'FAIL'
    for identity in ('research-current-early', 'research-prior-early'):
        assert decoded[identity]['raw_verdicts'] == ['PASS', 'PASS']
        assert decoded[identity]['panel_status'] == 'PENDING'
        assert decoded[identity]['distinct_full_reviewer_count'] == 1
    for ref, expected_count in zip(report['registrations'], (35, 30), strict=True):
        registration = json.loads(bound_bytes(ROOT, ref))
        observation = json.loads(bound_bytes(ROOT, registration['observations']))
        opinion = json.loads(bound_bytes(ROOT, registration['opinion']))
        assert _verify_quotes(observation) == expected_count
        assert registration['coordinator_exact_quote_checks'] == expected_count
        assert len(opinion['results']) == 3
        assert all(row['sample_checks'] == [] for row in opinion['results'])
        assert opinion['authority_effect'] == 'NONE'
        assert opinion['independent_human_admission'] is False
    assert 'do not replace old packets' in report['historical_negative_preservation']
