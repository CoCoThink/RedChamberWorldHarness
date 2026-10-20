"""Import staging preserves exact bytes and refuses original-input drift."""
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('snapshot_import', ROOT / 'tools/import_research_revision.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    root.mkdir()
    (root / 'text.txt').write_bytes('修订正文。\n'.encode())
    request = {'context': {'operation': 'revise', 'revision_template': 'revise-v2'},
               'parent': {'path': 'parent.json', 'sha256': 'a' * 64},
               'feedback': {'path': 'feedback.json', 'sha256': 'b' * 64}}
    (root / 'request.json').write_bytes(canonical_bytes(request))
    (root / 'fixed.json').write_bytes(b'{}')
    monkeypatch.setattr(TOOL.subprocess, 'check_output', lambda *args, **kwargs: b'text.txt\0request.json\0fixed.json')
    return root


def stub(monkeypatch, root, *, drift=False, fail=False, with_snapshot=False):
    def run(command, *, cwd=None, **kwargs):
        if command[0] == 'git':
            return SimpleNamespace(returncode=0)
        snapshot = Path(cwd)
        assert (snapshot / 'text.txt').read_bytes() == (root / 'text.txt').read_bytes()
        assert 'import_draft' in command[2]
        assert kwargs['env']['PYTHONPATH'] == str(snapshot / 'src')
        if fail:
            raise TOOL.subprocess.CalledProcessError(1, command)
        result = {'status': 'PASS'}
        for field in ('candidate', 'prepared_request', 'run', 'draft'):
            raw = canonical_bytes({'synthetic_field': field})
            relative = f'artifacts/{field}/{digest(raw)}.json'
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            result[field] = {'path': relative, 'sha256': digest(raw)}
        if with_snapshot:
            from rcwh.generation.records import binding
            from rcwh.generation.snapshots import freeze_inputs
            (snapshot / 'schemas').mkdir()
            shutil.copyfile(ROOT / 'schemas/writing_input_snapshot.schema.json', snapshot / 'schemas/writing_input_snapshot.schema.json')
            result['input_snapshot'] = freeze_inputs(snapshot, [binding(snapshot, 'text.txt')])
        (snapshot / 'snapshot-import-result.json').write_bytes(canonical_bytes(result))
        if drift:
            (root / 'fixed.json').write_bytes(b'changed')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(TOOL.subprocess, 'run', run)


def call(root):
    return TOOL.import_revision(root, 'text.txt', 'request.json', session_id='declared-reviser',
                                model_label='unverified', receipt_path='receipts/import.json')


def test_exact_outputs_copied_without_claiming_semantic_pass(inputs, monkeypatch):
    root = inputs
    stub(monkeypatch, root)
    result = call(root)
    for field in ('candidate', 'prepared_request', 'run', 'draft'):
        ref = result[field]
        assert digest((root / ref['path']).read_bytes()) == ref['sha256']
    receipt = json.loads((root / 'receipts/import.json').read_bytes())
    assert receipt['status'] == 'PASS' and receipt['changed_original_inputs'] == []
    assert len(receipt['inputs']) == 3
    assert 'literary quality' in receipt['limitation']
    with pytest.raises(FileExistsError):
        call(root)


@pytest.mark.parametrize('fault', ['drift', 'child-failure'])
def test_import_failure_copies_nothing(inputs, monkeypatch, fault):
    root = inputs
    stub(monkeypatch, root, drift=fault == 'drift', fail=fault == 'child-failure')
    with pytest.raises((ValueError, TOOL.subprocess.CalledProcessError)):
        call(root)
    assert not (root / 'artifacts').exists()
    assert not (root / 'receipts').exists()


def test_revision_mode_requires_actual_parent_and_template(inputs):
    root = inputs
    request = json.loads((root / 'request.json').read_bytes())
    request['parent'] = None
    (root / 'request.json').write_bytes(canonical_bytes(request))
    with pytest.raises(ValueError, match='actual revise-v2 parent'):
        call(root)


def test_v2_import_copies_snapshot_manifest_and_physical_blobs(inputs, monkeypatch):
    root = inputs
    stub(monkeypatch, root, with_snapshot=True)
    result = call(root)
    ref = result['input_snapshot']
    raw = (root / ref['path']).read_bytes()
    assert digest(raw) == ref['sha256']
    manifest = json.loads(raw)
    for entry in manifest['entries']:
        blob = entry['blob']
        assert digest((root / blob['path']).read_bytes()) == blob['sha256']
        assert (root / blob['path']).read_bytes() == (root / 'text.txt').read_bytes()
