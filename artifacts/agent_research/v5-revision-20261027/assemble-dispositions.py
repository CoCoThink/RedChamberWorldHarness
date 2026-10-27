"""Append explicit root dispositions without changing any raw review or history."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json

from rcwh.generation.records import binding, bound_bytes
from rcwh.workflow.release_packets import _write_immutable
from rcwh.workflow.review_campaign import status

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent


def main():
    root = json.loads((O / 'root-rulings-final.json').read_bytes())
    assert root['status'] == 'FINAL_ROOT_AUTHORED_RULINGS_AFTER_READING'
    prior_ref = binding(R, 'artifacts/agent_research/v4-context-followup-20261026/coordinator-dispositions.json')
    prior = json.loads(bound_bytes(R, prior_ref))
    comparison_ref = binding(R, (O / 'comparison/summary.json').relative_to(R).as_posix())
    comparison = json.loads(bound_bytes(R, comparison_ref))
    assert comparison['status'] == 'COMPLETE_MODEL_COMPARISON_NOT_LITERARY_PASS'
    campaign = status(R, 'data/agent_release/research-81-100-v5/review-campaign-v1.json')
    assert len(campaign['jobs']) == 82
    assert all(j['status'] == 'COMPLETE' and not j['needs_followup'] for j in campaign['jobs'])
    records = deepcopy(prior['records'])
    issues = deepcopy(prior['issues'])
    read = {row['record']['sha256'] for row in map(json.loads, (O / 'coordinator-notes-read.jsonl').read_text().splitlines()) if row['scope'] == 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR' and row['peer_credit'] is False}
    new_results = {}
    for path in sorted(O.glob('registration-*.json')):
        receipt = json.loads(path.read_bytes())
        ref = receipt['record']
        assert ref['sha256'] in read
        record = json.loads(bound_bytes(R, ref))
        assert json.loads(bound_bytes(R, record['raw_output'])) == record['opinion']
        records.append({'job_id': receipt['job_id'], 'record': ref, 'registration': binding(R, path.relative_to(R).as_posix()), 'results': len(record['opinion']['results']), 'root_reading': 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR', 'round': O.name})
        for result in record['opinion']['results']:
            new_results[(ref['sha256'], result['subject_id'])] = (receipt, result)
    rulings = {(r['record_sha256'], r['subject_id']): r for r in root['new_issue_rulings']}
    negative = {key for key, (_, result) in new_results.items() if result['verdict'] in ['FAIL', 'REJECT']}
    assert negative <= rulings.keys(), ('missing actual negative disposition', negative - rulings.keys())
    assert rulings.keys() <= new_results.keys()
    for key, ruling in rulings.items():
        receipt, result = new_results[key]
        assert ruling['rationale'].strip()
        issues.append({'record': receipt['record'], 'subject_id': result['subject_id'], 'job_id': receipt['job_id'], 'round': 'V5', 'original_result': result, 'ruling': ruling['ruling'], 'rationale': ruling['rationale'], 'affected_chapters': ruling['affected_chapters'], 'resolution_evidence': ruling.get('resolution_evidence', []), 'authority_effect': 'NONE'})
    all_results = [result for record in records for result in json.loads(bound_bytes(R, record['record']))['opinion']['results']]
    all_negative = [r for r in all_results if r['verdict'] in ['FAIL', 'REJECT']]
    assert len({r['record']['sha256'] for r in records}) == len(records)
    ledger = {'status': 'FINAL_ROOT_COORDINATOR_RULINGS', 'scope': 'V5_RESEARCH_ONLY_ALL_HISTORICAL_NEGATIVES_RETAINED', 'authority_effect': 'NONE', 'coordinator_session_id': 'coordinator:release-v1', 'prior_ledger': prior_ref, 'comparison': comparison_ref, 'editorial_assistance': binding(R, (O / 'design-assistance-ledger.json').relative_to(R).as_posix()), 'basis': 'Root actually read all new notes/sample checks and all new comparison reasons/evidence/risks. Earlier reading declarations and raw negatives remain. Model comparison is not P9.', 'records': records, 'issues': issues, 'chapters': root['chapters'], 'book_continuity_rulings': root['book_continuity_rulings'], 'required_future_work': root['required_future_work'], 'counts': {'total_actual_registered_records': len(records), 'new_v5_records': len(records) - len(prior['records']), 'current_jobs': len(campaign['jobs']), 'reused_current_jobs': sum(j['reused'] for j in campaign['jobs']), 'subject_results': len(all_results), 'negative_results_all_history': len(all_negative), 'negative_by_severity_all_history': dict(Counter(r.get('severity', 'BLOCKING') for r in all_negative)), 'new_negative_results': len(negative), 'disposition_entries_including_pass_annotations': len(issues), 'separate_model_comparison_opinions': len({d['identity'] for d in comparison['details']})}}
    target = (O / 'coordinator-dispositions.json').relative_to(R).as_posix()
    _write_immutable(R, target, ledger)
    print(json.dumps({'status': 'PASS', 'ledger': binding(R, target), 'counts': ledger['counts']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
