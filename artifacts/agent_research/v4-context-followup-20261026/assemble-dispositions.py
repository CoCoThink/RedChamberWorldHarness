"""Assemble explicit root rulings with unchanged raw opinions; no generated votes."""
from copy import deepcopy
from collections import Counter
from pathlib import Path
import json
from rcwh.generation.records import binding,bound_bytes
from rcwh.candidate_reviews import canonical_bytes
from rcwh.workflow.review_campaign import status
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent

def main():
 root=json.loads((O/'root-rulings-final.json').read_bytes())
 assert root['status']=='FINAL_ROOT_AUTHORED_RULINGS_AFTER_READING'
 prior_ref=binding(R,'artifacts/agent_research/v3-revision-20261025/coordinator-dispositions.json')
 prior=json.loads(bound_bytes(R,prior_ref));cmp_ref=binding(R,(R/'artifacts/agent_research/v4-risk-revision-20261026/comparison/summary.json').relative_to(R).as_posix())
 cmp=json.loads(bound_bytes(R,cmp_ref));assert cmp['status']=='COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS'
 campaign=status(R,'data/agent_release/research-81-100-v4-r4/review-campaign-v1.json')
 assert len(campaign['jobs'])==76 and all(j['status']=='COMPLETE' and not j['needs_followup'] for j in campaign['jobs'])
 registry=[];results={};records=deepcopy(prior['records'])
 for directory in (R/'artifacts/agent_research/v4-correction-20261026',R/'artifacts/agent_research/v4-risk-revision-20261026',O):
  read={x['record']['sha256'] for x in map(json.loads,(directory/'coordinator-notes-read.jsonl').read_text().splitlines()) if x['scope']=='ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR' and x['peer_credit'] is False}
  for p in sorted(directory.glob('registration-*.json')):
   receipt=json.loads(p.read_bytes());ref=receipt['record'];assert ref['sha256'] in read
   op=json.loads(bound_bytes(R,ref))['opinion'];registry.append(receipt)
   records.append({'job_id':receipt['job_id'],'record':ref,'registration':binding(R,p.relative_to(R).as_posix()),'results':len(op['results']),'root_reading':'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR','round':directory.name})
   for result in op['results']:results[(ref['sha256'],result['subject_id'])]=(receipt,result)
 rulings={(x['record_sha256'],x['subject_id']):x for x in root['new_issue_rulings']};negative={key for key,(_,r) in results.items() if r['verdict'] in ['FAIL','REJECT']}
 assert negative<=rulings.keys(),('missing specific negative ruling',negative-rulings.keys())
 assert rulings.keys()<=results.keys()
 issues=deepcopy(prior['issues'])  # Raw prior results and their historical rulings remain exact.
 prior_issues={(i['record']['sha256'],i['subject_id']):i for i in prior['issues']}
 for correction in root.get('historical_ruling_corrections',[]):
  key=(correction['record_sha256'],correction['subject_id']);old=prior_issues[key]
  assert correction['rationale'].strip() and correction['resolution_evidence']
  issues.append({'record':old['record'],'subject_id':old['subject_id'],'job_id':old['job_id'],
   'round':'V4_COORDINATOR_RECONSIDERATION_NOT_NEW_PEER_REVIEW','original_result':deepcopy(old['original_result']),
   'ruling':correction['ruling'],'rationale':correction['rationale'],
   'affected_chapters':correction['affected_chapters'],'resolution_evidence':correction['resolution_evidence'],
   'prior_disposition_retained_in':prior_ref,'supersedes_coordinator_disposition_only':True,
   'authority_effect':'NONE'})
 for key,ruling in rulings.items():
  receipt,result=results[key];assert ruling['rationale'].strip()
  issues.append({'record':receipt['record'],'subject_id':result['subject_id'],'job_id':receipt['job_id'],'round':'V4','original_result':result,'ruling':ruling['ruling'],'rationale':ruling['rationale'],'affected_chapters':ruling['affected_chapters'],'resolution_evidence':ruling.get('resolution_evidence',[]),'authority_effect':'NONE'})
 allresults=[]
 for rec in records:allresults.extend(json.loads(bound_bytes(R,rec['record']))['opinion']['results'])
 neg=[r for r in allresults if r['verdict'] in ['FAIL','REJECT']]
 ledger={'status':'FINAL_ROOT_COORDINATOR_RULINGS','scope':'V4_RESEARCH_ONLY_WITH_ALL_HISTORICAL_NEGATIVES_RETAINED','authority_effect':'NONE','coordinator_session_id':'coordinator:release-v1','prior_ledger':prior_ref,'comparison':cmp_ref,'editorial_assistance':binding(R,(O/'design-assistance-ledger.json').relative_to(R).as_posix()),'basis':'Actual root reading of every new note/sample check and every comparison. Prior read logs retained. No raw peer verdict edited; model A/B is not P9.','records':records,'issues':issues,'chapters':root['chapters'],'book_continuity_rulings':root['book_continuity_rulings'],'required_future_work':root['required_future_work'],'counts':{'total_actual_registered_records':len(records),'new_v4_records':len(registry),'current_jobs':len(campaign['jobs']),'reused_current_jobs':sum(j.get('reused',False) for j in campaign['jobs']),'subject_results':len(allresults),'negative_results_all_history':len(neg),'negative_by_severity_all_history':dict(Counter(r.get('severity','BLOCKING') for r in neg)),'new_negative_results':len(negative),'disposition_entries_including_pass_annotations':len(issues),'separate_model_comparison_opinions':len({d['identity'] for d in cmp['details']})}}
 target=O/'coordinator-dispositions.json';raw=canonical_bytes(ledger);assert not target.exists() or target.read_bytes()==raw;target.write_bytes(raw)
 print(json.dumps({'status':'PASS','ledger':binding(R,target.relative_to(R).as_posix()),'counts':ledger['counts']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
