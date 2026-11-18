"""Prepare or check a bounded, lossless research review partition; no model calls."""
import argparse
import json
from pathlib import Path

from rcwh.generation.scope_review import check, prepare


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--prepared')
    parser.add_argument('--export-receipt')
    parser.add_argument('--output')
    parser.add_argument('--check', metavar='DIRECTORY')
    parser.add_argument('--max-file-bytes',type=int,default=65536)
    parser.add_argument('--max-task-bytes',type=int,default=131072)
    parser.add_argument('--overhead-bytes',type=int,default=16384)
    parser.add_argument('--output-bytes',type=int,default=8192)
    args = parser.parse_args()
    if args.check:
        result=check(args.root.resolve(),args.check)
    else:
        if not all((args.prepared,args.export_receipt,args.output)):
            parser.error('--prepared, --export-receipt and --output are required')
        result=prepare(args.root.resolve(),args.prepared,args.export_receipt,args.output,
                       max_file_bytes=args.max_file_bytes,max_task_bytes=args.max_task_bytes,
                       overhead_bytes=args.overhead_bytes,output_bytes=args.output_bytes)
    print(json.dumps(result,ensure_ascii=False,indent=2))
