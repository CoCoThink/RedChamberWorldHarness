"""Explicit executable-scene research material, with independent local clocks."""
from copy import deepcopy
from pathlib import Path

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..evaluation.state import _flatten, canonical_target, normalized
from ..io import load_data
from ..knowledge import BUCKETS, KNOWLEDGE_PATH, CharacterKnowledgeRuntime
from ..object_network import ObjectNetworkRuntime
from .records import append_bytes, binding
from .world_projection import carriers as world_carriers, project as world_project

KIND = 'SCENE_INPUT_PROJECTION'
DIRECTORY = 'data/writing/scene-projections'
OBJECT_PATH = 'data/objects/m4.json'
RULES = ['src/rcwh/generation/scene_projection.py', 'src/rcwh/evaluation/state.py',
         'src/rcwh/knowledge.py', 'src/rcwh/object_network.py',
         'src/rcwh/generation/render.py', 'src/rcwh/generation/writing.py']


def rule_bindings():
    # Actual imported host implementation, including when carriers are in a clone.
    source_root = Path(__file__).resolve().parents[3]
    return {path: digest((source_root / path).read_bytes()) for path in RULES}


def _index(rows, field='id'):
    result = {}
    for row in rows:
        key = row[field]
        if key in result:
            raise ValueError(f'duplicate scene projection {field}: {key}')
        result[key] = row
    return result


def _strings(items, *, nonempty=False):
    if (not isinstance(items, list) or (nonempty and not items)
            or any(not isinstance(x, str) or not x for x in items)
            or items != sorted(set(items))):
        raise ValueError('scene projection lists must be sorted unique strings')


def scene_contracts(root, chapter):
    rows = {}
    for path in sorted((root / 'data/scenes').glob('*')):
        if path.suffix in {'.json', '.yaml', '.yml'}:
            contract = load_data(path)
            if contract.get('chapter') == chapter:
                rows[path.relative_to(root).as_posix()] = contract
    _index(rows.values())
    return rows


def _object_material(root, query, contract):
    data = load_data(repository_path(root, OBJECT_PATH))
    if set(data) != {'schema_version', 'epistemic_rule', 'objects', 'transitions',
                     'identity_edges', 'containment_edges', 'invariants', 'baseline_chapter'}:
        raise ValueError('unsupported object carrier fields')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('unsupported object schema')
    objects = _index(data['objects'])
    transitions = _index(data['transitions'])
    edges = [*data['identity_edges'], *data['containment_edges']]
    _index(edges)
    if any(not {'id', 'from', 'to'} <= set(e) for e in data['identity_edges']):
        raise ValueError('unsupported object identity edge')
    if any(not {'id', 'container'} <= set(e) or not {'contained', 'contained_literal'} & set(e)
           for e in data['containment_edges']):
        raise ValueError('unsupported object containment edge')
    selected = set(query['objects'])
    if not selected <= objects.keys():
        raise ValueError('unknown selected object')
    def endpoints(edge):
        return {edge[k] for k in ('from', 'to', 'container', 'contained') if k in edge}
    for edge in edges:
        if not endpoints(edge) <= objects.keys():
            raise ValueError('unknown object edge endpoint')
    while True:
        expanded = selected | set().union(*(endpoints(e) for e in edges if endpoints(e) & selected))
        if expanded == selected:
            break
        selected = expanded
    orders = set()
    for event in transitions.values():
        if (event['object_id'] not in objects or type(event['chapter']) is not int
                or type(event['sequence']) is not int):
            raise ValueError('invalid object transition target or order')
        order = (event['object_id'], event['chapter'], event['sequence'])
        if order in orders:
            raise ValueError('ambiguous object transition order')
        orders.add(order)
    baseline = data['baseline_chapter']
    if type(baseline) is not int or not 0 <= baseline < contract['chapter']:
        raise ValueError('invalid object baseline')
    checkpoint = query['object_checkpoint']
    cutoff = (contract['chapter'] - 1, float('inf'))
    if checkpoint != 'ENTRY':
        anchor = transitions[checkpoint]
        if anchor['object_id'] not in selected or anchor['chapter'] != contract['chapter']:
            raise ValueError('object checkpoint must belong to selected objects and chapter')
        cutoff = (anchor['chapter'], anchor['sequence'])
    relevant = sorted((e for e in transitions.values() if e['object_id'] in selected
                       and (e['chapter'], e['sequence']) <= cutoff),
                      key=lambda e: (e['chapter'], e['sequence'], e['id']))
    states = {oid: deepcopy(objects[oid]['baseline']) for oid in sorted(selected)}
    for event in relevant:
        if event['chapter'] <= baseline:
            raise ValueError('object transition precedes baseline')
        ObjectNetworkRuntime._assert_from_matches(states[event['object_id']], event)
        states[event['object_id']] = deepcopy(event['to'])
    legacy = []
    for oid in sorted(selected):
        if objects[oid].get('legacy_ref'):
            if checkpoint != 'ENTRY':
                raise ValueError('legacy object has no registered within-scene checkpoint')
            path = objects[oid]['legacy_ref']
            legacy.append({'network_id': oid, 'path': path, 'record': load_data(repository_path(root, path))})
    aliases = _index([item['record'] for item in legacy])
    if selected & aliases.keys():
        raise ValueError('object identity collision between network and legacy')
    required = set(contract.get('required_objects', []))
    if not required <= selected | aliases.keys():
        raise ValueError('scene projection omits required objects')
    return {'schema_version': data['schema_version'], 'epistemic_rule': data['epistemic_rule'],
            'invariants': data['invariants'], 'baseline_chapter': baseline,
            'objects': [objects[oid] for oid in sorted(selected)], 'transitions': relevant,
            'edges': [e for e in edges if endpoints(e) & selected], 'states': states,
            'registered': legacy, 'checkpoint': checkpoint}


def _knowledge_material(data, query, contract):
    facts, characters, scenes = (_index(data[k]) for k in ('facts', 'characters', 'scenes'))
    scene = deepcopy(scenes[contract['id']])
    if scene['chapter'] != contract['chapter'] or set(scene) != {
            'id', 'chapter', 'sequence', 'source_basis', 'participants', 'entry', 'events'}:
        raise ValueError('unsupported knowledge scene')
    participants = scene['participants']
    if len(participants) != len(set(participants)) or set(scene['entry']) != set(participants):
        raise ValueError('knowledge participant mismatch')
    if not set(participants) <= characters.keys() or not set(contract['participants']) <= set(participants):
        raise ValueError('missing knowledge participant')
    events = _index(scene['events'])
    sequence = _index(scene['events'], 'sequence')
    if any(type(s) is not int for s in sequence):
        raise ValueError('invalid knowledge event order')
    checkpoints = query['knowledge_checkpoints']
    needed = {'ENTRY', contract.get('knowledge_checkpoint', 'ENTRY')}
    needed.update(g.get('checkpoint', contract.get('knowledge_checkpoint', 'ENTRY'))
                  for g in contract.get('knowledge_guards', []))
    if not needed <= set(checkpoints) or not set(checkpoints) <= {'ENTRY', *events}:
        raise ValueError('missing or unknown knowledge checkpoint')
    cutoff = max((events[cp]['sequence'] for cp in checkpoints if cp != 'ENTRY'), default=None)
    scene['events'] = sorted((e for e in events.values() if cutoff is not None and e['sequence'] <= cutoff),
                             key=lambda e: e['sequence'])
    referenced = set()
    errors = []
    for cid, state in scene['entry'].items():
        CharacterKnowledgeRuntime._check_state(scene['id'], cid, state, facts, errors)
        referenced.update(f for bucket in state.values() for f in bucket)
    for event in scene['events']:
        if set(event) != {'id', 'sequence', 'updates'}:
            raise ValueError('unsupported knowledge event fields')
        for update in event['updates']:
            if set(update) != {'character', 'add', 'remove'} or update['character'] not in participants:
                raise ValueError('unsupported knowledge update')
            for op in ('add', 'remove'):
                if not set(update[op]) <= set(BUCKETS):
                    raise ValueError('invalid knowledge bucket')
                referenced.update(f for values in update[op].values() for f in values)
    for guard in contract.get('knowledge_guards', []):
        if guard['actor'] not in participants:
            raise ValueError('knowledge guard actor not registered')
        referenced.add(guard['fact'])
    for condition in [*contract.get('entry_state', []), *contract.get('preconditions', []), *contract.get('exit_state', [])]:
        parts = canonical_target(condition['equals']).split('.')
        if len(parts) == 4 and parts[0] == 'character' and parts[2] == 'knowledge':
            referenced.add(parts[3])
    if errors or not referenced <= facts.keys():
        raise ValueError('invalid or unknown knowledge fact: ' + '; '.join(errors))
    subset = {**{k: deepcopy(v) for k, v in data.items() if k not in {'facts', 'characters', 'scenes'}},
              'facts': [facts[f] for f in sorted(referenced)],
              'characters': [characters[cid] for cid in sorted(set(participants) | set(contract.get('voice_profile_hooks', [])))],
              'scenes': [scene]}
    runtime = CharacterKnowledgeRuntime(Path('.'), subset)
    snapshots = {cp: runtime.scene(scene['id'], cp) for cp in checkpoints}
    # Replay every prefix as well: later removals must not conceal an earlier conflict.
    for event in scene['events']:
        runtime.scene(scene['id'], event['id'])
    return subset, snapshots


def project(root: Path, query: dict) -> dict:
    if set(query) != {'version', 'chapter', 'characters', 'scenes'} or type(query['version']) is not int or query['version'] != 1:
        raise ValueError('unsupported scene projection query')
    world = world_project(root, {k: query[k] for k in ('version', 'chapter', 'characters')})
    if not isinstance(query['scenes'], list) or not query['scenes']:
        raise ValueError('scene projection requires explicit scenes')
    selected = _index(query['scenes'], 'path')
    if list(selected) != sorted(selected):
        raise ValueError('scene projection paths must be sorted')
    contracts = scene_contracts(root, query['chapter'])
    if set(selected) != set(contracts):
        raise ValueError('scene projection scene set changed or incomplete')
    knowledge = load_data(repository_path(root, KNOWLEDGE_PATH))
    if set(knowledge) != {'schema_version', 'id', 'epistemic_rule', 'sources', 'facts', 'characters', 'scenes', 'policy'}:
        raise ValueError('unsupported knowledge carrier fields')
    if type(knowledge['schema_version']) is not int or knowledge['schema_version'] != 1:
        raise ValueError('unsupported knowledge schema')
    rows, subsets = [], []
    for path, sq in selected.items():
        if set(sq) != {'path', 'objects', 'object_checkpoint', 'knowledge_checkpoints'}:
            raise ValueError('unsupported scene query fields')
        _strings(sq['objects']); _strings(sq['knowledge_checkpoints'], nonempty=True)
        if not isinstance(sq['object_checkpoint'], str) or not sq['object_checkpoint']:
            raise ValueError('explicit object checkpoint required')
        contract = contracts[path]
        if (not isinstance(contract['participants'], list) or not contract['participants']
                or len(contract['participants']) != len(set(contract['participants']))
                or not set(contract['participants']) <= set(query['characters'])):
            raise ValueError('scene projection omits declared participants')
        objects = _object_material(root, sq, contract)
        subset, checkpoints = _knowledge_material(knowledge, sq, contract)
        if not set(subset['scenes'][0]['participants']) <= set(query['characters']):
            raise ValueError('world projection omits knowledge participants')
        subsets.append(subset)
        values, origins = {}, {}
        for cid, state in world['material']['entry']['characters'].items():
            _flatten(f'character.{cid}', state, 'SELECTED_WORLD_ENTRY', values, origins)
        for oid, state in objects['states'].items():
            _flatten(f'object.{oid}', state, 'SELECTED_OBJECT_NETWORK_ENTRY', values, origins)
        for legacy in objects['registered']:
            _flatten(f"object.{legacy['record']['id']}", legacy['record'].get('state', {}),
                     'REGISTERED_OBJECT_ENTRY', values, origins)
        allowed_objects = set(objects['states']) | {x['record']['id'] for x in objects['registered']}
        for condition in [*contract.get('entry_state', []), *contract.get('preconditions', []), *contract.get('exit_state', [])]:
            target = canonical_target(condition['equals']); parts = target.split('.')
            allowed = set(query['characters']) if parts[0] == 'character' else allowed_objects
            if parts[1] not in allowed:
                raise ValueError('scene projection omits state target')
        for condition in contract.get('entry_state', []):
            target = canonical_target(condition['equals'])
            values[target] = normalized(condition['value']); origins[target] = 'SCENE_LOCAL_RECONSTRUCTION_INPUT'
        for condition in contract.get('preconditions', []):
            target = canonical_target(condition['equals'])
            if target not in values or values[target] != normalized(condition['value']):
                raise ValueError(f'scene projection unresolved or mismatched precondition: {target}')
        entry = {'values': values, 'origins': origins, 'knowledge': checkpoints['ENTRY'],
                 'fact_registry': sorted(x['id'] for x in subset['facts']),
                 'truth_layer': 'RECONSTRUCTION_AND_CHARACTER', 'evidence_effect': 'NONE',
                 'object_checkpoint': sq['object_checkpoint'], 'world_checkpoint': query['chapter'] - 1,
                 'temporal_alignment': 'NOT_INFERRED'}
        rows.append({'path': path, 'contract': contract, 'entry': entry, 'objects': objects,
                     'knowledge_checkpoints': checkpoints})
    frozen = deepcopy(subsets[0])
    for field in ('facts', 'characters', 'scenes'):
        union = {}
        for subset in subsets:
            for item in subset[field]:
                if item['id'] in union and union[item['id']] != item:
                    raise ValueError('conflicting frozen knowledge record')
                union[item['id']] = item
        frozen[field] = [union[key] for key in sorted(union)]
    return {'kind': KIND, 'protocol_version': 1, 'query': deepcopy(query), 'world': world,
            'rules': rule_bindings(),
            'scenes': rows, 'knowledge_runtime': frozen, 'scope': 'RESEARCH_EXECUTABLE_SCENE_INPUTS',
            'authority_effect': 'NONE', 'semantic_replay': 'NOT_CHECKED'}


def verify_projection(root: Path, document: dict) -> None:
    if canonical_bytes(document) != canonical_bytes(project(root, document['query'])):
        raise ValueError('STALE_SCENE_INPUT_PROJECTION: selected facts, scope, checkpoint or rule changed')


def frozen_knowledge(root: Path, document: dict):
    """Historical feedback must not re-query current carriers or re-verify freshness."""
    return CharacterKnowledgeRuntime(root, deepcopy(document['knowledge_runtime']))


def create_projection(root: Path, query: dict):
    def observed():
        paths = {*world_carriers(), OBJECT_PATH, KNOWLEDGE_PATH,
                 *scene_contracts(root, query['chapter'])}
        paths.update(p.relative_to(root).as_posix() for p in (root / 'data/objects').glob('*.yaml'))
        return [binding(root, path) for path in sorted(paths)]
    before = observed(); rules = rule_bindings(); document = project(root, query)
    if observed() != before or rule_bindings() != rules:
        raise ValueError('scene inputs changed while projecting')
    def save(directory, value):
        raw = canonical_bytes(value); path = f'{directory}/{digest(raw)}.json'
        if repository_path(root, path).exists():
            if repository_path(root, path).read_bytes() != raw:
                raise ValueError('scene projection content collision')
            return binding(root, path)
        return append_bytes(root, path, raw)
    ref = save(DIRECTORY, document)
    receipt = save('artifacts/scene-projections', {'kind': 'SCENE_PROJECTION_CREATION_RECEIPT',
                   'projection': ref, 'carriers_observed': before, 'implementation_observed': rules,
                   'authority_effect': 'NONE'})
    return {'projection': ref, 'creation_receipt': receipt}
