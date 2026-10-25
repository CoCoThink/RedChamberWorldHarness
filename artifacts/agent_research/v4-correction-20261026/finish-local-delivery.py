"""Bind actual finished checks; creates no reviews or qualification."""
from pathlib import Path
from collections import Counter
import json
from rcwh.generation.records import binding, bound_bytes

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REQUEST = 'data/agent_release/research-81-100-v4-r2/request.json'
EDITION = 'releases/agent/research-81-100-v4-r2'


def main():
    def load(path):
        return json.loads(path.read_bytes())

    def ref(name):
        return binding(R, (O / name).relative_to(R).as_posix())

    audit = load(O / 'actual-execution-verification.json')
    manifest = load(R / EDITION / 'manifest.json')
    lineage = load(O / 'final-writing-lineage.json')
    assets = load(O / 'final-assets-validation.txt')
    assert audit['status'] == manifest['status'] == lineage['status'] == assets['status'] == 'PASS'
    assert not manifest['findings'] and not assets['findings']
    assert len(lineage['chapters']) == len(manifest['chapters']) == 20
    assert Counter(v for c in manifest['chapters'] for v in c['gates'].values()) == {'PASS': 240}
    assert all(c['historical_integrity']['status'] == c['current_compatibility']['status'] == 'PASS'
               for c in lineage['chapters'])
    assert (O / 'final-repository-validation.txt').read_text().startswith('PASS:')
    request = load(R / REQUEST)
    for row in request['chapters']:
        bound_bytes(R, row['candidate'])
    index = {'kind': 'FINAL_RESEARCH_EDITION_HUMAN_HANDOFF_INDEX', 'edition': request['id'],
             'request': binding(R, REQUEST), 'manifest': binding(R, EDITION + '/manifest.json'),
             'book': binding(R, EDITION + '/book.md'),
             'candidates': [{'chapter': c['chapter'], 'candidate': c['candidate']} for c in request['chapters']],
             'comparison': ref('comparison/summary.json'), 'dispositions': ref('coordinator-dispositions.json'),
             'source_corpus_material_index': ref('human-material-index.json'),
             'human_reviews_received': 0, 'P9_credit': False, 'authority_effect': 'NONE',
             'limitation': 'Prepared materials only; neither human review nor publication qualification.'}
    local = {'status': 'PASS', 'scope': 'ACTUAL_LOCAL_RESEARCH_BUILD_AND_VALIDATION',
             'build_command': 'PYTHONPATH=src python -m rcwh.cli agent-release build ' + REQUEST + ' --json',
             'allow_pending': False, 'release_status': manifest['status'], 'chapter_count': 20,
             'release_gates': {'PASS': 240}, 'findings': [],
             **{k: index[k] for k in ('request', 'manifest', 'book')},
             'evidence': {name: ref(name) for name in ('actual-execution-verification.json',
                 'final-writing-lineage.json', 'final-assets-validation.txt', 'final-repository-validation.txt')},
             'clone_reproduction': 'SEPARATE_COMMITTED_CLONE_RECEIPT_REQUIRED',
             'final_ci': 'SEPARATE_GITHUB_FINAL_HEAD_RUN_REQUIRED', 'authority_effect': 'NONE', 'P9_credit': False}
    for name, value in [('human-final-release-index.json', index), ('final-local-validation.json', local)]:
        target = O / name
        assert not target.exists()
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(local, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
