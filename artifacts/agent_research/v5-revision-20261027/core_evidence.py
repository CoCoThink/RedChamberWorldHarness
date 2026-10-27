"""Validate actual core evidence; unresolved handoff never authorizes adoption."""
import json

from rcwh.generation.records import bound_bytes


OBLIGATIONS = {
    'MARRIAGE_DECISION': {87},
    'DETENTION_CAUSE': {92},
    'VERSE_PLACEMENT': {93},
}


def validate_core(root, current, *, unresolved_handoff=False, chapters=None):
    core = json.loads((current / 'core-causal-rulings.json').read_bytes())
    issues = core['issues']
    if len(issues) != 3 or {x['issue_id'] for x in issues} != OBLIGATIONS.keys():
        raise ValueError('all three core obligations require explicit evidence')
    directories = [current]
    context_previous = root / 'artifacts/agent_research/v4-context-followup-20261026'
    if context_previous.exists() and context_previous != current:
        directories.append(context_previous)
    previous = root / 'artifacts/agent_research/v4-risk-revision-20261026'
    if previous.exists() and previous != current:
        directories.append(previous)
    registered = {json.loads(p.read_bytes())['record']['sha256']
                  for directory in directories for p in directory.glob('registration-*.json')}
    root_read = {json.loads(line)['record']['sha256']
                 for directory in directories
                 for line in (directory / 'coordinator-notes-read.jsonl').read_text().splitlines()
                 if json.loads(line)['scope'] == 'ALL_RESULT_NOTES_AND_SAMPLE_CHECKS_READ_BY_COORDINATOR'}
    request_path = root / 'data/agent_release/research-81-100-v5/request.json'
    rows = {r['chapter']: r for r in json.loads(request_path.read_bytes())['chapters']} if request_path.exists() else None
    unresolved = set()
    for issue in issues:
        if type(issue['unresolved_same_gap']) is not bool:
            raise ValueError('explicit boolean core disposition required')
        if issue['unresolved_same_gap']:
            unresolved.update(OBLIGATIONS[issue['issue_id']])
        readers = set()
        for evidence in issue['fresh_formal_evidence']:
            digest = evidence['record']['sha256']
            if digest not in registered & root_read:
                raise ValueError('core evidence must be fresh, registered and root-read')
            opinion = json.loads(bound_bytes(root, evidence['record']))['opinion']
            if rows is not None and opinion['packet'] not in [rows[ch]['panel']['packet'] for ch in OBLIGATIONS[issue['issue_id']]]:
                raise ValueError('core evidence must match the selected current chapter packet')
            readers.add(opinion['reviewer']['id'])
            result = next(x for x in opinion['results'] if x['subject_id'] == evidence['subject_id'])
            quote = evidence['quote_from_notes']
            if not quote.strip() or quote not in result['notes'] or not evidence['interpretation'].strip():
                raise ValueError('exact reader quotation and root interpretation required')
            if result['verdict'] != 'PASS' and not (result['verdict'] == 'FAIL' and result.get('severity') == 'ADVISORY'):
                raise ValueError('incomplete or blocking results cannot establish this disposition')
        if len(readers) < 2:
            raise ValueError('two distinct fresh formal readers required per core obligation')
    if unresolved_handoff:
        if not unresolved or core['status'] != 'UNRESOLVED_RESEARCH_HANDOFF':
            raise ValueError('unresolved handoff requires actual unresolved core evidence')
        if chapters is not None and any(chapters[str(ch)]['outcome'] != 'PENDING' for ch in unresolved):
            raise ValueError('unresolved core chapters must remain PENDING; adoption forbidden')
    elif unresolved or core['status'] != 'CLOSED_BY_ACTUAL_NEW_READER_EVIDENCE':
        raise ValueError('core closure requires actual new-reader evidence; no coordinator override')
    return core, unresolved
