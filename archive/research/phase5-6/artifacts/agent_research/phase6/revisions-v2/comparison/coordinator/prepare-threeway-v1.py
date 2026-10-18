"""Prepare local anonymous research packets without changing any source bytes."""
from pathlib import Path
import json
import sys

from rcwh.backtest.session import anonymous_export
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.generation.records import append_bytes, binding, bound_bytes

root = Path(sys.argv[1]).resolve()
base = 'artifacts/agent_research/phase6/revisions-v2'
old = 'artifacts/agent_research/phase5'
selection_ref = binding(root, f'{base}/continuity-reading-selection-v1.json')
selected = {row['chapter']: row for row in json.loads(bound_bytes(root, selection_ref))['chapters']}
groups = [
    ('early', 'set-k7', range(81, 84), 'fullbook-early-export.json', 'fullbook-early-context.json'),
    ('middle', 'set-m4', range(84, 92), 'fullbook-middle-export-v1.json', 'fullbook-middle-context-v1.json'),
    ('late', 'set-p8', range(92, 98), 'fullbook-late-export-v1.json', 'fullbook-late-context-v1.json'),
    ('tail', 'set-r2', range(98, 101), 'fullbook-tail-export-v1.json', 'fullbook-tail-context-v1.json'),
]
reports = []
for stage, opaque, chapters, export_name, context_name in groups:
    chapters = list(chapters)
    export_ref = binding(root, f'{old}/{export_name}')
    previous_export = json.loads(bound_bytes(root, export_ref))
    previous_map = json.loads(bound_bytes(root, previous_export['mapping']))
    previous_context_ref = binding(root, f'{old}/{context_name}')
    previous_context = json.loads(bound_bytes(root, previous_context_ref))
    old_candidates = previous_map['mapping']
    baseline = next(row for row in old_candidates if 'baseline' in row['id'])
    revised = next(row for row in old_candidates if 'baseline' not in row['id'])
    old_rows = []
    for index, chapter in enumerate(chapters):
        if stage == 'early':
            draft_ref = previous_context['new_drafts'][index]
            draft = json.loads(bound_bytes(root, draft_ref))
            text_ref = draft['candidate']
            baseline_ref = binding(root, f'{old}/inputs/writing/baseline-ch{chapter}.md')
        else:
            row = previous_context['chapters'][index]
            assert row['chapter'] == chapter
            text_ref = row.get('new_text', row.get('text', row.get('revised_text')))
            baseline_ref = row['baseline']
            draft_ref = row.get('new_draft', row.get('draft', row.get('revised_draft')))
        # Validate all declared bindings, but do not rebind historical inputs.
        bound_bytes(root, text_ref)
        bound_bytes(root, baseline_ref)
        if draft_ref is not None:
            bound_bytes(root, draft_ref)
        old_rows.append({'chapter': chapter, 'research_text': text_ref,
                         'baseline': baseline_ref, 'draft': draft_ref})
    def sequence(refs):
        return ('\n\n'.join(bound_bytes(root, ref).decode('utf-8').rstrip() for ref in refs) + '\n').encode('utf-8')
    expected_research = sequence([row['research_text'] for row in old_rows])
    expected_baseline = sequence([row['baseline'] for row in old_rows])
    actual_research = bound_bytes(root, revised['text'])
    actual_baseline = bound_bytes(root, baseline['text'])
    # Early historical sequence has an extra final newline. Keep its actual
    # frozen bytes, require every nonterminal byte to match chapter assembly.
    assert expected_research.rstrip(b'\n') == actual_research.rstrip(b'\n')
    assert expected_baseline.rstrip(b'\n') == actual_baseline.rstrip(b'\n')
    old_boundary_observation = {
        'research_terminal_newline_count': len(actual_research) - len(actual_research.rstrip(b'\n')),
        'baseline_terminal_newline_count': len(actual_baseline) - len(actual_baseline.rstrip(b'\n')),
        'nonterminal_assembly_bytes_equal': True,
        'historical_sequence_bytes_unchanged': True,
    }
    current_rows = [selected[chapter] for chapter in chapters]
    current_ref = append_bytes(root, f'{base}/comparison/coordinator/{stage}-current-sequence-v1.txt',
                               sequence([row['candidate'] for row in current_rows]))
    # The old raw opinions and summary are preserved independently of the new packet:
    # new public paths do not automatically inherit old AgentPanel FAILs.
    summary_paths = sorted((root / old).glob(f'fullbook-{stage}-*summary*.json'))
    old_summaries = [binding(root, path.relative_to(root).as_posix()) for path in summary_paths]
    assert old_summaries, stage
    historical_opinions = []
    for directory in [root / old / 'submissions', root / previous_export['public_directory'] / '..' / 'submissions']:
        if directory.is_dir():
            for path in sorted(directory.glob(f'fullbook-{stage}-reader-*.json')):
                historical_opinions.append(binding(root, path.resolve().relative_to(root).as_posix()))
    local_readings = []
    for path in sorted((root / base / 'readings').glob('*.json')):
        # Keep all local reports as coordinator-only negative history, without
        # disclosing them to anonymous readers or treating presence as review PASS.
        local_readings.append(binding(root, path.relative_to(root).as_posix()))
    context = {
        'schema_version': 1, 'kind': 'THREE_WAY_RESEARCH_READING_CONTEXT',
        'status': 'NOT_ADOPTED_NOT_RELEASED', 'authority_effect': 'NONE',
        'chapters': chapters, 'current_selection': selection_ref,
        'current_chapters': current_rows, 'previous_context': previous_context_ref,
        'previous_chapters': old_rows, 'previous_export': export_ref,
        'previous_mapping': previous_export['mapping'], 'previous_packet': previous_export['packet'],
        'historical_reading_summaries': old_summaries,
        'historical_reader_outputs': historical_opinions,
        'local_phase6_readings_coordinator_only': local_readings,
        'assembly': 'rstrip chapter boundary whitespace only; two newlines between chapters and one terminal newline, no added version headers; internal prose unchanged.',
        'selection_effect': 'READING_ONLY_NOT_ADOPT; ch91 uses narrow v2. Original long-v1 FAILs and same-reader followup remain.',
        'source_sets': {'current': current_ref, 'previous': revised['text'], 'baseline': baseline['text']},
        'historical_boundary_observation': old_boundary_observation,
        'limitations': [
            'Descriptive literary research, not randomized controlled generation, equal resource comparison, human admission, source certification, or automatic winner.',
            'Current author contexts reused across chapters; per-chapter session labels do not create independent authors. All original previous_path values null.',
            'Historical stable baseline copy, not newly authored. Historical revised choices are explicit research versions, not adopted winners.',
            'New anonymous paths mean old panel negatives are not automatically merged by bytes. All historical negative opinions and summaries remain bound here and must be retained in final synthesis.',
            'Metadata anonymization does not prove process or file access isolation. Length, prose familiarity and chapter content may reveal identity.',
            'Author exclusion is coordinator assignment based, not generic AgentPanel author detection. Fresh reader agents must not be any current or historical author context.',
        ],
    }
    context_ref = append_bytes(root, f'{base}/comparison/coordinator/{stage}-context-v1.json', canonical_bytes(context))
    candidates = [
        {'id': f'research-current-{stage}', 'text': current_ref,
         'author_session_ids': [f'phase6-reviser-ch{chapter}-context1' for chapter in chapters] + (['main-coordinator-narrow-ch91-v2'] if 91 in chapters else [])},
        {'id': f'research-prior-{stage}', 'text': revised['text'], 'author_session_ids': revised['author_session_ids']},
        {'id': f'reference-copy-{stage}', 'text': baseline['text'], 'author_session_ids': baseline['author_session_ids']},
    ]
    exported = anonymous_export(root, f'artifacts/agent_research/reading/{opaque}-v1', candidates,
                                context=context_ref, coordinator_session_id=f'coordinator:reading-{opaque}')
    ref = append_bytes(root, f'{base}/comparison/coordinator/{stage}-export-v1.json', canonical_bytes(exported))
    reports.append({'segment': stage, 'chapters': chapters, 'context': context_ref, 'export': ref,
                    'packet': exported['packet'], 'reading_status': 'NOT_STARTED'})
    print(json.dumps({'segment': stage, 'packet': exported['packet'], 'export': ref}, ensure_ascii=False), flush=True)
print(append_bytes(root, f'{base}/comparison/coordinator/comparison-inventory-v1.json', canonical_bytes({
    'schema_version': 1, 'kind': 'THREE_WAY_PACKET_INVENTORY', 'authority_effect': 'NONE',
    'status': 'NOT_ADOPTED_NOT_RELEASED', 'segments': reports,
    'limitation': 'Preparation and byte integrity only; no reader results or automatic inheritance of historical verdicts.'})))
