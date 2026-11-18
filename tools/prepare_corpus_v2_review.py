"""Freeze or check offline human reading materials for the chapter-86 v2 corpus."""
import argparse
import json
from pathlib import Path
import socket

from rcwh.assets import AssetCatalog
from rcwh.corpus.audit import CorpusAudit
from rcwh.workflow.corpus_review_preparation import LANE, OUTPUT, materials, prepare
from rcwh.workflow.review_intake import DATASETS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--live-audit', action='store_true',
                        help='Print current audit separately; never freeze it in reading materials')
    args = parser.parse_args()
    root = args.root.resolve()

    def denied(*args, **kwargs):
        raise RuntimeError('Network forbidden during review preparation')

    socket.create_connection = socket.getaddrinfo = socket.socket.connect = socket.socket.connect_ex = denied
    result = prepare(root, args.output or root / OUTPUT, check=args.check)
    if args.live_audit:
        result['live_audit'] = CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASETS[LANE], rebuild=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
