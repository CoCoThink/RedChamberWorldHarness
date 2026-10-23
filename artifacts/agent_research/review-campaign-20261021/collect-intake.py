"""Retain registered reader findings verbatim; never generate dispositions."""
from collections import Counter
from pathlib import Path
import argparse
import json
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import bound_bytes

ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser()
p.add_argument('--directory', default=str(Path(__file__).resolve().parent.relative_to(ROOT)))
a = p.parse_args()
directory = ROOT / a.directory
records, issues, annotations = [], [], []
for path in sorted(directory.glob('registration-*.json')):
    registration = json.loads(path.read_bytes())
    ref = registration['record']
    opinion = json.loads(bound_bytes(ROOT, ref))['opinion']
    records.append(ref)
    for result in opinion['results']:
        row = {**result, 'job_id': registration['job_id'], 'record': ref,
               'disposition': 'PENDING_COORDINATOR_REVIEW'}
        if result['verdict'] != 'PASS':
            issues.append(row)
        elif result.get('severity') == 'ADVISORY':
            annotations.append(row)
value = {'registered_jobs': len(records), 'negative_results': len(issues),
         'by_severity': dict(Counter(r.get('severity', 'UNSPECIFIED') for r in issues)),
         'records': records, 'issues': issues, 'annotated_pass_results': annotations,
         'authority_effect': 'NONE'}
(directory / 'issue-intake.json').write_bytes(canonical_bytes(value))
print(json.dumps({k: v for k, v in value.items() if k not in ('records', 'issues', 'annotated_pass_results')}))
