"""Lossless, opt-in session transport and explicit UTF-8 byte reservations."""
from collections import Counter
from copy import deepcopy

from ..candidate_reviews import canonical_bytes, digest
from .records import binding, bound_bytes

TEMPLATE = 'data/writing/prompts/shared-values-v1.md'
MIN_SHARED_BYTES = 1024


def _child(value, part):
    if isinstance(value, dict) and isinstance(part, str) and part in value:
        return value[part]
    if isinstance(value, list) and type(part) is int and 0 <= part < len(value):
        return value[part]
    raise ValueError('invalid shared value path')


def _parent(value, path):
    if not isinstance(path, list) or not path:
        raise ValueError('shared value path must be nonempty')
    for part in path[:-1]:
        value = _child(value, part)
    _child(value, path[-1])
    return value, path[-1]


def _overlap(a, b):
    return a[:len(b)] == b or b[:len(a)] == a


def encode(task):
    groups = {}
    def visit(value, path):
        if isinstance(value, (dict, list)):
            raw = canonical_bytes(value)
            if path and len(raw) >= MIN_SHARED_BYTES:
                identity = digest(raw)
                row = groups.setdefault(identity, {'value':value, 'bytes':len(raw), 'paths':[]})
                if canonical_bytes(row['value']) != raw:
                    raise ValueError('shared value digest collision')
                row['paths'].append(path)
            for key, child in (value.items() if isinstance(value, dict) else enumerate(value)):
                visit(child, [*path, key])
    visit(task, [])
    selected, covered, shared = [], [], {}
    candidates = sorted(groups, key=lambda key: (-groups[key]['bytes']*(len(groups[key]['paths'])-1), key))
    for identity in candidates:
        row = groups[identity]
        paths = [p for p in row['paths'] if not any(_overlap(p, q) for q in covered)]
        overhead = sum(len(canonical_bytes({'path':p,'value':identity})) for p in paths) + 70
        if len(paths) < 2 or row['bytes']*(len(paths)-1) <= overhead:
            continue
        shared[identity] = deepcopy(row['value'])
        selected.extend({'path':p, 'value':identity} for p in paths)
        covered.extend(paths)
    skeleton = deepcopy(task)
    for item in selected:
        parent, key = _parent(skeleton, item['path']); parent[key] = None
    payload = {'kind':'PROMPT_SHARED_VIEW', 'version':1, 'task':skeleton,
               'shared':shared, 'bindings':sorted(selected, key=lambda item:canonical_bytes(item['path']))}
    if canonical_bytes(expand(payload)) != canonical_bytes(task):
        raise ValueError('shared view did not preserve exact task')
    return payload


def expand(payload):
    if (not isinstance(payload, dict) or set(payload) != {'kind','version','task','shared','bindings'}
            or payload['kind'] != 'PROMPT_SHARED_VIEW' or type(payload['version']) is not int
            or payload['version'] != 1 or not isinstance(payload['task'], dict)
            or not isinstance(payload['shared'], dict) or not isinstance(payload['bindings'], list)):
        raise ValueError('unsupported shared prompt view')
    for identity, value in payload['shared'].items():
        raw = canonical_bytes(value)
        if not isinstance(value, (dict, list)) or len(raw) < MIN_SHARED_BYTES or digest(raw) != identity:
            raise ValueError('invalid shared value identity')
    result, seen, counts = deepcopy(payload['task']), [], Counter()
    for item in payload['bindings']:
        if (not isinstance(item, dict) or set(item) != {'path','value'}
                or not isinstance(item['value'], str) or item['value'] not in payload['shared']):
            raise ValueError('missing shared value binding')
        path = item['path']
        parent, key = _parent(result, path)
        if parent[key] is not None or any(_overlap(path, old) for old in seen):
            raise ValueError('shared value paths overlap or do not point at placeholders')
        parent[key] = deepcopy(payload['shared'][item['value']])
        seen.append(path); counts[item['value']] += 1
    if set(counts) != set(payload['shared']) or any(n < 2 for n in counts.values()):
        raise ValueError('unused or non-shared value')
    return result


def validate_limits(limits):
    if (not isinstance(limits, dict) or set(limits) != {
            'version','max_context_bytes','overhead_reserve_bytes','output_reserve_bytes'}
            or type(limits['version']) is not int or limits['version'] != 1
            or any(type(limits[k]) is not int or limits[k] < (0 if k=='overhead_reserve_bytes' else 1)
                   for k in ('max_context_bytes','overhead_reserve_bytes','output_reserve_bytes'))):
        raise ValueError('invalid explicit UTF-8 context byte limits')


def admission(request, limits):
    validate_limits(limits)
    size = len(canonical_bytes(request))
    reserved = size + limits['overhead_reserve_bytes'] + limits['output_reserve_bytes']
    return {'version':1, 'unit':'UTF8_BYTES', 'status':'PASS' if reserved <= limits['max_context_bytes'] else 'FAIL',
            'scope':'PER_REQUEST_RESERVATIONS',
            'request_sha256':digest(canonical_bytes(request)), 'request_bytes':size,
            'overhead_reserve_bytes':limits['overhead_reserve_bytes'],
            'output_reserve_bytes':limits['output_reserve_bytes'], 'reserved_total_bytes':reserved,
            'max_context_bytes':limits['max_context_bytes'], 'token_capacity_status':'NOT_MEASURED',
            'external_context_usage':'UNVERIFIED_RESERVATION', 'authority_effect':'NONE'}


def check_output(raw, limits):
    validate_limits(limits)
    if len(raw) > limits['output_reserve_bytes']:
        raise ValueError('session output exceeds reserved UTF-8 bytes; no truncation performed')


def verify_admission(prepared):
    context = prepared['context']
    present = ['prompt_view_version' in context, 'context_limits' in context,
               'prompt_view' in prepared, 'byte_admission' in prepared]
    if not any(present):
        return
    if (not all(present) or prepared['schema_version'] != 2
            or type(context['prompt_view_version']) is not int or context['prompt_view_version'] != 1):
        raise ValueError('incomplete or unsupported shared-view context protocol')
    view = prepared['prompt_view']
    if view.get('template', {}).get('path') != TEMPLATE or view['template'] not in prepared['inputs']:
        raise ValueError('shared-view instructions must be explicitly bound inputs')
    actual = admission(prepared['request'], context['context_limits'])
    if actual['status'] != 'PASS':
        raise ValueError('request and reservations exceed explicit context byte budget; no truncation performed')
    if canonical_bytes(actual) != canonical_bytes(prepared['byte_admission']):
        raise ValueError('shared-view byte admission differs from actual request')


def render_view(root, rendered, context):
    """Never changes the canonical task or the legacy renderer's default bytes."""
    if 'prompt_view_version' not in context:
        if 'context_limits' in context:
            raise ValueError('context byte limits require an explicit shared view')
        return rendered
    if type(context['prompt_view_version']) is not int or context['prompt_view_version'] != 1:
        raise ValueError('unsupported prompt view version')
    if rendered.get('renderer_version', 1) != 2:
        raise ValueError('shared view requires renderer v2')
    validate_limits(context.get('context_limits'))
    result = deepcopy(rendered)
    template = binding(root, TEMPLATE)
    view = {'version':1, 'template':template, 'task_sha256':digest(canonical_bytes(result['task'])),
            'payload':encode(result['task'])}
    prompt = frozen_prompt(root, {'template':result['template'], 'prompt_view':view}, result['task'])
    result.update(prompt, prompt_view=view)
    result['inputs'] = sorted({r['path']:r for r in [*result['inputs'], template]}.values(), key=lambda r:r['path'])
    return result


def frozen_prompt(root, prepared, task, *, read=None, recompile=False):
    read = read or (lambda ref:bound_bytes(root, ref))
    system = read(prepared['template']).decode('utf-8')
    view = prepared.get('prompt_view')
    if view is None:
        payload = task
    else:
        if (set(view) != {'version','template','task_sha256','payload'}
                or type(view['version']) is not int or view['version'] != 1):
            raise ValueError('unsupported frozen prompt view')
        if recompile:
            if canonical_bytes(encode(prepared['task'])) != canonical_bytes(view['payload']):
                raise ValueError('shared view algorithm drift cannot be waived by runtime observations')
            view = {**view, 'payload':encode(task), 'task_sha256':digest(canonical_bytes(task))}
        if (view['task_sha256'] != digest(canonical_bytes(task))
                or canonical_bytes(expand(view['payload'])) != canonical_bytes(task)):
            raise ValueError('shared prompt view differs from canonical task')
        system += '\n' + read(view['template']).decode('utf-8')
        payload = view['payload']
    prompt = {'system':system, 'messages':[{'role':'user','content':canonical_bytes(payload).decode()}]}
    return {**prompt, 'prompt_sha256':digest(canonical_bytes(prompt)),
            **({'prompt_view':view} if view is not None else {})}
