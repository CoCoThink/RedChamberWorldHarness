"""Opt-in research world material; immutable selected facts, fresh query validation.

No carrier hash is part of prompt semantics. Carrier observations are kept in a
separate creation receipt. Executable scene state is intentionally unsupported.
"""
from copy import deepcopy
from pathlib import Path

from ..candidate_reviews import canonical_bytes, digest
from ..io import load_data
from .records import append_bytes, binding

KIND = 'WORLD_PROJECTION'
DIRECTORY = 'data/writing/world-projections'
FIELDS = {
    'core': {'schema_version', 'epistemic_rule', 'sources', 'characters', 'relations', 'institutions', 'baseline', 'events'},
    'locations': {'locations'}, 'presence': {'presence_matrix'}, 'body': {'body_matrix'},
    'resources': {'economy_stages', 'resource_flows'}, 'knowledge': {'knowledge_rules', 'longlines'},
}


def carriers():
    return [f'data/world/m3_{name}.json' for name in sorted(FIELDS)]


def _index(rows, field):
    result = {}
    for row in rows:
        key = row[field]
        if key in result:
            raise ValueError(f'duplicate world {field}: {key}')
        result[key] = row
    return result


def project(root: Path, query: dict) -> dict:
    if set(query) != {'chapter', 'characters', 'version'} or type(query['version']) is not int or query['version'] != 1:
        raise ValueError('unsupported world projection query')
    chapter, selected = query['chapter'], query['characters']
    if type(chapter) is not int or chapter < 1 or not isinstance(selected, list) or not selected:
        raise ValueError('world projection needs chapter and explicit characters')
    if any(not isinstance(x, str) or not x for x in selected) or selected != sorted(set(selected)):
        raise ValueError('world characters must be unique and sorted')
    docs = {name: load_data(root / f'data/world/m3_{name}.json') for name in FIELDS}
    for name, fields in FIELDS.items():
        if set(docs[name]) != fields:
            raise ValueError(f'unsupported world carrier fields: {name}')
    core = deepcopy(docs['core'])
    if type(core['schema_version']) is not int or core['schema_version'] != 1:
        raise ValueError('unsupported world schema version')
    chars = _index(core['characters'], 'id')
    _index(core['relations'], 'id')
    _index(core['institutions'], 'id')
    _index(docs['locations']['locations'], 'id')
    if not set(selected) <= chars.keys():
        raise ValueError('unknown selected world character')
    baseline = core['baseline']
    if set(baseline) != {'chapter', 'global', 'characters', 'relations'} or baseline['chapter'] > chapter - 1:
        raise ValueError('unsupported world baseline/checkpoint')
    core['characters'] = [chars[x] for x in selected]
    baseline['characters'] = {x: baseline['characters'][x] for x in selected}
    entry = deepcopy(baseline)
    events = _index(core['events'], 'id').values()
    orders = set(); relevant = []
    for event in events:
        if type(event['chapter']) is not int or type(event['sequence']) is not int:
            raise ValueError('world event order must be integral')
        order = (event['chapter'], event['sequence'])
        if order in orders:
            raise ValueError('ambiguous world event order')
        orders.add(order)
        effects = []
        for effect in event['effects']:
            if set(effect) != {'set', 'value'}:
                raise ValueError('unsupported world effect fields')
            parts = effect['set'].split('.')
            if parts[0] not in {'characters', 'relations', 'global'} or len(parts) < 2:
                raise ValueError('unsupported world effect target')
            if parts[0] == 'characters' and (len(parts) < 3 or parts[1] not in chars):
                raise ValueError('invalid world character effect')
            if parts[0] != 'characters' or parts[1] in selected:
                effects.append(effect)
        if event['chapter'] <= chapter and effects:
            relevant.append({**event, 'effects': effects})
    core['events'] = sorted(relevant, key=lambda e: (e['chapter'], e['sequence']))
    for event in core['events']:
        if event['chapter'] >= chapter:
            continue
        for effect in event['effects']:
            parts = effect['set'].split('.'); target = entry
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = deepcopy(effect['value'])
    entry['chapter'] = chapter - 1
    def chapter_row(name, field):
        return deepcopy(_index(docs[name][field], 'chapter')[chapter])
    groups = set(selected)
    for char in core['characters']:
        groups.update(char.get('groups', []))
    stages = [s for s in docs['resources']['economy_stages'] if s['chapter_start'] <= chapter <= s['chapter_end']]
    if len(stages) != 1:
        raise ValueError('world economy stage missing or ambiguous')
    material = {'core': core, 'entry': entry,
        'locations': docs['locations']['locations'],
        'presence': chapter_row('presence', 'presence_matrix'), 'body': chapter_row('body', 'body_matrix'),
        'resource_flow': chapter_row('resources', 'resource_flows'), 'economy': stages[0],
        'knowledge_rules': [r for r in docs['knowledge']['knowledge_rules'] if r['chapter'] <= chapter and groups.intersection(r['targets'])],
        'longlines': docs['knowledge']['longlines']}
    return {'kind': KIND, 'protocol_version': 1, 'query': deepcopy(query),
        'rule_sha256': digest(Path(__file__).read_bytes()), 'material': material,
        'scope': 'RESEARCH_SKELETON_WORLD_ONLY_CONSERVATIVE_GLOBAL_CONTEXT',
        'authority_effect': 'NONE', 'semantic_replay': 'NOT_CHECKED'}


def verify_projection(root: Path, document: dict) -> None:
    if canonical_bytes(document) != canonical_bytes(project(root, document['query'])):
        raise ValueError('STALE_WORLD_PROJECTION: selected facts, query or rule changed')


def create_projection(root: Path, chapter: int, characters: list[str]) -> dict:
    before = [binding(root, path) for path in carriers()]
    document = project(root, {'version': 1, 'chapter': chapter, 'characters': sorted(set(characters))})
    if before != [binding(root, path) for path in carriers()]:
        raise ValueError('world changed while projecting')
    def save(directory, content):
        raw = canonical_bytes(content); path = f'{directory}/{digest(raw)}.json'
        from ..assets.paths import repository_path
        if repository_path(root, path).exists():
            if repository_path(root, path).read_bytes() != raw:
                raise ValueError('projection content collision')
            return binding(root, path)
        return append_bytes(root, path, raw)
    ref = save(DIRECTORY, document)
    receipt = save('artifacts/world-projections', {'kind': 'WORLD_PROJECTION_CREATION_RECEIPT',
        'projection': ref, 'carriers_observed': before, 'authority_effect': 'NONE'})
    return {'projection': ref, 'creation_receipt': receipt}
