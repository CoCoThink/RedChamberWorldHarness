"""Freeze the corrected research edition and measure actual review reuse."""
from collections import Counter
from pathlib import Path
import json
from rcwh.candidate_reviews import canonical_bytes
from rcwh.workflow.release_packets import prepare
from rcwh.workflow.review_campaign import plan, status

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
EDITION = 'research-81-100-v2'
request = f'data/agent_release/{EDITION}/request.json'
campaign = f'data/agent_release/{EDITION}/review-campaign-v1.json'
previous = status(ROOT, 'data/agent_release/research-81-100-v1/review-campaign-v3.json')
assert previous['status'] == 'PASS' and not any(j['needs_followup'] for j in previous['jobs'])
prepared = prepare(ROOT, EDITION, 'data/agent_release/selection-81-100-v3.json', list(range(81, 101)),
                   coordinator_session_id='coordinator:release-v1',
                   reuse_request_path='data/agent_release/research-81-100-v1/request.json')
planned = plan(ROOT, request, campaign, batch_size=5)
execution = status(ROOT, campaign)
document = json.loads((ROOT / campaign).read_bytes())
jobs = {j['id']: j for j in document['jobs']}
report = {'prepared': prepared, 'planned': planned, 'execution': execution,
          'states': dict(Counter(j['status'] for j in execution['jobs'])),
          'reused_jobs': sum(j['reused'] for j in execution['jobs']),
          'fresh_jobs_by_kind': dict(Counter(jobs[j['id']]['kind'] for j in execution['jobs'] if not j['reused'])),
          'authority_effect': 'NONE'}
target = OUT / 'prepare-v2.json'
assert not target.exists(), 'do not replace a retained preparation report'
target.write_bytes(canonical_bytes(report))
print(json.dumps({k: v for k, v in report.items() if k not in ('prepared', 'execution')}, ensure_ascii=False))
