"""Receive original opinions without deciding their truth or granting adoption."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import tempfile

from ..assets import AssetCatalog
from ..assets.ingest import AssetIntake
from ..assets.paths import repository_path
from ..candidate_reviews import bound_data, canonical_bytes, digest
from ..io import load_data
from ..schema import validate_instance


LANES = ("source", "corpus-pilot", "corpus-full", "p9", "pilot", "scene-reading")
PILOT_SELECTION = "data/evaluation/pilot85_87/review_selection.json"
CLOSURE = "data/project/closure_roots.json"
DATASETS = {"corpus-pilot": "corpus:front80:pilot:v1", "corpus-full": "corpus:front80:v1-candidate"}
SCHEMAS = {"source": "source_audit_review", "corpus-pilot": "corpus_audit_review",
           "corpus-full": "corpus_audit_review", "p9": "paired_review", "scene-reading": "semantic_reading"}
DIRECTORIES = {"source": "data/provenance/audits/reviews", "corpus-pilot": "data/corpus/reviews",
               "corpus-full": "data/corpus/reviews", "p9": "data/evaluation/paired_reviews",
               "pilot": "data/evaluation/pilot85_87/reviews", "scene-reading": "data/evaluation/scene_readings"}


def selection_path(lane: str) -> str:
    if lane not in LANES:
        raise ValueError(f"未知评审类别: {lane}")
    if lane in DATASETS:
        return f"data/corpus/audits/{digest(DATASETS[lane].encode())}.json"
    return {"source": "data/provenance/audits/selection.json", "p9": "data/evaluation/paired_selection.json",
            "pilot": PILOT_SELECTION, "scene-reading": "data/evaluation/scene_readings.json"}[lane]


def _validate(root: Path, value: dict, schema: str) -> None:
    errors = validate_instance(value, root / f"schemas/{schema}.schema.json")
    if errors:
        raise ValueError("评审字段无效: " + "; ".join(errors))


def _read_original(path: Path) -> tuple[bytes, dict]:
    path = path.absolute()
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or not path.is_file():
        raise ValueError("原始评审必须是普通文件，不允许符号链接")
    raw = path.read_bytes()
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"JSON 重复字段: {key}")
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("原始评审必须是 JSON 对象")
    return raw, value


def _unfilled(value, prefix="") -> list[str]:
    if value is None or isinstance(value, str) and not value.strip():
        return [prefix]
    if isinstance(value, dict):
        return [issue for key, item in value.items() for issue in _unfilled(item, f"{prefix}/{key}")]
    if isinstance(value, list):
        return [issue for index, item in enumerate(value) for issue in _unfilled(item, f"{prefix}/{index}")]
    return []


def lane_summary(root: Path, lane: str) -> dict:
    if lane == "source":
        from ..provenance import ProvenanceRepository
        from ..provenance.audit import SourceAudit
        return SourceAudit(ProvenanceRepository.from_repo(root)).summary()
    if lane in DATASETS:
        from ..corpus.audit import CorpusAudit
        return CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASETS[lane], rebuild=False)
    if lane == "p9":
        from ..paired_review import PairedReview
        return PairedReview(AssetCatalog.from_repo(root)).selected_summary()
    if lane == "pilot":
        from ..evaluation.pilot import PilotStudy, selected_reviews
        study = PilotStudy(root)
        return selected_reviews(root, digest(canonical_bytes(study.context())))
    if lane == "scene-reading":
        from ..evaluation.semantics import check_reading
        from ..evaluation.state import SceneStateAdapter
        from ..evaluation.semantics import make_request
        from ..competition import CompetitionRegistry
        # Match the current production request, not a guessed historical context.
        contracts = [load_data(p) for p in sorted((root / "data/scenes").glob("*.yaml"))]
        from ..candidate_reviews import candidate_bytes
        requests = []
        for record in CompetitionRegistry.from_repo(root).records.values():
            for candidate in record["candidates"]:
                for contract in contracts:
                    if contract["chapter"] == record["chapter"]:
                        adapter = SceneStateAdapter(root, contract)
                        for version in (1, 2):
                            requests.append(make_request(contract, candidate_bytes(root, candidate).decode(),
                                                         adapter.snapshot(request_version=version), candidate.get("authors", []),
                                                         request_version=version))
        rows = []
        for binding in load_data(repository_path(root, selection_path(lane)))["readings"]:
            reading = bound_data(root, binding)
            _validate(root, reading, "semantic_reading")
            matches = [r for r in requests if all(reading[k] == r[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256"))]
            result = check_reading(matches[0], reading, load_data(root / "schemas/semantic_reading.schema.json"), root=root) if matches else {"status": "PENDING", "pending": ["NO_CURRENT_PRODUCTION_REQUEST_MATCH"]}
            rows.append({"path": binding["path"], **result})
        return {"status": "FAIL" if any(r["status"] == "FAIL" for r in rows) else "PENDING",
                "review_count": len(rows), "readings": rows, "automatic_literary_pass": False}
    raise ValueError(f"未知评审类别: {lane}")


def _protocol_preflight(root: Path, lane: str, selected: dict, record: dict) -> None:
    protocol = bound_data(root, selected["protocol"])
    if record["protocol_sha256"] != selected["protocol"]["sha256"]:
        raise ValueError("评审绑定的协议已过期")
    if lane == "source":
        identities = [r["source_ref"] for r in record["results"]]
        if len(identities) != len(set(identities)) or not set(identities) <= {s["source_ref"] for s in protocol["sources"]}:
            raise ValueError("来源复核对象重复或不在协议内")
    elif lane in DATASETS:
        if record["dataset_ref"] != DATASETS[lane] or record["manifest_sha256"] != protocol["manifest_sha256"]:
            raise ValueError("语料版本或摘要已过期")
        identities = [r["segment_id"] for r in record["checks"]]
        if len(identities) != len(set(identities)) or set(identities) != {s["segment_id"] for s in protocol["samples"]}:
            raise ValueError("语料审查样本不完整或重复")
    elif lane == "p9":
        from ..paired_review import PairedReview
        _, mapping = PairedReview(AssetCatalog.from_repo(root)).packet(selected["protocol"]["path"])
        if record["packet_sha256"] != selected["packet"]["sha256"]:
            raise ValueError("盲评包摘要已过期")
        if record["reviewer"]["id"] in protocol["author_ids"]:
            raise ValueError("作者自评不能登记为独立盲评")
        identities = [r["pair_id"] for r in record["pairs"]]
        if len(identities) != len(set(identities)) or set(identities) != {p["pair_id"] for p in mapping["pairs"]}:
            raise ValueError("盲评配对不完整或重复")
        if any(set(row["scores"]) != set(protocol["dimensions"]) for row in record["pairs"]):
            raise ValueError("盲评维度与协议不符")


def _scene_preflight(root: Path, original: dict, request_path: Path | None) -> dict:
    from ..evaluation.semantics import check_reading, make_request, validate_request
    from ..evaluation.state import SceneStateAdapter
    if request_path is None:
        raise ValueError("场景判读登记需要 --request 冻结请求文件")
    request = load_data(request_path)
    validate_request(request)
    contracts = [load_data(p) for p in sorted((root / "data/scenes").glob("*.yaml"))]
    contract = next((c for c in contracts if c["id"] == request["contract"]["id"]), None)
    if contract is None or contract != request["contract"]:
        raise ValueError("场景合同已变更或不是当前正式合同")
    # Verify candidate bytes against a repository artifact instead of trusting embedded text.
    from ..competition import CompetitionRegistry
    from ..candidate_reviews import candidate_bytes
    candidates = [c for record in CompetitionRegistry.from_repo(root).records.values()
                  if record["chapter"] == contract["chapter"] for c in record["candidates"]]
    matches = [c for c in candidates if candidate_bytes(root, c).decode() == request["text"]]
    if not matches:
        raise ValueError("请求正文未匹配当前竞争候选；请使用当前候选准备请求")
    if not any(c.get("authors", []) == request["authors"] for c in matches):
        raise ValueError("请求作者身份与当前候选登记不符，不能用请求侧声明替换正式作者信息")
    fresh = make_request(contract, request["text"], SceneStateAdapter(root, contract).snapshot(request_version=request["schema_version"]),
                         request["authors"], request_version=request["schema_version"])
    if fresh != request:
        raise ValueError("场景判读请求上下文已过期")
    if original["producer"]["kind"] != "INDEPENDENT_HUMAN":
        raise ValueError("此接收命令仅登记真人意见；模型轨迹使用既有 semantic run/check 流程")
    if any(original["producer"][key] == author[key] for author in request["authors"] for key in ("principal_id", "source_id")):
        raise ValueError("作者自注不能登记为独立判读")
    report = check_reading(request, original, load_data(root / "schemas/semantic_reading.schema.json"), root=root)
    if report["status"] == "FAIL" and not report["checks"]:
        raise ValueError("场景判读结构/绑定无效: " + "; ".join(report["findings"]))
    return report


def prepare_registration(root: Path, lane: str, file: Path, *, origin: str, identity: str | None = None,
                         request_path: Path | None = None) -> dict:
    """Read-only validation, including current selected opinions and frozen inputs."""
    if not origin.strip():
        raise ValueError("来源说明 --origin 不能为空")
    path = selection_path(lane)
    selected_raw = repository_path(root, path).read_bytes()
    selected = json.loads(selected_raw)
    raw, original = _read_original(file)
    sha = digest(raw)
    record_id = identity or f"{lane}:{sha[:12]}"
    if not record_id.strip():
        raise ValueError("评审 id 不能为空")
    if lane == "scene-reading":
        _validate(root, original, "semantic_reading")
        if any(not original["producer"][key].strip() for key in ("principal_id", "source_id")):
            raise ValueError("判读者身份和来源不能为空白")
        scene_report = _scene_preflight(root, original, request_path)
        record = original
    elif lane == "pilot":
        from ..evaluation.comparison import load_comparative_packet, validate_comparative_review
        from ..evaluation.pilot import PilotStudy, selected_reviews
        expected = digest(canonical_bytes(PilotStudy(root).context()))
        current = selected_reviews(root, expected)
        if current["findings"]:
            raise ValueError("既有阅读登记无效: " + "; ".join(current["findings"]))
        export = repository_path(root, selected["export_root"])
        packet, mapping, texts = load_comparative_packet(export, expected)
        if "raw_review" in original:
            raise ValueError("读者原件不能包含 raw_review 接收元数据")
        issues = _unfilled(original)
        if issues:
            raise ValueError("未填写字段: " + ", ".join(issues))
        validate_comparative_review(original, packet, mapping, texts)
        if identity is not None and identity != original["id"]:
            raise ValueError("pilot 的 --id 必须等于读者原件中的 id")
        record_id = original["id"]
        record = {**original, "raw_review": {"path": f"{DIRECTORIES[lane]}/raw/{sha}.json", "sha256": sha}, "authority_effect": "NONE"}
    else:
        issues = _unfilled(original)
        if issues:
            raise ValueError("未填写字段: " + ", ".join(issues))
        record = {**original, "schema_version": 1, "id": record_id,
                  "raw_review": {"asset_ref": f"asset:sha256:{sha}", "sha256": sha}, "authority_effect": "NONE"}
        schema = load_data(root / f"schemas/{SCHEMAS[lane]}.schema.json")
        expected_keys = set(schema["required"]) - {"schema_version", "id", "raw_review", "authority_effect"}
        if set(original) != expected_keys:
            raise ValueError("原件字段必须与该类别模板一致，不允许夹带结构化元数据")
        _validate(root, record, SCHEMAS[lane])
        lane_summary(root, lane)
        _protocol_preflight(root, lane, selected, record)
    key = "readings" if lane == "scene-reading" else "reviews"
    selection_schema = {"source": "source_audit_selection", "p9": "paired_review_selection",
                        "pilot": "pilot_review_selection", "scene-reading": "semantic_reading_index"}.get(lane, "corpus_audit_selection")
    _validate(root, selected, selection_schema)
    for binding in selected[key]:
        existing = bound_data(root, binding)
        if lane == "scene-reading":
            if all(existing[k] == record[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")):
                raise ValueError("该请求已有登记判读；既有选择器只读取首条，不能追加一条不会被使用的意见")
        elif existing["id"] == record_id:
            raise ValueError("重复评审 id")
        elif lane == "pilot":
            if any(existing["reviewer"][k] == original["reviewer"][k] for k in ("principal_id", "source_id")):
                raise ValueError("重复评审者或意见来源")
        elif existing["reviewer"]["id"] == original["reviewer"]["id"]:
            raise ValueError("重复评审者")
    relative = f"{DIRECTORIES[lane]}/{sha}.json"
    if repository_path(root, relative).exists():
        raise ValueError("该原件已有结构化记录，拒绝覆盖或重复登记")
    closure_path = repository_path(root, CLOSURE)
    closure_raw = closure_path.read_bytes() if closure_path.exists() else None
    closure = json.loads(closure_raw) if closure_raw is not None else None
    if closure:
        bindings = [b for b in closure["records"] if b["path"] == path]
        if len(bindings) > 1 or bindings and bindings[0]["sha256"] != digest(selected_raw):
            raise ValueError("选择文件的闭包绑定已过期；不能用接收操作刷新旧绑定")
    return {"lane": lane, "id": record_id, "raw": raw, "original": original, "record": record,
            "relative": relative, "selection_path": path, "selection_raw": selected_raw, "selection": selected,
            "closure_raw": closure_raw, "closure": closure, "key": key,
            "scene_report": scene_report if lane == "scene-reading" else None}


@contextmanager
def _intake_lock(root: Path):
    path = repository_path(root, ".rcwh-cache/review-intake.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.write(b"\0"); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _replace(root: Path, relative: str, before: bytes, after: bytes) -> None:
    path = repository_path(root, relative)
    if path.read_bytes() != before:
        raise ValueError(f"文件并发变更，拒绝覆盖: {relative}")
    descriptor, name = tempfile.mkstemp(prefix=".review-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(after); handle.flush(); os.fsync(handle.fileno())
        if repository_path(root, relative).read_bytes() != before:
            raise ValueError(f"文件并发变更，拒绝覆盖: {relative}")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def register(root: Path, lane: str, file: Path, *, origin: str, identity: str | None = None,
             dry_run: bool = False, request_path: Path | None = None) -> dict:
    if dry_run:
        plan = prepare_registration(root, lane, file, origin=origin, identity=identity, request_path=request_path)
        return {"status": "PASS", "scope": "REVIEW_REGISTRATION_PREFLIGHT", "dry_run": True,
                "id": plan["id"], "lane": lane, "written_files": [], "authority_effect": "NONE"}
    # Reject invalid inputs before creating even the coordinator lock file.
    plan = prepare_registration(root, lane, file, origin=origin, identity=identity, request_path=request_path)
    with _intake_lock(root):
        if repository_path(root, plan["selection_path"]).read_bytes() != plan["selection_raw"]:
            raise ValueError("选择文件在预检后改变，请重新预检")
        closure_path = repository_path(root, CLOSURE)
        if (closure_path.read_bytes() if closure_path.exists() else None) != plan["closure_raw"]:
            raise ValueError("闭包文件在预检后改变，请重新预检")
        if file.read_bytes() != plan["raw"]:
            raise ValueError("原件在预检后改变")
        if lane == "pilot":
            raw_relative = plan["record"]["raw_review"]["path"]
            raw_path = repository_path(root, raw_relative)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            if raw_path.exists():
                if raw_path.read_bytes() != plan["raw"]:
                    raise ValueError("原件路径已有不同内容")
            else:
                with raw_path.open("xb") as handle:
                    handle.write(plan["raw"])
            raw_binding = plan["record"]["raw_review"]
        else:
            receipt = AssetIntake(root).ingest(file, origin=origin, kind="REVIEW_RECORD")
            raw_binding = {"asset_ref": receipt["asset_ref"], "sha256": receipt["sha256"]}
            if raw_binding["sha256"] != digest(plan["raw"]):
                raise ValueError("实际接收原件与预检内容不同；原件已接收但未登记")
            if lane != "scene-reading":
                plan["record"]["raw_review"] = raw_binding
        new_raw = plan["raw"] if lane == "scene-reading" else canonical_bytes(plan["record"])
        selected = deepcopy(plan["selection"])
        selected[plan["key"]].append({"path": plan["relative"], "sha256": digest(new_raw)})
        selected_raw = canonical_bytes(selected)
        changes = [(plan["selection_path"], plan["selection_raw"], selected_raw)]
        if plan["closure"] is not None:
            closure = deepcopy(plan["closure"])
            changed_binding = False
            for binding in closure["records"]:
                if binding["path"] == plan["selection_path"]:
                    binding["sha256"] = digest(selected_raw)
                    changed_binding = True
            if changed_binding:
                changes.append((CLOSURE, plan["closure_raw"], canonical_bytes(closure)))
        written = []
        record_path = repository_path(root, plan["relative"])
        created = False
        write_complete = False
        created_identity = None
        try:
            record_path.parent.mkdir(parents=True, exist_ok=True)
            with record_path.open("xb") as handle:
                created = True
                stat = os.fstat(handle.fileno())
                created_identity = (stat.st_dev, stat.st_ino)
                handle.write(new_raw)
                handle.flush()
                write_complete = True
            for relative, before, after in changes:
                _replace(root, relative, before, after)
                written.append((relative, before, after))
            report = plan["scene_report"] if lane == "scene-reading" else lane_summary(root, lane)
            if lane == "pilot" and report["findings"]:
                raise ValueError("; ".join(report["findings"]))
        except (Exception, KeyboardInterrupt) as exc:
            conflicts = []
            for relative, before, after in reversed(written):
                try:
                    _replace(root, relative, after, before)
                except (OSError, ValueError) as rollback:
                    conflicts.append(str(rollback))
            if created and not conflicts:
                current_path = repository_path(root, plan["relative"])
                if current_path.exists():
                    stat = current_path.stat()
                    if (stat.st_dev, stat.st_ino) == created_identity and (not write_complete or current_path.read_bytes() == new_raw):
                        current_path.unlink()
                    else:
                        conflicts.append("本次记录在回滚前发生外部变更，未删除")
            raise ValueError(f"原件已接收，但登记失败并回滚: {exc}" + (f"；回滚冲突需人工处理: {conflicts}" if conflicts else "")) from exc
        return {"status": report["status"], "scope": "REVIEW_REGISTRATION_ONLY", "registered": True,
                "lane": lane, "id": plan["id"], "raw_review": raw_binding, "lane_report": report,
                "written_files": [plan["relative"], *[r for r, _, _ in changes]],
                "authority_effect": "NONE", "evidence_effect": "NONE", "automatic_literary_pass": False,
                "next": "将新文件纳入 Git 后运行 project acceptance --require-tracked --require-complete；登记不代表采用或文学通过。"}


def resolve_spans(file: Path, texts: Path, output: Path) -> dict:
    _, original = _read_original(file)
    value = deepcopy(original)
    sources = {}
    if texts.is_dir():
        observations = value.get("observations", {})
        for token in observations:
            if not re.fullmatch(r"read-[a-f0-9]{12}", token):
                raise ValueError("非法匿名文本 token")
            sources[token] = repository_path(texts, f"{token}.txt").read_bytes().decode()
    else:
        sources[None] = _read_text(texts)
    resolved = 0
    def walk(item, text):
        nonlocal resolved
        if isinstance(item, dict):
            if "spans" in item:
                for span in item["spans"]:
                    if not isinstance(span.get("quote"), str) or not span["quote"]:
                        raise ValueError("引句不能为空")
                    quote = span["quote"]
                    starts = [m.start() for m in re.finditer(f"(?={re.escape(quote)})", text)]
                    if "start" in span or "end" in span:
                        if set(span) != {"start", "end", "quote"} or type(span["start"]) is not int or type(span["end"]) is not int or not 0 <= span["start"] < span["end"] <= len(text) or text[span["start"]:span["end"]] != quote:
                            raise ValueError("已有偏移与原文不符")
                    else:
                        if set(span) - {"quote", "occurrence"}:
                            raise ValueError("引句对象含未知字段")
                        occurrence = span.pop("occurrence", None)
                        if not starts or occurrence is None and len(starts) != 1:
                            raise ValueError(f"引句匹配不唯一（{len(starts)}处），位置={starts}；需要 occurrence（从1计）: {quote!r}")
                        if occurrence is not None and (type(occurrence) is not int or not 1 <= occurrence <= len(starts)):
                            raise ValueError("occurrence 超出范围")
                        span["start"] = starts[(occurrence or 1) - 1]
                        span["end"] = span["start"] + len(quote)
                        resolved += 1
            for key, child in item.items():
                if key != "spans":
                    walk(child, text)
        elif isinstance(item, list):
            for child in item:
                walk(child, text)
    if None in sources:
        walk(value, sources[None])
    else:
        for token, item in value["observations"].items():
            walk(item, sources[token])
    with output.open("xb") as handle:
        handle.write(canonical_bytes(value))
    return {"status": "PASS", "scope": "PRE_SUBMISSION_SPAN_RESOLUTION", "resolved_spans": resolved,
            "output": str(output), "authority_effect": "NONE", "instruction": "请读者核对完整文件，再作为原始意见提交。"}


def _read_text(path: Path) -> str:
    if path.is_symlink() or any(p.is_symlink() for p in path.absolute().parents):
        raise ValueError("文本不允许符号链接")
    return path.read_bytes().decode()


def scene_template(request_path: Path, output: Path) -> dict:
    from ..evaluation.semantics import validate_request
    from ..evaluation.state import canonical_target
    request = load_data(request_path)
    validate_request(request)
    contract = request["contract"]
    targets = [b["id"] for b in contract.get("required_beats", []) + contract.get("forbidden_beats", []) + contract.get("knowledge_guards", [])]
    targets += [canonical_target(c["equals"]) for c in contract.get("exit_state", [])]
    template = {"schema_version": 1, "report_kind": "TEMPLATE",
                **{k: request[k] for k in ("candidate_sha256", "contract_sha256", "context_sha256")},
                "producer": {"principal_id": "", "source_id": "", "kind": "INDEPENDENT_HUMAN"},
                "coverage": [], "unresolved": [], "events": [], "notes": ""}
    with output.open("xb") as handle:
        handle.write(canonical_bytes(template))
    return {"status": "PASS", "scope": "SCENE_READING_TEMPLATE_ONLY", "output": str(output),
            "constraints_to_examine": targets, "contract": contract,
            "authority_effect": "NONE", "reading_status": "NOT_SUBMITTED",
            "instruction": "逐项阅读：确认检查过的填 coverage，不确定的填 unresolved；据原文填写 events。完成后改 report_kind 为 REVIEW_OPINION。"}


def status(root: Path) -> dict:
    rows = []
    for lane in LANES:
        try:
            report = lane_summary(root, lane)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            report = {"status": "FAIL", "findings": [str(exc)]}
        material = {"source": "delivery materialize source-review-v2",
                    "corpus-pilot": "delivery materialize corpus-review (pilot-audit)",
                    "corpus-full": "delivery materialize corpus-review (full-audit)",
                    "p9": "artifacts/reviews/p9-preparation-20261009/blind-pairs.zip",
                    "pilot": "artifacts/analysis/evaluation-refactor-20261009/pilot-reading/public",
                    "scene-reading": "semantic prepare + reviews scene-template"}[lane]
        rows.append({"lane": lane, "selection": selection_path(lane), "reading_material": material,
                     "guide": "docs/runbooks/REVIEWER_GUIDE_ZH.md",
                     "minimum_reviewers": report.get("minimum_reviewers", 2 if lane == "pilot" else None), **report})
    return {"status": "FAIL" if any(r["status"] == "FAIL" for r in rows) else "PENDING",
            "scope": "REVIEW_INPUT_STATUS", "lanes": rows, "authority_effect": "NONE",
            "independence_basis": "SUBMITTED_IDENTITIES_AND_ATTESTATIONS_NOT_EXTERNALLY_VERIFIED",
            "automatic_literary_pass": False}
