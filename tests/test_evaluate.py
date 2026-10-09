from pathlib import Path

from rcwh.evaluate import evaluate_scene_text, overall_status
from rcwh.io import load_data


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_ch86_stub_requires_attributed_semantic_reading():
    contract = load_data(root() / "data/scenes/ch86_last_night.yaml")
    text = (root() / "examples/ch86_candidate_stub.txt").read_text(encoding="utf-8")
    results = evaluate_scene_text(contract, text)
    assert overall_status(results) == "PENDING"


def test_complete_death_poem_fails():
    contract = load_data(root() / "data/scenes/ch86_last_night.yaml")
    text = "药还在。宝玉说再温一温。灯也还亮着。她随后写下一首绝命诗。"
    results = evaluate_scene_text(contract, text)
    assert next(r for r in results if r.evaluator == "lint:forbidden_beats").status == "WARN"
    assert overall_status(results) == "PENDING"
