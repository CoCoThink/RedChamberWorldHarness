"""Build an unadmitted draft successor to the pinned chapter-86 knowledge carrier."""
import hashlib
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/knowledge/v04_ch86.json'
SOURCE_SHA256 = 'dab6b92326cc4b006a37eb2d33913a98779fae7cae5c5ae3cac1dfb047fc9013'
OUTPUT = 'data/knowledge/v05_ch86_draft.json'


def build(root=ROOT):
    raw = (root / SOURCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('pinned v0.4 carrier changed')
    data = json.loads(raw)
    data['id'] = 'character-truth:v0.5:ch86:draft'
    scene = next(item for item in data['scenes'] if item['id'] == 'ch86_last_night_v04')
    scene['id'] = 'ch86_last_night_v05_draft'
    # The source has not established either person's entry-time belief. Leaving
    # it unspecified avoids asserting ignorance as well as unsupported belief.
    for actor in ('baoyu', 'zijuan'):
        scene['entry'][actor]['believes'].remove('baoyu_may_still_arrive_in_time')
    scene['entry']['baoyu']['knows'].remove('daiyu_illness_severe')
    # Replace the unsupported temporal claim with a separate, weaker inference.
    data['facts'].append({'id': 'daiyu_condition_critical', 'label': '黛玉病势危急',
                          'epistemic': 'CURRENT_SCENE_INFERENCE'})
    event = next(item for item in scene['events'] if item['id'] == 'K86-ZIJUAN-SEES-RAPID-DECLINE')
    event['updates'][0]['add']['suspects'] = ['daiyu_condition_critical']
    witnessed = next(item for item in scene['events'] if item['id'] == 'K86-V04-DEATH-WITNESSED')
    witness_update = next(item for item in witnessed['updates'] if item['character'] == 'zijuan')
    witness_update['remove']['suspects'] = ['daiyu_condition_critical']
    return canonical_bytes(data)


if __name__ == '__main__':
    target = ROOT / OUTPUT
    result = build()
    if target.exists() and target.read_bytes() != result:
        raise ValueError('refusing to overwrite different draft')
    target.write_bytes(result)
    print(f'wrote {OUTPUT}; semantic review and production admission remain pending')
