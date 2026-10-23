"""Serial native-reader custody helper; creates no review opinions."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse
import json
from rcwh.workflow import review_campaign as campaign

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PLAN = 'data/agent_release/research-81-100-v1/review-campaign-v3.json'
p = argparse.ArgumentParser()
p.add_argument('command', choices=['status', 'dispatch', 'register', 'recover', 'launch', 'read', 'log-read'])
p.add_argument('job', nargs='?')
p.add_argument('opinion', nargs='?')
p.add_argument('--origin')
a = p.parse_args()

def save(prefix, value):
    n = 1
    while (OUT / f'{prefix}-{n:03d}.json').exists():
        n += 1
    target = OUT / f'{prefix}-{n:03d}.json'
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return str(target.relative_to(ROOT))

if a.command == 'launch':
    r = campaign.status(ROOT, PLAN)
    job = next(j for j in r['jobs'] if j['id'] == a.job)
    with (OUT / 'launches.jsonl').open('a') as f:
        f.write(json.dumps({'observed_utc': datetime.now(timezone.utc).isoformat(), 'job': a.job,
            'attempt': job['attempts'], 'task': a.origin, 'fork_turns': 'none',
            'model': 'current environment route (declared)',
            'raw_output': f'/home/guan/rcwh-review-outputs-20261023/{a.job}-a{job["attempts"]}.json'}, ensure_ascii=False) + '\n')
elif a.command in {'read', 'log-read'}:
    n = int(a.job)
    e = json.loads((OUT / f'registration-{n:03d}.json').read_bytes())
    if a.command == 'read':
        r = json.loads((ROOT / e['record']['path']).read_bytes())
        print(json.dumps({'registration': n, 'job': e['job_id'], 'record': e['record'], 'results': r['opinion']['results']}, ensure_ascii=False, indent=2))
    else:
        with (OUT / 'coordinator-notes-read.jsonl').open('a') as f:
            f.write(json.dumps({'observed_utc': datetime.now(timezone.utc).isoformat(), 'registration': n,
                'job': e['job_id'], 'record': e['record'], 'scope': 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR',
                'basis': 'DECLARED_ACTUAL_TOOL_READING_NOT_PROVEN', 'peer_credit': False, 'authority_effect': 'NONE'}, ensure_ascii=False) + '\n')
elif a.command == 'dispatch':
    r = campaign.dispatch(ROOT, PLAN, limit=3, model_label='current agent environment (declared)')
    print(json.dumps({'observation': save('dispatch', r), **r}, ensure_ascii=False))
elif a.command == 'register':
    r = campaign.submit(ROOT, PLAN, a.job, a.opinion, origin=a.origin)
    print(json.dumps({'observation': save('registration', r), **r}, ensure_ascii=False))
elif a.command == 'recover':
    r = campaign.status(ROOT, PLAN)
    for job in r['jobs']:
        if job['status'] != 'ASSIGNED':
            continue
        assignment = job['assignment']
        campaign.fail(ROOT, PLAN, job['id'], assignment_sha256=assignment['sha256'],
            reason='2026-10-23 recovery: environment restarted; original native reader and uncommitted /tmp outputs are unavailable. No reading credit recovered.',
            interrupted=True)
        print(json.dumps({'interrupted': job['id'], 'assignment': assignment}))
else:
    r = campaign.status(ROOT, PLAN)
    r['observed_utc'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps({'observation': save('status', r), 'status': r['status'],
        'states': dict(Counter(j['status'] for j in r['jobs'])),
        'needs_followup': [j['id'] for j in r['jobs'] if j['needs_followup']]}, ensure_ascii=False))
