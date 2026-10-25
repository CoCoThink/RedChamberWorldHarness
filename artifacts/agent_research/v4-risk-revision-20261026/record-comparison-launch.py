"""Record only an already invoked native comparison task; creates no opinions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;C=O/'comparison'
p=argparse.ArgumentParser();p.add_argument('identity');p.add_argument('--origin',required=True);a=p.parse_args()
rows=[json.loads((R/ref['path']).read_bytes()) for ref in json.loads((C/'plan.json').read_bytes())['assignments']]
assignment=next(row for row in rows if row['id']==a.identity)
ref=next(ref for ref in json.loads((C/'plan.json').read_bytes())['assignments'] if json.loads((R/ref['path']).read_bytes())['id']==a.identity)
protocol=O/'comparison-reader-protocol-v1.md'
entry={'observed_utc':datetime.now(timezone.utc).isoformat(),'identity':a.identity,'task':a.origin,'fork_turns':'none','model':'current environment route (declared)','assignment':ref,'instruction_protocol':{'path':protocol.relative_to(R).as_posix(),'sha256':hashlib.sha256(protocol.read_bytes()).hexdigest()},'raw_output':f'/home/guan/rcwh-v4r3-outputs-20261026/{a.identity}.json','formal_review_credit':False,'P9_credit':False}
file=C/'launches.jsonl';old=[json.loads(s) for s in file.read_text().splitlines()] if file.exists() else []
assert not any(row['identity']==a.identity for row in old),'already recorded launch'
with file.open('a') as f:f.write(json.dumps(entry,ensure_ascii=False)+'\n')
