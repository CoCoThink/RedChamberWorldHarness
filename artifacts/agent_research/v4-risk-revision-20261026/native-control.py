"""Native reader serial custody; never authors or changes reader verdicts."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse,json
from rcwh.workflow import review_campaign as campaign
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
P='data/agent_release/research-81-100-v4-r3/review-campaign-v1.json'
a=argparse.ArgumentParser();a.add_argument('command',choices=['status','dispatch','register','launch','read','log-read']);a.add_argument('job',nargs='?');a.add_argument('opinion',nargs='?');a.add_argument('--origin');a.add_argument('--limit',type=int,default=3);args=a.parse_args()
def save(prefix,value):
 n=1
 while (O/f'{prefix}-{n:03d}.json').exists():n+=1
 file=O/f'{prefix}-{n:03d}.json';file.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return file.relative_to(R).as_posix()
if args.command=='dispatch':
 v=campaign.dispatch(R,P,limit=args.limit,model_label='current agent environment (declared); fresh native reader');print(json.dumps({'observation':save('dispatch',v),**v},ensure_ascii=False))
elif args.command=='register':
 v=campaign.submit(R,P,args.job,args.opinion,origin=args.origin);print(json.dumps({'observation':save('registration',v),**v},ensure_ascii=False))
elif args.command=='launch':
 s=campaign.status(R,P);j=next(j for j in s['jobs'] if j['id']==args.job)
 with (O/'launches.jsonl').open('a') as f:f.write(json.dumps({'observed_utc':datetime.now(timezone.utc).isoformat(),'job':args.job,'attempt':j['attempts'],'task':args.origin,'fork_turns':'none','raw_output':f'/home/guan/rcwh-v4r3-outputs-20261026/{args.job}-a{j["attempts"]}.json'},ensure_ascii=False)+'\n')
elif args.command in {'read','log-read'}:
 n=int(args.job);e=json.loads((O/f'registration-{n:03d}.json').read_bytes())
 if args.command=='read':
  v=json.loads((R/e['record']['path']).read_bytes());print(json.dumps({'registration':n,'job':e['job_id'],'record':e['record'],'results':v['opinion']['results']},ensure_ascii=False,indent=2))
 else:
  with (O/'coordinator-notes-read.jsonl').open('a') as f:f.write(json.dumps({'observed_utc':datetime.now(timezone.utc).isoformat(),'registration':n,'job':e['job_id'],'record':e['record'],'scope':'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR','basis':'DECLARED_ACTUAL_TOOL_READING_NOT_PROVEN','peer_credit':False,'authority_effect':'NONE'},ensure_ascii=False)+'\n')
else:
 s=campaign.status(R,P);print(json.dumps({'observation':save('status',s),'status':s['status'],'states':dict(Counter(j['status'] for j in s['jobs'])),'needs_followup':[j['id'] for j in s['jobs'] if j['needs_followup']]},ensure_ascii=False))
