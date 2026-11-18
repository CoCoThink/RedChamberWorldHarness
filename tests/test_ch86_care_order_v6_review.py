"""V6 review dispatch is gated on exact successful CI before readers are assigned."""
import json
from pathlib import Path

import pytest
import verify_ch86_care_order_v6_review as module

ROOT = Path(__file__).resolve().parents[1]


def test_v6_review_refuses_in_progress_ci_before_writing_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(module.amendment, 'verify', lambda root: None)
    monkeypatch.setattr(module.previous, 'verify', lambda root: None)
    ci = tmp_path / 'ci.json'
    ci.write_text(json.dumps({'status': 'in_progress', 'conclusion': None, 'headSha': 'not-current', 'jobs': []}))
    with pytest.raises(ValueError, match='completed successful CI'):
        module.prepare(ci, tmp_path)
    assert not (tmp_path / module.REVIEW / 'plan.json').exists()
