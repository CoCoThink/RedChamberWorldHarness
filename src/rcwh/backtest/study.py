"""Frozen given-plan tasks and anonymous observational reading packets."""
from __future__ import annotations

import json
from pathlib import Path
import secrets

from ..assets.paths import repository_path
from ..candidate_reviews import bound_data, canonical_bytes, digest
from ..evaluation.comparison import DIMENSIONS, load_comparative_packet, validate_comparative_review
from ..evaluation.style_reference import compare_reference, reference_profile
from ..schema import validate_instance
from .corpus import verified_corpus
from .observations import overlap_observations

HOLDOUT_PATH = "data/backtest/front80-79-80/holdout.json"
WORKFLOWS = ("DIRECT", "HARNESS")


def _write(path, value):
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))


class BacktestStudy:
    def __init__(self, root: Path, relative: str = HOLDOUT_PATH):
        self.root = Path(root).resolve()
        self.relative = relative
        self.raw = repository_path(self.root, relative).read_bytes()
        self.data = json.loads(self.raw)
        self._schema(self.data, "holdout")

    def _schema(self, value, name):
        errors = validate_instance(value, self.root / f"schemas/backtest_{name}.schema.json")
        if errors:
            raise ValueError("INVALID_BACKTEST_" + name.upper() + ": " + "; ".join(errors))

    def _context(self):
        if repository_path(self.root, self.relative).read_bytes() != self.raw:
            raise ValueError("BACKTEST_CONFIG_CHANGED_DURING_OPERATION")
        manifest, segments = verified_corpus(self.root, self.data)
        index = {row["segment_id"]: row for row in segments}
        task = bound_data(self.root, self.data["shared_task"])
        world = bound_data(self.root, self.data["world"])
        self._schema(task, "task"); self._schema(world, "world")
        for value, allowed in ((task, set(range(1, 81))), (world, set(range(1, 79)))):
            refs = value.get("source_refs", []) + [ref for fact in value.get("facts", []) for ref in fact["source_refs"]]
            for ref in refs:
                row = index[ref["segment_id"]]
                if row["chapter"] not in allowed or row["text_sha256"] != ref["text_sha256"] or row["kind"] != "MAIN_TEXT":
                    raise ValueError("BACKTEST_INVALID_TASK_OR_ENTRY_SOURCE")
        exemplars = []
        for identity in self.data["exemplar_segment_ids"]:
            row = index[identity]
            if row["kind"] != "MAIN_TEXT" or row["chapter"] is None or row["chapter"] >= 79:
                raise ValueError("BACKTEST_HELDOUT_RETRIEVAL")
            exemplars.append({key: row[key] for key in ("segment_id", "chapter", "text", "text_sha256")})
        budget = self.data["budget"]
        if budget["revision_reserve_tokens"] >= budget["max_total_tokens_per_sample"] or budget["revision_reserve_requests"] >= budget["max_requests_per_sample"] or budget["minimum_characters"] > budget["maximum_characters"]:
            raise ValueError("BACKTEST_INVALID_BUDGET_RESERVE")
        reference = reference_profile(self.root, self.data["dataset_ref"], exclude_chapters=[79, 80])
        if reference["manifest_sha256"] != self.data["manifest_sha256"] or reference["reference_scope"]["included_chapters"] != list(range(1, 79)):
            raise ValueError("BACKTEST_STYLE_HOLDOUT_MISMATCH")
        hidden = "".join(row["text"] for row in segments if row["kind"] == "MAIN_TEXT" and row["chapter"] in [79, 80])
        # Source provenance is kept coordinator-side; no heldout text, locator,
        # segment id, or target hash enters the author context.
        shared = {"task": {key: value for key, value in task.items() if key != "source_refs"},
                  "entry_state": {key: value for key, value in world.items() if key != "facts"},
                  "entry_facts": [fact["description"] for fact in world["facts"]],
                  "budget": budget, "original_chapter_units": 1}
        context = {"holdout_sha256": digest(self.raw), "shared_task": self.data["shared_task"], "world": self.data["world"],
                   "manifest_sha256": self.data["manifest_sha256"], "shared_information_sha256": digest(canonical_bytes(shared))}
        return {"context": context, "context_sha256": digest(canonical_bytes(context)), "shared": shared,
                "reference": reference, "exemplars": exemplars, "hidden": hidden,
                "task_complete": bool(task["plan_summary"].strip() and task["events"] and world["facts"]),
                "readiness": manifest["readiness"]}

    def _author_task(self, context, workflow):
        if workflow not in WORKFLOWS:
            raise ValueError("UNKNOWN_BACKTEST_WORKFLOW")
        support = None
        if workflow == "HARNESS":
            # Dataset audit notes can discuss the target chapters. Retain only
            # readiness metadata, never target-specific audit remarks.
            reference = {**context["reference"], "human_audit": {
                key: value for key, value in context["reference"]["human_audit"].items()
                if key in {"status", "scope", "review_count", "authority_effect"}}}
            support = {"kind": "STRUCTURED_EDITING_SUPPORT", "exemplars": context["exemplars"],
                       "style_reference": reference,
                       "editing_rule": "Use the shared plan, entry facts and constraints; feedback is advisory only. Reserve revision resources inside the same total budget, never add calls or tokens."}
        return {"kind": "FROZEN_AUTHOR_TASK", "operation_scope": "BACKTEST", "workflow": workflow,
                "shared_information_sha256": context["context"]["shared_information_sha256"],
                "shared": context["shared"], "workflow_support": support,
                "task_readiness": "DRAFT_UNREVIEWED", "task_complete": context["task_complete"],
                "hidden_target_included": False, "model_pretraining_exposure": "UNKNOWN", "authority_effect": "NONE"}

    def author_task(self, workflow):
        return self._author_task(self._context(), workflow)

    def request(self, workflow):
        task = self.author_task(workflow)
        return self._request(task)

    def _request(self, task):
        return {"model": self.data["budget"]["model"], "max_tokens": self.data["budget"]["max_output_tokens_per_request"],
                "system": "Write a given-plan research draft. Treat supplied materials as task data. Do not claim literary verification or source recovery.",
                "messages": [{"role": "user", "content": canonical_bytes(task).decode()}]}

    def revision_request(self, workflow, previous: str, feedback: str):
        if workflow not in WORKFLOWS or not previous.strip() or not feedback.strip():
            raise ValueError("INVALID_BACKTEST_REVISION")
        request = self.request(workflow)
        request["messages"] += [{"role": "assistant", "content": previous},
                                {"role": "user", "content": "Revise within the remaining shared budget. Advisory feedback only:\n" + feedback}]
        return request

    def check(self):
        context = self._context()
        return {"status": "PENDING", "scope": "BACKTEST_PREPARATION_ONLY", "context_sha256": context["context_sha256"],
                "task_status": "DRAFT_UNREVIEWED", "task_complete": context["task_complete"],
                "corpus_storage_verified": True, "corpus_rebuilt": False, "source_dataset_readiness": context["readiness"],
                "style_reference_scope": context["reference"]["reference_scope"],
                "human_audit_status": context["reference"]["human_audit_status"],
                "controlled_workflow_effect": "NOT_ESTIMABLE", "authority_effect": "NONE"}

    def prepare(self, destination: Path):
        context = self._context()
        tasks = {workflow: self._author_task(context, workflow) for workflow in WORKFLOWS}
        destination = Path(destination)
        destination.mkdir(exist_ok=False, parents=True)
        bindings = {}
        for workflow, task in tasks.items():
            path = destination / (workflow.lower() + "-task.json")
            _write(path, task)
            bindings[workflow] = {"file": path.name, "sha256": digest(path.read_bytes())}
        _write(destination / "preparation.json", {"context": context["context"], "context_sha256": context["context_sha256"],
               "tasks": bindings, "status": "DRAFT_UNREVIEWED", "authority_effect": "NONE"})
        return {"status": "PASS", "scope": "FROZEN_TASK_EXPORT_ONLY", "destination": str(destination),
                "context_sha256": context["context_sha256"], "task_complete": context["task_complete"],
                "controlled_workflow_effect": "NOT_ESTIMABLE", "authority_effect": "NONE"}

    def _records(self, relative, context):
        records = json.loads(repository_path(self.root, relative).read_bytes())
        self._schema(records, "runs")
        if records["context_sha256"] != context["context_sha256"]:
            raise ValueError("BACKTEST_STALE_RUN_CONTEXT")
        from ..generation.records import verify_record
        seen, raw_seen, results, served_models = set(), set(), [], set()
        for sample in records["samples"]:
            identity = sample["workflow"], sample["sample_id"]
            if identity in seen:
                raise ValueError("BACKTEST_DUPLICATE_SAMPLE")
            seen.add(identity)
            expected = self._request(self._author_task(context, sample["workflow"]))
            tokens = 0
            actual = True
            previous = None
            for position, round_record in enumerate(sample["rounds"]):
                binding = round_record["raw_run"]
                if binding["sha256"] in raw_seen:
                    raise ValueError("BACKTEST_DUPLICATE_RAW_RUN")
                raw_seen.add(binding["sha256"])
                record = bound_data(self.root, binding)
                output = verify_record(record)
                served_models.add(record["response"]["model"])
                if position:
                    expected = self._request(self._author_task(context, sample["workflow"]))
                    feedback = bound_data(self.root, round_record["feedback"])
                    if not isinstance(feedback, dict) or feedback.get("qualification") != "FEEDBACK_ONLY" or feedback.get("candidate_sha256") != digest(previous.encode()) or not isinstance(feedback.get("text"), str) or not feedback["text"].strip():
                        raise ValueError("BACKTEST_STALE_REVISION_FEEDBACK")
                    expected["messages"] += [{"role": "assistant", "content": previous}, {"role": "user", "content": "Revise within the remaining shared budget. Advisory feedback only:\n" + feedback["text"]}]
                elif "feedback" in round_record:
                    raise ValueError("BACKTEST_INITIAL_FEEDBACK_LEAK")
                if record["request"] != expected:
                    raise ValueError("BACKTEST_UNBALANCED_OR_STALE_REQUEST")
                usage = record["usage"]
                if any(type(usage.get(key)) is not int or usage[key] < 0 for key in ("input_tokens", "output_tokens")):
                    raise ValueError("BACKTEST_UNVERIFIED_TOKEN_BUDGET")
                if any(type(usage.get(key, 0)) is not int or usage.get(key, 0) < 0 for key in ("cache_creation_input_tokens", "cache_read_input_tokens")):
                    raise ValueError("BACKTEST_INVALID_CACHE_USAGE")
                tokens += usage["input_tokens"] + usage["output_tokens"] + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                actual = actual and record["provider"] == "anthropic"  # Replay/command cannot establish actual API execution.
                for ref in record["inputs"] + [record["template"]]:
                    if digest(repository_path(self.root, ref["path"]).read_bytes()) != ref["sha256"]:
                        raise ValueError("BACKTEST_STALE_RAW_RUN_DEPENDENCY")
                if record["budget"]["max_retries"] != 0 or record["budget"]["max_requests"] != 1:
                    raise ValueError("BACKTEST_UNACCOUNTED_RETRIES_OR_CALLS")
                previous = output
                budget = self.data["budget"]
                if sample["workflow"] == "HARNESS" and position == 0 and tokens > budget["max_total_tokens_per_sample"] - budget["revision_reserve_tokens"]:
                    raise ValueError("BACKTEST_REVISION_RESERVE_EXCEEDED")
            budget = self.data["budget"]
            if len(sample["rounds"]) > budget["max_requests_per_sample"] or tokens > budget["max_total_tokens_per_sample"]:
                raise ValueError("BACKTEST_TOTAL_BUDGET_EXCEEDED")
            if sample["workflow"] == "HARNESS" and len(sample["rounds"]) < 2:
                raise ValueError("BACKTEST_HARNESS_REVISION_MISSING")
            text_raw = repository_path(self.root, sample["text"]["path"]).read_bytes()
            if digest(text_raw) != sample["text"]["sha256"] or text_raw.decode() != previous:
                raise ValueError("BACKTEST_STALE_SAMPLE_TEXT")
            if not budget["minimum_characters"] <= len(previous.strip()) <= budget["maximum_characters"]:
                raise ValueError("BACKTEST_OUTPUT_LENGTH_BUDGET")
            results.append({"sample": sample, "text": previous, "actual": actual, "total_tokens": tokens,
                            "requests": len(sample["rounds"]), "overlap": overlap_observations(previous, context["hidden"]),
                            "style": compare_reference(previous, context["reference"])})
        if len(served_models) != 1:
            raise ValueError("BACKTEST_DIFFERENT_SERVED_MODELS")
        pairs = {workflow: {row["sample"]["sample_id"] for row in results if row["sample"]["workflow"] == workflow} for workflow in WORKFLOWS}
        if pairs["DIRECT"] != pairs["HARNESS"] or len(pairs["DIRECT"]) < self.data["samples_per_workflow"]:
            raise ValueError("BACKTEST_INCOMPLETE_PAIRED_SAMPLES")
        return records, results

    def export(self, destination: Path, records_path: str):
        context = self._context()
        records, results = self._records(records_path, context)
        candidates, mapping = [], []
        authors = records["authors"]
        texts = [(row["text"], {"workflow": row["sample"]["workflow"], "sample_id": row["sample"]["sample_id"], "text": row["sample"]["text"]}) for row in results]
        texts.append((context["hidden"], {"workflow": "ORIGINAL_REFERENCE", "original_chapter_units": 1}))
        for text, identity in texts:
            token = "read-" + secrets.token_hex(6)
            candidates.append({"token": token, "file": token + ".txt", "sha256": digest(text.encode())})
            mapping.append({"token": token, **identity})
        secrets.SystemRandom().shuffle(candidates)
        core = {"mapping": mapping, "authors": authors, "context_sha256": context["context_sha256"],
                "records": {"path": records_path, "sha256": digest(repository_path(self.root, records_path).read_bytes())}}
        packet = {"schema_version": 1, "context_sha256": context["context_sha256"], "candidates": candidates,
                  "coordinator_commitment": digest(canonical_bytes(core)), "minimum_reviewers": 2,
                  "questions": list(DIMENSIONS), "recognition_required": True,
                  "ranking_format": "Ordered nonempty token groups covering every candidate; ties permitted.",
                  "reference_limit": "Recognizable original is an upper reference, not evidence of lost-text recovery.", "authority_effect": "NONE"}
        destination = Path(destination)
        destination.mkdir(exist_ok=False, parents=True)
        public, coordinator = destination / "public", destination / "coordinator"
        public.mkdir(); coordinator.mkdir()
        text_index = {row["token"]: text for row, (text, _) in zip(mapping, texts)}
        for candidate in candidates:
            with (public / candidate["file"]).open("xb") as handle:
                handle.write(text_index[candidate["token"]].encode())
        _write(public / "packet.json", packet)
        _write(coordinator / "mapping.json", {"packet_sha256": digest(canonical_bytes(packet)), **core})
        template = {"report_kind": "TEMPLATE", "id": "", "packet_sha256": digest(canonical_bytes(packet)),
                    "context_sha256": context["context_sha256"], "reviewer": {"principal_id": "", "source_id": "", "kind": "INDEPENDENT_HUMAN", "mapping_unseen_during_review": None, "independent_of_authors": None},
                    "ranking": [], "recommendation": None,
                    "observations": {row["token"]: {dimension: {"reason": "", "spans": []} for dimension in DIMENSIONS} for row in candidates},
                    "recognition": {row["token"]: {"recognized_original": None, "familiarity": None, "reason": ""} for row in candidates},
                    "authority_effect": "NONE"}
        _write(public / "reading-template.json", template)
        return {"status": "PASS", "scope": "ANONYMOUS_MATERIAL_EXPORT", "public_directory": str(public), "coordinator_directory": str(coordinator), "reading_status": "PENDING", "authority_effect": "NONE"}

    def _reviews(self, export_root, bindings, context, records_path, samples):
        packet, mapping, texts = load_comparative_packet(Path(export_root), context["context_sha256"])
        if mapping["records"] != {"path": records_path, "sha256": digest(repository_path(self.root, records_path).read_bytes())}:
            raise ValueError("BACKTEST_STALE_EXPORT_RECORDS")
        identities = [(row["workflow"], row.get("sample_id")) for row in mapping["mapping"]]
        expected_identities = [(row["sample"]["workflow"], row["sample"]["sample_id"]) for row in samples] + [("ORIGINAL_REFERENCE", None)]
        if sorted(identities) != sorted(expected_identities) or len({row["token"] for row in mapping["mapping"]}) != len(mapping["mapping"]):
            raise ValueError("BACKTEST_EXPORT_SAMPLE_MAPPING_MISMATCH")
        sample_index = {(row["sample"]["workflow"], row["sample"]["sample_id"]): row for row in samples}
        for row in mapping["mapping"]:
            expected_text = context["hidden"] if row["workflow"] == "ORIGINAL_REFERENCE" else sample_index[(row["workflow"], row["sample_id"])]["text"]
            if texts[row["token"]] != expected_text:
                raise ValueError("BACKTEST_EXPORT_SAMPLE_TEXT_MISMATCH")
        valid, principals, sources, ids = [], set(), set(), set()
        for binding in bindings:
            review = bound_data(self.root, binding)
            recognition = review["recognition"]
            base = {key: value for key, value in review.items() if key != "recognition"}
            validate_comparative_review(base, packet, mapping, texts)
            if set(recognition) != set(texts):
                raise ValueError("BACKTEST_RECOGNITION_INCOMPLETE")
            for value in recognition.values():
                if type(value["recognized_original"]) is not bool or value["familiarity"] not in {"UNFAMILIAR", "FAMILIAR", "VERY_FAMILIAR"} or not isinstance(value["reason"], str) or not value["reason"].strip():
                    raise ValueError("BACKTEST_INVALID_RECOGNITION")
            raw = bound_data(self.root, review["raw_review"])
            if "raw_review" in raw or {key: value for key, value in raw.items() if key != "authority_effect"} != {key: value for key, value in review.items() if key not in {"raw_review", "authority_effect"}} or raw.get("authority_effect", "NONE") != "NONE":
                raise ValueError("BACKTEST_REVIEW_RAW_BINDING_MISMATCH")
            reviewer = review["reviewer"]
            if reviewer["principal_id"] in principals or reviewer["source_id"] in sources or review["id"] in ids:
                raise ValueError("BACKTEST_DUPLICATE_REVIEWER")
            principals.add(reviewer["principal_id"]); sources.add(reviewer["source_id"]); ids.add(review["id"])
            valid.append(review)
        pairwise = []
        for direct in [row for row in mapping["mapping"] if row["workflow"] == "DIRECT"]:
            harness = next(row for row in mapping["mapping"] if row["workflow"] == "HARNESS" and row["sample_id"] == direct["sample_id"])
            outcomes = []
            for review in valid:
                rank = {token: i for i, group in enumerate(review["ranking"]) for token in group}
                d, h = rank[direct["token"]], rank[harness["token"]]
                outcomes.append({"review_id": review["id"], "outcome": "TIE" if d == h else "HARNESS" if h < d else "DIRECT", "recognition": review["recognition"]})
            pairwise.append({"sample_id": direct["sample_id"], "outcomes": outcomes})
        return {"review_count": len(valid), "paired_observations": pairwise, "independence_basis": "SUBMITTED_IDENTITIES_AND_CUSTODY_ATTESTATIONS_NOT_EXTERNALLY_PROVEN"}

    def summary(self, records_path=None, export_root=None, reviews=()):
        context = self._context()
        result = self.check()
        result.update(valid_independent_review_count=0, budget_verification="PENDING_ACTUAL_RUNS", paired_observations=[],
                      limitations=self.data["limitations"], automatic_winner=None, literary_acceptance="PENDING", model_pretraining_exposure="UNKNOWN")
        if records_path is None:
            if reviews or export_root:
                raise ValueError("BACKTEST_REVIEWS_REQUIRE_RECORDED_RUNS")
            return result
        _, samples = self._records(records_path, context)
        result["samples"] = [{key: value for key, value in row.items() if key not in {"text", "sample"}} | {"workflow": row["sample"]["workflow"], "sample_id": row["sample"]["sample_id"], "text": row["sample"]["text"], "raw_runs": [round_record["raw_run"] for round_record in row["sample"]["rounds"]]} for row in samples]
        actual = all(row["actual"] for row in samples)
        result["budget_verification"] = "VERIFIED_RECORDED_COUNTERS" if actual else "REPLAY_OR_UNVERIFIED_EXECUTION_ONLY"
        if export_root is not None:
            reading = self._reviews(export_root, reviews, context, records_path, samples)
            result["valid_independent_review_count"] = reading["review_count"]
            result["paired_observations"] = reading["paired_observations"]
            result["independence_basis"] = reading["independence_basis"]
        elif reviews:
            raise ValueError("BACKTEST_REVIEWS_REQUIRE_ANONYMOUS_EXPORT")
        if actual and context["task_complete"] and result["valid_independent_review_count"] >= 2:
            result["controlled_workflow_effect"] = "OBSERVATIONAL_PAIRED_READINGS_AVAILABLE_NOT_CAUSAL_PROOF"
        return result
