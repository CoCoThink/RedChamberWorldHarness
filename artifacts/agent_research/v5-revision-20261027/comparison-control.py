"""Record raw anonymous model opinions; no formal gate or human qualification."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import argparse,hashlib,json,shutil
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent/'comparison'
def ref(p):return {'path':p.relative_to(R).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def load(p):return json.loads(p.read_bytes())
def save(p,v):
 raw=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();p.parent.mkdir(exist_ok=True,parents=True)
 assert not p.exists() or p.read_bytes()==raw, f'refuse overwrite {p}'
 p.write_bytes(raw)
def chapter_text(assignment, alias, chapter):
 from rcwh.workflow.agent_release import _split
 return _split((R/assignment['read_in_full'][alias]['path']).read_text(),tuple(assignment['chapters']))[1][chapter]
def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['register','read','log-read','summary']);a.add_argument('identity',nargs='?');a.add_argument('opinion',nargs='?');a.add_argument('--origin');args=a.parse_args()
 assignments={load(R/b['path'])['id']:(b,load(R/b['path'])) for b in load(O/'plan.json')['assignments']}
 if args.command=='register':
  b,assignment=assignments[args.identity];p=Path(args.opinion);raw=p.read_bytes();op=json.loads(raw);s=assignment['output_scaffold']
  for key in ('kind','assignment_id','reader_session','files','authority_effect','qualification'):assert op[key]==s[key],key
  assert sorted(x['chapter'] for x in op['results'])==sorted(assignment['chapters'])
  assert len(op['results'])==len(assignment['chapters']) and isinstance(op['unread_scope'],list)
  for alias,f in assignment['read_in_full'].items():assert ref(R/f['path'])=={'path':f['path'],'sha256':f['sha256']}
  for result in op['results']:
   assert result['preference'] in {'A','B','TIE','UNDETERMINED'} and result['reason'].strip()
   assert isinstance(result['risks'],list)
   if result['preference']!='UNDETERMINED':
    assert not op['unread_scope'] and {e['alias'] for e in result['evidence']}=={'A','B'}
    for e in result['evidence']:
     assert e['quote'].strip() and e['quote'] in chapter_text(assignment, e['alias'], result['chapter']),e
  dest=O/'opinions'/f'{args.identity}-{hashlib.sha256(raw).hexdigest()}.json';dest.parent.mkdir(exist_ok=True)
  assert not dest.exists() or dest.read_bytes()==raw;dest.write_bytes(raw)
  receipt={'kind':'RAW_MODEL_COMPARISON_CUSTODY','assignment':b,'opinion':ref(dest),'origin':args.origin,'registered_utc':datetime.now(timezone.utc).isoformat(),'formal_review_credit':False,'P9_credit':False}
  assert args.origin
  save(O/'receipts'/f'{args.identity}.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
 elif args.command in {'read','log-read'}:
  receipt=load(O/'receipts'/f'{args.identity}.json')
  if args.command=='read':print(json.dumps(load(R/receipt['opinion']['path']),ensure_ascii=False,indent=2))
  else:
   with (O/'coordinator-read.jsonl').open('a') as f:f.write(json.dumps({'opinion':receipt['opinion'],'scope':'ALL_RESULTS_REASONS_EVIDENCE_RISKS_READ_BY_ROOT','observed_utc':datetime.now(timezone.utc).isoformat(),'peer_credit':False},ensure_ascii=False)+'\n')
 else:
  read={r['opinion']['sha256'] for r in map(json.loads,(O/'coordinator-read.jsonl').read_text().splitlines())}
  mapping={m['id']:m for m in load(O/'version-mapping-COORDINATOR-ONLY.json')};votes=defaultdict(Counter);details=[]
  for identity in assignments:
   receipt=load(O/'receipts'/f'{identity}.json');assert receipt['opinion']['sha256'] in read
   op=load(R/receipt['opinion']['path']);assert not op['unread_scope']
   for result in op['results']:
    assert result['preference']!='UNDETERMINED', 'unread/undetermined requires real follow-up'
    version=mapping[identity].get(result['preference'],result['preference']);votes[result['chapter']][version]+=1
    details.append({'identity':identity,'chapter':result['chapter'],'preference_alias':result['preference'],'preference_version':version,'raw_opinion':receipt['opinion']})
  assert all(sum(v.values())==2 for v in votes.values())
  result={'status':'COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS','votes':{str(k):dict(v) for k,v in sorted(votes.items())},'details':details,'blinding':'VOLUNTARY_ALIAS_ONLY_NOT_TECHNICALLY_ENFORCED','authority_effect':'NONE','P9_credit':False}
  save(O/'summary.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
