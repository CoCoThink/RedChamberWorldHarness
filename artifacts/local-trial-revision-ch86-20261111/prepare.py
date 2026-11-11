"""Freeze bounded v4 packets after import; never dispatch readers."""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
BASE = 'artifacts/local-trial-revision-ch86-20261111'


def prepare(check=False):
    return runpy.run_path(str(ROOT/'artifacts/local-trial-ch86-20261110/prepare_review.py'))['prepare'](
        check=check, import_receipt=f'{BASE}/import.json', output=f'{BASE}/review',
        scenario=f'{BASE}/reading-inputs/scenario.json',
        contracts=f'{BASE}/reading-inputs/contracts')


if __name__ == '__main__':
    import sys
    print(json.dumps(prepare(check='--check' in sys.argv), ensure_ascii=False, indent=2))
