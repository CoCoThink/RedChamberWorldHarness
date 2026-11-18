import json
from pathlib import Path

import pytest

from prepare_ch86_knowledge_v06_draft import ROOT, OUTPUT, SOURCE, build
from rcwh.knowledge import CharacterKnowledgeRuntime


def test_review_findings_are_represented_without_inventing_ignorance():
    raw = build()
    assert (ROOT / OUTPUT).read_bytes() == raw
    data = json.loads(raw)
    runtime = CharacterKnowledgeRuntime(ROOT, data)
    scene = 'ch86_last_night_v06_draft'
    assert runtime.status(scene, 'daiyu', 'daiyu_illness_severe', 'ENTRY') == 'UNSPECIFIED'
    for actor in ('baoyu', 'zijuan', 'daiyu'):
        for fact in ('death_precise_time', 'death_physiological_detail', 'death_medical_cause'):
            for point in ('ENTRY', 'K86-V04-DEATH-WITNESSED', 'K86-V04-BAOYU-LEARNS-DEATH-ACCOUNT'):
                assert runtime.status(scene, actor, fact, point) == 'UNSPECIFIED'
    assert runtime.status(scene, 'zijuan', 'death_occurred', 'K86-V04-DEATH-WITNESSED') == 'knows'
    assert runtime.status(scene, 'baoyu', 'death_occurred', 'K86-V04-DEATH-WITNESSED') == 'does_not_know'
    assert runtime.status(scene, 'baoyu', 'death_relative_account', None) == 'knows'
    assert '不含普通观察' in next(f['label'] for f in data['facts'] if f['id'] == 'death_physiological_detail')


def test_changed_v05_cannot_silently_change_successor(tmp_path):
    source = tmp_path / SOURCE
    source.parent.mkdir(parents=True)
    source.write_text('{}')
    with pytest.raises(ValueError, match='pinned v0.5 carrier changed'):
        build(tmp_path)
