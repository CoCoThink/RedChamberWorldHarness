"""Reading assemblies are exact selections, not adoption or negative resets."""
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import digest
from rcwh.generation.records import bound_bytes
from rcwh.schema import validate_instance

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_comparison_baseline_chapters_match_unchanged_stable_v14():
    from rcwh.workflow.agent_release import _split

    path = ROOT / 'releases/stable/v1.4/readable/baseline.md'
    assert digest(path.read_bytes()) == '4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320'
    prefix, chapters = _split(path.read_text(encoding='utf-8'), tuple(range(81, 101)))
    assert prefix == ''
    for chapter, prose in chapters.items():
        copied = ROOT / f'artifacts/agent_research/phase5/inputs/writing/baseline-ch{chapter}.md'
        assert prose.rstrip() == copied.read_text(encoding='utf-8').rstrip()


def test_continuity_selection_and_exact_book_slices_preserve_ch91_history():
    selection = json.loads((BASE / 'continuity-reading-selection-v1.json').read_bytes())
    manifest = json.loads((BASE / 'continuity/reading-book-manifest-v1.json').read_bytes())
    assert selection['status'] == manifest['status'] == 'NOT_ADOPTED_NOT_RELEASED'
    assert selection['authority_effect'] == manifest['authority_effect'] == 'NONE'
    assert selection['actual_author_context_count'] == 4
    assert selection['controlled_previous_input_generation'] is False
    assert selection['independent_human_review'] is False
    assert [row['chapter'] for row in selection['chapters']] == list(range(81, 101))
    assert json.loads(bound_bytes(ROOT, manifest['selection'])) == selection
    book = bound_bytes(ROOT, manifest['book']).decode('utf-8')
    total = 0
    for selected, assembled in zip(selection['chapters'], manifest['chapters'], strict=True):
        chapter = selected['chapter']
        assert selected['revision'] == ('v2' if chapter == 91 else 'v1')
        assert selected['selection_effect'] == 'READING_ONLY_NOT_ADOPT'
        assert assembled['candidate'] == selected['candidate']
        raw = bound_bytes(ROOT, selected['candidate'])
        segment = book[assembled['start_character']:assembled['end_character_exclusive']]
        assert segment.encode('utf-8') == raw
        assert assembled['utf8_sha256'] == digest(raw)
        total += len(segment)
    assert manifest['body_character_sum'] == total == 195312
    assert manifest['release_or_admission_effect'] == 'NONE'
    original = json.loads((BASE / 'readings/ch91-v1-reader1.json').read_bytes())
    assert len(original['confirmed_local_failures']) == 2
    followup = json.loads((BASE / 'readings/ch91-v2-reader1.json').read_bytes())
    assert followup['review_relationship'] == 'SAME_READER_FOLLOWUP_NOT_ADDITIONAL_INDEPENDENT_REVIEWER'


def test_local_reading_coverage_does_not_multiply_reviewers_or_erase_failures():
    ledger = json.loads((BASE / 'local-reading-coverage-v1.json').read_bytes())
    assert ledger['coverage_chapter_count'] == 20
    assert ledger['unique_report_count'] == 16
    assert ledger['total_verified_v1_quotes'] == 496
    assert sum(row['coordinator_verified_quote_count'] for row in ledger['chapters']) == 496
    assert [row['chapter'] for row in ledger['chapters']] == list(range(81, 101))
    assert {row['chapter']: row['confirmed_hard_fail_count'] for row in ledger['chapters'] if row['confirmed_hard_fail_count']} == {91: 2}
    for row in ledger['chapters']:
        assert row['authority_effect'] == 'NONE' and row['adoption'] == 'NOT_GRANTED'
        bound_bytes(ROOT, row['candidate'])
        bound_bytes(ROOT, row['report'])
    assert ledger['narrow_followup']['relationship'] == 'SAME_READER_FOLLOWUP_NOT_ADDITIONAL_INDEPENDENT_REVIEWER'
    assert ledger['narrow_followup']['original_hard_fails_retained'] is True


def test_twenty_chapter_lexical_observation_cannot_claim_zero_hit_improvement():
    from rcwh.generation.narrator_audit import narrator_audit

    report = json.loads((BASE / 'narrator-observation-twenty-v1.json').read_bytes())
    assert report['literary_acceptance'] == 'NOT_GRANTED'
    assert report['qualification'] == 'FEEDBACK_ONLY'
    assert 'these patterns miss' in report['limitation']
    assert [row['chapter'] for row in report['chapters']] == list(range(81, 101))
    bound_bytes(ROOT, report['evaluator'])
    for row in report['chapters']:
        current = bound_bytes(ROOT, row['candidate']).decode('utf-8')
        for field, baseline in [('against_prior_research', 'prior_research_candidate'),
                                ('against_stable', 'stable_candidate'),
                                ('against_actual_short_parent', 'actual_short_parent_candidate')]:
            expected = narrator_audit(current, baseline=bound_bytes(ROOT, row[baseline]).decode('utf-8'))
            assert row[field] == expected
            assert row[field]['status'] == 'NOT_CHECKED'


@pytest.mark.parametrize('segment,first,last', [
    ('early', 81, 83), ('middle', 84, 91), ('late', 92, 97), ('tail', 98, 100),
])
def test_threeway_packets_bind_exact_sequences_and_retain_old_negative_history(segment, first, last):
    context_path = BASE / f'comparison/coordinator/{segment}-context-v1.json'
    context = json.loads(context_path.read_bytes())
    export = json.loads((BASE / f'comparison/coordinator/{segment}-export-v1.json').read_bytes())
    packet = json.loads(bound_bytes(ROOT, export['packet']))
    mapping = json.loads(bound_bytes(ROOT, export['mapping']))
    commitment = json.loads(bound_bytes(ROOT, export['commitment']))
    assert context['status'] == 'NOT_ADOPTED_NOT_RELEASED'
    assert context['selection_effect'].startswith('READING_ONLY_NOT_ADOPT')
    assert context['chapters'] == list(range(first, last + 1))
    assert not validate_instance(packet, ROOT / 'schemas/agent_packet.schema.json')
    assert len(packet['subjects']) == len(mapping['mapping']) == 3
    assert commitment['packet'] == mapping['packet'] == export['packet']
    assert bound_bytes(ROOT, mapping['context']) == context_path.read_bytes()
    public = {row['id']: row for row in packet['subjects']}
    for row in mapping['mapping']:
        subject = public[row['token']]
        assert subject['scope'] == 'CANDIDATE' and 'samples' not in subject
        assert bound_bytes(ROOT, row['text']) == bound_bytes(ROOT, subject['binding'])
        assert subject['binding'] == row['public_text']
        assert row['author_session_ids']
        assert row['id'] not in json.dumps(packet)
        assert row['text']['path'] not in json.dumps(packet)
    current = b'\n\n'.join(bound_bytes(ROOT, row['candidate']).rstrip() for row in context['current_chapters']) + b'\n'
    assert current == bound_bytes(ROOT, context['source_sets']['current'])
    assert context['historical_boundary_observation']['historical_sequence_bytes_unchanged'] is True
    assert context['historical_reading_summaries']
    for ref in context['historical_reading_summaries']:
        summary = json.loads(bound_bytes(ROOT, ref))
        assert summary['authority_effect'] == 'NONE'
    assert context['historical_reader_outputs']
    for ref in context['historical_reader_outputs']:
        bound_bytes(ROOT, ref)
    assert any('not automatically merged' in item for item in context['limitations'])
    assert context['local_phase6_readings_coordinator_only']
    for ref in context['local_phase6_readings_coordinator_only']:
        bound_bytes(ROOT, ref)
