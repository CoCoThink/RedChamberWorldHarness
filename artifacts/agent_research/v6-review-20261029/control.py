"""Serial native-review custody and explicit coordinator decisions; no opinions authored."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding, bound_bytes
from rcwh.workflow.agent_release import AgentRelease
from rcwh.workflow.release_packets import _write_immutable
from rcwh.workflow.review_campaign import submit, status

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent
REL = O.relative_to(R).as_posix()
BASE = 'data/agent_release/research-81-100-v6-r2'
REQUEST = BASE + '/request.json'
PLAN = BASE + '/review-campaign-v1.json'


def load(path):
    return json.loads((R / path).read_bytes())


def save(name, value):
    return _write_immutable(R, REL + '/' + name, value)


def registration(number):
    return load(REL + f'/registration-{number:03d}.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['intake', 'read', 'declare-read', 'status', 'finalize', 'build'])
    parser.add_argument('values', nargs='*')
    args = parser.parse_args()
    if args.command == 'intake':
        launches = [json.loads(s) for s in (O / 'launches.jsonl').read_text().splitlines()]
        for job in args.values:
            launch = next(x for x in launches if x['job'] == job)
            result = submit(R, PLAN, job, launch['raw_output'], origin=launch['task'])
            n = len(list(O.glob('registration-*.json'))) + 1
            save(f'registration-{n:03d}.json', result)
            print(json.dumps({'registration': n, 'job': job, 'record': result['record']}, ensure_ascii=False))
    elif args.command == 'read':
        for number in args.values:
            receipt = registration(int(number))
            record = json.loads(bound_bytes(R, receipt['record']))
            print(json.dumps({'registration': int(number), 'job': receipt['job_id'], 'record': receipt['record'],
                              'results': record['opinion']['results']}, ensure_ascii=False, indent=2))
    elif args.command == 'declare-read':
        # Run in a later tool call after actual complete notes display.
        log = O / 'coordinator-notes-read.jsonl'
        seen = {json.loads(s)['registration'] for s in log.read_text().splitlines()} if log.exists() else set()
        for number in map(int, args.values):
            if number in seen:
                raise ValueError('reading declaration already retained')
            receipt = registration(number)
            row = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'registration': number,
                   'job': receipt['job_id'], 'record': receipt['record'],
                   'scope': 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR',
                   'basis': 'DECLARED_ACTUAL_TOOL_READING_NOT_PROVEN', 'peer_credit': False, 'authority_effect': 'NONE'}
            with log.open('a') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    elif args.command == 'status':
        report = status(R, PLAN)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == 'finalize':
        ledger_ref = binding(R, REL + '/coordinator-dispositions.json')
        ledger = json.loads(bound_bytes(R, ledger_ref))
        campaign = status(R, PLAN)
        if any(j['status'] != 'COMPLETE' or j['needs_followup'] for j in campaign['jobs']):
            raise ValueError('actual reviews still incomplete')
        sys.path.insert(0, str(R / 'tools'))
        from verify_contract_revision import verify_core_evidence
        verify_core_evidence(R)
        known = {row['record']['sha256']: row['record'] for row in ledger['records']}
        issues = {(i['record']['sha256'], i['subject_id']): i for i in ledger['issues']}
        for row in ledger['records']:
            record = json.loads(bound_bytes(R, row['record']))
            for result in record['opinion']['results']:
                if result['verdict'] in {'FAIL', 'REJECT'}:
                    issue = issues.get((row['record']['sha256'], result['subject_id']))
                    if not issue or issue['original_result'] != result or not issue['rationale'].strip():
                        raise ValueError('unresolved/missing historical negative disposition')
        runtime = AgentRelease(R)
        report = runtime.evaluate(REQUEST)
        if report['status'] == 'FAIL' or report['findings']:
            raise ValueError('integrity failure cannot be overruled')
        if any(value != 'PASS' for c in report['chapters'] for name, value in c['gates'].items() if name != 'COORDINATOR_DECISION'):
            raise ValueError('non-coordinator gate not passed')
        request = load(REQUEST)
        save('request-before-decisions.json', request)
        reports = {c['chapter']: c for c in report['chapters']}
        decisions = []
        for row in request['chapters']:
            ch = row['chapter']; ruling = ledger['chapters'][str(ch)]
            reviews = reports[ch]['reviews']
            subjects = [reviews['candidate']] + [s for k in ('contract_reviews', 'source_reviews', 'corpus_reviews') for s in reviews.get(k, [])]
            opinions, dissent = {}, defaultdict(dict)
            for subject in subjects:
                for key in ('opinions', 'prior_context_opinions'):
                    for opinion in subject.get(key, []):
                        ref = opinion['record']
                        if known.get(ref['sha256']) != ref:
                            raise ValueError('unknown contextual record')
                        opinions[ref['sha256']] = ref
                        if opinion['verdict'] in {'FAIL', 'REJECT'}:
                            issue = issues[(ref['sha256'], opinion['subject_id'])]
                            if issue['original_result'].get('severity') != 'ADVISORY':
                                raise ValueError('cannot overrule blocking opinion')
                            dissent[ref['sha256']][opinion['subject_id']] = issue['rationale']
            packet = json.loads(bound_bytes(R, row['panel']['packet']))
            decision = {'schema_version': 1, 'decision_kind': 'AGENT_RELEASE_COORDINATOR_DECISION',
                'chapter': ch, 'candidate': row['candidate'], 'outcome': ruling['outcome'],
                'coordinator_session_id': packet['coordinator_session_id'],
                'rationale': ruling['rationale'] + f' 完整历史处置：{ledger_ref["path"]}（SHA256 {ledger_ref["sha256"]}）。仅为研究决定；不消除原负面，不授予文学、人工或P9资格。',
                'considered_opinions': [opinions[k] for k in sorted(opinions)],
                'rejected_opinions': [{'record': opinions[k], 'rationale': '；'.join(f'{s}：{why}' for s, why in sorted(v.items()))} for k, v in sorted(dissent.items())],
                'authority_effect': 'NONE'}
            runtime._validate(decision, 'decision')
            row['decision'] = _write_immutable(R, BASE + f'/coordinator/ch{ch}.json', decision)
            decisions.append({'chapter': ch, 'outcome': ruling['outcome'], 'decision': row['decision']})
        runtime._validate(request, 'request')
        (R / REQUEST).write_bytes(canonical_bytes(request))
        save('coordinator-decision-bindings.json', {'status': 'PASS', 'ledger': ledger_ref,
            'decisions': decisions, 'request': binding(R, REQUEST), 'authority_effect': 'NONE'})
        print(json.dumps({'status': 'PASS', 'decisions': len(decisions)}, ensure_ascii=False))
    else:
        report = AgentRelease(R).evaluate(REQUEST)
        save('final-release-evaluation.json', report)
        command = [sys.executable, '-m', 'rcwh.cli', 'agent-release', 'build', REQUEST, '--json']
        result = subprocess.run(command, cwd=R, env={**os.environ, 'PYTHONPATH': str(R / 'src')}, text=True, capture_output=True)
        receipt = {'kind': 'ACTUAL_NORMAL_RESEARCH_BUILD_ATTEMPT', 'command': command, 'allow_pending': False,
            'observed_utc': datetime.now(timezone.utc).isoformat(), 'request': binding(R, REQUEST),
            'release_status': report['status'], 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr, 'authority_effect': 'NONE', 'P9_credit': False}
        save('normal-build-attempt.json', receipt)
        if result.returncode != 0 or report['status'] != 'PASS':
            raise ValueError('normal build did not pass; actual refusal retained')
        print(json.dumps({'status': 'PASS', 'normal_build': True, 'output': report['output']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
