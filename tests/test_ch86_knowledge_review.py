"""Review custody fails closed without changing a reader's judgment."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/local-scenario-ch86-knowledge-split/review'
spec = importlib.util.spec_from_file_location('knowledge_review', ROOT / 'tools/verify_ch86_knowledge_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.fixture
def copied_review(tmp_path):
    plan = json.loads((ROOT / BASE / 'plan.json').read_bytes())
    execution = json.loads((ROOT / BASE / 'execution.json').read_bytes())
    manifest = json.loads((ROOT / plan['manifest']['path']).read_bytes())
    package = json.loads((ROOT / manifest['package']['path']).read_bytes())
    paths = {BASE + '/plan.json', BASE + '/execution.json', BASE + '/checkpoint-view.json'}
    def select(ref):
        paths.add(ref['path'])
    for field in ('input_ci', 'manifest', 'candidate', 'repository_instructions'):
        select(plan[field])
    for value in manifest.values():
        for ref in value if isinstance(value, list) else [value]:
            if isinstance(ref, dict) and 'path' in ref:
                select(ref)
    for ref in package['plan']:
        select(ref)
    for ref in plan['tasks']:
        select(ref)
        task = json.loads((ROOT / ref['path']).read_bytes())
        for item in task['read_inputs']:
            select(item)
    for attempt in execution['attempts']:
        select(attempt['raw_opinion'])
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    for relative in ('data/world/m3_core.json', 'data/objects/m4.json', 'data/objects/medicine_bowl.yaml'):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def mutate_opinion(root, change):
    execution_path = root / BASE / 'execution.json'
    execution = json.loads(execution_path.read_bytes())
    attempt = execution['attempts'][0]
    path = root / attempt['raw_opinion']['path']
    opinion = json.loads(path.read_bytes())
    change(opinion)
    path.write_bytes(canonical_bytes(opinion))
    # Rebind to test content validation independently of byte integrity.
    attempt['raw_opinion'] = binding(root, attempt['raw_opinion']['path'])
    execution_path.write_bytes(canonical_bytes(execution))


def test_real_semantic_review_verifies_custody():
    result = review.verify(ROOT)
    assert result['status'] == 'PASS'
    assert result['independent_model_opinions'] == 2
    assert result['scope'] == 'CUSTODY_AND_SELF_REPORTED_COVERAGE_ONLY'
    assert result['production_admission'] == 'NOT_GRANTED'


@pytest.mark.parametrize('case', ['incomplete', 'missing_read', 'duplicate_read', 'wrong_identity',
                                  'missing_finding', 'invent_quote', 'wrong_paragraph',
                                  'unassigned_citation', 'production'])
def test_rebound_invalid_opinion_cannot_claim_completion(copied_review, case):
    def change(opinion):
        if case == 'incomplete': opinion['reading_status'] = 'INCOMPLETE'
        elif case == 'missing_read': opinion['declared_read_files'].pop()
        elif case == 'duplicate_read': opinion['declared_read_files'].append(opinion['declared_read_files'][0])
        elif case == 'wrong_identity': opinion['reviewer']['principal_id'] = 'another reader'
        elif case == 'missing_finding': opinion['findings'].pop()
        elif case in ('invent_quote', 'wrong_paragraph'):
            opinion['findings'][0]['prose_quotes'] = [{'quote': '并不存在的正文句子' if case == 'invent_quote' else '气就没了', 'paragraphs': [1]}]
        elif case == 'unassigned_citation': opinion['findings'][0]['material_citations'] = [{'path': 'not-assigned.json', 'locator': 'facts'}]
        else: opinion['production_admission'] = 'GRANTED'
    mutate_opinion(copied_review, change)
    with pytest.raises((AssertionError, ValueError)):
        review.verify(copied_review)


def test_changed_original_opinion_fails_its_binding(copied_review):
    execution = json.loads((copied_review / BASE / 'execution.json').read_bytes())
    path = copied_review / execution['attempts'][0]['raw_opinion']['path']
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError):
        review.verify(copied_review)
