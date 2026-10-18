"""Bounded research-only corpus experiment; all repository imports run in /tmp copies.

Run with the supported Python using -I -B. Never registers or builds a dataset.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path('/mnt/d/Code/RedChamberWorldHarness')
OUT = Path('artifacts/agent_research/phase6/advancement/corpus-title-compatibility-v1')
SELF = Path('tools/experiment_corpus_furniture.py')
CONFIG = 'data/corpus/builds/front80-v2-candidate.json'
ORIGINAL = 'corpus/front80/v2-candidate'
CANDIDATE_CONFIG = 'data/corpus/builds/front80-title-experiment-v1.json'
CANDIDATE_ID = 'corpus:front80:title-experiment-v1'


def canonical(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(obj))


def paths():
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'])
    result = set()
    for name in raw.split(b'\0'):
        if not name:
            continue
        p = Path(os.fsdecode(name))
        if p == SELF or p == OUT or OUT in p.parents:
            continue
        if p.is_absolute() or '..' in p.parts:
            raise RuntimeError('Unsafe git path')
        result.add(p.as_posix())
    return sorted(result)


def safe_file(root, relative):
    p = root
    for part in Path(relative).parts:
        p = p / part
        if p.is_symlink():
            raise RuntimeError(f'Symlink prohibited: {p}')
    if not stat.S_ISREG(p.stat().st_mode):
        raise RuntimeError(f'Not regular file: {p}')
    return p


def snapshot(destination):
    records = {}
    for relative in paths():
        source = safe_file(ROOT, relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = file_sha(source)
        with source.open('rb') as incoming, target.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        after = file_sha(target)
        if before != after or file_sha(source) != before:
            raise RuntimeError(f'Input changed during capture: {relative}')
        if source.stat().st_ino == target.stat().st_ino and source.stat().st_dev == target.stat().st_dev:
            raise RuntimeError('Snapshot must not share file inodes')
        records[relative] = {'sha256': after, 'bytes': target.stat().st_size}
    return records


def check_drift(records):
    current = paths()
    changes = [{'path': p, 'change': 'added'} for p in set(current) - set(records)]
    changes += [{'path': p, 'change': 'removed'} for p in set(records) - set(current)]
    for p in set(records) & set(current):
        try:
            if file_sha(safe_file(ROOT, p)) != records[p]['sha256']:
                changes.append({'path': p, 'change': 'bytes'})
        except Exception as exc:
            changes.append({'path': p, 'change': repr(exc)})
    return sorted(changes, key=lambda row: row['path'])


WORKER = r'''
import json, pathlib, sys, time, traceback
root, config, output = map(pathlib.Path, sys.argv[1:])
sys.path.insert(0, str(root / 'src'))
from rcwh.assets import AssetCatalog
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import canonical_bytes
output.mkdir(parents=True, exist_ok=False)
start = time.perf_counter()
result = {'config': str(config), 'python': sys.version, 'pid': __import__('os').getpid(), 'rss': None}
try:
    manifest, products = CorpusRepository(AssetCatalog.from_repo(root)).compile(str(config))
    (output / 'manifest.json').write_bytes(canonical_bytes(manifest))
    for name, raw in products.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    result.update(status='RETURNED', product_count=len(products))
except BaseException as exc:
    result.update(status='ERROR', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
finally:
    result['duration_seconds'] = time.perf_counter() - start
    (output / 'execution.json').write_bytes(canonical_bytes(result))
    print(json.dumps(result, ensure_ascii=False), flush=True)
if result['status'] == 'ERROR':
    sys.exit(1)
'''


def compile_once(snapshot_root, stage, worker, config, label, report):
    output = stage / label
    start = time.perf_counter()
    report['compile_calls'] += 1
    if report['compile_calls'] > 3:
        raise RuntimeError('Compile budget exceeded')
    completed = subprocess.run([sys.executable, '-I', '-B', str(worker), str(snapshot_root), config, str(output)],
                               cwd=worker.parent, capture_output=True)
    (stage / (label + '.stdout.log')).write_bytes(completed.stdout)
    (stage / (label + '.stderr.log')).write_bytes(completed.stderr)
    entry = {'label': label, 'returncode': completed.returncode, 'wall_seconds': time.perf_counter() - start}
    if (output / 'execution.json').exists():
        entry.update(json.loads((output / 'execution.json').read_bytes()))
    report['executions'].append(entry)
    print(json.dumps({'compile': label, **entry}, ensure_ascii=False), flush=True)
    if completed.returncode:
        raise RuntimeError(f'{label} compile failed; no inputs patched and no further compile allowed')
    return output


def products(directory):
    m = json.loads((directory / 'manifest.json').read_bytes())
    return {name: (directory / name).read_bytes() for name in m['products']}


def rows(raw):
    return [json.loads(line) for line in raw.splitlines()][1:]


def identity_only(raw):
    return raw.replace(CANDIDATE_ID.encode(), b'corpus:front80:v2-candidate')


def intervals(segments):
    result = defaultdict(list)
    for s in segments:
        cursor = 0
        for span in s['locator']['spans']:
            length = span['end'] - span['start']
            text = s['text'][cursor:cursor + length]
            assert len(text) == length
            result[span['unit_ref']].append((span['start'], span['end'], s['kind'], text, s['segment_id']))
            cursor += length
        assert cursor == len(s['text'])
    for group in result.values():
        group.sort()
        assert all(a[1] <= b[0] for a, b in zip(group, group[1:]))
    return result


def compare_intervals(old, new):
    assert set(old) == set(new), 'Carrier unit set changed'
    changes = []
    id_counts = Counter()
    total = 0
    for unit in sorted(old):
        a, b = old[unit], new[unit]
        i = j = 0
        left = min(a[0][0], b[0][0])
        while i < len(a) and j < len(b):
            x, y = a[i], b[j]
            assert x[0] <= left < x[1] and y[0] <= left < y[1], f'Coverage gap mismatch {unit}:{left}'
            right = min(x[1], y[1])
            text = x[3][left-x[0]:right-x[0]]
            assert text == y[3][left-y[0]:right-y[0]], f'Text mismatch {unit}:{left}'
            total += right - left
            if x[4] != y[4]:
                id_counts[f'{x[2]}->{y[2]}'] += right - left
            if x[2] != y[2]:
                if changes and changes[-1]['unit_ref'] == unit and changes[-1]['end'] == left and (changes[-1]['old_kind'], changes[-1]['new_kind']) == (x[2], y[2]):
                    changes[-1]['end'] = right
                    changes[-1]['text'] += text
                else:
                    changes.append({'unit_ref': unit, 'start': left, 'end': right, 'old_kind': x[2], 'new_kind': y[2], 'text': text})
            left = right
            if right == x[1]:
                i += 1
            if right == y[1]:
                j += 1
            if i < len(a) and j < len(b) and left < min(a[i][0], b[j][0]):
                assert a[i][0] == b[j][0], 'Coverage differs across gap'
                left = a[i][0]
        assert i == len(a) and j == len(b), 'Coverage tail mismatch'
    return changes, total, dict(id_counts)


def analyze(root, base, cand, stage, retained):
    p, q = products(base), products(cand)
    old, new = rows(p['segments.jsonl']), rows(q['segments.jsonl'])
    ai, bi = intervals(old), intervals(new)
    changes, total, shifted_chars = compare_intervals(ai, bi)
    dump(stage / 'interval-change-mask.json', changes)
    checks = {}
    checks['exactly_30_intervals'] = len(changes) == 30
    checks['only_variant_appendix_to_editorial'] = all(c['old_kind'] in {'VARIANT', 'APPENDIX'} and c['new_kind'] == 'EDITORIAL' for c in changes)
    observed = Counter(c['text'].strip() for c in changes)
    checks['exact_five_titles_and_occurrence_counts'] = dict(observed) == retained
    by_id = {s['segment_id']: s for s in new}
    checks['core_records'] = {}
    for kind, expected in [('MAIN_TEXT', 5639), ('ZHIPI', 4653)]:
        a = [{k: v for k, v in s.items() if k != 'dataset_ref'} for s in old if s['kind'] == kind]
        b = [{k: v for k, v in s.items() if k != 'dataset_ref'} for s in new if s['kind'] == kind]
        checks['core_records'][kind] = {'old_count': len(a), 'new_count': len(b), 'expected_count': expected, 'exact_without_dataset_ref': a == b}
        checks[kind + '_unchanged'] = len(a) == len(b) == expected and a == b
    chapter_names = [n for n in p if n.startswith('chapters/')]
    checks['80_chapter_texts_and_refs_unchanged'] = len(chapter_names) == 80 and all(p[n] == identity_only(q[n]) for n in chapter_names)
    companion = json.loads((root / 'artifacts/agent_research/phase6/corpus/page-furniture-lines.json').read_bytes())
    old_index = {s['segment_id']: s for s in old}
    signature = lambda s: canonical({k: v for k, v in s.items() if k not in {'dataset_ref', 'segment_id'}})
    new_signatures = Counter(signature(s) for s in new)
    prior_members = []
    split = numbers = 0
    for item in companion['lines']:
        refs = [item['segment_ref']]
        prefix = item.get('existing_editorial_prefix')
        if prefix:
            split += 1
            refs += [s['segment_ref'] for s in prefix['prefix_segments']]
        else:
            numbers += 1
        for ref in refs:
            prior_members.append({'old_segment_id': ref, 'unchanged_core_found': new_signatures[signature(old_index[ref])] == 1})
    checks['old31split_66pagenumbers_unchanged'] = split == 31 and numbers == 66 and all(r['unchanged_core_found'] for r in prior_members)
    dump(stage / 'old-furniture-members.json', prior_members)
    # Exact carrier-bound matching, not same sequential ID guesses.
    location_key = lambda s: canonical({'section_ref': s['section_ref'], 'locator': s['locator'], 'text': s['text'], 'kind': s['kind']})
    new_locations = {location_key(s): s for s in new}
    shifted = []
    for s in old:
        matched = new_locations.get(location_key(s))
        if matched and matched['segment_id'] != s['segment_id']:
            shifted.append({'old_segment_id': s['segment_id'], 'new_segment_id': matched['segment_id'], 'kind': s['kind']})
    dump(stage / 'shifted-segment-ids.json', shifted)
    churn = [{'product': n, 'old_sha256': sha(p[n]), 'candidate_sha256': sha(q[n]), 'same_raw': p[n] == q[n], 'same_after_dataset_identity_only': p[n] == identity_only(q[n])} for n in p]
    dump(stage / 'product-churn.json', churn)
    exemplar = json.loads((root / 'data/writing/exemplars/ch89-research-v2.json').read_bytes())
    exemplar_rows = []
    for selected in exemplar['segments']:
        original = old_index[selected['segment_id']]
        current = by_id.get(selected['segment_id'])
        exemplar_rows.append({'segment_id': selected['segment_id'], 'expected_text_sha256': selected['text_sha256'], 'same_id_text_locator': bool(current and selected['text_sha256'] == current['text_sha256'] and original['locator'] == current['locator'])})
    bindings = []
    mismatches = []
    count = 0
    for chapter in range(81, 101):
        package_path = f'data/writing/packages/ch{chapter}-agent-research-v3.json'
        package = json.loads((root / package_path).read_bytes())
        request_path = f'artifacts/agent_research/phase6/revisions-v2/requests/ch{chapter}.json'
        request = json.loads((root / request_path).read_bytes())
        bound = list(request['inputs']) + [request[k] for k in ('package', 'parent', 'feedback', 'template') if isinstance(request.get(k), dict) and 'path' in request[k]]
        for binding in bound:
            count += 1
            if file_sha(root / binding['path']) != binding['sha256']:
                mismatches.append({'chapter': chapter, **binding})
        bindings.append({'chapter': chapter, 'package_path': package_path, 'package_sha256': file_sha(root / package_path), 'exemplar_set': package.get('exemplar_set'), 'request_path': request_path, 'request_sha256': file_sha(root / request_path), 'manifest_in_request_inputs': any(b['path'] == ORIGINAL + '/manifest.json' for b in request['inputs'])})
    package_impact = {'packages': bindings, 'exemplar': exemplar, 'exemplar_segments': exemplar_rows, 'old_prepared_binding_occurrences': count, 'old_prepared_binding_mismatches': mismatches, 'fresh_renderer_or_new_package_executed': False, 'lineage_calls': 0, 'new_exemplar_or_package_created': False, 'interpretation': 'All 20 existing packages select the shared v2 exemplar. Candidate identity and manifest differ even with identical selected segment text/locators. Adopting candidate requires a new bound exemplar and all 20 new packages plus genuine new generation lineage, not rebinding old drafts. This is binding impact analysis, not fresh validity or a measured generation cost.'}
    dump(stage / 'package-impact.json', package_impact)
    success = all(v for k, v in checks.items() if k != 'core_records') and not mismatches and all(r['same_id_text_locator'] for r in exemplar_rows)
    return {'checks': checks, 'interval_count': len(changes), 'title_occurrences': dict(observed), 'carrier_characters_compared': total, 'segment_counts': {'old': len(old), 'candidate': len(new)}, 'shifted_exact_locator_segment_count': len(shifted), 'shifted_by_kind': dict(Counter(r['kind'] for r in shifted)), 'shifted_id_characters_by_layer_change': shifted_chars, 'products_changed_raw': sum(not r['same_raw'] for r in churn), 'products_changed_beyond_dataset_identity': sum(not r['same_after_dataset_identity_only'] for r in churn), 'old_furniture': {'split_groups': split, 'page_numbers': numbers, 'members': len(prior_members)}, 'old_prepared_binding_occurrences': count, 'old_prepared_mismatches': len(mismatches), 'experimental_checks_satisfied': success}


def main():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('Supported Python 3.12 required')
    if (ROOT / OUT).exists():
        raise RuntimeError('Output directory must be absent')
    allocation = Path(tempfile.mkdtemp(prefix='rcwh-corpus-title-experiment-'))
    repo = allocation / 'repository'
    repo.mkdir()
    stage = allocation / 'results'
    stage.mkdir()
    report = {'schema_version': 1, 'qualification': 'MODEL', 'authority_effect': 'NONE', 'scope': 'RESEARCH_ONLY_SANDBOX_COMPILE_EXPERIMENT', 'status': 'FAIL', 'compile_calls': 0, 'executions': [], 'original_root': str(ROOT), 'allocated_tmp': str(allocation), 'python': sys.version, 'no_build_register_catalog_write_on_original': True, 'source_corpus_review_release_pass': False, 'original_opinions_and_fails_retained': True, 'new_package_or_lineage_calls': False}
    records = None
    started = time.perf_counter()
    try:
        records = snapshot(repo)
        dump(stage / 'original-input-snapshot.json', records)
        report['snapshot_files'] = len(records)
        report['snapshot_bytes'] = sum(v['bytes'] for v in records.values())
        report['snapshot_digest'] = sha(canonical(records))
        print(json.dumps({'snapshot_complete': report['snapshot_files'], 'bytes': report['snapshot_bytes']}), flush=True)
        worker = allocation / 'compile_worker.py'
        worker.write_text(WORKER)
        baseline = compile_once(repo, stage, worker, CONFIG, 'baseline', report)
        original = products(repo / ORIGINAL)
        actual = products(baseline)
        mismatches = sorted(n for n in set(original) | set(actual) if original.get(n) != actual.get(n))
        report['baseline'] = {'original_product_count': len(original), 'compiled_product_count': len(actual), 'mismatched_products': mismatches, 'manifest_exact_bytes': (baseline / 'manifest.json').read_bytes() == (repo / ORIGINAL / 'manifest.json').read_bytes()}
        if len(original) != 86 or mismatches:
            raise RuntimeError('Baseline did not exactly match all 86 canonical original product bytes; STOP')
        retained = json.loads((repo / 'artifacts/agent_research/phase6/corpus/page-furniture-lines.json').read_bytes())['intentionally_retained_top_titles']
        if not isinstance(retained, dict) or len(retained) != 5 or not all(isinstance(k, str) and isinstance(v, int) for k, v in retained.items()):
            raise RuntimeError('Unexpected actual retained-title shape; no normalization guessed')
        config = json.loads((repo / CONFIG).read_bytes())
        config['dataset_ref'] = CANDIDATE_ID
        config['layer_policy']['page_furniture']['running_headers'] += list(retained)
        assert config['schema_version'] == 2
        dump(repo / CANDIDATE_CONFIG, config)
        dump(stage / 'candidate-config.json', config)
        first = compile_once(repo, stage, worker, CANDIDATE_CONFIG, 'candidate-first', report)
        second = compile_once(repo, stage, worker, CANDIDATE_CONFIG, 'candidate-second', report)
        report['candidate_determinism'] = {'products_exact': products(first) == products(second), 'canonical_manifest_exact': (first / 'manifest.json').read_bytes() == (second / 'manifest.json').read_bytes(), 'separate_processes': report['executions'][1]['pid'] != report['executions'][2]['pid']}
        report['analysis'] = analyze(repo, baseline, first, stage, retained)
        if not all(report['candidate_determinism'].values()) or not report['analysis']['experimental_checks_satisfied']:
            raise RuntimeError('Candidate compatibility checks failed; actual outputs retained without adjustment')
        report['status'] = 'EXPERIMENT_CHECKS_SATISFIED_NOT_QUALIFICATION'
    except BaseException as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        try:
            drift = check_drift(records) if records is not None else [{'change': 'capture_incomplete'}]
        except BaseException as exc:
            drift = [{'change': 'drift_check_error', 'error': repr(exc)}]
        report['original_input_drift'] = drift
        report['original_input_no_drift'] = not drift
        if drift:
            report['status'] = 'FAIL_ORIGINAL_INPUT_DRIFT_NO_SUCCESS_COPYBACK'
        report['total_duration_seconds_before_copyback'] = time.perf_counter() - started
        dump(stage / 'report.json', report)
        destination = ROOT / OUT
        try:
            if destination.exists():
                raise RuntimeError('Output unexpectedly exists; do not overwrite')
            if drift:
                destination.mkdir()
                dump(destination / 'report.json', report)
            else:
                shutil.copytree(stage, destination, symlinks=False)
        finally:
            shutil.rmtree(allocation)
            report['own_allocated_tmp_removed'] = not allocation.exists()
            if destination.exists():
                dump(destination / 'report.json', report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['status'] == 'EXPERIMENT_CHECKS_SATISFIED_NOT_QUALIFICATION' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    raise SystemExit(main())
