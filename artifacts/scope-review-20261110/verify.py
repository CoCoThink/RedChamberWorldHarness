"""Verify this research execution's custody and citations; never grant writing admission."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bound(root, ref):
    path = (root / ref['path']).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('binding escapes repository')
    raw = path.read_bytes()
    if sha(raw) != ref['sha256'] or ('bytes' in ref and len(raw) != ref['bytes']):
        raise ValueError('binding bytes differ: ' + ref['path'])
    return raw


def verify(root, execution):
    manifest = json.loads(bound(root, execution['partition']))
    directory = Path(execution['partition']['path']).parent
    fragments = {}
    for name, ref in manifest['files'].items():
        if Path(name).name != name:
            raise ValueError('fragment is not an immediate file')
        raw = bound(root, dict(ref, path=(directory / name).as_posix()))
        fragments[name] = raw.decode() if name.endswith('.txt') else json.loads(raw)
    if execution['source_request_sha256'] != manifest['source_request_sha256']:
        raise ValueError('execution request differs from partition')
    protocol = bound(root, execution['protocol'])
    expected = {a['id']: a for a in manifest['assignments']}
    if len(execution['tasks']) != len(expected) or {t['id'] for t in execution['tasks']} != set(expected):
        raise ValueError('execution must cover every original assignment exactly once')
    if execution['max_parallel'] != 3 or execution['max_attempts_per_task'] != 3:
        raise ValueError('execution limits differ from authorized plan')
    results, used_agents, activity = [], {}, []
    for task in execution['tasks']:
        if task['assignment'] != expected[task['id']]:
            raise ValueError('assignment differs from original partition')
        if task['output_limit_bytes'] != manifest['limits']['output_bytes']:
            raise ValueError('output reservation differs from frozen partition')
        if task['status'] not in {'NOT_STARTED', 'RUNNING', 'RETRY_REQUIRED', 'RECEIVED'}:
            raise ValueError('invalid task status')
        scaffold = bound(root, task['scaffold'])
        dispatch = bound(root, task['dispatch'])
        external = len(protocol) + len(scaffold) + len(dispatch)
        if task['actual_external_file_bytes'] != external:
            raise ValueError('external input byte accounting differs')
        if len(task['attempts']) > execution['max_attempts_per_task']:
            raise ValueError('too many attempts')
        accepted, prior_context = [], 0
        initial_agent = None
        for attempt in task['attempts']:
            if attempt['status'] not in {'RUNNING', 'REJECTED', 'ACCEPTED'}:
                raise ValueError('invalid attempt status')
            start = json.loads(bound(root, attempt['start_receipt']))
            agent = start['observed_return']['task_name']
            repair = attempt.get('kind') == 'FORMAT_REPAIR'
            if agent != attempt['agent_name']:
                raise ValueError('reader identity differs')
            if repair:
                if agent != initial_agent or start['fork_turns'] != 'continuation' or accepted:
                    raise ValueError('format repair must retain original independent reader')
            elif agent in used_agents or start['fork_turns'] != 'none':
                raise ValueError('reader identity reused or startup differs')
            else:
                used_agents[agent] = task['id']
                initial_agent = agent
            wrapper = len(start['message'].encode())
            overhead = external + wrapper
            if start['actual_external_bytes_including_wrapper'] != overhead:
                raise ValueError('spawn byte accounting differs')
            if not repair and overhead > manifest['limits']['overhead_bytes']:
                raise ValueError('external context exceeds reservation')
            context = task['assignment']['input_bytes'] + overhead + (prior_context if repair else 0)
            if repair and start.get('repair_history_bytes') != prior_context:
                raise ValueError('format repair history accounting differs')
            if context + task['output_limit_bytes'] > manifest['limits']['max_task_bytes']:
                raise ValueError('task exceeds byte ceiling')
            prior_context += wrapper
            if 'raw_output' not in attempt:
                if attempt['status'] == 'ACCEPTED':
                    raise ValueError('accepted attempt has no original output')
                continue
            raw = bound(root, attempt['raw_output'])
            capture = attempt['capture']
            if capture['completed_at'] < capture['started_at']:
                raise ValueError('review completion precedes startup')
            activity.extend([(capture['started_at'], 1), (capture['completed_at'], -1)])
            prior_context += len(raw)
            if attempt['status'] != 'ACCEPTED':
                # Retain malformed or excessive original outputs as failed attempts.
                if not attempt.get('error'):
                    raise ValueError('rejected output lacks a recorded reason')
                continue
            if len(raw) > task['output_limit_bytes']:
                raise ValueError('original opinion exceeds output reservation')
            opinion = json.loads(raw)
            if opinion['assignment_id'] != task['id'] or opinion['partition_sha256'] != execution['partition']['sha256']:
                raise ValueError('opinion binds another assignment or partition')
            for k, v in (('authority_effect', 'NONE'), ('provider_consumption_proof', False),
                         ('independent_human_review', False), ('read_claim_basis', 'SELF_REPORTED')):
                if type(opinion[k]) is not type(v) or opinion[k] != v:
                    raise ValueError('opinion claims unsupported authority or proof')
            rows = opinion['files']
            if len(rows) != len(task['assignment']['files']) or {r['file'] for r in rows} != set(task['assignment']['files']):
                raise ValueError('opinion omitted or added assigned files')
            for row in rows:
                ref = manifest['files'][row['file']]
                if any(row[k] != ref[k] for k in ('sha256', 'bytes')) or type(row['read_complete']) is not bool:
                    raise ValueError('reader file declaration differs')
            if opinion['reading_status'] not in {'COMPLETE', 'NOT_CHECKED'} or opinion['scope_verdict'] not in {'PASS', 'PENDING', 'FAIL', 'NOT_CHECKED'}:
                raise ValueError('invalid reading status or scope verdict')
            if opinion['reading_status'] == 'COMPLETE':
                if not all(r['read_complete'] for r in rows):
                    raise ValueError('complete reading omitted assigned files')
                # COMPLETE covers assignment.files only. A truthful declaration
                # that other partitions were not read is a retained limitation.
            elif opinion['scope_verdict'] == 'PASS':
                raise ValueError('incomplete reading cannot pass scope')

            def evidence(items):
                for cite in items:
                    if cite['file'] not in task['assignment']['files'] or not isinstance(cite['path'], list):
                        raise ValueError('citation outside assigned scope')
                    value = fragments[cite['file']]
                    for part in cite['path']:
                        if isinstance(value, list):
                            if type(part) is not int or not 0 <= part < len(value):
                                raise ValueError('invalid array citation')
                        elif not isinstance(value, dict) or type(part) is not str or part not in value:
                            raise ValueError('invalid object citation')
                        value = value[part]
                    rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                    if not isinstance(cite['quote'], str) or not cite['quote'] or cite['quote'] not in rendered:
                        raise ValueError('citation quote absent at declared path')

            for finding in opinion['findings']:
                if not finding['evidence']:
                    raise ValueError('finding lacks original input evidence')
                evidence(finding['evidence'])
            if set(opinion['answers']) != {'shared_binding', 'future_knowledge', 'request_vs_execution', 'world_vs_knowledge'}:
                raise ValueError('missing comprehension question')
            for answer in opinion['answers'].values():
                if answer['status'] not in {'ANSWERED', 'NOT_CHECKED'}:
                    raise ValueError('invalid comprehension answer status')
                if not answer['answer'] or (answer['status'] == 'ANSWERED' and not answer['evidence']):
                    raise ValueError('answer lacks explanation or input evidence')
                evidence(answer['evidence'])
            accepted.append(opinion)
        if len(accepted) > 1 or (task['status'] == 'RECEIVED') != (len(accepted) == 1):
            raise ValueError('task completion differs from accepted original output')
        results.append({'id': task['id'], 'status': task['status'],
                        'reading_status': accepted[0]['reading_status'] if accepted else 'NOT_STARTED',
                        'scope_verdict': accepted[0]['scope_verdict'] if accepted else 'NOT_CHECKED',
                        'unread_scope': accepted[0]['unread_scope'] if accepted else [],
                        'rejected_attempts': sum(a['status'] == 'REJECTED' for a in task['attempts'])})
    parallel = peak = 0
    for _, change in sorted(activity):
        parallel += change
        peak = max(peak, parallel)
    if peak > execution['max_parallel'] or execution.get('observed_peak_parallel', peak) != peak:
        raise ValueError('observed concurrency differs from authorized ceiling')
    complete = sum(r['reading_status'] == 'COMPLETE' for r in results)
    decision_path = root / 'artifacts/scope-review-20261110/coordinator-decisions.json'
    coordinator = 'REQUIRED'
    if decision_path.exists():
        decision = json.loads(decision_path.read_bytes())
        if json.loads(bound(root, decision['execution'])) != execution or decision['partition'] != execution['partition']:
            raise ValueError('coordinator binds different execution')
        originals = [a['raw_output'] for t in execution['tasks'] for a in t['attempts'] if a['status'] == 'ACCEPTED']
        if complete != len(expected) or decision['accepted_opinions'] != originals:
            raise ValueError('coordinator requires all original opinions')
        if any(decision[k] != v for k, v in [('authority_effect', 'NONE'), ('evidence_effect', 'NONE'),
                ('scope_status', 'PENDING'), ('production_admission', 'NOT_GRANTED'),
                ('independent_human_review', False), ('provider_consumption_proof', False)]):
            raise ValueError('coordinator promotes unsupported authority')
        preserved = decision['original_contract_declarations_preserved']
        contract_files = [a['files'][2] for a in manifest['assignments'] if a['id'].startswith('contract-')]
        if len(preserved) != len(contract_files) or [r['file'] for r in preserved] != contract_files:
            raise ValueError('coordinator omitted original contract declarations')
        for row in preserved:
            original = fragments[row['file']]
            if row['state_declarations'] != {k: original.get(k, []) for k in ('entry_state', 'exit_state', 'preconditions')} or any(
                    row[k] != original.get(k) for k in ('unresolved', 'knowledge_binding', 'event_refs')):
                raise ValueError('coordinator changed original unknowns or unresolved items')
        for row in decision['choices'] + decision['roles'] + decision['objects']:
            for cite in row['basis']:
                value = fragments[cite['file']]
                for part in cite['path']:
                    value = value[part]
        order = decision['proposed_local_order']
        nodes = set(order['nodes'])
        if len(nodes) != len(order['nodes']) or any(a not in nodes or b not in nodes for a, b in order['before']):
            raise ValueError('invalid proposed local order nodes')
        pending = set(nodes)
        while pending:
            ready = {n for n in pending if not any(b == n and a in pending for a, b in order['before'])}
            if not ready:
                raise ValueError('proposed local order contains a cycle')
            pending -= ready
        phases = {s for p in decision['pressure_phases'] for s in p['seeds']}
        if phases != {'86-S' + str(i) for i in range(1, 7)}:
            raise ValueError('pressure phases omitted a seed obligation')
        coordinator = decision['status']
    return {'custody_check': 'PASS', 'tasks': len(results), 'complete_readings': complete,
            'observed_peak_parallel': peak, 'independent_native_readers': len(used_agents),
            'tasks_received': sum(r['status'] == 'RECEIVED' for r in results), 'results': results,
            'scope_status': 'PENDING', 'coordinator_decision': coordinator,
            'complete_author_input_comprehension': 'NOT_PROVEN', 'provider_consumption_proof': False,
            'independent_human_review': False, 'production_admission': 'NOT_GRANTED', 'authority_effect': 'NONE'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--execution', default='artifacts/scope-review-20261110/execution.json')
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve(), json.loads((args.root / args.execution).read_bytes())), ensure_ascii=False, indent=2))
