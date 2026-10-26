"""Audit actual custody and release results. No scores/opinions are generated."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import json,subprocess
from core_evidence import validate_core
from rcwh.generation.records import binding,bound_bytes
from rcwh.workflow.review_campaign import status
from rcwh.workflow.agent_release import AgentRelease
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_bytes())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def main():
 campaign=status(R,'data/agent_release/research-81-100-v4-r3/review-campaign-v1.json')
 assert len(campaign['jobs'])==74 and all(j['status']=='COMPLETE' and not j['needs_followup'] for j in campaign['jobs'])
 receipts=[load(p) for p in sorted(O.glob('registration-*.json'))]
 fresh_jobs={j['id'] for j in campaign['jobs'] if not j['reused']}
 assert len(receipts)==len(fresh_jobs) and {r['job_id'] for r in receipts}==fresh_jobs
 assert len({r['job_id'] for r in receipts})==len(receipts)
 rootlog=lines(O/'coordinator-notes-read.jsonl');valid=[r for r in rootlog if r['scope']=='ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR'];assert len(valid)==len(receipts) and len({r['record']['sha256'] for r in valid})==len(receipts)
 assert {r['record']['sha256'] for r in valid}=={r['record']['sha256'] for r in receipts}
 earlier=R/'artifacts/agent_research/v4-correction-20261026'
 earlier_receipts=[load(p) for p in sorted(earlier.glob('registration-*.json'))];assert len(earlier_receipts)==7
 earlier_read=lines(earlier/'coordinator-notes-read.jsonl');assert len(earlier_read)==7
 assert {x['record']['sha256'] for x in earlier_receipts}=={x['record']['sha256'] for x in earlier_read}
 for receipt in earlier_receipts:
  record=json.loads(bound_bytes(R,receipt['record']))
  assert json.loads(bound_bytes(R,record['raw_output']))==record['opinion']
 earlier_ci=load(earlier/'input-ci.json');assert earlier_ci['conclusion']=='success' and all(j['conclusion']=='success' for j in earlier_ci['jobs'])
 earlier_completed=max(datetime.fromisoformat(j['completedAt'].replace('Z','+00:00')) for j in earlier_ci['jobs'])
 earlier_launches=lines(earlier/'launches.jsonl');assert len(earlier_launches)==7
 assert all(x['fork_turns']=='none' and datetime.fromisoformat(x['observed_utc'])>earlier_completed for x in earlier_launches)
 ci=load(O/'input-ci-binding.json');assert ci['conclusion']=='success' and ci['headSha']==load(O/'input-commit.json')['commit']
 ci_jobs=load(O/'input-ci.json')['jobs'];assert len(ci_jobs)==2 and all(j['conclusion']=='success' for j in ci_jobs)
 completed=max(datetime.fromisoformat(j['completedAt'].replace('Z','+00:00')) for j in ci_jobs)
 launches=lines(O/'launches.jsonl')
 assert {x.get('job_id',x.get('job')) for x in launches}==fresh_jobs
 assert len(launches)==sum(j['attempts'] for j in campaign['jobs'])
 assert len({(x['job_id'],x['attempt']) for x in launches})==len(launches)
 failed=[]
 for launch in launches:
  bound_bytes(R,launch['assignment'])
  event=load(R/campaign['attempt_directory']/launch['job_id']/f"attempt-{launch['attempt']}.json")
  assert event['assignment']==launch['assignment'] and event['attempt']==launch['attempt']
  assert event['status'] in {'FAILED','REGISTERED'}
  if event['status']=='FAILED':
   assert event['record'] is None and event['error'].strip() and event['status_code'] in {429,500,502,503,504}
   assert event['error'] in bound_bytes(R,event['stderr']).decode()
   failed.append({'job':launch['job_id'],'attempt':launch['attempt'],'task':launch['task'],'status_code':event['status_code'],'error':event['error']})
  else:
   assert any(r['job_id']==launch['job_id'] and r['record']==event['record'] for r in receipts)
 assert len(launches)==len(receipts)+len(failed)
 assert all(x['fork_turns']=='none' and datetime.fromisoformat(x['observed_utc'])>completed for x in launches)
 assert len({x['task'] for x in launches})==len(launches)
 plan=json.loads((R/'data/agent_release/research-81-100-v4-r3/review-campaign-v1.json').read_bytes())
 metadata={j['id']:j for j in plan['jobs']}
 jobs={j['id']:{**metadata[j['id']],**j} for j in campaign['jobs']};seams=Counter();subjects=[];book=[]
 for receipt in receipts:
  job=jobs[receipt['job_id']];assert job['record']==receipt['record'] and not job.get('reused',False)
  record=load(R/receipt['record']['path']);bound_bytes(R,receipt['record']);raw=bound_bytes(R,record['raw_output']);assert json.loads(raw)==record['opinion']
  subjects.extend(record['opinion']['results'])
  if job['kind']=='BOOK':
   notes='\n'.join(x['notes'] for x in record['opinion']['results'])
   for left,right in job['continuity']['seams']:
    assert f'{left}→{right}' in notes,(job['id'],left,right)
    seams[(left,right)]+=1
   book.append({'job':job['id'],'record':receipt['record'],'seams':job['continuity']['seams'],'verdicts':[x['verdict'] for x in record['opinion']['results']]})
 assert len(book)==8 and len(seams)==19 and set(seams.values())=={2}
 comparison=load(O/'comparison/summary.json');assert comparison['status']=='COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS' and comparison['P9_credit'] is False
 cl=lines(O/'comparison/launches.jsonl');assert len(cl)==4 and len({x['task'] for x in cl})==4
 assert not {x['task'] for x in cl}&{x['task'] for x in launches+earlier_launches}
 assert all(x['fork_turns']=='none' and x['P9_credit'] is False for x in cl)
 assert all(datetime.fromisoformat(x['observed_utc'])>completed for x in cl)
 cr=[load(p) for p in sorted((O/'comparison/receipts').glob('*.json'))];assert len(cr)==4
 readcmp=lines(O/'comparison/coordinator-read.jsonl');assert len(readcmp)==4
 assert {x['opinion']['sha256'] for x in cr}=={x['opinion']['sha256'] for x in readcmp}
 for receipt in cr:bound_bytes(R,receipt['opinion'])
 ledger=load(O/'coordinator-dispositions.json');assert ledger['comparison']==binding(R,(O/'comparison/summary.json').relative_to(R).as_posix())
 release=AgentRelease(R).evaluate('data/agent_release/research-81-100-v4-r3/request.json')
 assert release['status'] in {'PASS','PENDING'} and not release['findings'] and len(release['chapters'])==20
 handoff=release['status']=='PENDING'
 core,unresolved=validate_core(R,O,unresolved_handoff=handoff,chapters=ledger['chapters'])
 assert {ch['chapter'] for ch in release['chapters'] if ch['gates']['COORDINATOR_DECISION']=='PENDING'}==unresolved
 assert all(v=='PASS' for ch in release['chapters'] for name,v in ch['gates'].items() if name!='COORDINATOR_DECISION')
 gates=Counter(v for ch in release['chapters'] for v in ch['gates'].values())
 assert gates=={'PASS':240-len(unresolved),**({'PENDING':len(unresolved)} if unresolved else {})}
 if handoff:
  assert not (R/'releases/agent/research-81-100-v4-r3').exists()
  build=load(O/'normal-build-attempt.json');assert build['release_status']=='PENDING' and build['refused'] and build['allow_pending'] is False
  assert build['exit_code']!=0 and 'only explicit pending staging is allowed' in build['stderr']
  delivery={'reading_book':binding(R,'data/agent_release/research-81-100-v4-r3/reading/book.md'),'evaluation':binding(R,(O/'final-release-evaluation.json').relative_to(R).as_posix()),'published_book':None,'published_manifest':None}
 else:
  delivery={'book':binding(R,'releases/agent/research-81-100-v4-r3/book.md'),'manifest':binding(R,'releases/agent/research-81-100-v4-r3/manifest.json')}
 preserved=['data/world','data/scenes','data/provenance','sources','releases/stable',
            'releases/agent/research-81-100-v1','releases/agent/research-81-100-v2','releases/agent/research-81-100-v3',
            'data/agent_release/research-81-100-v1','data/agent_release/research-81-100-v2','data/agent_release/research-81-100-v3',
            'data/agent_release/selection-81-100-v4.json']
 subprocess.run(['git','diff','--exit-code','29a81d5','--',*preserved],cwd=R,check=True,capture_output=True)
 changes=subprocess.check_output(['git','diff','--name-status','29a81d5','--','data/planning'],cwd=R,text=True).splitlines()
 assert set(changes)=={'A\tdata/planning/contracts/agent-final-v1/92-S6.v3.json','A\tdata/planning/contracts/agent-final-v1/93-S2.v3.json'}
 assert binding(R,'releases/agent/research-81-100-v3/book.md')['sha256']=='ea7fcdb562474f84455df65a6ba173a04025fb7d6b753c6d237ed47b21c50335'
 assert binding(R,'data/agent_release/research-81-100-v3/request.json')['sha256']=='bd20c3cdaaf70db7eeda7a60a90a09375408c164c7fe75f2e2ea7a3bb2572d41'
 negatives=[x for x in subjects if x['verdict'] in ('FAIL','REJECT')]
 result={'status':'PASS','scope':'ACTUAL_EXECUTION_CUSTODY_NOT_MACHINE_PROOF_OF_READING_OR_LITERARY_QUALITY','worktree_base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'input_ci':ci,'new_formal_records':len(receipts),'actual_formal_launches':len(launches),'failed_transport_attempts':failed,'core_status':core['status'],'release_status':release['status'],'unresolved_chapters':sorted(unresolved),'earlier_r2_records_retained':7,'reused_current_jobs':sum(j.get('reused',False) for j in campaign['jobs']),'new_subject_results':len(subjects),'new_negative_results':len(negatives),'new_negative_severity':dict(Counter(x.get('severity','BLOCKING') for x in negatives)),'valid_root_reading_declarations':len(valid),'retracted_premature_root_declarations':sum(x['scope']=='RETRACTED_PREMATURE_ROOT_READING_DECLARATION' for x in rootlog),'book_readers':book,'unique_seams':19,'reader_seam_notes':sum(seams.values()),'comparison_readers':4,'comparison_votes':comparison['votes'],'release_gates':dict(gates),'request':binding(R,'data/agent_release/research-81-100-v4-r3/request.json'),**delivery,'preserved_trees':preserved,'resource_parity':'RESOURCE_PARITY_NOT_VERIFIED','P9_credit':False,'authority_effect':'NONE'}
 target=O/'actual-execution-verification.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['book_readers','comparison_votes']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
