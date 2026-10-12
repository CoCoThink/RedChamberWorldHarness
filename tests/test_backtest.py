"""Offline fixtures; never invent production authors, facts, or reviewer attestations."""
import argparse
import copy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.application import backtest as cli
from rcwh.assets import AssetCatalog
from rcwh.backtest import corpus as bc
from rcwh.backtest.observations import overlap_observations
from rcwh.backtest.study import BacktestStudy, HOLDOUT_PATH
from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluation import style_reference as sr
from rcwh.generation.records import run_task
from rcwh.generation.runner import Budget, ReplayRunner

ROOT = Path(__file__).resolve().parents[1]


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return {"path": name, "sha256": digest(path.read_bytes())}


@pytest.fixture
def study(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    config = json.loads((ROOT / HOLDOUT_PATH).read_bytes())
    config["budget"].update(max_output_tokens_per_request=64, minimum_characters=1, maximum_characters=1000,
                            max_total_tokens_per_sample=1000, revision_reserve_tokens=400)
    for key in ("shared_task", "world"):
        value = json.loads((ROOT / config[key]["path"]).read_bytes())
        if key == "shared_task":
            value.update(plan_summary="", events=[], source_refs=[])
        else:
            value["facts"] = []
        config[key] = write(tmp_path, config[key]["path"], value)
    rows = [{"record_type": "SEGMENT", "dataset_ref": config["dataset_ref"], "segment_id": f"segment-{chapter}",
             "chapter": chapter, "kind": "MAIN_TEXT", "text": "原文秘密不入提示" if chapter >= 79 else "了甲“的乙”",
             "asset_ref": config["edition_asset_ref"]} for chapter in range(1, 81)]
    for row in rows:
        row["text_sha256"] = digest(row["text"].encode())
    manifest = {"dataset_ref": config["dataset_ref"], "readiness": "CANDIDATE_PENDING_HUMAN_AUDIT",
                "build_config": {"document": {"chapters": list(range(1, 81))}}}
    raw = canonical_bytes(manifest)
    (tmp_path / "manifest.json").write_bytes(raw)
    ref = "asset:sha256:" + digest(raw)
    config["manifest_sha256"] = digest(raw)
    binding = {"manifest_ref": ref, "manifest_sha256": digest(raw)}
    catalog = AssetCatalog(tmp_path, {ref: {"path": "manifest.json", "sha256": digest(raw), "bytes": len(raw)}}, {})
    state = {"rows": rows, "binding": binding, "calls": []}
    monkeypatch.setattr(bc.AssetCatalog, "from_repo", classmethod(lambda cls, root: catalog))
    monkeypatch.setattr(sr.AssetCatalog, "from_repo", classmethod(lambda cls, root: catalog))
    monkeypatch.setattr(bc.CorpusRepository, "registry", lambda self: {config["dataset_ref"]: state["binding"]})
    def load(self, dataset_ref, *, rebuild=True):
        state["calls"].append(rebuild)
        products = {"segments.jsonl": b"\n".join(canonical_bytes(row).strip() for row in [{"record_type": "FILE_SCOPE", "dataset_ref": dataset_ref}, *state["rows"]])}
        for chapter in range(1, 81):
            selected = [row for row in state["rows"] if row["chapter"] == chapter and row["kind"] == "MAIN_TEXT"]
            products[f"chapters/ch{chapter:02d}.json"] = canonical_bytes({"dataset_ref": dataset_ref, "chapter": chapter, "segment_refs": [row["segment_id"] for row in selected], "text": "".join(row["text"] for row in selected)})
        return manifest, products
    monkeypatch.setattr(bc.CorpusRepository, "load", load)
    monkeypatch.setattr(sr.CorpusAudit, "summary", lambda self, dataset_ref, rebuild=True: {"status": "PENDING", "findings": [{"notes": "原文秘密不入提示"}], "authority_effect": "NONE"})
    write(tmp_path, HOLDOUT_PATH, config)
    return BacktestStudy(tmp_path), state


def test_prepare_shared_task_budget_and_no_target_leak(study, tmp_path):
    backtest, state = study
    direct, harness = backtest.author_task("DIRECT"), backtest.author_task("HARNESS")
    assert direct["shared"] == harness["shared"]
    assert direct["shared_information_sha256"] == harness["shared_information_sha256"]
    assert direct["workflow_support"] is None
    assert "原文秘密不入提示" not in json.dumps(harness, ensure_ascii=False)
    assert harness["workflow_support"]["style_reference"]["chapter_count"] == 78
    report = backtest.prepare(tmp_path / "prepared")
    assert report["controlled_workflow_effect"] == "NOT_ESTIMABLE"
    assert report["task_complete"] is False
    assert set((tmp_path / "prepared").iterdir()) == {tmp_path / "prepared" / name for name in ("direct-task.json", "harness-task.json", "preparation.json")}
    assert not any(state["calls"])
    with pytest.raises(FileExistsError):
        backtest.prepare(tmp_path / "prepared")


@pytest.mark.parametrize("mutation, message", [
    (lambda rows: rows.append(copy.deepcopy(rows[0])), "DUPLICATE_SEGMENT"),
    (lambda rows: rows[0].update(text_sha256="0" * 64), "STALE_SEGMENT_SHA"),
    (lambda rows: rows[78].update(asset_ref="another-edition"), "MIXED_EDITION"),
])
def test_corrupt_rows_fail_closed(study, mutation, message):
    backtest, state = study
    mutation(state["rows"])
    with pytest.raises(ValueError, match=message):
        backtest.check()


def test_stale_manifest_and_holdout_exemplar_fail(study):
    backtest, state = study
    state["binding"]["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="STALE_MANIFEST"):
        backtest.check()
    state["binding"]["manifest_sha256"] = backtest.data["manifest_sha256"]
    backtest.data["exemplar_segment_ids"] = ["segment-79"]
    with pytest.raises(ValueError, match="HELDOUT_RETRIEVAL"):
        backtest.check()


def test_overlap_is_observation_not_threshold_verdict():
    report = overlap_observations("甲，乙丙", "甲乙丙丁", n=2)
    assert report["normalized_han"]["fraction"] == 1
    assert report["exact"]["fraction"] == pytest.approx(1 / 3)
    assert report["verdict"] is None and report["model_pretraining_exposure"] == "UNKNOWN"
    assert overlap_observations("", "甲", n=8)["exact"]["fraction"] is None


def make_runs(backtest):
    root = backtest.root
    inputs = [backtest.data["shared_task"], backtest.data["world"]]
    template = write(root, "fixture-template.json", {"fixture": True})
    samples = []
    for workflow in ("DIRECT", "HARNESS"):
        for sample_id in ("one", "two"):
            rounds, previous = [], None
            for position in range(2 if workflow == "HARNESS" else 1):
                text = f"样本{workflow}{sample_id}{position}甲乙丙丁"
                request = backtest.request(workflow) if position == 0 else backtest.revision_request(workflow, previous, "调整章法")
                response = {"id": f"fixture-{workflow}-{sample_id}-{position}", "model": backtest.data["budget"]["model"],
                            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 10}}
                run = run_task(root, ReplayRunner([response]), request, inputs=inputs, template=template, budget=Budget(max_tokens=64, max_output_tokens=64))
                round_record = {"raw_run": run["raw_run"]}
                if position:
                    round_record["feedback"] = write(root, f"feedback-{workflow}-{sample_id}.json", {"qualification": "FEEDBACK_ONLY", "candidate_sha256": digest(previous.encode()), "text": "调整章法"})
                rounds.append(round_record)
                previous = text
            path = root / f"{workflow}-{sample_id}.txt"
            path.write_text(previous)
            samples.append({"workflow": workflow, "sample_id": sample_id, "rounds": rounds, "text": {"path": path.name, "sha256": digest(path.read_bytes())}})
    write(root, "runs.json", {"schema_version": 1, "context_sha256": backtest.check()["context_sha256"], "samples": samples,
                              "authors": [{"principal_id": "fixture-author", "source_id": "fixture-author-source"}], "authority_effect": "NONE"})
    return samples


def test_replay_export_and_summary_never_claim_actual_effect(study, tmp_path):
    backtest, _ = study
    make_runs(backtest)
    backtest.export(tmp_path / "export", "runs.json")
    packet = json.loads((tmp_path / "export/public/packet.json").read_bytes())
    assert len(packet["candidates"]) == 5 and packet["recognition_required"]
    template = json.loads((tmp_path / "export/public/reading-template.json").read_bytes())
    assert all(row["recognized_original"] is None for row in template["recognition"].values())
    report = backtest.summary("runs.json", tmp_path / "export")
    assert report["controlled_workflow_effect"] == "NOT_ESTIMABLE"
    assert report["valid_independent_review_count"] == 0
    assert report["budget_verification"] == "REPLAY_OR_UNVERIFIED_EXECUTION_ONLY"
    assert report["automatic_winner"] is None


def test_stale_candidate_and_duplicate_raw_run_rejected(study):
    backtest, _ = study
    samples = make_runs(backtest)
    (backtest.root / samples[0]["text"]["path"]).write_text("tampered")
    with pytest.raises(ValueError, match="STALE_SAMPLE_TEXT"):
        backtest.summary("runs.json")


def test_duplicate_raw_runs_and_budget_reserves_fail_closed(study):
    backtest, _ = study
    samples = make_runs(backtest)
    registry = json.loads((backtest.root / "runs.json").read_bytes())
    registry["samples"][1]["rounds"][0] = samples[0]["rounds"][0]
    write(backtest.root, "runs.json", registry)
    with pytest.raises(ValueError, match="DUPLICATE_RAW_RUN"):
        backtest.summary("runs.json")
    registry["samples"][1]["rounds"][0] = samples[1]["rounds"][0]
    raw_binding = registry["samples"][2]["rounds"][0]["raw_run"]
    raw_run = json.loads((backtest.root / raw_binding["path"]).read_bytes())
    raw_run["usage"]["input_tokens"] = 700
    raw_run["response"]["usage"]["input_tokens"] = 700
    raw_run["response_sha256"] = digest(canonical_bytes(raw_run["response"]))
    registry["samples"][2]["rounds"][0]["raw_run"] = write(backtest.root, raw_binding["path"], raw_run)
    write(backtest.root, "runs.json", registry)
    with pytest.raises(ValueError, match="REVISION_RESERVE_EXCEEDED"):
        backtest.summary("runs.json")


def fixture_review(backtest, export_root, identity):
    packet = json.loads((export_root / "public/packet.json").read_bytes())
    template = json.loads((export_root / "public/reading-template.json").read_bytes())
    template.update(report_kind="REVIEW_OPINION", id=identity, recommendation="NEITHER")
    template["reviewer"].update(principal_id=identity, source_id=identity + "-source", mapping_unseen_during_review=True, independent_of_authors=True)
    template["ranking"] = [[row["token"] for row in packet["candidates"]]]
    for candidate in packet["candidates"]:
        token = candidate["token"]
        text = (export_root / "public" / candidate["file"]).read_text()
        for dimension in template["observations"][token].values():
            dimension.update(reason="Synthetic test fixture only", spans=[{"start": 0, "end": 1, "quote": text[:1]}])
        template["recognition"][token] = {"recognized_original": False, "familiarity": "UNFAMILIAR", "reason": "Synthetic fixture, not real reader validation"}
    raw = write(backtest.root, identity + "-raw.json", template)
    return write(backtest.root, identity + "-receipt.json", {**template, "raw_review": raw})


def test_two_reader_validation_raw_binding_and_recognition(study, tmp_path):
    backtest, _ = study
    make_runs(backtest)
    export_root = tmp_path / "export"
    backtest.export(export_root, "runs.json")
    reviews = [fixture_review(backtest, export_root, identity) for identity in ("fixture-reader-a", "fixture-reader-b")]
    report = backtest.summary("runs.json", export_root, reviews)
    assert report["valid_independent_review_count"] == 2
    assert len(report["paired_observations"]) == 2
    assert report["controlled_workflow_effect"] == "NOT_ESTIMABLE"  # Replay fixtures are never actual runs.
    with pytest.raises(ValueError, match="DUPLICATE_REVIEWER"):
        backtest.summary("runs.json", export_root, [reviews[0], reviews[0]])
    receipt = json.loads((backtest.root / reviews[0]["path"]).read_bytes())
    receipt["recognition"] = {}
    changed = write(backtest.root, reviews[0]["path"], receipt)
    with pytest.raises(ValueError, match="RECOGNITION_INCOMPLETE"):
        backtest.summary("runs.json", export_root, [changed])
    receipt["recognition"] = json.loads((backtest.root / receipt["raw_review"]["path"]).read_bytes())["recognition"]
    receipt["recommendation"] = "CONTINUE"
    changed = write(backtest.root, reviews[0]["path"], receipt)
    with pytest.raises(ValueError, match="RAW_BINDING_MISMATCH"):
        backtest.summary("runs.json", export_root, [changed])


def test_cli_adapter_summary_pending_and_fail_closed(study, capsys):
    backtest, _ = study
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    cli.add_commands(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(["--root", str(backtest.root), "backtest", "summary"])
    assert args.func(args) == 2
    assert json.loads(capsys.readouterr().out)["controlled_workflow_effect"] == "NOT_ESTIMABLE"
    args = parser.parse_args(["--root", str(backtest.root), "backtest", "check", "--config", "../outside"])
    assert args.func(args) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"
