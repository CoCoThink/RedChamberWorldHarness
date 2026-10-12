"""API execution of frozen author tasks, separate from immutable studies."""
from __future__ import annotations

import json
from pathlib import Path

from ..candidate_reviews import canonical_bytes, digest
from .records import binding, run_task
from .render import PromptRenderer, request_for
from .runner import Budget, DEFAULT_MODEL, ModelRunner


def prepare_task(root: Path, task: dict) -> dict:
    """Task information is frozen before either workflow receives responses."""
    from .records import bound_bytes
    inputs = [item["binding"] for item in task.get("constraints", []) if "binding" in item]
    for ref in inputs:
        bound_bytes(root, ref)
    return PromptRenderer(root).render("author-v1", {
        "frozen_author_task": task,
        "output_instruction": "Return only JSON conforming to response_format. No Markdown fence.",
    }, inputs)


def execute_task(root: Path, task: dict, runner: ModelRunner, budget: Budget, *,
                 model: str = DEFAULT_MODEL) -> dict:
    rendered = prepare_task(root, task)
    result = run_task(root, runner, request_for(rendered, budget, model),
                      inputs=rendered["inputs"], template=rendered["template"], budget=budget)
    response = json.loads(result["output"])
    chapters = response["chapters"]
    if [c["chapter"] for c in chapters] != task["chapters"]:
        raise ValueError("author task chapter coverage mismatch")
    limits = task["budget"]
    for chapter in chapters:
        if not isinstance(chapter["text"], str) or not (
            limits["minimum_trial_characters_per_chapter"] <= len(chapter["text"].strip())
            <= limits["maximum_trial_characters_per_chapter"]
        ):
            raise ValueError("author task output outside frozen character budget")
    if not response.get("producer"):
        raise ValueError("author task output has no producer declaration")
    return {"status": "PASS", "scope": "AUTHOR_EXECUTION_ONLY",
            "request": task, "input_sha256": digest(canonical_bytes(task)),
            "raw_run": result["raw_run"], "response": response,
            "served_model": result["record"]["response"]["model"],
            "usage": result["record"]["usage"], "budget": budget.to_dict(),
            "literary_acceptance": "PENDING", "authority_effect": "NONE",
            "context_isolation_basis": "PROVIDER_RUN_RECORDED_NOT_PRETRAINING_ISOLATED"}
