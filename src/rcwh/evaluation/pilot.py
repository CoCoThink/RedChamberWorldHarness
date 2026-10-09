"""Three consecutive chapters, causal alternatives and reproducible trial packets."""
from itertools import combinations
import json
from pathlib import Path
import secrets
import subprocess
import time

from ..candidate_reviews import bound_data, canonical_bytes, digest
from ..io import load_data
from .style import style_diagnostics

STUDY_PATH = "data/evaluation/pilot85_87/study.json"


class PilotStudy:
    def __init__(self, root: Path, relative: str = STUDY_PATH):
        self.root = root
        self.relative = relative
        self.data = load_data(root / relative)

    def context(self) -> dict:
        inputs = [(b, bound_data(self.root, b)) for b in self.data["inputs"]]
        return {"study_sha256": digest((self.root / self.relative).read_bytes()),
                "inputs": [{"binding": b, "value": value} for b, value in inputs]}

    def summary(self) -> dict:
        context = self.context()
        chapters = self.data["chapters"]
        if len(chapters) != 3 or chapters != list(range(chapters[0], chapters[0]+3)):
            raise ValueError("pilot requires three consecutive chapters")
        arms = self.data["arms"]
        if len({a["id"] for a in arms}) != len(arms):
            raise ValueError("duplicate pilot arm")
        route_arms = [a for a in arms if a["workflow"] == "IMPROVED_HARNESS"]
        if len(route_arms) < 2 or not any(a["workflow"] == "DIRECT_WRITING" for a in arms):
            raise ValueError("pilot needs two causal alternatives and a direct-writing arm")
        comparisons = []
        for left, right in combinations(route_arms, 2):
            def decisions(arm):
                return {tuple(d[k] for k in ("chapter", "actor", "action", "recipient", "consequence")) for d in arm["causal_choices"]}
            l, r = decisions(left), decisions(right)
            if not l or not r or l == r:
                raise ValueError("compression or wording changes alone are not different causal routes")
            comparisons.append({"left": left["id"], "right": right["id"], "left_only": sorted(l-r), "right_only": sorted(r-l),
                                "scope": "DECLARED_CAUSAL_PLAN_DIFFERENCE", "text_realisation": "PENDING_READING"})
        drafts = []
        for arm in arms:
            if [c["chapter"] for c in arm["drafts"]] != chapters:
                raise ValueError("each arm must contain all three consecutive chapters")
            previous = None
            for chapter in arm["drafts"]:
                raw = (self.root / chapter["text"]["path"]).read_bytes()
                if digest(raw) != chapter["text"]["sha256"]:
                    raise ValueError("stale pilot draft")
                text = raw.decode()
                if len(text.strip()) < self.data["budget"]["minimum_trial_characters_per_chapter"]:
                    raise ValueError("pilot draft is missing actual prose")
                if previous is not None and previous != chapter["entry"]:
                    raise ValueError("pilot chapter intent exit/entry discontinuity")
                previous = chapter["exit"]
                for claim in chapter["intent_spans"]:
                    if not 0 <= claim["start"] < claim["end"] <= len(text) or text[claim["start"]:claim["end"]] != claim["quote"]:
                        raise ValueError("invalid pilot intent span")
                drafts.append({"arm": arm["id"], "chapter": chapter["chapter"], "sha256": digest(raw),
                               "length": len(text), "intent_links": "CONSISTENT", "semantic_realisation": "PENDING_INDEPENDENT_READING",
                               "style": style_diagnostics(text)})
        return {"status": "PENDING", "scope": "CONSECUTIVE_RESEARCH_TRIAL", "chapters": chapters,
                "context_sha256": digest(canonical_bytes(context)), "drafts": drafts, "route_comparisons": comparisons,
                "direct_control_status": "CONTAMINATED_INTERNAL_EXAMPLE_REQUIRES_FRESH_AUTHOR_RUN",
                "controlled_workflow_effect": "NOT_ESTIMABLE", "valid_independent_review_count": 0,
                "costs": [{"arm": a["id"], "record": a["costs"]} for a in arms],
                "remaining": ["FRESH_DIRECT_AND_OLD_WORKFLOW_CONTROL", "INDEPENDENT_SEMANTIC_READINGS", "TWO_COMPARATIVE_READERS", "REVISION_AND_REREVIEW"],
                "authority_effect": "NONE", "stable_active_mutated": False}

    def export(self, destination: Path) -> dict:
        summary = self.summary()
        destination.mkdir(exist_ok=False)
        public, coordinator = destination / "public", destination / "coordinator"
        public.mkdir(); coordinator.mkdir()
        candidates, mapping = [], []
        for arm in self.data["arms"]:
            token = "read-" + secrets.token_hex(6)
            text = "\n\n".join((self.root / c["text"]["path"]).read_bytes().decode() for c in arm["drafts"])
            raw = text.encode(); name = token + ".txt"
            (public / name).write_bytes(raw)
            candidates.append({"token": token, "file": name, "sha256": digest(raw)})
            mapping.append({"token": token, "arm": arm["id"]})
        packet = {"schema_version": 1, "context_sha256": summary["context_sha256"], "candidates": candidates,
                  "questions": self.data["review_questions"], "minimum_reviewers": 2,
                  "ranking_format": "Ordered nonempty groups; tokens in a group tie; cover all candidates.",
                  "recommendation_choices": ["CONTINUE", "NEITHER"], "authority_effect": "NONE"}
        mapping_core = {"mapping": mapping, "authors": self.data["authors"], "context_sha256": summary["context_sha256"]}
        packet["coordinator_commitment"] = digest(canonical_bytes(mapping_core))
        raw = canonical_bytes(packet); (public / "packet.json").write_bytes(raw)
        (coordinator / "mapping.json").write_bytes(canonical_bytes({"packet_sha256": digest(raw), **mapping_core}))
        from .comparison import DIMENSIONS
        template = {"report_kind": "TEMPLATE", "id": "", "packet_sha256": digest(raw),
                    "context_sha256": summary["context_sha256"], "reviewer": {"principal_id": "", "source_id": "",
                    "kind": "INDEPENDENT_HUMAN", "mapping_unseen_during_review": None, "independent_of_authors": None},
                    "ranking": [], "recommendation": None, "observations": {c["token"]: {d: {"reason": "", "spans": []} for d in DIMENSIONS} for c in candidates},
                    "authority_effect": "NONE"}
        (public / "reading-template.json").write_bytes(canonical_bytes(template))
        return {"status": "PASS", "scope": "ANONYMOUS_MATERIAL_EXPORT", "packet_sha256": digest(raw),
                "public_directory": str(public), "coordinator_directory": str(coordinator), "reading_status": "PENDING"}

    def author_request(self, workflow: str, route: str) -> dict:
        """Fresh-run controls receive the frozen task; no trial feedback leaks in."""
        if workflow not in {"DIRECT_WRITING", "LEGACY_HARNESS", "IMPROVED_HARNESS"}:
            raise ValueError("unknown writing workflow")
        chosen = next(a for a in self.data["arms"] if a["id"] == route)
        sources = [{"binding": b, "value": bound_data(self.root, b)} for b in self.data["inputs"]]
        scene = next(s["value"] for s in sources if s["value"].get("id") == "ch86_last_night")
        support = None
        if workflow == "LEGACY_HARNESS":
            support = {"kind": "LEGACY_LEXICAL_HINTS", "required": scene["required_beats"],
                       "forbidden": scene["forbidden_beats"], "historical_keyword_groups": scene["historical_adapter_requirements"],
                       "evaluation_limit": "Original substring checks, retained only as experimental treatment."}
        elif workflow == "IMPROVED_HARNESS":
            support = {"kind": "STRUCTURED_EVENT_EDITING_GUIDANCE",
                       "required_events": [{"id": b["id"], "description": b["description"]} for b in scene["required_beats"]],
                       "forbidden_events": [{"id": b["id"], "description": b["description"]} for b in scene["forbidden_beats"]],
                       "exit_state": scene["exit_state"], "knowledge_guards": [{k:v for k,v in g.items() if k != "any_text"} for g in scene["knowledge_guards"]],
                       "reading_questions": self.data["review_questions"],
                       "rule": "Use actions and information transfer, not word quotas; author sidecars never qualify their own prose."}
        return {"kind": "FROZEN_AUTHOR_TASK", "chapters": self.data["chapters"], "task": self.data["task"],
                "constraints": sources, "route": chosen["causal_choices"], "workflow": workflow,
                "budget": self.data["budget"], "workflow_support": support, "feedback": [],
                "response_format": {"chapters": [{"chapter": "integer", "text": "full chapter text"}],
                                    "producer": "actual author/model/settings identity", "usage": "actual provider counters or null"},
                "authority_effect": "NONE"}

    def run_author(self, workflow: str, route: str, command: list[str], output: Path, timeout: int = 60) -> dict:
        request = self.author_request(workflow, route)
        raw = canonical_bytes(request)
        started = time.monotonic()
        try:
            result = subprocess.run(command, input=raw, capture_output=True, timeout=timeout, check=False)
            stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, returncode = exc.stdout or b"", exc.stderr or b"", None
        trace = {"request": request, "input_sha256": digest(raw), "command": command,
                 "stdout": stdout.decode(errors="replace"), "stdout_sha256": digest(stdout),
                 "stderr": stderr.decode(errors="replace"), "returncode": returncode,
                 "elapsed_seconds": time.monotonic()-started, "program_invocations": 1,
                 "provider_usage_basis": "SUBMITTED_PROVIDER_COUNTERS_NOT_LOCALLY_VERIFIED", "status": "FAIL"}
        try:
            response = json.loads(trace["stdout"])
            chapters = response["chapters"]
            if returncode != 0 or [c["chapter"] for c in chapters] != self.data["chapters"] or not response["producer"]:
                raise ValueError("invalid author execution output")
            if any(not self.data["budget"]["minimum_trial_characters_per_chapter"] <= len(c["text"].strip()) <= self.data["budget"]["maximum_trial_characters_per_chapter"] for c in chapters):
                raise ValueError("actual author output outside trial budget")
            trace.update(status="PASS", response=response, usage=response.get("usage"))
        except (KeyError, TypeError, ValueError) as exc:
            trace["findings"] = [str(exc)]
        with output.open("xb") as handle:
            handle.write(canonical_bytes(trace))
        return {"status": trace["status"], "scope": "AUTHOR_EXECUTION_ONLY", "trace_path": str(output),
                "trace_sha256": digest(output.read_bytes()), "literary_acceptance": "PENDING",
                "context_isolation_basis": "OPERATOR_EXECUTION_PROTOCOL_NOT_AUTOMATICALLY_PROVEN"}
