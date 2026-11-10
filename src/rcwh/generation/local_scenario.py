"""Explicit research scenario: a partial-order editorial model, never observed truth."""
from copy import deepcopy
import json

from ..candidate_reviews import canonical_bytes, digest
from .records import bound_bytes

KIND = 'LOCAL_EDITORIAL_SCENARIO'
SCOPE = 'EDITORIAL_MODEL_ONLY_NOT_OBSERVED'


def indexed(rows):
    result = {}
    for row in rows:
        if not isinstance(row.get('id'), str) or not row['id'] or row['id'] in result:
            raise ValueError('missing or duplicate local identity')
        result[row['id']] = row
    return result


def compile_scenario(document):
    """Replay only causally established prefixes; never linearize siblings."""
    fields = {'actors', 'authority_effect', 'before', 'chapter', 'containment', 'contracts', 'events',
              'evidence_effect', 'extra_editorial_choices', 'facts', 'initial', 'initial_basis',
              'invariants', 'kind', 'messages', 'narrative_roles_and_props', 'objects',
              'original_declarations', 'pressure_phases', 'production_admission', 'realization_in_prose',
              'scope', 'seed_ids', 'semantic_replay', 'source_conflicts', 'unconstrained_pairs',
              'unresolved', 'upgrade_rule', 'version'}
    if set(document) != fields:
        raise ValueError('unsupported local scenario fields')
    if (document.get('kind') != KIND or type(document.get('version')) is not int
            or document['version'] != 1 or type(document.get('chapter')) is not int
            or document['chapter'] < 1 or document.get('scope') != SCOPE
            or document.get('authority_effect') != 'NONE' or document.get('evidence_effect') != 'NONE'
            or document.get('production_admission') != 'NOT_GRANTED'):
        raise ValueError('unsupported local editorial scenario or authority')
    if document['realization_in_prose'] != 'NOT_STARTED' or document['semantic_replay'] != 'NOT_CHECKED':
        raise ValueError('editorial scenario cannot claim prose execution or semantic acceptance')
    actors, objects = indexed(document['actors']), indexed(document['objects'])
    if set(actors) & set(objects):
        raise ValueError('actor/object identity collision')
    for rows in (actors, objects):
        for identity, row in rows.items():
            allowed = {'id', 'name', 'registration', 'identity_record', 'duty', 'provenance'}
            if not set(row) <= allowed or not row.get('name'):
                raise ValueError('unsupported local identity fields')
            if row['registration'] not in {'EXISTING_IDENTITY_ONLY', 'NEW_LOCAL_IDENTITY'}:
                raise ValueError('invalid local registration')
            if row['registration'] == 'NEW_LOCAL_IDENTITY' and not identity.startswith(f"local:ch{document['chapter']}:"):
                raise ValueError('new local identity escapes chapter namespace')
    if 'G01' in objects:
        raise ValueError('poetry interface is not an object')
    for edge in document['containment']:
        if edge['container'] not in objects or edge['contained'] not in objects or edge['container'] == edge['contained']:
            raise ValueError('invalid local containment edge')
    facts = indexed(document['facts'])
    events = indexed(document['events'])
    parents = {key: set() for key in events}
    for a, b in document['before']:
        if a not in events or b not in events or a == b or a in parents[b]:
            raise ValueError('invalid or duplicate local order edge')
        parents[b].add(a)
    ancestors, pending = {}, set(events)
    while pending:
        ready = sorted(n for n in pending if parents[n] <= ancestors.keys())
        if not ready:
            raise ValueError('local event order contains a cycle')
        for n in ready:
            ancestors[n] = set(parents[n]).union(*(ancestors[p] for p in parents[n]))
        pending.difference_update(ready)
    for a, b in document['unconstrained_pairs']:
        if a not in events or b not in events or a in ancestors[b] or b in ancestors[a]:
            raise ValueError('an explicitly unordered pair was silently linearized')
    initial = deepcopy(document['initial'])
    for target in initial:
        parts = target.split('.')
        if len(parts) < 3 or parts[0] not in {'actor', 'object'} or parts[1] not in (actors if parts[0] == 'actor' else objects):
            raise ValueError('state target has no registered entity')
        if parts[2] == 'knowledge':
            if parts[0] != 'actor' or len(parts) != 4 or parts[3] not in facts or initial[target] not in {'UNKNOWN', 'NOT_KNOWN', 'KNOWS', 'BELIEVES'}:
                raise ValueError('invalid local knowledge declaration')
    messages = indexed(document['messages'])
    for message in messages.values():
        if set(message) != {'id', 'sender', 'receiver', 'sent_at', 'received_at', 'facts', 'route', 'duration'}:
            raise ValueError('unsupported message fields')
        sender, receiver = message['sender'], message['receiver']
        sent, received = message['sent_at'], message['received_at']
        if (sender not in actors or receiver not in actors or sender == receiver
                or sent not in events or received not in events or sent not in ancestors[received]
                or not message['facts'] or not set(message['facts']) <= facts.keys()
                or len(message['facts']) != len(set(message['facts']))):
            raise ValueError('message lacks actors, facts or causal delivery')
        if sender not in events[sent]['participants'] or receiver not in events[received]['participants']:
            raise ValueError('message endpoint absent from event')
    writers = {target: [] for target in initial}
    for eid, event in events.items():
        if set(event) != {'id', 'participants', 'description', 'observed_facts', 'effects', 'requires', 'execution', 'scope'}:
            raise ValueError('unsupported event fields')
        if (not set(event['participants']) <= actors.keys() or not event['description']
                or len(event['participants']) != len(set(event['participants']))
                or event.get('execution') != 'NOT_OBSERVED' or event.get('scope') != SCOPE):
            raise ValueError('event references unregistered participant')
        seen = set()
        for effect in event['effects']:
            if set(effect) - {'target', 'from', 'to', 'reason', 'basis'}:
                raise ValueError('unsupported local effect fields')
            target = effect['target']
            if target not in initial or target in seen or not effect['reason']:
                raise ValueError('invalid, duplicate or unexplained local effect')
            seen.add(target); writers[target].append(eid)
            parts = target.split('.')
            if parts[2] == 'knowledge':
                if effect['to'] not in {'UNKNOWN', 'NOT_KNOWN', 'KNOWS', 'BELIEVES'}:
                    raise ValueError('invalid knowledge effect')
                basis = effect['basis']
                if basis['kind'] == 'OBSERVATION':
                    if parts[1] not in event['participants'] or parts[3] not in event['observed_facts']:
                        raise ValueError('knowledge update has no local observation')
                elif basis['kind'] == 'MESSAGE':
                    msg = messages[basis['id']]
                    if (msg['received_at'] != eid or msg['receiver'] != parts[1]
                            or parts[3] not in msg['facts'] or effect['to'] != 'KNOWS'):
                        raise ValueError('knowledge update precedes or differs from delivered message')
                else:
                    raise ValueError('knowledge effect has no observation or message')
        if not set(event['observed_facts']) <= facts.keys():
            raise ValueError('observation references an unknown fact')
    for target, ids in writers.items():
        for i, a in enumerate(ids):
            for b in ids[i+1:]:
                if a not in ancestors[b] and b not in ancestors[a]:
                    raise ValueError('unordered local writes: ' + target)

    def state_for(selected):
        state = deepcopy(initial)
        for eid in ancestors:  # topological insertion order; siblings cannot write the same target
            if eid in selected:
                for effect in events[eid]['effects']:
                    if state[effect['target']] != effect['from']:
                        raise ValueError('local from-state mismatch: ' + eid)
                    state[effect['target']] = deepcopy(effect['to'])
        return state

    checkpoints = {'ENTRY': {'scope': SCOPE, 'execution': 'NOT_OBSERVED', 'events': [], 'values': initial}}
    for eid, event in events.items():
        entry = state_for(ancestors[eid])
        for requirement in event['requires']:
            if requirement['target'] not in entry or entry[requirement['target']] != requirement['value']:
                raise ValueError('local event precondition not established: ' + eid)
            if any(w != eid and w not in ancestors[eid] and eid not in ancestors[w]
                   for w in writers[requirement['target']]):
                raise ValueError('precondition depends on an unordered branch: ' + eid)
        for msg in messages.values():
            if msg['sent_at'] == eid:
                for fact in msg['facts']:
                    if entry.get(f"actor.{msg['sender']}.knowledge.{fact}") != 'KNOWS':
                        raise ValueError('sender does not know the transmitted fact before dispatch')
            if msg['received_at'] == eid:
                for fact in msg['facts']:
                    if not any(e['target'] == f"actor.{msg['receiver']}.knowledge.{fact}"
                               and e['to'] == 'KNOWS' and e.get('basis') == {'kind': 'MESSAGE', 'id': msg['id']}
                               for e in event['effects']):
                        raise ValueError('delivery lacks its explicit recipient update')
        values = state_for(ancestors[eid] | {eid})
        indeterminate = {target: sorted(w for w in ids if w != eid and w not in ancestors[eid]
                                       and eid not in ancestors[w])
                         for target, ids in writers.items()}
        indeterminate = {target: ids for target, ids in indeterminate.items() if ids}
        for target in indeterminate:
            values[target] = 'UNKNOWN_AT_UNORDERED_CUT'
        checkpoints[eid] = {'scope': SCOPE, 'execution': 'NOT_OBSERVED',
                            'events': sorted(ancestors[eid] | {eid}),
                            'values': values, 'indeterminate_due_to_unordered_events': indeterminate}
    for rule in document['invariants']:
        if rule['kind'] == 'DISTINCT':
            if len(set(rule['ids'])) != len(rule['ids']) or not set(rule['ids']) <= objects.keys():
                raise ValueError('object distinctness violated')
        elif rule['kind'] == 'CONSTANT':
            if any(cp['values'].get(rule['target']) != rule['value'] for cp in checkpoints.values()):
                raise ValueError('constant local state violated: ' + rule['target'])
        elif rule['kind'] == 'NO_EFFECT':
            if events[rule['event']]['effects']:
                raise ValueError('a request was treated as an executed effect')
        elif rule['kind'] == 'ACQUIRE_AT':
            if (initial[rule['target']] != 'NOT_KNOWN' or writers[rule['target']] != [rule['event']]
                    or checkpoints[rule['event']]['values'][rule['target']] != 'KNOWS'):
                raise ValueError('knowledge acquisition crossed the declared boundary')
        else:
            raise ValueError('unknown local invariant')
    return {'kind': 'LOCAL_EDITORIAL_CHECKPOINTS', 'version': 1, 'scope': SCOPE,
            'scenario_sha256': digest(canonical_bytes(document)), 'checkpoints': checkpoints,
            'authority_effect': 'NONE', 'production_admission': 'NOT_GRANTED'}


def verify_material(root, package):
    """Only explicitly selected local files; no global discovery or substitution."""
    if len(package['world']) != 1:
        raise ValueError('local scenario requires exclusive selected material')
    scenario = json.loads(bound_bytes(root, package['world'][0]))
    if package.get('operation_scope') != 'RESEARCH' or scenario['chapter'] != package['chapter']:
        raise ValueError('local scenario is chapter-bound research only')
    compiled = compile_scenario(scenario)
    from ..io import load_data
    world_actors = indexed(load_data(root / 'data/world/m3_core.json')['characters'])
    world_objects = indexed(load_data(root / 'data/objects/m4.json')['objects'])
    legacy = load_data(root / 'data/objects/medicine_bowl.yaml')
    world_objects[legacy['id']] = legacy
    for field, registry in [('actors', world_actors), ('objects', world_objects)]:
        for row in scenario[field]:
            if row['registration'] == 'EXISTING_IDENTITY_ONLY':
                source = registry[row['id']]
                if row['identity_record'] != {k: source[k] for k in ('id', 'name')}:
                    raise ValueError('selected existing identity changed')
    contracts = []
    for ref in package['plan']:
        bound_bytes(root, ref)
        value = load_data(root / ref['path'])
        if value.get('kind') == 'LOCAL_SCENE_CONTRACT':
            contracts.append((ref, value))
    if len(contracts) != len(scenario['contracts']) or [ref for ref, _ in contracts] != scenario['contracts']:
        raise ValueError('local contract set differs from scenario selection')
    actors, objects = indexed(scenario['actors']), indexed(scenario['objects'])
    assigned_events = set()
    for _, contract in contracts:
        if (contract['chapter'] != package['chapter'] or contract['revision'] != 'v3'
                or contract['scope'] != SCOPE or contract['authority_effect'] != 'NONE'
                or contract['evidence_effect'] != 'NONE' or contract['status'] != 'UNREVIEWED_EDITORIAL_MODEL'
                or not set(contract['participants']) <= actors.keys()
                or not set(contract['required_objects']) <= objects.keys()):
            raise ValueError('invalid local contract scope')
        if any(cp not in compiled['checkpoints'] for cp in [contract['entry_checkpoint'], *contract['checkpoints']]):
            raise ValueError('contract checkpoint is not in local model')
        for cp in contract['checkpoints']:
            event = next(e for e in scenario['events'] if e['id'] == cp)
            if not set(event['participants']) <= set(contract['participants']):
                raise ValueError('local event actor is outside its contract')
            assigned_events.add(cp)
        if contract['original_declarations'] != scenario['original_declarations'][contract['id']]:
            raise ValueError('original state/unknown declarations changed')
    declared = {p for _, c in contracts for p in c['participants']}
    if set(actors) != declared:
        raise ValueError('local actor is missing from contract coverage')
    if [c['id'] for _, c in contracts] != scenario['seed_ids']:
        raise ValueError('local seed coverage changed')
    if assigned_events != {e['id'] for e in scenario['events']}:
        raise ValueError('local event lacks a scene obligation')
    return scenario, compiled, contracts


def is_local_package(root, relative):
    from ..assets.paths import repository_path
    from ..io import load_data
    package = load_data(repository_path(root, relative))
    return bool(package.get('world') and load_data(repository_path(root, package['world'][0]['path'])).get('kind') == KIND)


def checkpoint_view(compiled):
    """Exact base-plus-overrides encoding; no state or unknown is summarized away."""
    base = compiled['checkpoints']['ENTRY']['values']
    return {**{k: v for k, v in compiled.items() if k != 'checkpoints'},
            'encoding': 'ENTRY_BASE_PLUS_EXPLICIT_OVERRIDES', 'entry_values': deepcopy(base),
            'checkpoints': {name: {**{k: v for k, v in cp.items() if k != 'values'},
                                   'overrides': {k: deepcopy(v) for k, v in cp['values'].items() if v != base[k]}}
                            for name, cp in compiled['checkpoints'].items()},
            'reconstruction': 'For each checkpoint, copy entry_values then replace each key in overrides; never combine sibling checkpoints.'}


def render_draft(root, package_path, chapter, *, route='harness', characters=6000,
                 plan_path=None, previous_path=None):
    """Opt-in local renderer; legacy renderer bytes and rule hashes stay frozen."""
    from ..assets import AssetCatalog
    from ..graph import ProvenanceGraph
    from ..io import load_data
    from ..literary_inputs import LiteraryInputs
    from .dependencies import WritingDependencies, without_governance
    from .records import binding
    from .render import PromptRenderer
    if plan_path is not None or previous_path is not None:
        raise ValueError('local pilot requires its explicit bound plan and no implicit previous context')
    if type(chapter) is not int or characters < 1 or route not in {'harness', 'direct'}:
        raise ValueError('invalid local writing request')
    catalog = AssetCatalog.from_repo(root)
    report = LiteraryInputs(catalog).package(package_path)
    if report['status'] != 'PASS':
        raise ValueError('local writing input integrity failed: ' + '; '.join(report['findings']))
    package = report['package']
    if package['chapter'] != chapter:
        raise ValueError('local writing chapter mismatch')
    scenario, compiled, contracts = verify_material(root, package)
    paths = {package_path, package['exemplar_set']['path'],
             catalog.resolve(report['exemplars']['spec']['manifest_ref']).path.relative_to(root).as_posix()}
    paths.update(r['path'] for r in [*package['world'], *package['plan']])
    plans = {r['path']: load_data(root / r['path']) for r in package['plan']}
    cards = [value for value in plans.values() if 'card_fields' in value]
    if len(cards) != 1 or cards[0]['chapter'] != chapter:
        raise ValueError('local writing requires one original chapter card')
    graph = ProvenanceGraph.from_repo(root)
    dependencies = WritingDependencies(root, catalog, graph)
    dependencies.selected(package, report)
    dependencies.walk(report['exemplars']['spec'])
    # Model records bind only the selected material. Scope opinions and full global
    # carriers remain audit evidence, not transitive prompt dependencies.
    paths.update(dependencies.files)
    data = {'chapter': chapter, 'target_characters': characters, 'operation_scope': 'RESEARCH',
            'package': package, 'world': {package['world'][0]['path']: scenario}, 'plan': plans,
            'chapter_plan': cards[0], 'local_checkpoints': checkpoint_view(compiled),
            'scenes': [{'path': ref['path'], 'contract': {'kind': 'SCENE_SKELETON', 'id': c['id'],
                        'chapter': chapter, 'participants': c['participants']}, 'local_contract': c,
                        'entry': None, 'unresolved': 'LOCAL_EDITORIAL_MODEL_NOT_OBSERVED_OR_TEXT_VERIFIED'}
                       for ref, c in contracts],
            'agent_contracts': [], 'previous_ending': None, 'threads': None,
            'exemplars': report['exemplars']['segments'],
            'exemplar_dataset_ref': report['exemplars']['spec']['dataset_ref'],
            'sources': [{'record': graph.sources[ref['source_ref']], 'verification': row}
                        for ref, row in zip(package['sources'], report['sources'], strict=True)],
            'guidance': 'Use the selected causal constraints. Checkpoints describe only an editorial model; '
                        'realization in prose requires independent reading. Preserve every original UNKNOWN. '
                        'Scene seeds overlap in time; their list order is not a chronological clock. '
                        'Never fill the G01 gap or turn a request to warm medicine into an executed action.'}
    if 'supplemental_source_sets' in report:
        data['supplemental_source_sets'] = report['supplemental_source_sets']
    result = PromptRenderer(root, version=2).render('author-v1', without_governance(data),
                                                  [binding(root, p) for p in sorted(paths)])
    result.update(renderer_version=2, dependency_records=dependencies.manifest_records(),
                  readiness={'scope': report['scope'], 'blockers': report['production_blockers']},
                  selection_context={'operation': 'draft', 'package_path': package_path, 'chapter': chapter,
                                     'route': route, 'characters': characters, 'plan_path': None,
                                     'previous_path': None, 'parent_path': None, 'feedback_path': None,
                                     'notes_path': None})
    return result
