"""Prepare/check current source-audit reading materials offline, without opinions."""
import argparse
import json
from pathlib import Path

from rcwh.workflow.source_audit_preparation import BASE, CHECKS, documents, run

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(ROOT, args.check), ensure_ascii=False))
