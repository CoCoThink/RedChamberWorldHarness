"""Index current source/corpus reading materials, with no human-review credit."""
from pathlib import Path
import json
from rcwh.generation.records import binding, bound_bytes
from rcwh.workflow.release_packets import _write_immutable

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
PLAN = 'data/agent_release/research-81-100-v5/review-campaign-v1.json'


def main():
    plan = json.loads((R / PLAN).read_bytes())
    groups = {}
    for job in plan['jobs']:
        if job['kind'] not in ['SOURCE', 'CORPUS']:
            continue
        key = (job['kind'], job['packet']['sha256'], tuple(job['subjects']))
        if key in groups:
            continue
        for ref in [*job['read_in_full'], *job.get('inspect_images', [])]:
            bound_bytes(R, ref)
        groups[key] = {k: job[k] for k in ['kind', 'packet', 'subjects', 'read_in_full', 'samples', 'reading_bytes', 'inspect_images', 'image_bytes'] if k in job}
        groups[key]['status'] = 'MATERIAL_INDEX_ONLY_NO_HUMAN_CREDIT'
    index = {'kind': 'HUMAN_HANDOFF_MATERIAL_INDEX', 'edition': 'research-81-100-v5', 'campaign': binding(R, PLAN), 'groups': list(groups.values()), 'binding_policy': 'Exact current campaign paths/hashes checked. This is not semantic reading, source verification or human review.', 'authority_effect': 'NONE', 'independent_human_admission': False, 'human_reviews_received': 0, 'P9_credit': False, 'previous_index': binding(R, 'artifacts/agent_research/v4-context-followup-20261026/human-material-index.json'), 'context_change': '84/87 joint mourning timeline,94/95 renewed stay,96/97 absence onset; all specific selected candidates bound per subject. Original source and corpus inputs unchanged.'}
    _write_immutable(R, (O / 'human-material-index.json').relative_to(R).as_posix(), index)
    print(json.dumps({'status': 'INDEX_PREPARED_NO_QUALIFICATION', 'groups': len(groups), 'human_reviews_received': 0, 'P9_credit': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
