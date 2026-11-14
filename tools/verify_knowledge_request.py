"""Verify a frozen knowledge request, its projection, and all bound dependencies."""
import argparse
import json
from pathlib import Path

from rcwh.generation.knowledge_projection import verify_request


def verify(root: Path, request_path: str):
    request = verify_request(root, request_path)
    return {"status": "PASS", "request": request_path,
            "knowledge_version": request["knowledge_version"],
            "authority_effect": "NONE",
            "production_admission": request["production_admission"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve(), args.request), ensure_ascii=False, indent=2))
