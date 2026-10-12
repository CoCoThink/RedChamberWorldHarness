"""Append-only model traces and author bindings, with reproducible extraction."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..io import load_data
from ..schema import validate_instance
from .runner import Budget, ModelRunner

EXTRACTION = "CONCAT_TEXT_BLOCKS_UTF8_NO_SEPARATOR"


def binding(root: Path, relative: str) -> dict:
    return {"path": relative, "sha256": digest(repository_path(root, relative).read_bytes())}


def bound_bytes(root: Path, ref: dict) -> bytes:
    raw = repository_path(root, ref["path"]).read_bytes()
    if digest(raw) != ref["sha256"]:
        raise ValueError(f"stale generation input: {ref['path']}")
    return raw


def append_bytes(root: Path, relative: str, raw: bytes) -> dict:
    """Publish a fsynced temp file via atomic no-replace link, never overwrite."""
    path = repository_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    repository_path(root, relative)  # recheck created parent components
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".generation-", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return {"path": relative, "sha256": digest(raw)}


def store(root: Path, directory: str, value: dict) -> dict:
    raw = canonical_bytes(value)
    return append_bytes(root, f"{directory}/{digest(raw)}.json", raw)


def extract_output(response: dict) -> str:
    if response.get("stop_reason") != "end_turn":
        raise ValueError(f"incomplete/refused model response: {response.get('stop_reason')}")
    content = response.get("content")
    if not isinstance(content, list):
        raise ValueError("model content must be a list")
    pieces = []
    for block in content:
        if not isinstance(block, dict) or "type" not in block:
            raise ValueError("malformed model content block")
        if block["type"] == "text":
            if not isinstance(block.get("text"), str):
                raise ValueError("malformed model text block")
            pieces.append(block["text"])
        elif block["type"] not in {"thinking", "redacted_thinking", "fallback"}:
            raise ValueError("unexpected model output block")
    text = "".join(pieces)
    if not text.strip():
        raise ValueError("empty model output")
    return text


def verify_record(record: dict) -> str:
    schema = Path(__file__).resolve().parents[3] / "schemas/model_run.schema.json"
    errors = validate_instance(record, schema)
    if errors:
        raise ValueError("invalid raw model run: " + "; ".join(errors))
    for field in ("request", "response"):
        if digest(canonical_bytes(record[field])) != record[f"{field}_sha256"]:
            raise ValueError(f"raw model {field} identity mismatch")
    if record["usage"] != record["response"].get("usage") or record["stop_reason"] != record["response"].get("stop_reason"):
        raise ValueError("raw response metadata mismatch")
    if record["status"] != "PASS":
        raise ValueError("failed raw run cannot qualify as authored output")
    usage = record["usage"]
    for key in ("input_tokens", "output_tokens"):
        if type(usage.get(key)) is not int or usage[key] < 0:
            raise ValueError("raw model usage requires nonnegative input/output token counts")
    text = extract_output(record["response"])
    if text != record["output"] or digest(text.encode()) != record["output_sha256"]:
        raise ValueError("raw model output identity mismatch")
    budget = Budget(**record["budget"])
    budget.validate(fallback=bool(record["request"].get("fallbacks")))
    if record["request"]["max_tokens"] != budget.max_tokens:
        raise ValueError("raw request token ceiling mismatch")
    if usage["output_tokens"] > budget.max_output_tokens:
        raise ValueError("actual output usage exceeds explicit budget")
    if len(canonical_bytes(record["request"])) > budget.max_input_bytes:
        raise ValueError("raw request exceeds input byte ceiling")
    return text


def verify_raw_run(root: Path, legacy_run: dict, candidate_raw: bytes) -> None:
    """Optional strict extension for candidate_reviews.verified_author_model."""
    if "raw_run" not in legacy_run:
        return
    record = json.loads(bound_bytes(root, legacy_run["raw_run"]))
    text = verify_record(record)
    if text.encode() != candidate_raw or text != legacy_run["output"]:
        raise ValueError("raw response differs from authored candidate")
    if legacy_run["model"]["name"] != record["response"]["model"]:
        raise ValueError("author identity differs from served model")
    if legacy_run["prompt"] != record["request"]["system"] or legacy_run["input"] != canonical_bytes(record["request"]["messages"]).decode():
        raise ValueError("legacy prompt/input differs from raw request")
    for ref in record["inputs"] + [record["template"]]:
        bound_bytes(root, ref)


def run_task(root: Path, runner: ModelRunner, request: dict, *, inputs: list[dict], template: dict,
             budget: Budget) -> dict:
    """Generic Messages request hook; callers own task/response-schema semantics."""
    if request.get("fallbacks"):
        raise ValueError("provider fallbacks are not enabled in this bounded runner")
    budget.validate()
    request, inputs, template = deepcopy(request), deepcopy(inputs), deepcopy(template)
    if request.get("max_tokens") != budget.max_tokens:
        raise ValueError("request max_tokens differs from explicit budget")
    if not isinstance(request.get("system"), str) or not isinstance(request.get("messages"), list):
        raise ValueError("generation requires a system string and messages list")
    if len(canonical_bytes(request)) > budget.max_input_bytes:
        raise ValueError("request exceeds explicit input byte ceiling; no truncation performed")
    for ref in inputs + [template]:
        bound_bytes(root, ref)
    started = datetime.now(timezone.utc).isoformat()
    result = runner.run(deepcopy(request), budget)
    response = result["response"]
    try:
        output = extract_output(response)
        status, findings = "PASS", []
    except ValueError as exc:
        output, status, findings = "", "FAIL", [str(exc)]
    record = {"schema_version": 1, "kind": "MODEL_RUN", "provider": runner.provider,
              "sdk_version": runner.sdk_version, "request": request,
              "request_sha256": digest(canonical_bytes(request)), "response": response,
              "response_sha256": digest(canonical_bytes(response)), "request_id": result.get("request_id"),
              "usage": response.get("usage", {}), "stop_reason": response.get("stop_reason"),
              "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
              "template": template, "inputs": inputs, "budget": budget.to_dict(),
              "extraction": EXTRACTION, "output": output, "output_sha256": digest(output.encode()),
              "status": status, "findings": findings, "authority_effect": "NONE"}
    if status == "PASS":
        try:
            verify_record(record)
        except ValueError as exc:
            record["status"] = status = "FAIL"
            record["findings"] = findings = [str(exc)]
    raw_run = store(root, "artifacts/runs", record)
    if status != "PASS":
        raise ValueError(f"model run failed ({raw_run['path']}): " + "; ".join(findings))
    return {"raw_run": raw_run, "output": output, "record": record}


def legacy_run(result: dict, source_id: str) -> dict:
    record = result["record"]
    model = record["response"]["model"]
    prompt, actual_input = record["request"]["system"], canonical_bytes(record["request"]["messages"]).decode()
    return {"schema_version": 1, "source_id": source_id,
            "model": {"provider": "anthropic" if record["provider"] == "anthropic" else record["provider"],
                      "name": model, "version": model, "family": "claude", "session": record["response"]["id"]},
            "prompt": prompt, "prompt_sha256": digest(prompt.encode()), "prompt_summary": "Versioned writing task",
            "input": actual_input, "input_sha256": digest(actual_input.encode()),
            "output": result["output"], "output_sha256": digest(result["output"].encode()),
            "raw_run": result["raw_run"]}
