#!/usr/bin/env python3
"""One-shot, chapter-bounded, byte-preserving proposal assembly; no activation/build."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path('/mnt/d/Code/RedChamberWorldHarness')
HERE = ROOT / 'artifacts/agent_research/phase6/stable-proposal'
MANIFEST = ROOT / 'data/releases/proposals/v1.5.json'
OUTPUT = ROOT / 'releases/proposals/v1.5/book.md'
BASELINE = ROOT / 'releases/stable/v1.4/readable/baseline.md'
SUBMISSIONS = 'artifacts/agent_research/phase5/submissions/'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def relative(path):
    return str(path.relative_to(ROOT))

def binding(path):
    p = ROOT / path
    data = p.read_bytes()
    return {'path': path, 'sha256': sha(data), 'bytes': len(data)}

def load(path):
    return json.loads((ROOT / path).read_bytes())

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def protected_snapshot():
    paths = {p for p in (ROOT / 'releases/stable').rglob('*') if p.is_file()}
    paths.update(p for p in (ROOT / 'data').rglob('*current*.json') if p.is_file())
    paths.update(p for p in (ROOT / 'data/releases').rglob('*')
                 if p.is_file() and 'proposals' not in p.relative_to(ROOT / 'data/releases').parts)
    return {relative(p): binding(relative(p)) for p in sorted(paths)}

assert not MANIFEST.exists() and not OUTPUT.exists(), 'Never overwrite a proposal.'
assert set(p.name for p in HERE.iterdir()) <= {'assemble.py', 'protected-before.json'}, 'Fresh evidence directory or same one-shot preflight checkpoint required.'
current_path = 'data/project/current.json'
current = load(current_path)
selected_path = current['owners']['release']
assert selected_path == 'releases/stable/v1.4/manifest.json'
selected = load(selected_path)
baseline = BASELINE.read_bytes()
assert selected['text_asset_ref'] == 'asset:release:stable:v1.4:readable'
assert sha(baseline) == selected['text_sha256'] == '4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320'
assert len(baseline) == 545334
catalog = (ROOT / 'data/catalog/assets/42.yaml').read_text(encoding='utf-8')
assert 'id: asset:release:stable:v1.4:readable\n  path: releases/stable/v1.4/readable/baseline.md\n  sha256: ' + sha(baseline) in catalog
before = protected_snapshot()
status_before = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain=v1', '-uall']).decode()
if (HERE / 'protected-before.json').exists():
    assert load(relative(HERE / 'protected-before.json')) == before, 'Preflight retry must retain original protected snapshot.'
else:
    save(HERE / 'protected-before.json', before)

# Heading starts define an exact, contiguous partition, not normalized chapter text.
heading_matches = list(re.finditer(rb'(?m)^# [^\n]+\n', baseline))
assert len(heading_matches) == 20 and heading_matches[0].start() == 0
chapters = {}
for i, match in enumerate(heading_matches):
    chapter = 81 + i
    start = match.start()
    end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(baseline)
    chapters[chapter] = {'start': start, 'end': end, 'heading': match.group().decode('utf-8'), 'bytes': baseline[start:end]}

summary_paths = ['artifacts/agent_research/phase5/' + name for name in
                 ['EARLY_READING_RESULTS.md', 'LATE_READING_RESULTS.md', 'TAIL_READING_RESULTS.md']]
summary_bindings = [binding(p) for p in summary_paths]

def locate(chapter, text):
    raw = text.encode('utf-8')
    c = chapters[chapter]
    assert c['bytes'].count(raw) == 1, (chapter, text, 'not unique in chapter')
    offset = c['bytes'].index(raw)
    absolute = c['start'] + offset
    assert baseline.count(raw) == 1, (chapter, text, 'not unique in baseline')
    line = baseline[:absolute].count(b'\n') + 1
    return {'chapter': chapter, 'original_span': text, 'original_span_sha256': sha(raw),
            'baseline_byte_start': absolute, 'baseline_byte_end_exclusive': absolute + len(raw),
            'chapter_byte_start': offset, 'chapter_byte_end_exclusive': offset + len(raw),
            'baseline_physical_line': line,
            'chapter_physical_line': c['bytes'][:offset].count(b'\n') + 1,
            'offset_convention': 'zero-based UTF-8 byte offsets; end exclusive',
            'original_occurrences_in_chapter': 1, 'original_occurrences_in_baseline': 1}

def pointer(obj, ptr):
    for part in ptr.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj

all_evidence = []
def evidence(report_name, pointer_path):
    path = SUBMISSIONS + report_name
    obj = load(path)
    item = pointer(obj, pointer_path)
    quote = item.get('quote', item.get('text'))
    chapter = item['chapter']
    token = item.get('subject_id', item.get('token'))
    subject_path = item['path']
    subject_hash = item.get('subject_sha256', item.get('sha256'))
    subject = (ROOT / subject_path).read_bytes()
    assert sha(subject) == subject_hash
    packet_path = obj['packet']['path']
    packet = load(packet_path)
    assert sha((ROOT / packet_path).read_bytes()) == obj['packet']['sha256']
    psubject = next(x for x in packet['subjects'] if x['id'] == token)
    assert psubject['binding'] == {'path': subject_path, 'sha256': subject_hash}
    line = item.get('line', item.get('physical_line', item.get('line_start')))
    assert quote in subject.decode('utf-8').splitlines()[line - 1]
    assert chapters[chapter]['bytes'].count(quote.encode('utf-8')) == 1
    sequence = [81,82,83] if 'early' in subject_path else list(range(92,98)) if 'late' in subject_path else [98,99,100]
    subject_headings = list(re.finditer(rb'(?m)^# [^\n]+\n', subject))
    assert len(subject_headings) == len(sequence)
    separator_differences = []
    for i, baseline_chapter in enumerate(sequence):
        ss = subject_headings[i].start()
        se = subject_headings[i+1].start() if i+1 < len(sequence) else len(subject)
        reader_chapter = subject[ss:se]
        stable_chapter = chapters[baseline_chapter]['bytes']
        # Actual anonymous export removes one trailing blank-line LF in some
        # chapters. Require every heading/body byte to agree and disclose each
        # precise separator difference; NEVER normalize the output baseline.
        reader_body = reader_chapter.rstrip(b'\n')
        stable_body = stable_chapter.rstrip(b'\n')
        assert reader_body == stable_body, ('reader body differs from selected stable', baseline_chapter)
        stable_tail = stable_chapter[len(stable_body):]
        reader_tail = reader_chapter[len(reader_body):]
        assert len(stable_tail) - len(reader_tail) in [0,1]
        if stable_tail != reader_tail:
            separator_differences.append({'chapter': baseline_chapter,
                'baseline_trailing_LF_count': len(stable_tail), 'reader_trailing_LF_count': len(reader_tail),
                'only_difference': 'one trailing separator LF omitted by anonymous export'})
    record = {'observation_report': binding(path), 'json_pointer': pointer_path,
              'reviewer': obj['reviewer'], 'packet': binding(packet_path), 'subject': binding(subject_path),
              'subject_id': token, 'chapter': chapter, 'subject_physical_line': line,
              'quote': quote, 'quote_sha256': sha(quote.encode('utf-8')),
              'baseline_location': locate(chapter, quote),
              'mechanical_checks': {'subject_hash_matches_report_and_packet': True,
                                    'all_subject_heading_and_body_bytes_equal_selected_stable': True,
                                    'subject_whole_bytes_equal_baseline_slice': not separator_differences,
                                    'anonymous_export_separator_differences': separator_differences,
                                    'quote_exact_at_reported_subject_line': True}}
    all_evidence.append(record)
    return record

def opinion(name, corrected_name=None):
    path = SUBMISSIONS + name
    obj = load(path)
    result = obj['results'][0]
    answer = {'original_report': binding(path), 'original_result_pointer': '/results/0',
              'original_verdict': result['verdict'], 'original_notes': result['notes'],
              'reviewer': obj['reviewer'], 'authority_effect': obj['authority_effect'],
              'independent_human_admission': obj['independent_human_admission']}
    assert obj['authority_effect'] == 'NONE' and not obj['independent_human_admission']
    if corrected_name:
        corrected_path = SUBMISSIONS + corrected_name
        corrected = load(corrected_path)
        assert corrected['reviewer'] == obj['reviewer'] and corrected['packet'] == obj['packet']
        answer['preserved_same_reader_revision'] = {
            'report': binding(corrected_path), 'result_pointer': '/results/0',
            'verdict': corrected['results'][0]['verdict'], 'notes': corrected['results'][0]['notes'],
            'not_an_additional_reader': True}
    return answer

early_opinions = [opinion('fullbook-early-reader-2.json')]
late_opinions = [opinion('fullbook-late-reader-1.json', 'fullbook-late-reader-1-verdict-v2.json'),
                 opinion('fullbook-late-reader-2.json')]
tail_opinions = [opinion('fullbook-tail-reader-1.json'),
                 opinion('fullbook-tail-reader-2.json', 'fullbook-tail-reader-2-format-v2.json')]

issues = [
    {'id': 'proposal-ch83-date', 'chapter': 83, 'status': 'PROPOSED',
     'reason': '保留“隔了几日”的场景间隔；只把宝玉指向射圃相见的“今日”改为“那日”，不额外断定恰为前两天，不改麒麟身份/转交链。',
     'reader_opinions': early_opinions,
     'reader_evidence': [evidence('fullbook-early-reader-2-observations.json', '/dimensions/6/token_observations/0/evidence/' + str(i)) for i in [0,1]],
     'patches': [('我今日在他身上见了一个，像得很。', '我那日在他身上见了一个，像得很。')]},
    {'id': 'proposal-ch92-snack-count', 'chapter': 92, 'status': 'PENDING',
     'reason': '第91回明确只装一块，另一块给贾母；第92回开头也一块，吃后却剩另一块，稍后搜袖只剩空油纸，夜间又回忆“麝月那两块点心”。改开头一为两违背91→92接口；只修吃后句仍遗留回忆数量。不能证明“两块”是否包含留给贾母的那块，也不能凭空补取物/补吃。保守保持整回原bytes，两段候选修改均未施用，原局部FAIL继续保留，待用户决定。',
     'reader_opinions': late_opinions,
     'reader_evidence': [evidence('fullbook-late-reader-2-observations.json', '/exact_quote_evidence/' + str(i)) for i in [0,1]],
     'patches': [],
     'pending_alternatives': [
         {**locate(92, '想了一想，只吃了一块，另一块仍包好。'),
          'suggested_text': '想了一想，吃了那块点心，油纸仍叠好。', 'applied': False,
          'limitation': '可与搜袖时空油纸一致，但单独施用仍遗留夜间两块回忆。'},
         {**locate(92, '又想麝月那两块点心，自己竟真一块也没带回来。'),
          'suggested_text': '又想麝月那块点心，自己竟真没带回来。', 'applied': False,
          'limitation': '需要判定这句回忆只计宝玉带走的那块，而不计第91回另一块留贾母；现不将该解释认证为事实。'}],
     'additional_baseline_context': [
         locate(91, '宝钗在灯下理那两块干点心，用一小张油纸包好，又停了停，只放了一块进去。麝月看见，问：“怎么少一块？”宝钗道：“另一块留给老太太明早吃。宝玉不过出去半日，一块够了。”'),
         locate(92, '宝玉身上原没有什么，只摸出那张包点心的油纸。那人展开看了一眼，笑道：“吃完了还留这个作什么？”')],
     'actual_reading_scope': '第91回末段1515–1544行、第92回全回1545–1678行及92→93接口1679–1681行实际读取；非全书文学重评。'},
    {'id': 'proposal-ch96-self-quotation', 'chapter': 96, 'status': 'PROPOSED',
     'reason': '信文已有“天下会强嘴”，仅删叙述标作宝钗念到的自引里多出的“最”；不反改信文本、不改人物评价或诗文。',
     'reader_opinions': late_opinions,
     'reader_evidence': [evidence('fullbook-late-reader-2-observations.json', '/exact_quote_evidence/' + str(i)) for i in [20,21]],
     'patches': [('宝钗念到“天下最会强嘴的原不只宝哥哥一个”', '宝钗念到“天下会强嘴的原不只宝哥哥一个”')]},
    {'id': 'proposal-ch98-parcel-location', 'chapter': 98, 'status': 'PROPOSED',
     'reason': '删除“同自己的书札包一起”，保留原指代“桌角有一个小布包”及顺手拿起。前段旧帕包裹玉并放桌角、离去后青灰书札包仍在桌角，次晨拆出五封书札两张题签，后亲返旧帕包玉并取回书札；原文本已足以识别两包，不将小布包额外改名成玉包，也不补隐形放回/交接。此最小删除只取消明确“两包同时拿起”的冲突，不认证全回物件或台词毫无瑕疵。',
     'reader_opinions': tail_opinions,
     'reader_evidence': [evidence('fullbook-tail-reader-1-observations.json', '/quote_ledger/' + str(i)) for i in [2,3,4,6]] +
                        [evidence('fullbook-tail-reader-2-observations.json', '/quotes/' + str(i)) for i in [3,4,5]],
     'additional_baseline_context': [
         locate(98, '麝月把通灵玉取下来，找一块洗过多次的旧帕包好，搁在桌角'),
         locate(98, '几封书札另用一块青灰布包着；旧帕包的通灵玉仍压在桌角薄书下。')],
     'patches': [('见桌角有一个小布包，顺手同自己的书札包一起拿起', '见桌角有一个小布包，顺手拿起')]},
]

patches = []
for issue in issues:
    pairs = issue.pop('patches')
    issue['applied_patch_ids'] = []
    for old, new in pairs:
        patch = locate(issue['chapter'], old)
        patch.update({'id': issue['id'] + '-patch', 'issue_id': issue['id'],
                      'suggested_text': new, 'suggested_text_sha256': sha(new.encode('utf-8')),
                      'status': 'PROPOSED_IN_OUTPUT_NOT_ACTIVATED'})
        assert old != new and '\n' not in old and '\n' not in new
        patch['proposed_occurrences_in_baseline_chapter'] = chapters[issue['chapter']]['bytes'].count(new.encode('utf-8'))
        assert patch['proposed_occurrences_in_baseline_chapter'] == 0
        patches.append(patch)
        issue['applied_patch_ids'].append(patch['id'])
patches.sort(key=lambda p: p['baseline_byte_start'])
assert [p['chapter'] for p in patches] == [83,96,98]

# Assemble exclusively by slicing immutable bytes. No global replacement,
# Markdown parsing, newline normalization, or re-rendering of chapter text.
chunks = []
cursor = 0
output_cursor = 0
copy_ledger = []
for patch in patches:
    start, end = patch['baseline_byte_start'], patch['baseline_byte_end_exclusive']
    assert cursor <= start < end
    copied = baseline[cursor:start]
    chunks.append(copied)
    copy_ledger.append({'baseline_start': cursor, 'baseline_end_exclusive': start,
                        'output_start': output_cursor, 'output_end_exclusive': output_cursor + len(copied),
                        'sha256': sha(copied)})
    output_cursor += len(copied)
    proposed = patch['suggested_text'].encode('utf-8')
    patch['output_byte_start'] = output_cursor
    patch['output_byte_end_exclusive'] = output_cursor + len(proposed)
    chunks.append(proposed)
    output_cursor += len(proposed)
    cursor = end
copied = baseline[cursor:]
chunks.append(copied)
copy_ledger.append({'baseline_start': cursor, 'baseline_end_exclusive': len(baseline),
                    'output_start': output_cursor, 'output_end_exclusive': output_cursor + len(copied),
                    'sha256': sha(copied)})
proposal = b''.join(chunks)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open('xb') as f:
    f.write(proposal)

# Exhaustive chapter and blank/nonblank paragraph-run coverage of BOTH files.
# Runs include headings, verse lines, empty lines, terminal separators and EOF.
chapter_ledger = []
paragraph_ledger = []
output_start = 0
for chapter, c in chapters.items():
    chapter_patches = [p for p in patches if p['chapter'] == chapter]
    delta = sum(len(p['suggested_text'].encode('utf-8')) - len(p['original_span'].encode('utf-8')) for p in chapter_patches)
    output_end = output_start + len(c['bytes']) + delta
    proposed_chapter = proposal[output_start:output_end]
    assert proposed_chapter.startswith(c['heading'].encode('utf-8'))
    original_lines = c['bytes'].splitlines(keepends=True)
    proposed_lines = proposed_chapter.splitlines(keepends=True)
    assert len(original_lines) == len(proposed_lines)
    assert [x for x in original_lines if not x.strip()] == [x for x in proposed_lines if not x.strip()]
    assert len(c['bytes']) - len(proposed_chapter) == -delta
    assert all(c['start'] <= p['baseline_byte_start'] < p['baseline_byte_end_exclusive'] <= c['end'] for p in chapter_patches)
    if not chapter_patches:
        assert proposed_chapter == c['bytes']
    for p in chapter_patches:
        assert proposed_chapter.count(p['suggested_text'].encode('utf-8')) == 1
        assert proposed_chapter.count(p['original_span'].encode('utf-8')) == 0
        p['suggested_occurrences_in_output_chapter'] = 1
        p['suggested_occurrences_in_entire_output'] = proposal.count(p['suggested_text'].encode('utf-8'))
        assert p['suggested_occurrences_in_entire_output'] == 1
    chapter_ledger.append({'chapter': chapter, 'heading': c['heading'],
                           'baseline_byte_start': c['start'], 'baseline_byte_end_exclusive': c['end'],
                           'output_byte_start': output_start, 'output_byte_end_exclusive': output_end,
                           'baseline_sha256': sha(c['bytes']), 'output_sha256': sha(proposed_chapter),
                           'physical_line_count': len(original_lines), 'patch_ids': [p['id'] for p in chapter_patches],
                           'heading_identical': True, 'blank_lines_identical': True,
                           'unchanged_chapter_bytes_identical': not chapter_patches})
    oldpos, newpos = c['start'], output_start
    i = 0
    while i < len(original_lines):
        blank = not original_lines[i].strip()
        j = i + 1
        while j < len(original_lines) and (not original_lines[j].strip()) == blank:
            j += 1
        oldrun = b''.join(original_lines[i:j])
        newrun = b''.join(proposed_lines[i:j])
        overlapping = [p['id'] for p in chapter_patches if oldpos <= p['baseline_byte_start'] < oldpos + len(oldrun)]
        if not overlapping:
            assert oldrun == newrun
        paragraph_ledger.append({'chapter': chapter, 'run_kind': 'BLANK_SEPARATOR' if blank else 'NONBLANK_PARAGRAPH_RUN',
                                 'chapter_line_start': i + 1, 'chapter_line_end': j,
                                 'baseline_byte_start': oldpos, 'baseline_byte_end_exclusive': oldpos + len(oldrun),
                                 'output_byte_start': newpos, 'output_byte_end_exclusive': newpos + len(newrun),
                                 'baseline_sha256': sha(oldrun), 'output_sha256': sha(newrun),
                                 'patch_ids': overlapping, 'identical': oldrun == newrun})
        oldpos += len(oldrun)
        newpos += len(newrun)
        i = j
    assert oldpos == c['end'] and newpos == output_end
    output_start = output_end
assert output_start == len(proposal)
assert b''.join(baseline[c['start']:c['end']] for c in chapters.values()) == baseline
assert chapters[92]['bytes'] == proposal[chapter_ledger[11]['output_byte_start']:chapter_ledger[11]['output_byte_end_exclusive']]
assert proposal.count(b'\n') == baseline.count(b'\n')
assert re.findall(rb'\s+', baseline) == re.findall(rb'\s+', proposal), 'All whitespace byte runs must be identical.'
# Invert the three precise output spans. This is stronger than trusting a diff.
reverse_chunks = []
end = 0
for p in patches:
    reverse_chunks.extend([proposal[end:p['output_byte_start']], p['original_span'].encode('utf-8')])
    end = p['output_byte_end_exclusive']
reverse_chunks.append(proposal[end:])
assert b''.join(reverse_chunks) == baseline
for run in copy_ledger:
    assert baseline[run['baseline_start']:run['baseline_end_exclusive']] == proposal[run['output_start']:run['output_end_exclusive']]

after = protected_snapshot()
assert before == after, 'Protected current/release bytes or path set changed.'
coverage = {'kind': 'PROPOSAL_MECHANICAL_BYTE_COVERAGE', 'scope': 'Selected stable readable chapters 81–100, not an assembled 1–100 novel or a literary reread.',
            'offset_convention': 'zero-based UTF-8 bytes; end exclusive',
            'baseline': binding(relative(BASELINE)), 'output': binding(relative(OUTPUT)),
            'chapters': chapter_ledger, 'paragraph_runs': paragraph_ledger,
            'unchanged_copy_ranges': copy_ledger,
            'chapter_boundary_coverage': {'all_chapters': list(range(81,101)), 'all_19_internal_boundaries_covered': True,
                                          'headings_and_owned_trailing_separators_preserved': True,
                                          'first_byte_through_EOF_covered_without_gap_or_overlap': True},
            'paragraph_run_count': len(paragraph_ledger), 'mechanical_only': True}
save(HERE / 'coverage.json', coverage)
save(HERE / 'protected-after.json', after)
manifest = {'proposal_format_version': 1, 'kind': 'STABLE_TEXT_EDIT_PROPOSAL_NOT_RELEASE_MANIFEST_NOT_BUILD',
            'id': 'proposal:stable:v1.5', 'status': 'PROPOSAL_NOT_ACTIVATED', 'authority': 'NONE',
            'authority_effect': 'NONE', 'requires_user_approval': True, 'may_be_rejected': True,
            'activation_authorized': False, 'automatic_adoption_authorized': False,
            'baseline': {'asset': selected['text_asset_ref'], **binding(relative(BASELINE)),
                         'selected_by': binding(current_path), 'release_manifest': binding(selected_path),
                         'catalog_asset_entry': binding('data/catalog/assets/42.yaml'),
                         'text_scope': 'Entire selected stable readable bytes: 20 chapters, 81–100. No added front80 text.',
                         'baseline_release_status': selected['status'], 'baseline_evidence_closure': selected['evidence_closure']},
            'initial_target_absence': {'checked_before_any_write': True,
                                       'paths': ['data/releases/proposals/v1.5.json', 'releases/proposals/v1.5/book.md',
                                                 'artifacts/agent_research/phase6/stable-proposal/'],
                                       'method': 'read-only shell test -e of all three targets before creating assemble.py; all three absent'},
            'phase5_reading_summaries': summary_bindings, 'issues': issues, 'applied_patches': patches,
            'counts': {'reported_problem_groups': 4, 'proposed_problem_groups_in_output': 3,
                       'pending_problem_groups': 1, 'actual_disjoint_patch_spans': 3},
            'output': binding(relative(OUTPUT)),
            'mechanical_coverage': binding(relative(HERE / 'coverage.json')),
            'protected_before': binding(relative(HERE / 'protected-before.json')),
            'protected_after': binding(relative(HERE / 'protected-after.json')),
            'limits': ['原EARLY/LATE/TAIL基线FAIL及原报告/更正意见全部保留，不因提案修改撤销。',
                       '第92回PENDING且整回不变，原数量FAIL仍在提案正文，不得声称四处均已修复。',
                       '机械bytes核验不等于来源PASS、文学PASS、全书一致、独立真人评审、采用或激活。',
                       '不变更current、stable v1.4、release登记、catalog或build；该JSON仅为自有proposal格式。',
                       '未检查/修复四个问题之外的字句、来源合同、文学取舍、日期词或角色回忆；一律不外推通过。']}
save(MANIFEST, manifest)
status_after = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain=v1', '-uall']).decode()
added_status_lines = sorted(set(status_after.splitlines()) - set(status_before.splitlines()))
removed_status_lines = sorted(set(status_before.splitlines()) - set(status_after.splitlines()))
assert not removed_status_lines
allowed = ['?? artifacts/agent_research/phase6/stable-proposal/', '?? data/releases/proposals/v1.5.json', '?? releases/proposals/v1.5/book.md']
assert all(any(line.startswith(prefix) for prefix in allowed) for line in added_status_lines)
report = {'kind': 'ACTUAL_PROPOSAL_MECHANICAL_VERIFICATION', 'status': 'PROPOSAL_NOT_ACTIVATED',
          'authority': 'NONE', 'requires_user_approval': True, 'baseline': binding(relative(BASELINE)),
          'output': binding(relative(OUTPUT)), 'manifest': binding(relative(MANIFEST)),
          'counts': manifest['counts'], 'pending': ['proposal-ch92-snack-count'],
          'checks': {'baseline_hash_equals_current_selected_release_and_catalog': True,
                     'only_three_exact_chapter_bounded_patch_spans_applied': True,
                     'three_spans_correspond_to_three_of_four_reported_problem_groups': True,
                     'pending_chapter92_entire_bytes_unchanged': True,
                     'original_and_suggested_spans_each_unique_in_their_chapter_and_file': True,
                     'all_nonpatch_bytes_exact_copy': True,
                     'inverse_patch_reconstruction_equals_entire_baseline': True,
                     'all_20_chapters_all_19_interfaces_and_all_paragraph_runs_covered': True,
                     'all_headings_and_all_whitespace_byte_runs_identical': True,
                     'protected_current_and_stable_release_hashes_and_path_sets_unchanged': True,
                     'reader_report_hashes_packet_hashes_subject_hashes_exact_quote_lines_verified': True,
                     'reader_subject_heading_and_body_bytes_equal_baseline_with_disclosed_separator_LF_differences': True,
                     'git_status_increment_within_write_allowlist': True},
          'protected_file_count': len(before), 'chapter_count': 20, 'paragraph_run_count': len(paragraph_ledger),
          'reader_evidence_records_verified': len(all_evidence), 'actual_applied_patch_ids': [p['id'] for p in patches],
          'git_status_added_lines_before_report_file': added_status_lines,
          'not_claimed': ['FOUR_PATCHES_APPLIED', 'CHAPTER92_FIXED', 'SOURCE_PASS', 'LITERARY_PASS',
                          'WHOLE_NOVEL_CONSISTENCY_PASS', 'RELEASE_OR_BUILD_PASS', 'ACTIVATION', 'AUTOMATIC_ADOPTION'],
          'original_negative_verdicts': 'EARLY baseline FAIL; LATE corrected reader1 baseline FAIL and reader2 baseline FAIL; TAIL both baseline FAIL. Original reader1 LATE reading-only PASS and reader2 TAIL original format issues are preserved and bound, not hidden.',
          'commands': ['python -I artifacts/agent_research/phase6/stable-proposal/assemble.py'],
          'reading_vs_mechanics': 'Read summaries and exact reader quotes; actually read complete chapter92 and 91→92 interface, plus affected context. Full bytes/paragraph/chapter coverage is mechanical, not a claim of a new full-book literary read.'}
save(HERE / 'report.json', report)
assert protected_snapshot() == before
print(json.dumps({'manifest': str(MANIFEST), 'output': str(OUTPUT), 'output_bytes': len(proposal),
                  'output_sha256': sha(proposal), 'actual_patch_spans': len(patches), 'pending_chapter': 92,
                  'paragraph_runs': len(paragraph_ledger), 'protected_file_count': len(before)}, ensure_ascii=False, indent=2))
