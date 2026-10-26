"""Add the missing selected-candidate context; preserves all prose and old inputs."""
from copy import deepcopy
from pathlib import Path
import json

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding
from rcwh.workflow.agent_panel import verify_packet
from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.release_packets import chapter_packets, _write_immutable
from rcwh.workflow.review_campaign import plan

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
OLD = 'data/agent_release/research-81-100-v4-r3/request.json'
NEW = 'data/agent_release/research-81-100-v4-r4/request.json'
PLAN = 'data/agent_release/research-81-100-v4-r4/review-campaign-v1.json'


def main():
    original = json.loads((R / OLD).read_bytes())
    current = deepcopy(original)
    current['id'] = 'research-81-100-v4-r4'
    rows = {r['chapter']: r for r in current['chapters']}
    rows[92]['review_context_chapters'] = {'contract-92-6': [93]}
    subjects = []
    for row in rows.values():
        subjects.extend(verify_packet(R, row['panel']['packet'])['subjects'])
    prepared = chapter_packets(R, subjects, rows, 'coordinator:release-v1')
    for ch, row in rows.items():
        if ch != 92 and prepared[ch] != row['panel']['packet']:
            raise ValueError('unrelated chapter packet changed')
        row['panel']['packet'] = prepared[ch]
    for before, after in zip(original['chapters'], current['chapters']):
        assert all(after[k] == v for k, v in before.items() if k != 'panel')
    assert original['book_review'] == current['book_review']
    AgentRelease(R)._validate(current, 'request')
    request_ref = _write_immutable(R, NEW, current)
    result = plan(R, NEW, PLAN, batch_size=3, max_read_bytes=197 * 1024, max_attempts=3)
    document = json.loads((R / PLAN).read_bytes())
    result.update(kind='BOUND_CROSS_CHAPTER_CONTEXT_FOLLOWUP', previous_request=binding(R, OLD),
                  current_request=request_ref, changed_prose_chapters=[], changed_chapter_packets=[92],
                  declaration={'chapter': 92, 'subject_id': 'contract-92-6', 'read_chapters': [93]},
                  current_jobs=len(document['jobs']),
                  reading_bytes=[j['reading_bytes'] for j in document['jobs'] if j['chapter'] == 92],
                  old_not_checked_record=binding(R, 'data/agent_panel/records/3ac7459a5088883484a7f61e91a7b6a0528d0a30e6c90b22d83cad5332014813.json'),
                  reuse_basis='Other chapter packets and full BOOK packet remain exact; retain all old observations. New92 packet requires fresh readers after its input CI.',
                  authority_effect='NONE')
    _write_immutable(R, (O / 'preparation.json').relative_to(R).as_posix(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
