import json
from pathlib import Path

import pytest

from prepare_ch86_knowledge_v05_draft import ROOT, OUTPUT, SOURCE, build
from rcwh.knowledge import CharacterKnowledgeRuntime


def test_draft_replays_without_unsupported_entry_or_stale_suspicion():
    assert (ROOT / OUTPUT).read_bytes() == build()
    runtime = CharacterKnowledgeRuntime(ROOT, json.loads(build()))
    scene = 'ch86_last_night_v05_draft'
    assert runtime.status(scene, 'baoyu', 'daiyu_illness_severe', 'ENTRY') == 'UNSPECIFIED'
    for actor in ('baoyu', 'zijuan'):
        assert runtime.status(scene, actor, 'baoyu_may_still_arrive_in_time', None) == 'UNSPECIFIED'
    assert runtime.status(scene, 'zijuan', 'daiyu_condition_critical', 'K86-ZIJUAN-SEES-RAPID-DECLINE') == 'suspects'
    assert runtime.status(scene, 'zijuan', 'daiyu_condition_critical', 'K86-V04-DEATH-WITNESSED') == 'UNSPECIFIED'
    assert runtime.status(scene, 'zijuan', 'death_occurred', 'K86-V04-DEATH-WITNESSED') == 'knows'
    assert runtime.status(scene, 'baoyu', 'death_occurred', 'K86-V04-DEATH-WITNESSED') == 'does_not_know'
    assert runtime.status(scene, 'baoyu', 'death_occurred', None) == 'knows'


def test_draft_rejects_changed_source(tmp_path):
    source = tmp_path / SOURCE
    source.parent.mkdir(parents=True)
    source.write_text('{}')
    with pytest.raises(ValueError, match='pinned v0.4 carrier changed'):
        build(tmp_path)
