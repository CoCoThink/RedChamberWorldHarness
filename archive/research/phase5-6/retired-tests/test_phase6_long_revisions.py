"""Frozen long candidates meet mechanical floors, not literary acceptance."""
import json
from pathlib import Path

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.prose_integrity import prose_integrity
from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/revisions-v2'


@pytest.mark.parametrize('chapter,total,body_han,body_floor', [
    (81, 9441, 7747, 5911),
    (82, 9645, 8081, 6352),
    (83, 9470, 8035, 5773),
    (84, 9130, 7808, 6479),
    (85, 9038, 7722, 6584),
    (86, 10195, 8609, 7924),
    (87, 9632, 8138, 7283),
    (88, 9516, 8126, 7513),
    (89, 10349, 8961, 8929),
    (90, 10065, 8657, 7895),
    (91, 10055, 8334, 6432),
    (92, 10162, 8562, 8126),
    (93, 9576, 8126, 6408),
    (94, 9506, 8144, 7271),
    (95, 9895, 8478, 8779),
    (96, 9350, 7827, 6252),
    (97, 9999, 8560, 7354),
    (98, 10088, 8684, 7270),
    (99, 10038, 8609, 8500),
    (100, 10045, 8645, 7315),
])
def test_frozen_candidate_length_and_exact_revision_lineage(chapter, total, body_han, body_floor):
    text_path = BASE / f'authored/ch{chapter}-v1.txt'
    raw = text_path.read_bytes()
    text = raw.decode('utf-8')
    body = text.split('\n\n', 1)[1]
    disclosure = json.loads((BASE / f'authored/ch{chapter}-v1-disclosure.json').read_bytes())
    observation = json.loads((BASE / f'ch{chapter}-v1-mechanical-observation.json').read_bytes())
    request = json.loads((BASE / f'editorial-requests-v1/ch{chapter}.json').read_bytes())
    assert len(text) == total
    assert sum('一' <= char <= '鿿' for char in body) == body_han >= 7000
    assert sum(not char.isspace() for char in body) >= body_floor
    assert digest(raw) == observation['candidate']['sha256']
    assert observation['parent'] == request['parent']
    assert request['context']['revision_template'] == 'revise-v2'
    assert request['context']['notes_path'].endswith(f'notes-ch{chapter}-v1.txt')
    parent = json.loads(bound_bytes(ROOT, request['parent']))
    assert parent['package'] == request['package']
    assert parent['parent'] is None
    assert len(bound_bytes(ROOT, parent['candidate']).decode()) < 3000
    assert request['task']['original'] == bound_bytes(ROOT, parent['candidate']).decode()
    assert request['task']['editorial_notes'] == (ROOT / request['context']['notes_path']).read_text(encoding='utf-8')
    assert disclosure['execution_basis'] == 'SESSION_AUTHORED_NOT_PROVIDER_VERIFIED'
    assert disclosure['provider_proof'] == 'NONE'
    assert disclosure['formal_eligibility'] is False
    assert disclosure.get('human_qualification', False) is False
    prompt = {'system': bound_bytes(ROOT, request['template']).decode('utf-8'),
              'messages': [{'role': 'user', 'content': canonical_bytes(request['task']).decode('utf-8')}]}
    assert digest(canonical_bytes(prompt)) == request['prompt_sha256']
    assert digest(canonical_bytes(request['request'])) == request['request_sha256']
    assert prose_integrity(text)['status'] == 'PASS'
    assert observation['literary_acceptance'] == 'NOT_GRANTED'
