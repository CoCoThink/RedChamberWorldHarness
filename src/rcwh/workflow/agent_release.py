"""Agent-reviewed research editions, isolated from stable publication/admission.

Gates follow the evidence floor (rcwh.findings): only integrity failures and
violations of evidence-layer hard locks FAIL. Author preferences, P-Lock
anchors and plan-card details are advisories; checks that are not implemented
are INFO. PENDING means a required input or reviewer is actually missing.
A PASS is local byte-bound MODEL review, never a human/evidence qualification
and never stable/ACTIVE adoption, which stays the owner's decision.
The manifest is the commit marker; pending staging contains no adopted prose.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import tempfile

from ..assets import AssetCatalog, AssetError
from ..assets.paths import repository_path
from ..assets.transactions import digest, sync_directory, write_durable
from ..candidate_reviews import canonical_bytes
from ..contracts import coverage_errors, project_chapters, record_sha256, unique_index
from ..evaluation.style_reference import CHAPTER_HEADING, _chapter_number
from ..io import load_data
from ..promotion import load_promotion_policy, policy_supported
from ..findings import combine as _status
from ..schema import validate_instance
from .agent_panel import AgentPanel, _check_sample, _sample_records


DIRECTORY = "releases/agent"
# Unresolved dependent references are missing inputs, not integrity failures.
_MISSING_INPUT_PREFIXES = ("UNRESOLVED_DEPENDENT_", "UNRESOLVED_HISTORICAL_ADAPTER", "CHAPTER_SCENE_SCOPE_MISSING")


def _split(text: str, scope: tuple[int, ...]) -> tuple[str, dict[int, str]]:
    headings = list(CHAPTER_HEADING.finditer(text))
    ids = [_chapter_number(m["number"]) for m in headings]
    if ids != list(scope):
        raise AssetError(f"chapter heading/coverage mismatch: expected {list(scope)}, got {ids}")
    chapters = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        chapter = text[match.start():end]
        if not text[match.end():end].strip():
            raise AssetError(f"chapter {ids[index]} has no prose body")
        chapters[ids[index]] = chapter
    return text[:headings[0].start()], chapters


def _integrity(text: str) -> dict:
    heading = CHAPTER_HEADING.match(text)
    body = text[heading.end():] if heading else ""
    return {"sha256": digest(text.encode("utf-8")), "bytes": len(text.encode("utf-8")),
            "characters": len(text), "body_characters": len("".join(body.split())),
            "heading": heading.group().strip() if heading else "MISSING"}


class AgentRelease:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.catalog = AssetCatalog.from_repo(self.root)
        self.schema = load_data(repository_path(self.root, "schemas/agent_release_manifest.schema.json"))

    def _validate(self, document: dict, kind: str) -> None:
        schema = self.schema if kind == "manifest" else {
            "$ref": f"#/$defs/{kind}", "$defs": self.schema["$defs"]}
        errors = validate_instance(document, schema)
        if errors:
            raise AssetError(f"invalid agent release {kind}: " + "; ".join(errors))

    def _bound(self, binding: dict) -> bytes:
        raw = repository_path(self.root, binding["path"]).read_bytes()
        if digest(raw) != binding["sha256"]:
            raise AssetError(f"stale agent release binding: {binding['path']}")
        return raw

    def _request(self, request: dict | str | Path) -> dict:
        if not isinstance(request, dict):
            path = Path(request)
            relative = path.relative_to(self.root).as_posix() if path.is_absolute() else path.as_posix()
            request = load_data(repository_path(self.root, relative))
        self._validate(request, "request")
        chapters = project_chapters(self.root)
        try:
            rows = unique_index(request["chapters"], "chapter")
        except ValueError as exc:
            raise AssetError(str(exc)) from exc
        errors = coverage_errors(rows, chapters, "agent release chapter dispositions")
        if errors:
            raise AssetError("; ".join(errors))
        if not any(row["mode"] == "AGENT_CANDIDATE" for row in rows.values()):
            raise AssetError("agent release requires at least one actually changed chapter")
        return request

    def _stable_snapshot(self) -> dict[str, str]:
        paths = [self.root / "data/project/current.json"]
        for directory in ("releases", "data/project", "data/releases"):
            base = self.root / directory
            if base.exists():
                paths.extend(p for p in base.rglob("*") if p.is_file()
                             and not p.relative_to(self.root).as_posix().startswith(DIRECTORY + "/"))
        return {p.relative_to(self.root).as_posix(): digest(p.read_bytes()) for p in paths if p.is_file()}

    def _packet_summary(self, packet: dict) -> dict:
        # An absent packet is a missing review input (PENDING), not a failure.
        if not repository_path(self.root, packet["path"]).is_file():
            raise FileNotFoundError(f"agent review packet not found: {packet['path']}")
        return AgentPanel(self.root).summary(packet=packet)

    def _subject(self, ref: dict, scope: str, binding: dict | None = None) -> tuple[str, dict]:
        report = self._packet_summary(ref["packet"])
        if report["record_integrity_status"] != "PASS" or report.get("findings"):
            return "FAIL", report
        matches = [s for panel in report["panels"] for s in panel["subjects"] if s["id"] == ref["subject_id"]]
        if len(matches) != 1 or matches[0]["scope"] != scope:
            raise AssetError(f"agent release panel subject scope mismatch: {ref['subject_id']}")
        subject = matches[0]
        if binding is not None and subject["binding"] != binding:
            raise AssetError(f"agent release panel candidate binding mismatch: {ref['subject_id']}")
        state = subject["status"]
        if state == "FAIL" and not subject.get("findings"):
            raise AssetError(f"panel subject failed without a recorded finding: {ref['subject_id']}")
        if state == "PASS" and subject["distinct_reviewer_count"] < 2:
            state = "PENDING"
        return state, subject

    def _authors(self, row: dict, subject: dict) -> tuple[str, list[dict]]:
        if "draft" not in row:
            return "PENDING", []
        from ..generation.writing import load_draft
        from ..generation.session import EXECUTION_BASIS

        authors, sessions, seen = [], set(), set()
        current = row["draft"]
        while current is not None:
            key = record_sha256(current)
            if key in seen:
                raise AssetError("agent release author lineage cycle")
            seen.add(key)
            self._bound(current)
            draft, text = load_draft(self.root, current["path"])
            if current == row["draft"] and (draft["candidate"] != row["candidate"] or draft["chapter"] != row["chapter"]
                    or text.encode("utf-8") != self._bound(row["candidate"])):
                raise AssetError("agent release draft differs from candidate chapter")
            if draft.get("execution_basis") != EXECUTION_BASIS:
                return "PENDING", authors
            if draft["package"] != row.get("writing_package"):
                raise AssetError("agent release draft writing package mismatch")
            run = json.loads(self._bound(draft["run"]))
            sessions.add(run["session_id"])
            authors.extend(draft["authors"])
            current = draft["parent"]
        from .attribution import release_attribution
        if "rebind_receipt" not in row and any(s.startswith("rebind-") for s in sessions):
            raise AssetError("rebind draft requires an explicit rebind_receipt")
        attribution = release_attribution(self.root, row) if "rebind_receipt" in row else None
        if attribution is not None:
            authors = attribution["contributors"]
            sessions.update(a["principal_id"].removeprefix("session:")
                            for a in authors + attribution["custodians"])
        if any(o["reviewer"]["session_id"] in sessions for o in subject.get("opinions", [])):
            raise AssetError("candidate author/reviser cannot be a peer reviewer")
        return "PASS", authors

    def _compatibility(self, row: dict) -> tuple[str, dict]:
        from ..generation.lineage import current_compatibility

        if "draft" not in row:
            return "PENDING", {"compatibility": "NOT_CHECKED", "findings": ["DRAFT_REQUIRED"]}
        self._bound(row["draft"])
        report = current_compatibility(self.root, row["draft"]["path"])
        state = "PENDING" if report["compatibility"] == "NOT_CHECKED" else report["status"]
        return state, report

    def _decision(self, row: dict, subject: dict) -> str:
        if "decision" not in row:
            return "PENDING"
        decision = json.loads(self._bound(row["decision"]))
        self._validate(decision, "decision")
        if decision["chapter"] != row["chapter"] or decision["candidate"] != row["candidate"]:
            raise AssetError("coordinator decision candidate/chapter mismatch")
        packet = json.loads(self._bound(row["panel"]["packet"]))
        if decision["coordinator_session_id"] != packet["coordinator_session_id"]:
            raise AssetError("coordinator decision session differs from bound packet")
        if any(r["session_id"] == decision["coordinator_session_id"] for r in subject.get("full_reviewers", [])):
            raise AssetError("coordinator cannot count as a candidate peer reviewer")
        opinions = {record_sha256(o["record"]): o for o in subject.get("opinions", [])}
        considered = {record_sha256(o) for o in decision["considered_opinions"]}
        if considered != set(opinions):
            return "PENDING"  # A new opinion invalidates a previously complete decision.
        rejected = decision["rejected_opinions"]
        rejected_ids = [record_sha256(o["record"]) for o in rejected]
        if len(rejected_ids) != len(set(rejected_ids)) or not set(rejected_ids) <= set(opinions):
            raise AssetError("coordinator rejected opinions are duplicate or unbound")
        negative = {key for key, o in opinions.items() if o["verdict"] in {"FAIL", "REJECT"}}
        if not negative <= set(rejected_ids):
            return "PENDING"  # Every dissent needs an explicit, reasoned ruling.
        # Overruled dissent stays recorded in the decision. A BLOCKING negative
        # still fails the CANDIDATE_PEERS gate; the coordinator cannot lift it.
        if decision["outcome"] == "REJECT":
            return "FAIL"
        return "PASS" if decision["outcome"] == "ADOPT" else "PENDING"

    def _inputs(self, row: dict, *, authors: list[dict] | None = None) -> tuple[dict, dict]:
        author_sessions = {a["principal_id"].removeprefix("session:") for a in authors or []
                           if a["principal_id"].startswith("session:")}
        def check_peer_sessions(subjects):
            if any(o["reviewer"]["session_id"] in author_sessions
                   for subject in subjects for o in subject.get("opinions", [])):
                raise AssetError("candidate author/reviser cannot review own dependent inputs")

        gates = {"WRITING_PACKAGE": "PENDING", "CONTRACT_PEERS": "PENDING",
                 "SOURCE_PEERS": "PENDING", "CORPUS_PEERS": "PENDING"}
        reports = {}
        if "writing_package" not in row:
            return gates, reports
        self._bound(row["writing_package"])
        from .admission import chapter_scope
        from ..corpus.dataset import CorpusRepository

        scope = chapter_scope(self.root, row["writing_package"]["path"], plan_contracts=True)
        if scope["chapter"] != row["chapter"]:
            raise AssetError("agent release writing package chapter mismatch")
        missing_contracts = "CHAPTER_SCENE_SCOPE_MISSING" in scope["findings"]
        missing_inputs = [f for f in scope["findings"] if f.startswith(_MISSING_INPUT_PREFIXES)]
        failures = [f for f in scope["findings"] if f not in missing_inputs]
        if failures:
            raise AssetError("; ".join(failures))
        reports["missing_inputs"] = missing_inputs
        package = load_data(repository_path(self.root, row["writing_package"]["path"]))
        exemplar_binding = package["exemplar_set"]
        self._bound(exemplar_binding)
        exemplars = load_data(repository_path(self.root, exemplar_binding["path"]))
        reports["input_scope"] = scope
        gates["WRITING_PACKAGE"] = "PENDING" if [f for f in missing_inputs if f != "CHAPTER_SCENE_SCOPE_MISSING"] else "PASS"
        if "research_source_sets" in package:
            from ..literary_inputs import LiteraryInputs
            checked = LiteraryInputs(self.catalog).package(row["writing_package"]["path"])
            if checked["status"] != "PASS":
                raise AssetError("supplemental writing input integrity failed")
            # Byte-checked research context; its proposed claims are not
            # evidence and are reported, not held as an unreachable gate.
            reports["supplemental_source_sets"] = checked["supplemental_source_sets"]

        # The candidate's reviewers must also see the exact package and contracts.
        try:
            packet_report = self._packet_summary(row["panel"]["packet"])
        except FileNotFoundError as exc:
            # Only the peer gates wait on the packet; package/source/corpus
            # checks below still run and report their own state.
            packet_report = None
            reports["contract_peer_pending"] = str(exc)
        integrity_failed = packet_report is not None and (
            packet_report["record_integrity_status"] != "PASS" or packet_report.get("findings"))
        if integrity_failed:
            gates["CONTRACT_PEERS"] = "FAIL"
            reports["contract_peer_findings"] = packet_report.get("findings", [])
        elif packet_report is not None:
            subjects = [s for p in packet_report["panels"] for s in p["subjects"]]
            check_peer_sessions(subjects)
            requirements = [("PACKAGE", row["writing_package"])]
            for path in scope["paths"]:
                if path.startswith("data/scenes/") or path in scope.get("advisory_contract_paths", []):
                    requirements.append(("CONTRACT", {"path": path, "sha256": digest(repository_path(self.root, path).read_bytes())}))
            states = ["PENDING"] if missing_contracts else []
            # A contract that contradicts itself or the replayed world fails.
            # Unchecked/unimplemented tiers (e.g. prose semantic replay) are
            # INFO: reported in the contract reports, never a holding gate.
            for report in scope.get("advisory_contract_reports", []):
                tiers = (report["declared_compatibility"]["status"],
                         report["deterministic_world_state_replay"]["status"])
                states.append("FAIL" if "FAIL" in tiers else "PASS")
            for kind, binding in requirements:
                matching = [s for s in subjects if s["scope"] == kind and s["binding"] == binding]
                states.append(_status(s["status"] for s in matching))
            gates["CONTRACT_PEERS"] = _status(states)
            reports["contract_peer_bindings"] = [binding for _, binding in requirements]

        for key, kind, required in (("source_reviews", "SOURCE", set(scope["used_source_ids"])),
                                    ("corpus_reviews", "CORPUS", set(scope["dataset_refs"]))):
            states, found, reviews = [], set(), []
            for ref in row.get(key, []):
                state, subject = self._subject(ref, kind)
                if "binding" not in subject:
                    states.append("FAIL"); reviews.append(subject); continue
                check_peer_sessions([subject])
                identity = subject["source_ref"] if kind == "SOURCE" else subject["dataset_ref"]
                if identity in found or identity not in required:
                    raise AssetError(f"duplicate or out-of-scope {kind} peer review: {identity}")
                found.add(identity)
                if kind == "SOURCE":
                    from ..provenance import ProvenanceRepository
                    provenance = ProvenanceRepository.from_repo(self.root)
                    source = provenance.graph.sources[identity]
                    document = load_data(repository_path(self.root, subject["binding"]["path"]))
                    records = document.get("sources", [document])
                    matches = [s for s in records if s.get("id") == identity]
                    if matches != [source]:
                        raise AssetError("source peer record differs from actual chapter provenance source")
                    source_report = provenance.source_report(source, locators=True)
                    subject = {**subject, "source_proof": source_report}
                    if source_report["status"] != "PASS":
                        # Missing carriers/locators are unresolved research inputs,
                        # not independent-human qualification and not a safety PASS.
                        failures = source_report["findings"]
                        stale = any(any(term in f.upper() for term in ("STALE", "MISMATCH", "INVALID")) for f in failures)
                        state = _status([state, "FAIL" if stale else "PENDING"])
                if kind == "CORPUS":
                    corpus = CorpusRepository(self.catalog)
                    corpus.load(identity, rebuild=True)
                    registry = corpus.registry()[identity]
                    manifest = self.catalog.resolve(registry["manifest_ref"])
                    expected = {"path": manifest.relative_path, "sha256": manifest.sha256}
                    if subject["binding"] != expected or exemplars["manifest_ref"] != manifest.id or exemplars["manifest_sha256"] != manifest.sha256:
                        raise AssetError("corpus peer review does not bind selected exemplar manifest")
                    product_samples = {s["id"]: s for s in subject.get("samples", [])}
                    coverage = {s["sample_id"]: s for s in subject.get("sample_coverage", [])}
                    for segment in exemplars["segments"]:
                        sample = product_samples.get(segment["segment_id"])
                        if sample is None:
                            state = _status([state, "PENDING"]); continue
                        try:
                            records = _sample_records(self.root, sample["binding"])
                            if records is None:
                                raise ValueError("corpus peer sample carrier has no records")
                            _check_sample(records, segment["segment_id"])
                        except (KeyError, OSError, TypeError, ValueError) as exc:
                            raise AssetError("corpus peer sample differs from selected exemplar") from exc
                        actual = next((record for record in records
                                       if isinstance(record, dict)
                                       and segment["segment_id"] in (record.get("segment_id"), record.get("id"))), None)
                        if actual is None or actual.get("text_sha256") != segment["text_sha256"]:
                            raise AssetError("corpus peer sample differs from selected exemplar")
                        state = _status([state, coverage.get(segment["segment_id"], {}).get("status", "PENDING")])
                states.append(state); reviews.append(subject)
            if found != required:
                states.append("PENDING")
            gate = "SOURCE_PEERS" if kind == "SOURCE" else "CORPUS_PEERS"
            # A chapter with no dependent sources/datasets has nothing to review.
            gates[gate] = "PASS" if not required and not states else _status(states)
            if not required:
                reports.setdefault("info", []).append(f"{gate}: NO_DEPENDENT_{kind}S")
            reports[key] = reviews
        return gates, reports

    def _policy(self, row: dict, changed: set[int], book: str, chapter: str) -> str:
        if "policy" not in row:
            return "PENDING"
        agent_path = f"data/promotion/policies/agent/ch{row['chapter']}.v1.json"
        if row["policy"]["path"] == agent_path:
            from ..agent_policies import evaluate_agent_policy
            policy = json.loads(self._bound(row["policy"]))
            checked = evaluate_agent_policy(self.root, policy, row["chapter"], chapter)
            if checked["status"] == "FAIL":
                return "FAIL"
            if row["plock_ref"] != (policy["plock"]["ref"] or "NONE"):
                raise AssetError("agent release P-Lock differs from declared chapter protection")
            if policy["plock"]["required"]:
                from ..literary_eval import evaluate_literary_candidate
                evaluated = evaluate_literary_candidate(self.root, row["plock_ref"], chapter,
                                                       candidate_name=f"agent-ch{row['chapter']}")
                # A P-Lock protects literary work already written; a lost anchor
                # is a replaceable REPLACEMENT_CASE advisory, never evidence.
                if evaluated["machine_status"] == "INFRASTRUCTURE_BLOCKED":
                    return "PENDING"
            return checked["status"]
        expected_path = f"data/promotion/policies/ch{row['chapter']}.json"
        if row["policy"]["path"] != expected_path:
            raise AssetError("agent release policy must be the declared chapter policy")
        self._bound(row["policy"])
        policy = load_promotion_policy(self.root, row["chapter"])
        if not policy_supported(policy, row["chapter"], changed, row["plock_ref"]):
            return "PENDING"
        from ..literary_eval import evaluate_literary_candidate
        payload = evaluate_literary_candidate(self.root, row["plock_ref"], chapter, candidate_name=f"agent-ch{row['chapter']}")
        checks = (all(s in book for s in policy["required_book_strings"]),
                  not any(s in book for s in policy["forbidden_book_strings"]),
                  all(s in book for s in policy["carry_over_anchors"]),
                  payload["machine_status"] == "READY_FOR_BLIND_READ")
        return "PASS" if all(checks) else "FAIL"

    def _evaluate(self, request: dict | str | Path) -> tuple[dict, bytes]:
        request = self._request(request)
        baseline = self.catalog.resolve(request["baseline"]["asset_ref"])
        if baseline.sha256 != request["baseline"]["sha256"] or not self.catalog.assets[baseline.id]["immutable"]:
            raise AssetError("agent release baseline must bind an immutable catalog asset")
        scope = project_chapters(self.root)
        prefix, before = _split(baseline.path.read_bytes().decode("utf-8"), scope)
        rows = unique_index(request["chapters"], "chapter")
        changed = {ch for ch, row in rows.items() if row["mode"] == "AGENT_CANDIDATE"}
        after, reports = dict(before), {}
        gates = {"BASELINE_IDENTITY": "PASS", "BOOK_STRUCTURE": "PASS", "NON_TARGET_INTEGRITY": "PASS"}
        for ch in scope:
            row, base = rows[ch], _integrity(before[ch])
            report = {"chapter": ch, "provenance": "NOT_NEW_AUTHORED", "status": "PASS", "baseline": base,
                      "integrity": base, "gates": {"BYTE_INTEGRITY": "PASS"}, "findings": [], "pending": [],
                      "bindings": {}, "reviews": {}, "minimum_body_characters": 0}
            reports[ch] = report
            if ch not in changed:
                continue
            report["bindings"] = {k: row[k] for k in ("candidate", "panel", "policy", "decision", "writing_package", "draft", "rebind_receipt") if k in row}
            report["gates"] = {name: "PENDING" for name in ("BYTE_INTEGRITY", "FULL_CHAPTER_LENGTH", "CANDIDATE_PEERS", "AUTHOR_PROVENANCE", "CURRENT_WRITING_INPUTS", "COORDINATOR_DECISION", "CHAPTER_SAFETY_POLICY", "WRITING_PACKAGE", "CONTRACT_PEERS", "SOURCE_PEERS", "CORPUS_PEERS")}
            try:
                raw = self._bound(row["candidate"])
                body = raw.decode("utf-8")
                candidate_prefix, candidate = _split(body, (ch,))
                if candidate_prefix:
                    raise AssetError("candidate chapter must start with its heading, not unbound prefatory prose")
                body = candidate[ch]
                integrity = _integrity(body)
                report["integrity"] = integrity
                if body.rstrip() == before[ch].rstrip():
                    raise AssetError("declared changed chapter is identical to baseline")
                report["gates"]["BYTE_INTEGRITY"] = "PASS"
                minimum = max(row["minimum_body_characters"], math.ceil(base["body_characters"] * row["minimum_baseline_ratio"]))
                report["minimum_body_characters"] = minimum
                report["gates"]["FULL_CHAPTER_LENGTH"] = "PASS" if integrity["body_characters"] >= minimum else "FAIL"
                if integrity["body_characters"] < minimum:
                    report["findings"].append(f"chapter excerpt/length regression: {integrity['body_characters']} < {minimum}")
                from ..generation.prose_integrity import prose_integrity
                prose_check = prose_integrity(body)
                report["gates"]["PROSE_INTEGRITY"] = "PENDING" if prose_check["status"] == "WARN" else prose_check["status"]
                report["reviews"]["prose_integrity"] = prose_check
                if prose_check["status"] == "FAIL":
                    report["findings"].append("repeated paragraph padding cannot qualify as full-chapter prose")
                after[ch] = body  # Exact reviewed bytes; no implicit normalization.
            except (KeyError, OSError, UnicodeError, ValueError) as exc:
                report["gates"]["BYTE_INTEGRITY"] = "FAIL"
                report["findings"].append(str(exc))

        book = (prefix + "".join(after[ch] for ch in scope)).encode("utf-8")
        try:
            _split(book.decode("utf-8"), scope)
        except (UnicodeError, ValueError) as exc:
            gates["BOOK_STRUCTURE"] = "FAIL"
        for ch in sorted(changed):
            row, report = rows[ch], reports[ch]
            operations = {
                "CANDIDATE_PEERS": lambda: self._subject(row["panel"], "CANDIDATE", row["candidate"]),
                "AUTHOR_PROVENANCE": lambda: self._authors(row, report["reviews"].get("candidate", {})),
                "CURRENT_WRITING_INPUTS": lambda: self._compatibility(row),
                "COORDINATOR_DECISION": lambda: self._decision(row, report["reviews"].get("candidate", {})),
                "CHAPTER_SAFETY_POLICY": lambda: self._policy(row, changed, book.decode("utf-8"), after[ch]),
                "INPUT_PEERS": lambda: self._inputs(row, authors=report["reviews"].get("authors", [])
                    + report["reviews"].get("author_lineage", {}).get("custodians", [])),
            }
            for name, operation in operations.items():
                try:
                    result = operation()
                    if name == "CANDIDATE_PEERS":
                        report["gates"][name], report["reviews"]["candidate"] = result
                        if result[0] == "FAIL":
                            report["findings"].extend(f"CANDIDATE_PEERS: {f}" for f in result[1].get("findings", []))
                    elif name == "AUTHOR_PROVENANCE":
                        report["gates"][name], report["reviews"]["authors"] = result
                        if "rebind_receipt" in row:
                            from .attribution import release_attribution
                            report["reviews"]["author_lineage"] = release_attribution(self.root, row)
                    elif name == "CURRENT_WRITING_INPUTS":
                        report["gates"][name], report["reviews"]["current_writing_inputs"] = result
                        if result[0] == "FAIL":
                            report["findings"].extend(f"CURRENT_WRITING_INPUTS: {f}" for f in result[1]["findings"])
                    elif name == "INPUT_PEERS":
                        input_gates, input_reports = result
                        report["gates"].update(input_gates); report["reviews"].update(input_reports)
                        report["findings"].extend(f"CONTRACT_PEERS: {f}" for f in input_reports.get("contract_peer_findings", []))
                        report["pending"].extend(f"WRITING_PACKAGE: {f}" for f in input_reports.get("missing_inputs", []))
                        if "contract_peer_pending" in input_reports:
                            report["pending"].append(f"CONTRACT_PEERS: {input_reports['contract_peer_pending']}")
                    else:
                        report["gates"][name] = result
                except (KeyError, OSError, UnicodeError, TypeError, ValueError) as exc:
                    # Integrity/binding violations block; an absent file or key
                    # is a missing input that leaves the gate PENDING.
                    state = "PENDING" if isinstance(exc, (KeyError, FileNotFoundError)) else "FAIL"
                    report["gates"]["WRITING_PACKAGE" if name == "INPUT_PEERS" else name] = state
                    (report["findings"] if state == "FAIL" else report["pending"]).append(f"{name}: {exc}")
            report["pending"] += [name for name, status in report["gates"].items() if status == "PENDING"]
            report["status"] = _status(report["gates"].values())
            report["provenance"] = {"PASS": "RESEARCH_AGENT_REVIEWED", "PENDING": "RESEARCH_AGENT_PENDING", "FAIL": "RESEARCH_AGENT_FAILED"}[report["status"]]
        for ch in scope:
            gates[f"CH{ch}"] = reports[ch]["status"]
            if ch not in changed and after[ch] != before[ch]:
                gates["NON_TARGET_INTEGRITY"] = "FAIL"
        state = _status(gates.values())
        output = f"{DIRECTORY}/{request['id']}"
        manifest = {
            "schema_version": 1, "manifest_kind": "AGENT_RELEASE_MANIFEST", "id": request["id"], "status": state,
            "provenance": {"PASS": "RESEARCH_AGENT_REVIEWED", "PENDING": "RESEARCH_AGENT_PENDING", "FAIL": "RESEARCH_AGENT_FAILED"}[state],
            "authority_effect": "NONE", "usage": "RESEARCH_ONLY", "independent_human_admission": False,
            "stable_active_effect": "NONE", "automatic_winner": False,
            "baseline": {"asset_ref": baseline.id, "sha256": baseline.sha256, "path": baseline.relative_path, "bytes": baseline.size},
            "request_sha256": record_sha256(request), "scope": list(scope), "changed_chapters": sorted(changed),
            "chapters": [reports[ch] for ch in scope], "gates": gates,
            "findings": [f"CH{ch}: {finding}" for ch in scope for finding in reports[ch]["findings"]],
            "pending": [f"CH{ch}: {reason}" for ch in scope for reason in reports[ch]["pending"]],
            "output": {"directory": output, "manifest_path": f"{output}/manifest.json",
                       "text": {"path": f"{output}/book.md", "sha256": digest(book), "bytes": len(book)} if state == "PASS" else None},
        }
        if "book_review" in request:
            # Continuity reading is always advisory, independent of every gate.
            excluded = {a["principal_id"].removeprefix("session:") for report in reports.values()
                        for a in report["reviews"].get("authors", [])
                        + report["reviews"].get("author_lineage", {}).get("custodians", [])}
            manifest["advisories"] = {"book_continuity": self._book_review(request["book_review"], book, excluded)}
        self._validate(manifest, "manifest")
        return manifest, book

    def _book_review(self, ref: dict, book: bytes, excluded: set[str]) -> dict:
        try:
            from .book_review import subjects as book_subjects
            subjects = book_subjects(self.root, ref, book=book, chapters=list(project_chapters(self.root)))
            report = self._packet_summary(ref["packet"])
            if any(o["reviewer"]["session_id"] in excluded for panel in report["panels"]
                   for subject in panel["subjects"] for o in subject["opinions"]):
                raise AssetError("book author/reviser/custodian cannot be its continuity reader")
            progress = {s["id"]: s for panel in report["panels"] for s in panel["subjects"]}
            return {"severity": "ADVISORY", "gate_effect": "NONE", "packet": ref["packet"],
                    "status": report["status"], "panels": report["panels"], "findings": report["findings"],
                    "segments": [{"subject_id": s["id"], "chapters": s.get("chapters", list(project_chapters(self.root))),
                                  "binding": s["binding"], "status": progress[s["id"]]["status"],
                                  "distinct_reviewer_count": progress[s["id"]]["distinct_reviewer_count"]} for s in subjects]}
        except (KeyError, OSError, TypeError, ValueError) as exc:
            return {"severity": "ADVISORY", "gate_effect": "NONE", "status": "INVALID", "findings": [str(exc)]}

    def _evaluate_scoped(self, request: dict | str | Path) -> tuple[dict, bytes]:
        # All chapters bind the same corpus: verify its rebuild once per pass.
        from ..corpus.dataset import rebuild_scope
        with rebuild_scope():
            return self._evaluate(request)

    def evaluate(self, request: dict | str | Path) -> dict:
        return self._evaluate_scoped(request)[0]

    def build(self, request: dict | str | Path, *, allow_pending: bool = False) -> dict:
        snapshot = self._stable_snapshot()
        manifest, book = self._evaluate_scoped(request)
        if manifest["status"] == "FAIL" or (manifest["status"] == "PENDING" and not allow_pending):
            raise AssetError(f"agent release {manifest['status']}; only explicit pending staging is allowed")
        base = repository_path(self.root, DIRECTORY)
        target = repository_path(self.root, manifest["output"]["directory"])
        base.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise AssetError("agent release already exists; refusing overwrite")
        stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=base))
        reserved = False
        try:
            if manifest["status"] == "PASS":
                write_durable(stage / "book.md", book)
            write_durable(stage / "manifest.json", canonical_bytes(manifest))
            # Recompute all bindings and reviews just before publishing a marker.
            latest, latest_book = self._evaluate_scoped(request)  # Fresh scope: genuine re-verification.
            if latest != manifest or latest_book != book or self._stable_snapshot() != snapshot:
                raise AssetError("agent release inputs or stable storage changed while staging")
            target.mkdir()  # Exclusive reservation; never replace even an empty edition.
            reserved = True
            if manifest["status"] == "PASS":
                os.link(stage / "book.md", target / "book.md")
            os.link(stage / "manifest.json", target / "manifest.json")  # Atomic commit marker, no overwrite.
            sync_directory(target)
            sync_directory(base)
        except BaseException:
            if reserved:
                shutil.rmtree(target)
            raise
        finally:
            shutil.rmtree(stage)
        return manifest
