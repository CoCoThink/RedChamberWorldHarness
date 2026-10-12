"""Offline author execution does not mutate frozen studies or qualify reviews."""
import json
from pathlib import Path
import shutil

import pytest

from rcwh.generation.runner import Budget, ReplayRunner
from rcwh.generation.tasks import execute_task, prepare_task

ROOT = Path(__file__).resolve().parents[1]


def task():
    return {"kind": "FROZEN_AUTHOR_TASK", "chapters": [85, 86, 87],
            "budget": {"minimum_trial_characters_per_chapter": 1,
                       "maximum_trial_characters_per_chapter": 100},
            "response_format": {"chapters": []}}


def setup(tmp_path):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    shutil.copytree(ROOT / "data/writing/prompts", tmp_path / "data/writing/prompts")
    return tmp_path


def response(chapters=None):
    return {"id": "fixture:model:response", "model": "fixture-model", "stop_reason": "end_turn",
            "content": [{"type": "text", "text": json.dumps({
                "chapters": chapters or [{"chapter": c, "text": "合成示例。"} for c in [85, 86, 87]],
                "producer": "fixture-only"})}],
            "usage": {"input_tokens": 10, "output_tokens": 40}}


def test_frozen_task_api_records_response_and_actual_usage(tmp_path):
    root = setup(tmp_path)
    original = task()
    assert prepare_task(root, original)["task"]["frozen_author_task"] == original
    result = execute_task(root, original, ReplayRunner([response()]), Budget())
    assert result["usage"]["output_tokens"] == 40
    assert result["literary_acceptance"] == "PENDING"
    assert result["response"]["producer"] == "fixture-only"
    assert (root / result["raw_run"]["path"]).is_file()
    assert not (root / "data/evaluation").exists()


def test_wrong_author_task_output_retains_raw_run_not_qualifying_output(tmp_path):
    root = setup(tmp_path)
    with pytest.raises(ValueError, match="coverage mismatch"):
        execute_task(root, task(), ReplayRunner([response([{"chapter": 99, "text": "fixture"}])]), Budget())
    assert len(list((root / "artifacts/runs").glob("*.json"))) == 1
