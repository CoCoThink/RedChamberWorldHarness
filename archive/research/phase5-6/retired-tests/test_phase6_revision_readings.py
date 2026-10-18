"""Actual model reading custody preserves local failures and reading limits."""
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import digest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_ch88_99_reading_keeps_missing_seed_and_actual_terminal_scope():
    report = json.loads((BASE / 'readings/ch88-99-v1-reader1.json').read_bytes())
    assert report['disposition'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['automatic_PASS'] is False and report['automatic_ADOPT'] is False
    assert [row['chapter'] for row in report['chapters']] == [88, 99]
    total = 0
    for chapter in report['chapters']:
        assert chapter['determinate_text_defect_audit']['confirmed_text_FAILs'] == []
        assert chapter['literary_reservations_not_determinate_FAIL']
        for quote in chapter['evidence']:
            marker = 'artifacts/agent_research/phase6/'
            assert marker in quote['path']
            path = ROOT / marker / quote['path'].split(marker, 1)[1]
            text = path.read_text(encoding='utf-8')
            assert quote['quote'] in '\n'.join(text.splitlines()[quote['line_start'] - 1:quote['line_end']])
            total += 1
    assert total == 45
    boundary = report['actual_reading_scope']['adjacent_boundary_only']
    assert boundary['read_entire_chapter'] is False
    marker = 'artifacts/agent_research/phase6/'
    path = ROOT / marker / boundary['path'].split(marker, 1)[1]
    assert digest(path.read_bytes()) == boundary['sha256']
    for quote in boundary['boundary_quotes']:
        assert quote['quote'] in '\n'.join(path.read_text(encoding='utf-8').splitlines()[quote['line_start'] - 1:quote['line_end']])


def test_ch89_reading_preserves_qualified_observations_not_historical_execution():
    report = json.loads((BASE / 'readings/ch89-v1-reader1.json').read_bytes())
    assert report['disposition'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['automatic_PASS'] is False and report['automatic_ADOPT'] is False
    assert report['overall_feedback']['confirmed_internal_contradiction_count'] == 0
    assert report['overall_feedback']['historical_execution_inferred'] is False
    assert len(report['literary_risks']) == 4
    assert len(report['verbatim_evidence']) == 21
    for quote in report['verbatim_evidence']:
        marker = 'artifacts/agent_research/phase6/'
        assert marker in quote['path']
        path = ROOT / marker / quote['path'].split(marker, 1)[1]
        assert quote['exact_quote'] in '\n'.join(path.read_text(encoding='utf-8').splitlines()[quote['line_start'] - 1:quote['line_end']])


def test_ch90_reading_preserves_rice_gap_and_rebuke_timing():
    report = json.loads((BASE / 'readings/ch90-v1-reader1.json').read_bytes())
    assert report['disposition'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['literary_acceptance'] == 'NOT_GRANTED'
    assert report['reading_custody']['candidate']['all_lines_read'] is True
    assert report['continuity_audit']['definite_hard_contradictions_found'] == []
    assert {row['id'] for row in report['continuity_audit']['localized_gaps_and_ambiguities']} == {'C01', 'C02', 'C03'}
    assert report['literary_assessment_separate_registers']['审核式纠偏']
    assert len(report['evidence']) == 24
    refs = [report['reading_custody'][key] for key in ('candidate', 'disclosure', 'notes90', 'first_ten_editor90')]
    refs += report['reading_custody']['selected_contracts']
    for ref in refs:
        path = ROOT / ref['path'].split('/RedChamberWorldHarness/', 1)[1]
        assert digest(path.read_bytes()) == ref['sha256']
    for quote in report['evidence']:
        path = ROOT / quote['path'].split('/RedChamberWorldHarness/', 1)[1]
        assert quote['quote'] in '\n'.join(path.read_text(encoding='utf-8').splitlines()[quote['line_start'] - 1:quote['line_end']])


def test_ch95_reading_preserves_shortfall_style_risks_and_unknowns():
    report = json.loads((BASE / 'readings/ch95-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['adoption'] == 'NOT_ADOPTED' and report['human_qualification'] is False
    assert report['actual_reading']['coverage_fraction'] == 1.0
    assert report['hard_fail_findings'] == []
    assert len(report['substantive_style_risks']) == 4
    assert report['length_observation']['suggested_total_range_met'] is False
    assert report['length_observation']['shortfall_to_suggested_lower_bound'] == 105
    assert report['length_observation']['both_body_floors_met'] is True
    for ref in report['bindings']:
        path = ROOT / ref['path'].split('/RedChamberWorldHarness/', 1)[1]
        assert digest(path.read_bytes()) == ref['sha256']
    assert len(report['verbatim_evidence']) == 28
    for quote in report['verbatim_evidence']:
        path = ROOT / quote['path'].split('/RedChamberWorldHarness/', 1)[1]
        assert quote['quote'] in '\n'.join(path.read_text(encoding='utf-8').splitlines()[quote['line_start'] - 1:quote['line_end']])


@pytest.mark.parametrize('chapter,quote_count', [(82, 21), (87, 28)])
def test_two_chapter_reader_keeps_qualified_results_and_exact_evidence(chapter, quote_count):
    report = json.loads((BASE / f'readings/ch{chapter}-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['automatic_adopt'] is False
    assert report['confirmed_contradictions'] == []
    assert report['overall_assessment']['verdict'] == 'REVISE_RECOMMENDED_NOT_ADOPTED'
    assert report['style_and_literary_risks']
    assert len(report['evidence_quotes']) == quote_count
    for evidence in report['evidence_quotes']:
        path = Path(evidence['path'])
        marker = 'artifacts/agent_research/phase6/'
        assert marker in path.as_posix()
        path = ROOT / marker / path.as_posix().split(marker, 1)[1]
        text = path.read_text(encoding='utf-8')
        assert evidence['quote'] in '\n'.join(text.splitlines()[evidence['line_start'] - 1:evidence['line_end']])


@pytest.mark.parametrize('chapter,quote_count', [(94, 30), (100, 33)])
def test_final_local_readings_preserve_risks_and_exact_frozen_evidence(chapter, quote_count):
    report = json.loads((BASE / f'readings/ch{chapter}-v1-reader1.json').read_bytes())
    assert report.get('mode', report.get('usage')) == 'FEEDBACK_ONLY'
    assert report['authority_effect'] == 'NONE' and report['adoption'] == 'NOT_ADOPTED'
    assert report['formal_eligibility'] is False and report['human_qualification'] is False
    if chapter == 94:
        assert report['confirmed_contradictions'] == []
        assert report['verdict']['registered_old_bundle_chain'] == 'OPEN_NOT_REPAIRED_OR_EXECUTED'
        assert len(report['literary_risks']) == 5
    else:
        assert report['confirmed_new_contradictions'] == []
        assert len(report['literary_risks_not_converted_to_hard_failures']) == 4
        assert report['full_chapter_coverage']['coverage_fraction'] == 1.0
        assert report['mechanical_observation']['terminal_followed_only_by_final_newline'] is True
        for ref in report['inputs_actually_consumed']:
            marker = 'artifacts/agent_research/phase6/' if 'artifacts/agent_research/phase6/' in ref['path'] else 'data/'
            assert marker in ref['path']
            path = ROOT / marker / ref['path'].split(marker, 1)[1]
            assert digest(path.read_bytes()) == ref['sha256']
    assert len(report['verbatim_quotes']) == quote_count
    for evidence in report['verbatim_quotes']:
        marker = 'artifacts/agent_research/phase6/'
        assert marker in evidence['path']
        path = ROOT / marker / evidence['path'].split(marker, 1)[1]
        text = path.read_text(encoding='utf-8')
        assert evidence['quote'] in '\n'.join(text.splitlines()[evidence['line_start'] - 1:evidence['line_end']])


def test_three_chapter_actual_reading_keeps_release_boundary_and_precise_quotes():
    report = json.loads((BASE / 'readings/ch85-92-93-v1-reader1.json').read_bytes())
    assert report['disposition'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['automatic_ADOPT'] is False and report['automatic_PASS'] is False
    assert [row['chapter'] for row in report['chapters']] == [85, 92, 93]
    assert report['cross_chapter_local_audit']['92_to93_release']['decision'] == 'ONE_PERMISSION_ONE_ACTUAL_EXIT_NO_DUPLICATE_RELEASE_OBSERVED'
    total = 0
    for chapter in report['chapters']:
        assert chapter['coverage']['coverage_fraction'] == 1.0
        assert chapter['independent_judgment']['confirmed_continuity_failure'] is False
        assert chapter['confirmed_object_time_knowledge_contradictions'] == []
        assert chapter['literary_risks']
        for key in ('candidate', 'disclosure'):
            ref = chapter[key]
            marker = 'artifacts/agent_research/phase6/'
            assert marker in ref['path']
            path = ROOT / marker / ref['path'].split(marker, 1)[1]
            assert digest(path.read_bytes()) == ref['sha256']
        for quote in chapter['verbatim_evidence']:
            marker = 'artifacts/agent_research/phase6/'
            assert marker in quote['path']
            path = ROOT / marker / quote['path'].split(marker, 1)[1]
            text = path.read_text(encoding='utf-8')
            assert quote['quote'] in '\n'.join(text.splitlines()[quote['line_start'] - 1:quote['line_end']])
            total += 1
    assert total == 54


def test_ch83_84_actual_full_reading_keeps_information_risks_separate_from_failure():
    report = json.loads((BASE / 'readings/ch83-84-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['adoption'] == 'NOT_ADOPTED'
    assert [row['chapter'] for row in report['chapter_reviews']] == [83, 84]
    total = 0
    for chapter in report['chapter_reviews']:
        assert chapter['overall_literary_pass'] == 'NOT_GRANTED'
        assert chapter['confirmed_local_failures'] == []
        for evidence in chapter['exact_evidence']:
            text = (ROOT / evidence['path']).read_text(encoding='utf-8')
            assert evidence['quote'] in text.splitlines()[evidence['line'] - 1]
            total += 1
    assert total == 46


@pytest.mark.parametrize('chapter,quote_count', [(97, 29), (98, 31)])
def test_late_chapter_action_readings_are_feedback_not_adoption(chapter, quote_count):
    report = json.loads((BASE / f'readings/ch{chapter}-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['formal_eligibility'] is False and report['human_qualification'] is False
    assert report['adoption'] in {'NOT_ADOPTED', 'NO_AUTOMATIC_ADOPT'}
    if chapter == 98:
        assert report['confirmed_local_failures_current_revision'] == []
        assert report['prior_failures_comparison_only']
        assert len(report['action_reconstruction']) == 12
        assert report['literary_risks_separate_from_confirmed_failures']
    else:
        assert len(report['remaining_issues']) == 4
        assert len(report['protected_exact_phrases']) == 3
    assert len(report['verbatim_quotes']) == quote_count
    for evidence in report['verbatim_quotes']:
        text = (ROOT / evidence['path']).read_text(encoding='utf-8')
        assert evidence['quote'] in '\n'.join(text.splitlines()[evidence['line_start'] - 1:evidence['line_end']])


def test_ch91_reading_retains_both_local_failures_and_exact_evidence():
    report = json.loads((BASE / 'readings/ch91-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['adoption'] == 'NOT_ADOPTED'
    assert report['reading_coverage']['coverage_fraction'] == 1.0
    assert report['overall_assessment']['confirmed_local_fail_count'] == 2
    assert {item['id'] for item in report['confirmed_local_failures']} == {
        'FAIL-01-SECOND-COAT-MISSING-RECEIPT', 'FAIL-02-SCARF-KNOT-CONTINUITY'}
    assert report['snow_object_chain']['recipient'] == 'UNSPECIFIED_NOT_ASSIGNED'
    for key in ('candidate', 'disclosure', 'editorial_notes', 'editor_report'):
        binding = report['inputs'][key]
        assert digest((ROOT / binding['path']).read_bytes()) == binding['sha256']
    assert len(report['verbatim_quotes']) == 22
    for evidence in report['verbatim_quotes']:
        text = (ROOT / evidence['path']).read_text(encoding='utf-8')
        assert evidence['quote'] in '\n'.join(text.splitlines()[evidence['line_start'] - 1:evidence['line_end']])
        if 'character_offset_start' in evidence:
            assert text[evidence['character_offset_start']:evidence['character_offset_end_exclusive']] == evidence['quote']


def test_ch86_bounded_reading_no_local_fail_is_not_adoption():
    report = json.loads((BASE / 'readings/ch86-v1-reader1.json').read_bytes())
    assert report['authority_effect'] == 'NONE'
    assert report['formal_eligibility'] is False and report['human_qualification'] is False
    assert report['automatic_adopt'] is False
    assert report['confirmed_failures'] == []
    assert len(report['literary_concerns']) == 4
    assert len(report['evidence']) == 29
    for evidence in report['evidence']:
        path = Path(evidence['path'])
        # Diagnostic absolute paths record the author's checkout. Resolve only
        # the declared research subtree in a materialized verification checkout.
        if path.is_absolute():
            marker = 'artifacts/agent_research/phase6/'
            assert marker in path.as_posix()
            path = ROOT / marker / path.as_posix().split(marker, 1)[1]
        else:
            path = ROOT / path
        assert path.resolve().is_relative_to(ROOT)
        text = path.read_text(encoding='utf-8')
        start, end = evidence['lines']
        assert evidence['quote'] in '\n'.join(text.splitlines()[start - 1:end])


def test_ch81_reader_keeps_extra_exposure_and_does_not_award_adoption():
    report = json.loads((BASE / 'readings/ch81-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['automatic_ADOPT'] is False and report['automatic_PASS'] is False
    assert report['confirmed_local_failures'] == []
    assert report['overall_assessment']['confirmed_local_fail_count'] == 0
    assert report['isolation_and_execution']['scope_deviation_disclosed']
    assert report['isolation_and_execution']['independent_blind_review_claimed'] is False
    assert len(report['review_issues_not_confirmed_failures']) == 3
    assert len(report['verbatim_quotes']) == 26
    for evidence in report['verbatim_quotes']:
        text = (ROOT / evidence['path']).read_text(encoding='utf-8')
        assert evidence['quote'] in '\n'.join(text.splitlines()[evidence['line_start'] - 1:evidence['line_end']])


def test_ch96_reader_preserves_craft_risks_despite_no_confirmed_hard_failure():
    report = json.loads((BASE / 'readings/ch96-v1-reader1.json').read_bytes())
    assert report['mode'] == 'FEEDBACK_ONLY' and report['authority_effect'] == 'NONE'
    assert report['automatic_adopt'] is False and report['formal_eligibility'] is False
    assert report['literary_observations']['confirmed_failures'] == []
    assert report['literary_observations']['residual_findings']
    assert len(report['verbatim_quotes']) == 29
    for evidence in report['verbatim_quotes']:
        text = (ROOT / evidence['path']).read_text(encoding='utf-8')
        assert evidence['quote'] in '\n'.join(text.splitlines()[evidence['line_start'] - 1:evidence['line_end']])
