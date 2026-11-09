"""Read-only research diagnostics; structural coverage never grants scope approval."""
from copy import deepcopy

from ..candidate_reviews import canonical_bytes, digest
from ..evaluation.state import canonical_target
from .prompt_view import expand

STATE_FIELDS = ('entry_state', 'preconditions', 'exit_state')


def assess(task):
    """Inspect explicit IDs only; never infer actors or local clocks from prose."""
    projections = [v for v in task.get('world', {}).values()
                   if isinstance(v, dict) and v.get('kind') == 'SCENE_INPUT_PROJECTION']
    if len(projections) != 1:
        raise ValueError('scope audit requires exactly one executable scene projection')
    projection = projections[0]
    characters = set(projection['query']['characters'])
    objects, facts, states, knowledge_actors = set(), set(), set(), set()
    for scene in projection['scenes']:
        objects.update(scene['objects']['states'])
        objects.update(row['record']['id'] for row in scene['objects']['registered'])
        states.update(scene['entry']['values'])
        facts.update(scene['entry']['fact_registry'])
        knowledge_actors.update(scene['entry']['knowledge']['states'])
    scene_ids = {s['contract']['id'] for s in projection['scenes']}
    findings, contracts = [], []

    def finding(status, code, path, detail):
        findings.append({'status':status, 'code':code, 'path':path, 'detail':detail})

    for index, contract in enumerate(task['agent_contracts']):
        base = ['agent_contracts', index]
        rows = []
        for field in STATE_FIELDS:
            for n, condition in enumerate(contract.get(field, [])):
                path = [*base, field, n]
                target = canonical_target(condition['equals'])
                parts = target.split('.')
                present = parts[1] in (characters if parts[0] == 'character' else objects)
                if not present:
                    finding('FAIL', 'MISSING_STATE_ENTITY', path, target)
                if len(parts) >= 4 and parts[0] == 'character' and parts[2] == 'knowledge':
                    if parts[3] not in facts:
                        finding('FAIL', 'MISSING_FACT_ID', path, parts[3])
                    available = parts[1] in knowledge_actors and parts[3] in facts
                else:
                    available = target in states
                unknown = condition.get('status') == 'UNKNOWN' or condition.get('value') is None
                if not available:
                    finding('PENDING' if unknown else 'FAIL', 'NO_PROJECTED_STATE_FIELD', path, target)
                if unknown:
                    finding('PENDING', 'LOCAL_STATE_UNKNOWN', path, target)
                rows.append({'path':path, 'target':target, 'declaration':deepcopy(condition),
                             'entity_present':present, 'chapter_field_present':available,
                             'local_state_proven':False})
        for n, actor in enumerate(contract.get('participants') or []):
            if actor not in characters:
                finding('FAIL', 'MISSING_PARTICIPANT', [*base,'participants',n], actor)
            if actor not in knowledge_actors:
                finding('PENDING', 'NO_SCENE_KNOWLEDGE_ENTRY', [*base,'participants',n], actor)
        for n, oid in enumerate(contract.get('required_objects', [])):
            if oid not in objects:
                finding('FAIL', 'MISSING_REQUIRED_OBJECT', [*base,'required_objects',n], oid)
        for n, record in enumerate(contract.get('references', {}).get('knowledge', [])):
            fact = record['value']['id']
            if fact not in facts:
                finding('FAIL', 'MISSING_FACT_ID', [*base,'references','knowledge',n], fact)
        if contract.get('participants_status') != 'KNOWN':
            finding('PENDING', 'PARTICIPANT_SET_UNRESOLVED', [*base,'participants_status'], contract.get('participants_status'))
        # Equal IDs are a necessary structural match, never a semantic clock mapping.
        if contract['id'] not in scene_ids:
            finding('PENDING', 'NO_EXECUTABLE_SCENE_ID_MATCH', [*base,'id'], contract['id'])
        finding('PENDING', 'LOCAL_CLOCK_MAPPING_UNREVIEWED', [*base,'entry_checkpoint'],
                deepcopy(contract.get('entry_checkpoint')))
        if contract.get('knowledge_binding') is None:
            finding('PENDING', 'NO_LOCAL_KNOWLEDGE_BINDING', [*base,'knowledge_binding'], None)
        for n, unresolved in enumerate(contract.get('unresolved', [])):
            finding('PENDING', 'DECLARED_UNRESOLVED', [*base,'unresolved',n], unresolved)
        contracts.append({'id':contract['id'], 'path':base, 'participants':contract.get('participants'),
                          'required_objects':contract.get('required_objects', []), 'states':rows,
                          'unresolved':deepcopy(contract.get('unresolved', []))})
    finding('PENDING', 'FREE_TEXT_SCOPE_REQUIRES_READING', ['chapter_plan'],
            'Read the entire chapter card and contract prose; no name-to-ID inference was performed.')
    finding('PENDING', 'SHARED_VIEW_UNDERSTANDING_UNREVIEWED', [],
            'Lossless expansion is structural evidence, not a reader comprehension result.')
    return {'kind':'WRITING_SCOPE_PREFLIGHT', 'version':1,
            'status':'FAIL' if any(f['status']=='FAIL' for f in findings) else 'PENDING',
            'explicit_id_coverage':'FAIL' if any(f['status']=='FAIL' for f in findings) else 'PASS',
            'selected':{'characters':sorted(characters), 'objects':sorted(objects), 'facts':sorted(facts),
                        'knowledge_actors':sorted(knowledge_actors), 'executable_scene_ids':sorted(scene_ids)},
            'contracts':contracts, 'findings':findings, 'local_clock_mapping':'NOT_INFERRED',
            'independent_review':'NOT_PERFORMED', 'production_admission':'NOT_GRANTED', 'authority_effect':'NONE'}


INSTRUCTIONS = '''Read all assigned files completely. Research scope and shared-reference review only.
The message fragment is the actual system/role/model envelope and shared binding table.
Task fragments are the exact top-level skeleton values; shared fragments are literal values.
Apply bindings at their typed paths; unbound nulls remain null. Follow references at EVERY
assigned occurrence. A value existing in the registry does not mean an actor knows it.
Chapter world state and the legacy executable scene are not six local scene checkpoints.
Keep network and legacy object identities distinct; preserve all UNKNOWN and unresolved notes.
Read prose for missing roles/objects too; do not manufacture IDs, chronology or state.
Report exact fragment/path evidence, remaining gaps and required decisions. Explain why
later death-time knowledge cannot be copied into an earlier entry, why a request to warm
medicine is not an executed warming, and why world presence does not establish knowledge.
This is a partition of the actual author input, not a new shorter author prompt. Each task
has only its assigned partition; the full set must be reviewed before any overall conclusion.
Do not mark PASS merely because reconstruction or hashes pass. Do not claim independent
human/provider identity, complete author-prompt comprehension or production eligibility.
'''


def bundle(prepared, exported_raw, *, max_file_bytes=65536, max_task_bytes=131072,
           overhead_bytes=16384, output_bytes=8192):
    """Return a complete lossless partition and bounded assignments, with no I/O."""
    for value in (max_file_bytes, max_task_bytes, overhead_bytes, output_bytes):
        if type(value) is not int or value <= 0:
            raise ValueError('review byte limits must be explicit positive integers')
    if exported_raw != canonical_bytes(prepared['request']):
        raise ValueError('review partition differs from exported author payload')
    view = prepared['prompt_view']['payload']
    if canonical_bytes(expand(view)) != canonical_bytes(prepared['task']):
        raise ValueError('review partition task differs from prepared task')
    files, task_map, shared_map = {}, {}, {}
    def add(name, value):
        raw = canonical_bytes(value)
        if len(raw) > max_file_bytes:
            raise ValueError(f'review file exceeds explicit byte ceiling: {name}')
        files[name] = raw
        return name
    for index, (key, value) in enumerate(sorted(view['task'].items())):
        task_map[key] = add(f'task-{index:02}.json', value)
    for identity, value in sorted(view['shared'].items()):
        shared_map[identity] = add(f'shared-{identity}.json', value)
    message = add('message.json', {'request':{k:v for k,v in prepared['request'].items() if k!='messages'},
                  'role':prepared['request']['messages'][0]['role'],
                  'payload':{k:v for k,v in view.items() if k not in {'task','shared'}}})
    files['instructions.txt'] = INSTRUCTIONS.encode()
    if len(files['instructions.txt']) > max_file_bytes:
        raise ValueError('review instructions exceed explicit byte ceiling')
    assignments, assigned = [], set()
    common = [message, 'instructions.txt']
    def assign(label, paths):
        paths = sorted(set([*common, *paths]))
        size = sum(len(files[p]) for p in paths)
        total = size + overhead_bytes + output_bytes
        if total > max_task_bytes:
            raise ValueError(f'review task exceeds explicit byte ceiling: {label}')
        assignments.append({'id':label, 'files':paths, 'input_bytes':size,
                            'reserved_total_bytes':total, 'status':'NOT_STARTED'})
        assigned.update(paths)
    card = [b['value'] for b in view['bindings'] if b['path']==['chapter_plan']]
    card_files = [shared_map[c] for c in card] if card else [task_map['chapter_plan']]
    for index, contract in enumerate(prepared['task']['agent_contracts']):
        refs = [b['value'] for b in view['bindings'] if b['path']==['agent_contracts',index]]
        if not refs:
            # Non-shared small contracts still live in the complete array fragment.
            selected = [task_map['agent_contracts']]
        else:
            selected = [shared_map[x] for x in refs]
        assign(f'contract-{index+1:02}', [*selected,*card_files, task_map['agent_contracts'],task_map['plan']])
    # Full projection skeleton plus its shared contract/entry/checkpoints.
    projection_shared = [shared_map[b['value']] for b in view['bindings']
                         if b['path'][0] in {'world','scenes'}]
    assign('projection', [task_map['world'], task_map['scenes'], *projection_shared, *card_files])
    # Every remaining literal fragment gets an explicit assignment; no tail truncation.
    remaining, chunk, context_index = sorted(set(files)-assigned), [], 1
    common_size = sum(len(files[p]) for p in common)
    for path in remaining:
        if chunk and (common_size + sum(len(files[p]) for p in [*chunk,path])
                      + overhead_bytes + output_bytes > max_task_bytes):
            assign(f'context-{context_index:02}',chunk)
            context_index += 1; chunk = []
        chunk.append(path)
    if chunk:
        assign(f'context-{context_index:02}',chunk)
    manifest = {'kind':'WRITING_SCOPE_REVIEW_PARTITION', 'version':1,
                'source_request_sha256':digest(exported_raw), 'task_sha256':digest(canonical_bytes(prepared['task'])),
                'message':message, 'task_fragments':task_map, 'shared_fragments':shared_map,
                'files':{p:{'sha256':digest(raw),'bytes':len(raw)} for p,raw in sorted(files.items())},
                'limits':{'unit':'UTF8_BYTES','max_file_bytes':max_file_bytes,'max_task_bytes':max_task_bytes,
                          'overhead_bytes':overhead_bytes,'output_bytes':output_bytes,
                          'token_capacity_status':'NOT_MEASURED','external_context_usage':'UNVERIFIED_RESERVATION'},
                'assignments':assignments, 'review_status':'NOT_STARTED', 'authority_effect':'NONE'}
    if reconstruct(manifest, files) != exported_raw:
        raise ValueError('review partition did not preserve exact author request')
    return manifest, files


def reconstruct(manifest, files):
    """Check a delivered partition using only its own files, never the full packet."""
    if set(files) != set(manifest['files']):
        raise ValueError('review partition file set mismatch')
    limits = manifest['limits']
    if (manifest.get('kind') != 'WRITING_SCOPE_REVIEW_PARTITION' or type(manifest.get('version')) is not int
            or manifest['version'] != 1 or limits['unit'] != 'UTF8_BYTES'
            or any(type(limits[k]) is not int or limits[k] <= 0 for k in (
                'max_file_bytes','max_task_bytes','overhead_bytes','output_bytes'))):
        raise ValueError('invalid review partition version or byte limits')
    for path, raw in files.items():
        if (manifest['files'][path] != {'sha256':digest(raw),'bytes':len(raw)}
                or len(raw) > limits['max_file_bytes']):
            raise ValueError('review partition fragment identity or size mismatch')
    assigned = set()
    if len({t['id'] for t in manifest['assignments']}) != len(manifest['assignments']):
        raise ValueError('duplicate review assignment identity')
    for task in manifest['assignments']:
        if (len(task['files']) != len(set(task['files'])) or not set(task['files']) <= set(files)
                or not {manifest['message'],'instructions.txt'} <= set(task['files'])):
            raise ValueError('invalid review assignment files')
        size = sum(len(files[p]) for p in task['files'])
        total = size + limits['overhead_bytes'] + limits['output_bytes']
        if size != task['input_bytes'] or total != task['reserved_total_bytes'] or total > limits['max_task_bytes']:
            raise ValueError('review assignment byte reservation mismatch')
        assigned.update(task['files'])
    if assigned != set(files):
        raise ValueError('review partition has unassigned fragments')
    import json
    def read(path): return json.loads(files[path])
    message = read(manifest['message'])
    view = {**message['payload'], 'task':{k:read(p) for k,p in manifest['task_fragments'].items()},
            'shared':{k:read(p) for k,p in manifest['shared_fragments'].items()}}
    if digest(canonical_bytes(expand(view))) != manifest['task_sha256']:
        raise ValueError('partition canonical task identity mismatch')
    raw = canonical_bytes({**message['request'],'messages':[{'role':message['role'],'content':canonical_bytes(view).decode()}]})
    if digest(raw) != manifest['source_request_sha256']:
        raise ValueError('partition author request identity mismatch')
    return raw
