"""Bind actual finished checks; creates no reviews or qualification."""
from pathlib import Path
from collections import Counter
import json
from rcwh.generation.records import binding, bound_bytes

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REQUEST = 'data/agent_release/research-81-100-v5/request.json'
EDITION = 'releases/agent/research-81-100-v5'


def main():
    def load(path):
        return json.loads(path.read_bytes())

    def ref(name):
        return binding(R, (O / name).relative_to(R).as_posix())

    audit = load(O / 'actual-execution-verification.json')
    pending = audit['release_status'] == 'PENDING'
    manifest = load(O / 'final-release-evaluation.json') if pending else load(R / EDITION / 'manifest.json')
    lineage = load(O / 'final-writing-lineage.json')
    assets = load(O / 'final-assets-validation.txt')
    assert audit['status'] == lineage['status'] == assets['status'] == 'PASS'
    assert manifest['status'] == ('PENDING' if pending else 'PASS')
    assert not manifest['findings'] and not assets['findings']
    assert len(lineage['chapters']) == len(manifest['chapters']) == 20
    assert dict(Counter(v for c in manifest['chapters'] for v in c['gates'].values())) == audit['release_gates']
    if pending:
        assert not (R / EDITION).exists() and audit['unresolved_chapters']
        refusal = load(O / 'normal-build-attempt.json')
        assert refusal['refused'] and not refusal['allow_pending'] and refusal['exit_code'] != 0
    assert all(c['historical_integrity']['status'] == c['current_compatibility']['status'] == 'PASS'
               for c in lineage['chapters'])
    assert (O / 'final-repository-validation.txt').read_text().startswith('PASS:')
    request = load(R / REQUEST)
    plan = load(R / 'data/agent_release/research-81-100-v5/review-campaign-v1.json')
    continuity = {ref['path']: ref for job in plan['jobs'] if job['kind'] == 'BOOK'
                  for ref in job['read_in_full']}
    for context_ref in continuity.values():
        bound_bytes(R, context_ref)
    for row in request['chapters']:
        bound_bytes(R, row['candidate'])
    index = {'kind': 'UNRESOLVED_RESEARCH_HUMAN_HANDOFF_INDEX' if pending else 'FINAL_RESEARCH_EDITION_HUMAN_HANDOFF_INDEX', 'edition': request['id'],
             'request': binding(R, REQUEST), 'manifest': None if pending else binding(R, EDITION + '/manifest.json'),
             'book': None if pending else binding(R, EDITION + '/book.md'),
             'evaluation': ref('final-release-evaluation.json'),
             'reading_book': binding(R, 'data/agent_release/research-81-100-v5/reading/book.md'),
             'release_status': manifest['status'], 'unresolved_chapters': audit['unresolved_chapters'],
             'candidates': [{'chapter': c['chapter'], 'candidate': c['candidate']} for c in request['chapters']],
             'continuity_packet': request['book_review']['packet'],
             'continuity_reading': list(continuity.values()),
             'comparison': binding(R, 'artifacts/agent_research/v5-revision-20261027/comparison/summary.json'), 'dispositions': ref('coordinator-dispositions.json'),
             'source_corpus_material_index': ref('human-material-index.json'),
             'human_reviews_received': 0, 'P9_credit': False, 'authority_effect': 'NONE',
             'limitation': 'Prepared materials only; neither human review nor publication qualification.'}
    local = {'status': 'PASS', 'scope': 'ACTUAL_LOCAL_UNRESOLVED_HANDOFF_AND_BUILD_REFUSAL' if pending else 'ACTUAL_LOCAL_RESEARCH_BUILD_AND_VALIDATION',
             'build_command': load(O / 'normal-build-attempt.json')['command'],
             'allow_pending': False, 'release_status': manifest['status'], 'chapter_count': 20,
             'release_gates': audit['release_gates'], 'normal_build_succeeded': not pending,
             'unresolved_chapters': audit['unresolved_chapters'], 'findings': [],
             **{k: index[k] for k in ('request', 'manifest', 'book', 'evaluation', 'reading_book')},
             'evidence': {name: ref(name) for name in ('actual-execution-verification.json',
                 'final-writing-lineage.json', 'final-assets-validation.txt', 'final-repository-validation.txt',
                 'normal-build-attempt.json')},
             'clone_reproduction': 'SEPARATE_COMMITTED_CLONE_RECEIPT_REQUIRED',
             'final_ci': 'SEPARATE_GITHUB_FINAL_HEAD_RUN_REQUIRED', 'authority_effect': 'NONE', 'P9_credit': False}
    for name, value in [('human-final-release-index.json', index), ('final-local-validation.json', local)]:
        target = O / name
        assert not target.exists()
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(local, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
