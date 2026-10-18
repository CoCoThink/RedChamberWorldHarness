"""New local followup supports literal repair without claiming literary adoption."""
import json
from pathlib import Path

from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_actual_ch86_v2_followup_retains_original_fail_and_new_referent_risks():
    custody = json.loads((BASE / 'readings/ch86-v2-reader2-custody-v1.json').read_bytes())
    report = json.loads(bound_bytes(ROOT, custody['report']))
    assert custody['verified_quotes'] == 28
    assert report['disposition'] == 'NOT_ADOPTED_NOT_RELEASED'
    assert report['scope']['full_text_coverage'] is True
    assert report['reader_identity']['original_reader_impersonated'] is False
    assert report['reader_identity']['whole_book_reader'] is False
    assert report['reader_identity']['human_qualification'] is False
    assert report['current_v2_definite_content_failures'] == []
    assert len(report['confirmed_failures']) == 2
    assert all(row['status'] == 'FAIL_RETAINED_NO_WAIVER' for row in report['confirmed_failures'])
    assert report['three_replacement_context_review']['hearing_this_sentence_after_forward_move']['classification'] == 'COHERENT_WITH_REFERENTIAL_AND_TIMING_RISK_NOT_DEFINITE_FAIL'
    assert len(report['uncertainties_and_literary_risks']) >= 3
    count = 0

    def verify(value):
        nonlocal count
        if isinstance(value, dict):
            if {'path', 'line_start', 'line_end', 'quote'} <= value.keys():
                path = ROOT / value['path']
                assert path.resolve().is_relative_to(BASE)
                text = path.read_text(encoding='utf-8')
                assert value['quote'] in '\n'.join(text.splitlines()[value['line_start'] - 1:value['line_end']])
                count += 1
            for child in value.values():
                verify(child)
        elif isinstance(value, list):
            for child in value:
                verify(child)

    verify(report)
    assert count == 28
    for ref in report['actual_read_ranges_and_hashes']:
        if 'sha256' in ref:
            bound_bytes(ROOT, {'path': ref['path'], 'sha256': ref['sha256']})
