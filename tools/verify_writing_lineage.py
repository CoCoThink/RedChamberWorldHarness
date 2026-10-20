"""Verify selected chapter histories separately from current writing inputs.

Optional migration appends snapshots only after the original v1 checks pass.
No requests, drafts, review opinions or release selections are rewritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.dataset import rebuild_scope
from rcwh.generation.lineage import current_compatibility, freeze_history
from rcwh.generation.records import append_bytes, bound_bytes
from rcwh.generation.writing import load_draft


def verify(root: Path, request_path: str, *, migrate: bool = False, current: bool = True) -> dict:
    request = json.loads(repository_path(root, request_path).read_bytes())
    rows = []
    with rebuild_scope():
        for row in request['chapters']:
            if row['mode'] != 'AGENT_CANDIDATE':
                continue
            result = {'chapter': row['chapter'], 'draft': row['draft'], 'historical_integrity': {'status': 'FAIL'}}
            try:
                bound_bytes(root, row['draft'])
                if migrate:
                    result['migration'] = freeze_history(root, row['draft']['path'])
                draft, text = load_draft(root, row['draft']['path'])
                if (draft['chapter'] != row['chapter'] or draft['candidate'] != row['candidate']
                        or text.encode('utf-8') != bound_bytes(root, row['candidate'])):
                    raise ValueError('selected release candidate differs from its historical draft')
                result['historical_integrity'] = {'status': 'PASS'}
                if current:
                    result['current_compatibility'] = current_compatibility(root, row['draft']['path'])
            except (OSError, KeyError, TypeError, ValueError) as exc:
                result['historical_integrity']['findings'] = [str(exc)]
            rows.append(result)
    passed = bool(rows) and all(row['historical_integrity']['status'] == 'PASS'
                                and row.get('current_compatibility', {'status': 'PASS'})['status'] == 'PASS'
                                for row in rows)
    return {'status': 'PASS' if passed else 'FAIL', 'scope': 'SELECTED_WRITING_LINEAGES',
            'request': request_path, 'chapters': rows, 'authority_effect': 'NONE',
            'limitation': 'Custody and input compatibility only; no literary, human or publication qualification.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--request', default='data/agent_release/research-81-100-v1/request.json')
    parser.add_argument('--freeze-history', action='store_true')
    parser.add_argument('--history-only', action='store_true')
    parser.add_argument('--output', help='Append a new repository-relative report')
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify(root, args.request, migrate=args.freeze_history, current=not args.history_only)
    if args.output:
        append_bytes(root, args.output, canonical_bytes(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
