"""Freeze and verify evidence for the chapter 86 knowledge semantic review."""
import argparse
import json
from pathlib import Path

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.knowledge_projection import verify_request
from rcwh.generation.records import binding, bound_bytes, append_bytes

ROOT = Path(__file__).resolve().parents[1]
REQUEST = 'data/writing/knowledge-requests/87f537580cb65cfcb19b7b4d9eb8d84ff89d467e9ed174e6b3bfc2fa7fb1744d.json'
SOURCES = {
    'candidate': 'artifacts/candidates/ch86/2319feaac4b3f3824b185520cb0eae9d3968ab24e01e491be17547d3013b67c2.txt',
    'candidate_import': 'artifacts/local-trial-revision-ch86-20261111/import.json',
    'editorial_scenario': 'data/writing/local-scenarios/ch86-v6/scenario.json',
    'prior_boundary_analysis': 'artifacts/local-trial-revision-ch86-20261111/review/semantic-boundary.md',
}
DIRECTORY = 'data/writing/knowledge-review-evidence'


def build(root):
    verify_request(root, REQUEST)
    refs = {role: binding(root, path) for role, path in SOURCES.items()}
    imported = json.loads(bound_bytes(root, refs['candidate_import']))
    if imported['candidate'] != refs['candidate']:
        raise ValueError('candidate does not match the recorded import')
    return {'kind': 'KNOWLEDGE_SEMANTIC_REVIEW_EVIDENCE', 'protocol_version': 1,
            'request': binding(root, REQUEST), 'materials': refs,
            'instructions': ['Read the complete candidate and scenario against every projected checkpoint.',
                             'The candidate and scenario are downstream research material, not Evidence Truth.',
                             'Prior analysis is context, not an independent review or a required conclusion.',
                             'Cite passages, identify missing support and preserve uncertainty.'],
            'semantic_review': 'NOT_COMPLETED', 'production_admission': 'NOT_GRANTED',
            'authority_effect': 'NONE'}


def verify(root, path):
    raw = repository_path(root, path).read_bytes()
    if Path(path).stem != digest(raw):
        raise ValueError('evidence bundle digest mismatch')
    document = json.loads(raw)
    if canonical_bytes(document) != canonical_bytes(build(root)):
        raise ValueError('stale or incomplete knowledge review evidence')
    return document


def create(root):
    raw = canonical_bytes(build(root))
    path = f'{DIRECTORY}/{digest(raw)}.json'
    if repository_path(root, path).exists():
        verify(root, path)
        return binding(root, path)
    return append_bytes(root, path, raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', help='verify a repository-relative evidence bundle')
    args = parser.parse_args()
    print(json.dumps(verify(ROOT, args.check) if args.check else create(ROOT), ensure_ascii=False, sort_keys=True))
