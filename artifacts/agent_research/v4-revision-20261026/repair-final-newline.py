"""Pre-freeze actual formatting correction; preserve original imports and failed attempt."""
from pathlib import Path
from copy import deepcopy
import json,shutil,subprocess,hashlib
from rcwh.generation.records import binding,bound_bytes
from rcwh.generation.session import prepare_request,import_draft
from rcwh.generation.writing import feedback_report
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
with rebuild_scope():
 s=json.loads((R/'data/agent_release/selection-81-100-v5.json').read_bytes());r=next(r for r in s['chapters'] if r['chapter']==92);previous=deepcopy(r)
 base=O/'revisions/ch92-format'
 def write(suffix,value):
  p=Path(str(base)+suffix);assert not p.exists();p.write_bytes(value if isinstance(value,bytes) else canonical_bytes(value));return binding(R,p.relative_to(R).as_posix())
 f=write('-feedback.json',feedback_report(R,r['draft']['path']))
 notes=write('-notes.json',{'kind':'ROOT_ACTUAL_FORMAT_CORRECTION','chapter':92,'reason':'末段替换漏保留文件末尾换行，首轮prepare拼接标题失败；仅追加一枚LF，正文措辞不变，首轮输入尚未冻结或派读。','authority_effect':'NONE'})
 q=write('-request.json',prepare_request(R,parent_path=r['draft']['path'],feedback_path=f['path'],notes_path=notes['path'],revision_template='revise-v2',renderer_version=2))
 raw=bound_bytes(R,r['candidate']);assert not raw.endswith(b'\n');t=write('-edited.txt',raw+b'\n')
 result=import_draft(R,t['path'],q['path'],session_id='coordinator-format-20261026:ch92',session_model_label='current agent environment (declared); root actual final-newline correction',parent_path=r['draft']['path'],feedback_path=f['path'])
 r.update(candidate=result['candidate'],draft=result['draft']);s['id']='selection:81-100:v6'
 (R/'data/agent_release/selection-81-100-v6.json').write_bytes(canonical_bytes(s));write('-result.json',{'previous':previous,'current':r,'import':result,'bytes_added':'0a','semantic_change':False})
 failed=R/'data/agent_release/research-81-100-v4'
 assert not subprocess.check_output(['git','ls-files',str(failed.relative_to(R))],cwd=R).strip()
 assert not (failed/'request.json').exists()
 inventory=[{'original_path':p.relative_to(R).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(failed.rglob('*')) if p.is_file()]
 (O/'preparation-failure-001.json').write_bytes(canonical_bytes({'status':'WITHDRAWN_PRE_FREEZE_NO_READER_CREDIT','failure':json.loads((O/'prepare-output.json').read_bytes()),'files':inventory,'cause':'Root omitted final LF in ch92 edit; appended in a separate truthful revision before freezing. Temporary release directory removed and will be freshly prepared; content-addressed candidates/drafts remain retained.','authority_effect':'NONE'}))
 shutil.rmtree(failed)
 (O/'prepare-output.json').rename(O/'prepare-output-failed-001.json')
 print('Appended LF as retained actual revision; new selection-v6; failed pre-freeze preparation withdrawn.')
