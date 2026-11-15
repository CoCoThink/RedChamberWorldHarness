"""Create a conservative, unadmitted successor without rewriting v0.5 evidence."""
import hashlib
import json
from pathlib import Path

from rcwh.candidate_reviews import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'data/knowledge/v05_ch86_draft.json'
SOURCE_SHA256 = '1010cd458a6e1070b25b2941e6a78cece0360fc83ec9c2c7c423f2a67523c89b'
OUTPUT = 'data/knowledge/v06_ch86_draft.json'


def build(root=ROOT):
    raw = (root / SOURCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('pinned v0.5 carrier changed')
    data = json.loads(raw)
    data['id'] = 'character-truth:v0.6:ch86:draft'
    fact = next(f for f in data['facts'] if f['id'] == 'death_physiological_detail')
    fact['label'] = '医学测量或专业判定的生理死亡细节；不含普通观察'
    scene = next(s for s in data['scenes'] if s['id'] == 'ch86_last_night_v05_draft')
    scene['id'] = 'ch86_last_night_v06_draft'
    scene['entry']['daiyu']['knows'].remove('daiyu_illness_severe')
    uncertain = {'death_precise_time', 'death_physiological_detail', 'death_medical_cause'}
    for actor in scene['entry'].values():
        actor['does_not_know'] = [fact_id for fact_id in actor['does_not_know'] if fact_id not in uncertain]
    return canonical_bytes(data)


if __name__ == '__main__':
    target = ROOT / OUTPUT
    result = build()
    if target.exists() and target.read_bytes() != result:
        raise ValueError('refusing to overwrite different draft')
    target.write_bytes(result)
    print(f'wrote {OUTPUT}; semantic review and production admission remain pending')
