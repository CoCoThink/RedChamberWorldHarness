"""Blocker resolution is an honest archive, not a release bypass."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/agent_research/phase6/advancement'


def test_blocker_matrix_preserves_external_and_user_selected_blockers():
    text = (BASE / 'blocker-resolution-v1.md').read_text(encoding='utf-8')
    for phrase in (
        'NOT_ADOPTED_NOT_RELEASED',
        '保留FAIL',
        'PENDING_EXTERNAL_EVIDENCE',
        '95→96',
        '不build、不commit、不push、不改stable',
        'source',
        'Corpus human acceptance',
    ):
        assert phrase in text


def test_final_evaluation_still_fails_without_build():
    execution = json.loads((BASE / 'final-evaluation-v1/execution.json').read_bytes())
    report = json.loads((BASE / 'final-evaluation-v1/report.json').read_bytes())
    assert execution['status'] == report['status'] == 'FAIL'
    assert execution['build_called'] is False
    assert execution['stable_snapshot_unchanged'] is True
    assert report['output']['text'] is None
