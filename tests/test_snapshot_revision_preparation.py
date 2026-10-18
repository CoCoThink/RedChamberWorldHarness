"""Snapshot preparation refuses input drift and only copies declared new outputs."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rcwh.candidate_reviews import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('snapshot_revisions', ROOT / 'tools/prepare_research_revisions.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


@pytest.fixture
def preparation(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    root.mkdir()
    (root / 'inventory.json').write_bytes(canonical_bytes({'chapters': [{'chapter': 81}]}))
    (root / 'notes').mkdir()
    (root / 'notes/notes-ch81-v1.txt').write_text('Actual editorial notes.', encoding='utf-8')
    (root / 'input.txt').write_bytes(b'frozen inputs')
    files = ['inventory.json', 'notes/notes-ch81-v1.txt', 'input.txt']
    monkeypatch.setattr(TOOL.subprocess, 'check_output', lambda *args, **kwargs: '\0'.join(files).encode())
    return root


def execute_stub(monkeypatch, root, *, mutate=False, missing=False, fail=False):
    def run(command, *, cwd=None, **kwargs):
        if command[0] == 'git':
            return SimpleNamespace(returncode=0)
        snapshot = Path(cwd)
        assert (snapshot / 'input.txt').read_bytes() == b'frozen inputs'
        assert 'prepared_request_integrity_report' in command[2]
        assert kwargs['env']['PYTHONPATH'] == str(snapshot / 'src')
        if fail:
            raise TOOL.subprocess.CalledProcessError(1, command)
        output = snapshot / 'new-requests'
        output.mkdir()
        (output / 'ch81.json').write_bytes(b'{"request":"fixture"}\n')
        if not missing:
            (output / 'preparation-report.json').write_bytes(b'{"status":"PASS"}\n')
        if mutate:
            (root / 'input.txt').write_bytes(b'changed inputs')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(TOOL.subprocess, 'run', run)


def test_snapshot_copyback_has_exact_bytes_and_input_manifest(preparation, monkeypatch):
    root = preparation
    execute_stub(monkeypatch, root)
    TOOL.prepare(root, 'inventory.json', 'notes', 'new-requests')
    assert (root / 'new-requests/ch81.json').read_bytes() == b'{"request":"fixture"}\n'
    custody = json.loads((root / 'new-requests/snapshot-custody.json').read_bytes())
    assert custody['status'] == 'PASS' and custody['input_files'] == 3
    assert custody['changed_original_inputs'] == []
    assert custody['scope'] == 'SNAPSHOT_INPUT_AND_COPYBACK_BYTE_IDENTITY'
    assert len(custody['output_hashes']) == 2


@pytest.mark.parametrize('fault', ['drift', 'missing', 'failed-child'])
def test_snapshot_failure_never_publishes_partial_output(preparation, monkeypatch, fault):
    root = preparation
    execute_stub(monkeypatch, root, mutate=fault == 'drift', missing=fault == 'missing', fail=fault == 'failed-child')
    with pytest.raises((ValueError, TOOL.subprocess.CalledProcessError)):
        TOOL.prepare(root, 'inventory.json', 'notes', 'new-requests')
    assert not (root / 'new-requests').exists()


def test_existing_output_and_unavailable_notes_refused(preparation):
    root = preparation
    (root / 'new-requests').mkdir()
    with pytest.raises(FileExistsError):
        TOOL.prepare(root, 'inventory.json', 'notes', 'new-requests')
    with pytest.raises(ValueError, match='notes unavailable'):
        TOOL.prepare(root, 'inventory.json', 'missing-notes', 'other-requests')
