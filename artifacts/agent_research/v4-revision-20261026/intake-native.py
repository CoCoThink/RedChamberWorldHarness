"""Serial custody plus full opinion display. Does not declare coordinator reading."""
from pathlib import Path
import json,sys
from rcwh.workflow.review_campaign import submit
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
launches=[json.loads(x) for x in (O/'launches.jsonl').read_text().splitlines()]
for job in sys.argv[1:]:
 launch=next(x for x in reversed(launches) if x.get('job_id',x.get('job'))==job)
 raw=Path(launch['raw_output']);op=json.loads(raw.read_bytes())
 result=submit(R,'data/agent_release/research-81-100-v4/review-campaign-v1.json',job,str(raw),origin=launch['task'])
 n=len(list(O.glob('registration-*.json')))+1;p=O/f'registration-{n:03d}.json';assert not p.exists();p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'registration':n,'job':job,'record':result['record'],'results':op['results']},ensure_ascii=False,indent=2),flush=True)
