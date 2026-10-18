"""A local repair keeps its real long parent and all original negative records."""
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import bound_bytes
from rcwh.generation.prose_integrity import prose_integrity

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


def test_ch91_v2_changes_only_three_declared_local_spans():
    disclosure = json.loads((BASE / 'authored/ch91-v2-disclosure.json').read_bytes())
    request = json.loads(bound_bytes(ROOT, disclosure['request']))
    parent = json.loads(bound_bytes(ROOT, request['parent']))
    original = bound_bytes(ROOT, parent['candidate']).decode('utf-8')
    revised = bound_bytes(ROOT, disclosure['candidate']).decode('utf-8')
    assert parent['candidate']['sha256'] == '751bca67b2e72bd13883a8ee2331baaf60878967b3c4f276b277e7cc2b11c602'
    assert request['parent'] == disclosure['parent']
    assert parent['parent'] is not None
    assert parent['package'] == request['package']
    assert request['task']['original'] == original
    assert request['task']['feedback']['checks'][0]['status'] == 'FAIL'
    assert len(request['task']['feedback']['checks'][0]['findings']) == 2
    assert request['context']['notes_path'].endswith('ch91-v1-repair-notes-v1.txt')
    assert len(disclosure['changes']) == 3
    rebuilt = original
    for patch in disclosure['changes']:
        assert original.count(patch['original']) == 1
        start = patch['original_character_start']
        assert original[start:start + len(patch['original'])] == patch['original']
        assert len(original[:start].encode('utf-8')) == patch['original_utf8_start']
        rebuilt = rebuilt.replace(patch['original'], patch['replacement'], 1)
    assert rebuilt == revised
    assert original.splitlines()[0] == revised.splitlines()[0]
    assert original.splitlines()[-1] == revised.splitlines()[-1]
    assert '她才将结松了' in original and '她才将结松了' not in revised
    assert '短袖的一件翻出右襟' in revised
    assert len(revised) == 10172
    assert prose_integrity(revised)['status'] == 'PASS'
    reader = json.loads(bound_bytes(ROOT, disclosure['retained_original_reader_report']))
    assert reader['overall_assessment']['confirmed_local_fail_count'] == 2
    assert disclosure['literary_acceptance'] == 'NOT_GRANTED'
    assert disclosure['provider_proof'] == 'NONE'
    prompt = {'system': bound_bytes(ROOT, request['template']).decode('utf-8'),
              'messages': [{'role': 'user', 'content': canonical_bytes(request['task']).decode('utf-8')}]}
    assert digest(canonical_bytes(prompt)) == request['prompt_sha256']
    assert digest(canonical_bytes(request['request'])) == request['request_sha256']


def test_same_reader_full_followup_does_not_erase_v1_failures_or_add_independence():
    followup = json.loads((BASE / 'readings/ch91-v2-reader1.json').read_bytes())
    original = json.loads((BASE / 'readings/ch91-v1-reader1.json').read_bytes())
    assert followup['review_relationship'] == 'SAME_READER_FOLLOWUP_NOT_ADDITIONAL_INDEPENDENT_REVIEWER'
    assert followup['mode'] == 'FEEDBACK_ONLY' and followup['authority_effect'] == 'NONE'
    assert followup['formal_eligibility'] is False and followup['human_qualification'] is False
    assert len(original['confirmed_local_failures']) == 2
    assert len(followup['defect_followup']) == 2
    assert all(row['v1_status'] == 'FAIL_RETAINED_FOR_V1' for row in followup['defect_followup'])
    assert all(row['v2_assessment'].startswith('REPAIRED_LOCAL_') for row in followup['defect_followup'])
    assert followup['style_risks_retained_not_new_confirmed_failures']
    assert len(followup['verbatim_quotes']) == 12
    for quote in followup['verbatim_quotes']:
        text = (ROOT / quote['path']).read_text(encoding='utf-8')
        assert quote['quote'] in '\n'.join(text.splitlines()[quote['line_start'] - 1:quote['line_end']])
        if 'character_offset_start' in quote:
            assert text[quote['character_offset_start']:quote['character_offset_end_exclusive']] == quote['quote']
