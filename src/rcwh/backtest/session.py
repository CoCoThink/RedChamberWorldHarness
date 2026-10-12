"""Session-declared paired holdout drafts and anonymous agent reading exports.

This is separate from BacktestStudy's provider-record workflow. Byte custody
and declared length/round parity can be checked; session resource usage, model
identity, pretraining exposure and causal workflow effects cannot be verified.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import secrets

from ..assets.paths import repository_path
from ..candidate_reviews import canonical_bytes, digest
from ..evaluation.style_reference import compare_reference
from ..generation.records import append_bytes, binding, bound_bytes
from ..io import load_data
from ..schema import validate_instance
from .observations import overlap_observations
from .study import BacktestStudy, HOLDOUT_PATH, WORKFLOWS

EXECUTION_BASIS = "SESSION_AUTHORED_NOT_PROVIDER_VERIFIED"


def _base() -> dict:
    return {"execution_basis": EXECUTION_BASIS, "resource_parity": "NOT_VERIFIED",
            "model_pretraining_exposure": "UNKNOWN", "controlled_workflow_effect": "NOT_ESTIMABLE",
            "independent_human_admission": False, "usage": "RESEARCH_ONLY", "authority_effect": "NONE"}


def _json(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate session-backtest field: {key}")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite session-backtest value")))
    if not isinstance(value, dict):
        raise ValueError("session backtest requires a JSON object")
    return value


def _schema(root: Path, value: dict, kind: str) -> None:
    schema = load_data(repository_path(root, "schemas/session_backtest.schema.json"))
    errors = validate_instance(value, {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{kind}"})
    if errors:
        raise ValueError("invalid session backtest " + kind + ": " + "; ".join(errors))


def _store(root: Path, directory: str, raw: bytes, suffix: str = "json") -> dict:
    relative = f"{directory}/{digest(raw)}.{suffix}"
    ref = {"path": relative, "sha256": digest(raw)}
    try:
        return append_bytes(root, relative, raw)
    except FileExistsError:
        if bound_bytes(root, ref) != raw:
            raise ValueError("immutable session backtest file conflict")
        return ref


def _label(value: str, description: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"nonblank {description} required")


def anonymous_export(root: Path, destination: str, candidates: list[dict], *, context: dict,
                     coordinator_session_id: str, original: dict | None = None) -> dict:
    """Reusable CANDIDATE agent packet; identities live only in coordinator map.

    candidates: [{id, text: {path, sha256}, author_session_ids: [str]}].
    context is an immutable registry/context binding. original, when supplied,
    is a reference-text binding whose identity is not disclosed to readers.
    Only public/ is for readers; never send them the coordinator directory.
    """
    root = Path(root).resolve()
    _label(coordinator_session_id, "coordinator session ID")
    bound_bytes(root, context)
    if not candidates:
        raise ValueError("anonymous export requires candidates")
    if len({row["id"] for row in candidates}) != len(candidates):
        raise ValueError("duplicate anonymous candidate ID")
    rows = []
    forbidden = set()
    for candidate in candidates:
        if set(candidate) != {"id", "text", "author_session_ids"}:
            raise ValueError("anonymous candidates require id, text and author_session_ids only")
        _label(candidate["id"], "candidate ID")
        sessions = candidate["author_session_ids"]
        if not isinstance(sessions, list) or not sessions:
            raise ValueError("candidate author session IDs required")
        for session in sessions:
            _label(session, "author session ID")
        raw = bound_bytes(root, candidate["text"])
        if not raw.decode("utf-8").strip():
            raise ValueError("empty anonymous candidate")
        forbidden.update([candidate["id"], candidate["text"]["path"], *sessions])
        rows.append((raw, {"kind": "SESSION_CANDIDATE", **deepcopy(candidate)}))
    if original is not None:
        raw = bound_bytes(root, original)
        if not raw.decode("utf-8").strip():
            raise ValueError("empty anonymous original reference")
        forbidden.add(original["path"])
        rows.append((raw, {"kind": "ORIGINAL_REFERENCE", "text": deepcopy(original)}))
    destination_path = repository_path(root, destination)
    if destination_path.exists():
        raise FileExistsError("anonymous destination already exists")
    subjects, mapping, files = [], [], []
    for raw, identity in rows:
        token = "read-" + secrets.token_hex(12)
        relative = f"{destination}/public/{token}.txt"
        text_ref = {"path": relative, "sha256": digest(raw)}
        subjects.append({"id": token, "scope": "CANDIDATE", "binding": text_ref})
        mapping.append({"token": token, "public_text": text_ref, **identity})
        files.append((relative, raw))
    secrets.SystemRandom().shuffle(subjects)
    packet = {"schema_version": 1, "packet_kind": "AGENT_REVIEW_PACKET", "id": "reading-" + secrets.token_hex(12),
              "coordinator_session_id": coordinator_session_id, "subjects": subjects,
              "authority_effect": "NONE", "usage": "RESEARCH_ONLY"}
    errors = validate_instance(packet, repository_path(root, "schemas/agent_packet.schema.json"))
    if errors:
        raise ValueError("invalid anonymous agent packet: " + "; ".join(errors))
    # Never leak source paths, sample IDs or author sessions through metadata.
    public_raw = canonical_bytes(packet)
    for identity in forbidden:
        # Very short IDs can accidentally occur inside opaque tokens or generic
        # schema vocabulary. Exact labels are never emitted; distinctive IDs and
        # full source paths must not occur anywhere in public metadata.
        if len(identity) >= 8 and identity.encode() in public_raw:
            raise ValueError("anonymous packet metadata leaks candidate/author identity")
    packet_ref = {"path": f"{destination}/public/packet.json", "sha256": digest(public_raw)}
    core = {"schema_version": 1, "kind": "SESSION_ANONYMOUS_MAPPING", "context": deepcopy(context),
            "packet": packet_ref, "mapping": mapping, "authority_effect": "NONE", "usage": "RESEARCH_ONLY"}
    for relative, raw in files:
        append_bytes(root, relative, raw)
    append_bytes(root, packet_ref["path"], public_raw)
    mapping_ref = _store(root, f"{destination}/coordinator", canonical_bytes(core))
    commitment = append_bytes(root, f"{destination}/coordinator/commitment.json",
                              canonical_bytes({"packet": packet_ref, "mapping": mapping_ref, "context": context}))
    return {"status": "PASS", "packet": packet_ref, "mapping": mapping_ref, "commitment": commitment,
            "public_directory": f"{destination}/public", "coordinator_directory": f"{destination}/coordinator",
            "reading_status": "PENDING", "outcome": "NOT_ESTIMABLE", **_base()}


class SessionBacktest:
    def __init__(self, root: Path, config_path: str = HOLDOUT_PATH):
        self.root = Path(root).resolve()
        self.study = BacktestStudy(self.root, config_path)

    def _sources(self) -> list[dict]:
        """Coordinator-only closure of source/config/schema/catalog dependencies."""
        root = self.root
        paths = {self.study.relative, self.study.data["shared_task"]["path"], self.study.data["world"]["path"],
                 "schemas/session_backtest.schema.json", "schemas/agent_packet.schema.json"}
        for domain in ("data/catalog", "data/corpus", "data/provenance", "data/backtest"):
            directory = repository_path(root, domain)
            for path in sorted(directory.rglob("*")) if directory.exists() else []:
                if path.is_file() and path.suffix in {".json", ".jsonl", ".yaml", ".yml"}:
                    paths.add(path.relative_to(root).as_posix())
        for path in sorted((root / "schemas").glob("backtest_*.schema.json")):
            paths.add(path.relative_to(root).as_posix())
        from ..assets import AssetCatalog
        from ..corpus.dataset import CorpusRepository
        catalog = AssetCatalog.from_repo(root)
        registry = CorpusRepository(catalog).registry()[self.study.data["dataset_ref"]]
        asset = catalog.resolve(registry["manifest_ref"])
        manifest_path = asset.path.relative_to(root).as_posix()
        paths.add(manifest_path)
        manifest = _json(repository_path(root, manifest_path).read_bytes())
        config = manifest.get("build_config", {})
        if "path" in config:
            paths.add(config["path"])
            inputs = config.get("document", {}).get("inputs")
            if isinstance(inputs, dict):
                paths.add(inputs["path"])
        dependency_refs = [item["asset_ref"] for item in manifest.get("dependencies", []) + list(manifest.get("products", {}).values())]
        seen = set()
        while dependency_refs:
            ref = dependency_refs.pop()
            if ref in seen:
                continue
            seen.add(ref)
            dependency = catalog.resolve(ref)
            paths.add(dependency.path.relative_to(root).as_posix())
            record = catalog.assets.get(ref, {})
            dependency_refs.extend(record.get("derived_from", []))
        return [binding(root, path) for path in sorted(paths)]

    def _preparation(self, ref: dict) -> tuple[dict, dict]:
        value = _json(bound_bytes(self.root, ref))
        _schema(self.root, value, "preparation")
        for source in value["inputs"]:
            bound_bytes(self.root, source)
        context = self.study._context()
        current = self._make_preparation(value["characters"], value["sample_ids"], value["coordinator_session_id"], context)
        if canonical_bytes(value) != canonical_bytes(current):
            raise ValueError("STALE_SESSION_BACKTEST_PREPARATION")
        return value, context

    def _make_preparation(self, characters: int, sample_ids: list[str], coordinator_session_id: str, context: dict) -> dict:
        _label(coordinator_session_id, "coordinator session ID")
        budget = self.study.data["budget"]
        if type(characters) is not int or not budget["minimum_characters"] <= characters <= budget["maximum_characters"]:
            raise ValueError("session target characters outside shared length ceiling")
        if (not isinstance(sample_ids, list) or len(sample_ids) < self.study.data["samples_per_workflow"]
                or len(set(sample_ids)) != len(sample_ids)):
            raise ValueError("session preparation requires complete paired sample IDs, at least two")
        for sample_id in sample_ids:
            _label(sample_id, "sample ID")
        requests = {workflow: self.study.request(workflow) for workflow in WORKFLOWS}
        tasks = {workflow: _json(requests[workflow]["messages"][0]["content"].encode()) for workflow in WORKFLOWS}
        if (tasks["DIRECT"]["shared"] != tasks["HARNESS"]["shared"]
                or tasks["DIRECT"]["shared_information_sha256"] != tasks["HARNESS"]["shared_information_sha256"]):
            raise ValueError("session shared author information is unbalanced")
        return {"schema_version": 1, "kind": "SESSION_BACKTEST_PREPARATION", "config": binding(self.root, self.study.relative),
                "context_sha256": context["context_sha256"], "inputs": self._sources(), "tasks": tasks,
                "characters": characters, "sample_ids": sample_ids, "coordinator_session_id": coordinator_session_id,
                "requests": requests, **_base()}

    def _request(self, preparation: dict, workflow: str, parent: dict | None, feedback: dict | None) -> dict:
        if workflow not in WORKFLOWS:
            raise ValueError("unknown session workflow")
        request = deepcopy(preparation["requests"][workflow])
        task = _json(request["messages"][0]["content"].encode())
        task["shared"]["target_characters"] = preparation["characters"]
        request["messages"][0]["content"] = canonical_bytes(task).decode()
        if parent is not None:
            previous = self._round(parent)[0]
            opinion = _json(bound_bytes(self.root, feedback))
            _schema(self.root, opinion, "feedback")
            if opinion["parent"] != parent or opinion["candidate_sha256"] != previous["candidate"]["sha256"]:
                raise ValueError("STALE_SESSION_REVISION_FEEDBACK")
            request["messages"] += [{"role": "assistant", "content": previous["output"]},
                                    {"role": "user", "content": "Revise within the remaining shared budget. Advisory feedback only:\n" + opinion["text"]}]
        return request

    def _packet(self, preparation_ref: dict, preparation: dict, workflow: str, sample_id: str, *,
                round_index: int = 0, parent: dict | None = None, feedback: dict | None = None) -> dict:
        if sample_id not in preparation["sample_ids"]:
            raise ValueError("unknown prepared sample ID")
        request = self._request(preparation, workflow, parent, feedback)
        return {"schema_version": 1, "kind": "SESSION_BACKTEST_AUTHOR_PACKET", "preparation": preparation_ref,
                "workflow": workflow, "sample_id": sample_id, "round_index": round_index,
                "characters": preparation["characters"], "request": request,
                "request_sha256": digest(canonical_bytes(request)), "parent": parent, "feedback": feedback, **_base()}

    def prepare(self, destination: str, *, characters: int, sample_ids=("one", "two"),
                coordinator_session_id: str) -> dict:
        if repository_path(self.root, destination).exists():
            raise FileExistsError("session preparation destination exists")
        context = self.study._context()
        preparation = self._make_preparation(characters, list(sample_ids), coordinator_session_id, context)
        _schema(self.root, preparation, "preparation")
        ref = _store(self.root, f"{destination}/coordinator/preparations", canonical_bytes(preparation))
        packets = []
        for workflow in WORKFLOWS:
            for sample_id in preparation["sample_ids"]:
                packet = self._packet(ref, preparation, workflow, sample_id)
                packet_ref = _store(self.root, f"{destination}/author-packets", canonical_bytes(packet))
                packets.append({"workflow": workflow, "sample_id": sample_id, "packet": packet_ref,
                                "request_sha256": packet["request_sha256"]})
        return {"status": "PASS", "preparation": ref, "author_packets": packets, **_base()}

    def _verify_packet(self, ref: dict) -> tuple[dict, dict]:
        packet = _json(bound_bytes(self.root, ref))
        _schema(self.root, packet, "packet")
        preparation, _ = self._preparation(packet["preparation"])
        expected = self._packet(packet["preparation"], preparation, packet["workflow"], packet["sample_id"],
                                round_index=packet["round_index"], parent=packet["parent"], feedback=packet["feedback"])
        if packet["parent"] is None:
            if packet["round_index"] != 0 or packet["feedback"] is not None:
                raise ValueError("session initial round cannot carry parent/feedback")
        else:
            parent, _ = self._round(packet["parent"])
            if (parent["workflow"] != packet["workflow"] or parent["sample_id"] != packet["sample_id"]
                    or parent["preparation"] != packet["preparation"] or parent["round_index"] + 1 != packet["round_index"]):
                raise ValueError("SESSION_BACKTEST_REVISION_LINEAGE_MISMATCH")
        if canonical_bytes(expected) != canonical_bytes(packet):
            raise ValueError("session author packet differs from exact prepared request")
        return packet, preparation

    def register(self, text_path: str, packet_path: str, *, session_id: str, session_model_label: str) -> dict:
        text_source, packet_source = binding(self.root, text_path), binding(self.root, packet_path)
        raw, packet_raw = bound_bytes(self.root, text_source), bound_bytes(self.root, packet_source)
        packet, _ = self._verify_packet(packet_source)
        text = raw.decode("utf-8")
        budget = self.study.data["budget"]
        if not text.strip() or not budget["minimum_characters"] <= len(text.strip()) <= budget["maximum_characters"]:
            raise ValueError("session output outside shared character ceiling")
        _label(session_id, "session ID"); _label(session_model_label, "session model label")
        if packet["round_index"] >= budget["max_requests_per_sample"]:
            raise ValueError("session declared rounds exceed prepared maximum")
        candidate = {"path": f"artifacts/session-backtest/text/{digest(raw)}.txt", "sha256": digest(raw)}
        packet_ref = {"path": f"artifacts/session-backtest/packets/{digest(packet_raw)}.json", "sha256": digest(packet_raw)}
        record = {"schema_version": 1, "kind": "SESSION_BACKTEST_ROUND", "session_id": session_id,
                  "session_configured_model": {"label": session_model_label, "basis": "UNVERIFIED_DECLARATION"},
                  "preparation": packet["preparation"], "workflow": packet["workflow"], "sample_id": packet["sample_id"],
                  "round_index": packet["round_index"], "packet_source": packet_source, "packet": packet_ref,
                  "request_sha256": packet["request_sha256"], "text_source": text_source, "candidate": candidate,
                  "output": text, "output_sha256": digest(raw), "parent": packet["parent"], "feedback": packet["feedback"], **_base()}
        _schema(self.root, record, "round")
        _store(self.root, "artifacts/session-backtest/text", raw, "txt")
        _store(self.root, "artifacts/session-backtest/packets", packet_raw)
        ref = _store(self.root, "artifacts/session-backtest/rounds", canonical_bytes(record))
        return {"status": "PASS", "round": ref, "candidate": candidate, **_base()}

    def _round(self, ref: dict) -> tuple[dict, dict]:
        record = _json(bound_bytes(self.root, ref))
        _schema(self.root, record, "round")
        packet_raw = bound_bytes(self.root, record["packet"])
        if bound_bytes(self.root, record["packet_source"]) != packet_raw:
            raise ValueError("session packet source mismatch")
        packet, preparation = self._verify_packet(record["packet"])
        raw = bound_bytes(self.root, record["candidate"])
        if bound_bytes(self.root, record["text_source"]) != raw or record["output"].encode() != raw or digest(raw) != record["output_sha256"]:
            raise ValueError("session text/output source lineage mismatch")
        for key in ("preparation", "workflow", "sample_id", "round_index", "request_sha256", "parent", "feedback"):
            if record[key] != packet[key]:
                raise ValueError("session round/packet binding mismatch: " + key)
        budget = self.study.data["budget"]
        if (not budget["minimum_characters"] <= len(record["output"].strip()) <= budget["maximum_characters"]
                or record["round_index"] >= budget["max_requests_per_sample"]):
            raise ValueError("session round violates prepared length/round ceilings")
        return record, preparation

    def prepare_revision(self, destination: str, parent_round_path: str, feedback_path: str) -> dict:
        parent_ref, feedback_ref = binding(self.root, parent_round_path), binding(self.root, feedback_path)
        parent, preparation = self._round(parent_ref)
        packet = self._packet(parent["preparation"], preparation, parent["workflow"], parent["sample_id"],
                              round_index=parent["round_index"] + 1, parent=parent_ref, feedback=feedback_ref)
        if packet["round_index"] >= self.study.data["budget"]["max_requests_per_sample"]:
            raise ValueError("session declared rounds exceed prepared maximum")
        _schema(self.root, packet, "packet")
        ref = _store(self.root, destination, canonical_bytes(packet))
        return {"status": "PASS", "packet": ref, "request_sha256": packet["request_sha256"], **_base()}

    def _samples(self, records: dict) -> tuple[list[dict], dict]:
        _schema(self.root, records, "registry")
        preparation, context = self._preparation(records["preparation"])
        seen, rows = set(), []
        for row in records["samples"]:
            identity = row["workflow"], row["sample_id"]
            if identity in seen:
                raise ValueError("duplicate session sample")
            seen.add(identity)
            record, _ = self._round(row["final_round"])
            if (record["preparation"] != records["preparation"] or record["workflow"] != row["workflow"]
                    or record["sample_id"] != row["sample_id"] or record["candidate"] != row["text"]):
                raise ValueError("session registry sample/round mismatch")
            chain, current = [], record
            while True:
                chain.append(current)
                if current["parent"] is None:
                    break
                current, _ = self._round(current["parent"])
            if row["workflow"] == "HARNESS" and len(chain) < 2:
                raise ValueError("SESSION_HARNESS_REVISION_REQUIRED")
            rows.append({"workflow": row["workflow"], "sample_id": row["sample_id"], "text": row["text"],
                         "output": record["output"], "rounds": list(reversed(chain))})
        expected = {(workflow, sample_id) for workflow in WORKFLOWS for sample_id in preparation["sample_ids"]}
        if seen != expected:
            raise ValueError("SESSION_INCOMPLETE_PAIRED_SAMPLES")
        return rows, context

    def registry(self, destination: str, round_paths: list[str]) -> dict:
        rounds = [(binding(self.root, path), self._round(binding(self.root, path))[0]) for path in round_paths]
        if not rounds:
            raise ValueError("session registry needs all paired final rounds")
        preparations = {canonical_bytes(record["preparation"]) for _, record in rounds}
        if len(preparations) != 1:
            raise ValueError("session registry mixes preparations")
        samples = [{"workflow": record["workflow"], "sample_id": record["sample_id"], "final_round": ref,
                    "text": record["candidate"]} for ref, record in rounds]
        samples.sort(key=lambda row: (row["workflow"], row["sample_id"]))
        value = {"schema_version": 1, "kind": "SESSION_BACKTEST_REGISTRY", "preparation": rounds[0][1]["preparation"],
                 "samples": samples, **_base()}
        self._samples(value)
        ref = _store(self.root, destination, canonical_bytes(value))
        return {"status": "PASS", "registry": ref, **_base()}

    def export(self, destination: str, registry_path: str, *, coordinator_session_id: str) -> dict:
        registry_ref = binding(self.root, registry_path)
        value = _json(bound_bytes(self.root, registry_ref))
        rows, context = self._samples(value)
        candidates = [{"id": row["workflow"] + ":" + row["sample_id"], "text": row["text"],
                       "author_session_ids": sorted({r["session_id"] for r in row["rounds"]})} for row in rows]
        original = _store(self.root, "artifacts/session-backtest/coordinator/reference", context["hidden"].encode(), "txt")
        return anonymous_export(self.root, destination, candidates, context=registry_ref,
                                coordinator_session_id=coordinator_session_id, original=original)

    def _export(self, mapping_path: str, registry_ref: dict, rows: list[dict], context: dict) -> dict:
        mapping_ref = binding(self.root, mapping_path)
        if Path(mapping_path).stem != mapping_ref["sha256"]:
            raise ValueError("non-content-addressed anonymous coordinator mapping")
        mapping = _json(bound_bytes(self.root, mapping_ref))
        _schema(self.root, mapping, "mapping")
        commitment_path = (Path(mapping_path).parent / "commitment.json").as_posix()
        commitment = _json(repository_path(self.root, commitment_path).read_bytes())
        if commitment != {"packet": mapping["packet"], "mapping": mapping_ref, "context": registry_ref}:
            raise ValueError("SESSION_STALE_EXPORT_REGISTRY_OR_MAPPING_COMMITMENT")
        if mapping["context"] != registry_ref:
            raise ValueError("SESSION_STALE_EXPORT_REGISTRY")
        from ..workflow.agent_panel import verify_packet
        packet = verify_packet(self.root, mapping["packet"])
        subjects = {subject["id"]: subject for subject in packet["subjects"]}
        candidates = {row["workflow"] + ":" + row["sample_id"]: row for row in rows}
        seen, tokens, original_count = set(), set(), 0
        for row in mapping["mapping"]:
            token = row["token"]
            if token in tokens or token not in subjects or subjects[token]["binding"] != row["public_text"]:
                raise ValueError("session anonymous subject mapping mismatch")
            tokens.add(token)
            raw = bound_bytes(self.root, row["public_text"])
            if row["kind"] == "ORIGINAL_REFERENCE":
                original_count += 1
                expected = context["hidden"].encode()
            else:
                if row["id"] in seen or row["id"] not in candidates:
                    raise ValueError("session anonymous candidate identity mismatch")
                seen.add(row["id"])
                candidate = candidates[row["id"]]
                if (row["text"] != candidate["text"] or row["author_session_ids"] != sorted({r["session_id"] for r in candidate["rounds"]})):
                    raise ValueError("session anonymous author/text mapping mismatch")
                expected = candidate["output"].encode()
            if bound_bytes(self.root, row["text"]) != expected or raw != expected:
                raise ValueError("session anonymous public text differs from registry/reference")
        if seen != set(candidates) or original_count != 1 or tokens != set(subjects):
            raise ValueError("SESSION_INCOMPLETE_ANONYMOUS_PAIRS")
        return mapping

    def summary(self, registry_path: str, mapping_path: str | None = None) -> dict:
        registry_ref = binding(self.root, registry_path)
        records = _json(bound_bytes(self.root, registry_ref))
        rows, context = self._samples(records)
        reading = None
        if mapping_path is not None:
            mapping = self._export(mapping_path, registry_ref, rows, context)
            from ..workflow.agent_panel import summary
            reading = summary(self.root, packet=mapping["packet"])
        excluded_author_readings = []
        if reading is not None:
            author_sessions = {r["session_id"] for row in rows for r in row["rounds"]}
            # AgentPanel checks coordinator/reader separation; backtests also
            # exclude any round author's session, even with a different ID.
            panel = reading["panels"][0] if reading["panels"] else None
            if panel:
                for subject in panel["subjects"]:
                    excluded = [opinion for opinion in subject["opinions"]
                                if opinion["reviewer"]["session_id"] in author_sessions]
                    excluded_author_readings.extend(excluded)
                    full = [reviewer for reviewer in subject["full_reviewers"]
                            if reviewer["session_id"] not in author_sessions]
                    if (subject["status"] == "PASS"
                            and (len({r["id"] for r in full}) < 2 or len({r["session_id"] for r in full}) < 2)):
                        subject["status"] = "PENDING"
                if reading["status"] == "PASS" and any(subject["status"] != "PASS" for subject in panel["subjects"]):
                    reading["status"] = panel["status"] = "PENDING"
        samples = [{"workflow": row["workflow"], "sample_id": row["sample_id"], "text": row["text"],
                    "declared_rounds": len(row["rounds"]), "overlap": overlap_observations(row["output"], context["hidden"]),
                    "style": compare_reference(row["output"], context["reference"])} for row in rows]
        available = reading is not None and reading["status"] == "PASS"
        return {"status": "PASS", "scope": "SESSION_BACKTEST_DESCRIPTIVE_ONLY", "registry": registry_ref,
                "paired_sample_count": len(rows) // 2, "samples": samples,
                "outcome": "DESCRIPTIVE_AGENT_READING_ONLY" if available else "NOT_ESTIMABLE", "agent_reading": reading,
                "excluded_author_readings": excluded_author_readings,
                "declared_shared_information_parity": "VERIFIED_PREPARED_BYTES",
                "declared_character_target_parity": "VERIFIED_PREPARED_BYTES", "actual_token_usage": "NOT_VERIFIED",
                "automatic_winner": None, "literary_acceptance": "PENDING", **_base()}
