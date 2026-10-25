"""Bounded anonymous A/B packets. Model-only, voluntary blinding; no P9 credit."""
from pathlib import Path
import hashlib,json,secrets
R=Path(__file__).resolve().parents[3]; O=Path(__file__).resolve().parent/'comparison'
def bind(path):
 raw=path.read_bytes();return {'path':path.relative_to(R).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def main():
 assert not O.exists(), 'comparison preparation is immutable; use a new version'
 O.mkdir(); old=json.loads((R/'data/agent_release/research-81-100-v3/request.json').read_bytes());new=json.loads((R/'data/agent_release/research-81-100-v4-r3/request.json').read_bytes())
 rows=[{r['chapter']:r for r in v['chapters']} for v in (old,new)]
 changed=[ch for ch in rows[0] if rows[0][ch]['candidate']!=rows[1][ch]['candidate']]
 groups=[]; group=[];size=0
 for ch in changed:
  cost=sum(len((R/row[ch]['candidate']['path']).read_bytes()) for row in rows)+10
  assert cost<197*1024
  if group and size+cost>197*1024:groups.append(group);group=[];size=0
  group.append(ch);size+=cost
 if group:groups.append(group)
 mapping=[]; assignments=[]
 for n,chapters in enumerate(groups,1):
  folder=O/f'group-{n:02d}';folder.mkdir()
  # Randomize each reader independently to limit systematic A/B preference.
  for reader in (1,2):
   task=folder/f'reader-{reader}';task.mkdir();order=[0,1] if secrets.randbits(1) else [1,0]
   refs={}
   for alias,index in zip(['A','B'],order):
    path=task/f'{alias}.md'; path.write_bytes(b'\n\n'.join((R/rows[index][ch]['candidate']['path']).read_bytes() for ch in chapters));refs[alias]=bind(path)
   total=sum(b['bytes'] for b in refs.values());assert total<=197*1024
   identity=f'literary-ab-g{n:02d}-r{reader}'
   assignment={'kind':'MODEL_LITERARY_ANONYMOUS_COMPARISON','id':identity,'chapters':chapters,'read_in_full':refs,'reading_bytes':total,'max_read_bytes':197*1024,
    'instructions':'只读本任务 A/B 两文件，逐回完整读；不读版本映射、历史、设计、意见或仓库其他正文。分别比较人物声口、动作因果、时间/物件可读性、叙事节奏、重复纠错与自证旁白。逐回独立选择 A/B/TIE/UNDETERMINED；可偏好不同版本。引两版原句定位优劣，指出新生问题，不因更清楚就自动判文学更好。材料未读完则 UNDETERMINED 并写 unread_scope。匿名仅是自愿限读、模型新上下文，不是技术隔离或人工盲评。',
    'output_scaffold':{'kind':'MODEL_LITERARY_COMPARISON_OPINION','assignment_id':identity,'reader_session':identity,'files':refs,'results':[{'chapter':ch,'preference':'UNDETERMINED','reason':'','evidence':[],'risks':[]} for ch in chapters],'unread_scope':[],'authority_effect':'NONE','qualification':'MODEL_ONLY_NOT_P9'}}
   path=task/'assignment.json';path.write_text(json.dumps(assignment,ensure_ascii=False,indent=2)+'\n');assignments.append(bind(path))
   mapping.append({'id':identity,'A':'v3' if order[0]==0 else 'v4','B':'v3' if order[1]==0 else 'v4','chapters':chapters})
 (O/'version-mapping-COORDINATOR-ONLY.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
 (O/'plan.json').write_text(json.dumps({'kind':'ANONYMOUS_MODEL_COMPARISON_PLAN','assignments':assignments,'changed_chapters':changed,'groups':groups,'blinding':'VOLUNTARY_ALIAS_ONLY_READING_NOT_TECHNICALLY_ENFORCED','formal_review_credit':False,'P9_credit':False},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'groups':groups,'fresh_readers':len(assignments),'max_reading_bytes':max(json.loads((R/b['path']).read_bytes())['reading_bytes'] for b in assignments)},ensure_ascii=False))
if __name__=='__main__':main()
