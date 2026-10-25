"""Record actual launches after the root has invoked native agent tools."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('dispatch');p.add_argument('--protocol',action='store_true');a=p.parse_args()
d=json.loads((O/a.dispatch).read_bytes());existing=[json.loads(s) for s in (O/'launches.jsonl').read_text().splitlines()] if (O/'launches.jsonl').exists() else []
with (O/'launches.jsonl').open('a') as out:
 for item in d['assignments']:
  kind,ch,index,reader=item['job_id'].split('-');name=f'v4c_ch{ch}_{index}_{reader}_a{item["attempt"]}' if kind=='CHAPTER' else f'v4c_book_{index}_{reader}_a{item["attempt"]}'
  row={'observed_utc':datetime.now(timezone.utc).isoformat(),**item,'task':'/root/'+name,'fork_turns':'none','model':'current environment route (declared)','raw_output':f'/home/guan/rcwh-v4c-outputs-20261026/{item["job_id"]}-a{item["attempt"]}.json'}
  if a.protocol:
   f=O/'native-reader-protocol-v1.md';row['instruction_protocol']={'path':f.relative_to(R).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
  if kind=='BOOK':
   row['seam_note_requirement']='Each assigned seam separately labelled and discussed in subject notes; COMPLETE alone does not prove reading coverage.'
  found=[x for x in existing if x.get('job_id',x.get('job'))==item['job_id'] and x['attempt']==item['attempt']]
  if found:assert len(found)==1 and found[0]['task']==row['task'];continue
  out.write(json.dumps(row,ensure_ascii=False)+'\n')
