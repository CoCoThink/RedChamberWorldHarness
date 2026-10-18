"""Snapshot evaluation preserves a failing result and refuses input drift."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('snapshot_evaluation', ROOT / 'tools/evaluate_research_snapshot.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    (tmp_path / 'request.json').write_bytes(b'{}')
    (tmp_path / 'fixed.txt').write_bytes(b'unchanged')
    monkeypatch.setattr(MODULE.subprocess, 'check_output', lambda *a, **k: b'request.json\0fixed.txt')
    return tmp_path


def child(monkeypatch, root, fault=None):
    def run(command, *, cwd=None, **kwargs):
        if command[0] == 'git':
            return SimpleNamespace(returncode=0)
        assert 'engine.evaluate(REQUEST)' in command[3]
        assert 'engine.build(' not in command[3]
        if fault == 'child':
            raise MODULE.subprocess.CalledProcessError(1, command)
        snapshot = Path(cwd)
        out = snapshot / 'results'
        out.mkdir()
        raw = canonical_bytes({'status': 'FAIL'})
        (out / 'report.json').write_bytes(raw)
        (out / 'execution.json').write_bytes(canonical_bytes({
            'status': 'FAIL', 'build_called': fault == 'build', 'stable_snapshot_unchanged': True,
            'request': {'path': 'request.json', 'sha256': digest(b'{}')},
            'report': {'path': 'results/report.json', 'sha256': digest(raw)}}))
        if fault == 'drift':
            (root / 'fixed.txt').write_bytes(b'changed')
        if fault == 'addition':
            (root / 'new.txt').write_bytes(b'new input')
            monkeypatch.setattr(MODULE.subprocess, 'check_output', lambda *a, **k: b'request.json\0fixed.txt\0new.txt')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(MODULE.subprocess, 'run', run)


def test_evaluate_fail_is_retained_without_build(inputs, monkeypatch):
    child(monkeypatch, inputs)
    result = MODULE.evaluate(inputs, 'request.json', 'results')
    assert result['status'] == 'FAIL' and result['build_called'] is False
    custody = json.loads((inputs / 'results/snapshot-custody.json').read_bytes())
    assert custody['snapshot_removed'] is True and custody['changed_original_inputs'] == []
    with pytest.raises(FileExistsError):
        MODULE.evaluate(inputs, 'request.json', 'results')


@pytest.mark.parametrize('fault', ['drift', 'addition', 'child', 'build'])
def test_no_copyback_on_drift_child_failure_or_false_execution(inputs, monkeypatch, fault):
    child(monkeypatch, inputs, fault)
    with pytest.raises((ValueError, MODULE.subprocess.CalledProcessError)):
        MODULE.evaluate(inputs, 'request.json', 'results')
    assert not (inputs / 'results').exists()


def test_linux_claim_requires_linux(inputs, monkeypatch):
    monkeypatch.setattr(MODULE.sys, 'platform', 'win32')
    with pytest.raises(ValueError, match='requires Linux'):
        MODULE.evaluate(inputs, 'request.json', 'results')
    assert not (inputs / 'results').exists()
