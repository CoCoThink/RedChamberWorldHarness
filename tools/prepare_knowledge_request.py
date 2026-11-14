"""Create an immutable versioned knowledge projection and bind one task to it."""
import argparse
import json
from pathlib import Path

from rcwh.generation.knowledge_projection import create, prepare_request
from rcwh.io import load_data


def prepare(root: Path, task_path: str, *, version: str, scene_id: str,
            checkpoints: list[str]):
    task = load_data(root / task_path)
    projection = create(root, version=version, scene_id=scene_id,
                        checkpoints=checkpoints)
    request = prepare_request(root, projection_path=projection["projection"]["path"],
                              task=task)
    return {"projection": projection, "request": request,
            "authority_effect": "NONE", "production_admission": "NOT_GRANTED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--task", required=True, help="repository-relative task JSON")
    parser.add_argument("--version", required=True)
    parser.add_argument("--scene", required=True)
    parser.add_argument("--checkpoint", action="append", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root.resolve(), args.task, version=args.version,
                             scene_id=args.scene, checkpoints=args.checkpoint),
                     ensure_ascii=False, indent=2))
