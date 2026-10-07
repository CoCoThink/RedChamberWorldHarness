from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_data


_SENTENCE_SPLIT = re.compile(r"[。！？!?；;]+|\n+")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
_SPACE = re.compile(r"\s+")


def _cv(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance) / mean


def _clean_units(text: str) -> tuple[list[str], list[str]]:
    paragraphs = [
        _SPACE.sub(" ", x).strip()
        for x in _PARAGRAPH_SPLIT.split(text)
        if _SPACE.sub(" ", x).strip()
    ]
    sentences = [
        _SPACE.sub(" ", x).strip()
        for x in _SENTENCE_SPLIT.split(text)
        if _SPACE.sub(" ", x).strip()
    ]
    return paragraphs, sentences


def _sha_token(prefix: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{digest}"


def _walk_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield ("KEY", str(key))
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    elif isinstance(value, str):
        yield ("VALUE", value)


@dataclass
class LiteraryEvaluatorSuite:
    root: Path
    data: dict[str, Any]

    @classmethod
    def from_repo(cls, root: Path) -> "LiteraryEvaluatorSuite":
        path = root / "data" / "literary_eval" / "v05_suite.json"
        return cls(root=root, data=load_data(path) or {})

    def summary(self) -> dict[str, Any]:
        completion = self.data.get("completion", {})
        return {
            "id": self.data.get("id"),
            "status": self.data.get("status"),
            "authority": self.data.get("authority"),
            "automatic_literary_pass": self.data.get("automatic_literary_pass"),
            "acceptance": completion,
            "all_acceptance": bool(completion) and all(completion.values()),
        }

    def culture_deletion_test(self, text: str) -> dict[str, Any]:
        cfg = self.data["culture_not_museum"]
        _, sentences = _clean_units(text)
        spans = []
        suspect = []
        for index, sentence in enumerate(sentences, start=1):
            culture_hits = [x for x in cfg["culture_terms"] if x in sentence]
            if not culture_hits:
                continue
            action_hits = [x for x in cfg["action_terms"] if x in sentence]
            relation_hits = [x for x in cfg["relation_terms"] if x in sentence]
            deleted = sentence
            for term in culture_hits:
                deleted = deleted.replace(term, "")
            deleted = _SPACE.sub(" ", deleted).strip(" ，、：；。！？")
            attached = bool(action_hits or relation_hits)
            item = {
                "sentence_index": index,
                "culture_hits": culture_hits,
                "action_hits": action_hits,
                "relation_hits": relation_hits,
                "action_attached": attached,
                "deletion_variant": deleted,
                "source_chars": len(sentence),
                "deleted_chars": len(sentence) - len(deleted),
            }
            spans.append(item)
            if (
                len(sentence) >= cfg["minimum_sentence_chars"]
                and not attached
            ):
                suspect.append(item)
        return {
            "status": "FLAG_MUSEUM_RISK" if suspect else "PASS",
            "culture_spans": len(spans),
            "suspect_spans": suspect,
            "automatic_failure": False,
            "note": (
                "Deletion test is a machine probe: culture-only display spans are flagged "
                "for human review, but the heuristic cannot prove literary failure."
            ),
        }

    def exposition_detector(self, text: str) -> dict[str, Any]:
        cfg = self.data["exposition"]
        exact_hits = [x for x in cfg["hard_terms"] if x in text]
        pattern_hits = []
        for pattern in cfg.get("generic_patterns", []):
            for match in re.finditer(pattern, text):
                pattern_hits.append(match.group(0))
        hits = list(dict.fromkeys(exact_hits + pattern_hits))
        return {
            "status": "FAIL_EXPLICIT_EXPOSITION" if hits else "PASS",
            "hits": hits,
            "automatic_failure": bool(hits),
        }

    def ambiguity_preservation(self, text: str) -> dict[str, Any]:
        cfg = self.data["ambiguity"]
        guard_hits = []
        for guard in cfg.get("guards", []):
            hits = [x for x in guard["any_text"] if x in text]
            if hits:
                guard_hits.append({
                    "id": guard["id"],
                    "hits": hits,
                    "protects": guard["protects"],
                })
        generic_hits = [x for x in cfg.get("generic_closure_terms", []) if x in text]
        bad = bool(guard_hits or generic_hits)
        return {
            "status": "FAIL_AMBIGUITY_CLOSURE" if bad else "PASS",
            "guard_hits": guard_hits,
            "generic_hits": generic_hits,
            "automatic_failure": bad,
        }

    def structural_variation(self, text: str) -> dict[str, Any]:
        cfg = self.data["structure"]
        paragraphs, sentences = _clean_units(text)
        if len(text) < cfg["min_chars_for_full_check"]:
            return {
                "status": "INSUFFICIENT_SAMPLE",
                "automatic_failure": False,
                "paragraphs": len(paragraphs),
                "sentences": len(sentences),
                "risks": [],
            }

        paragraph_lengths = [len(x) for x in paragraphs]
        sentence_lengths = [len(x) for x in sentences]
        paragraph_cv = _cv(paragraph_lengths)
        sentence_cv = _cv(sentence_lengths)

        prefix_chars = cfg["paragraph_prefix_chars"]
        prefixes = []
        for paragraph in paragraphs:
            cleaned = re.sub(r'^[#>\s“”‘’"\'\-]+', "", paragraph)
            if cleaned:
                prefixes.append(cleaned[:prefix_chars])
        repeated_prefix_ratio = 0.0
        repeated_prefix = None
        if prefixes:
            repeated_prefix, repeated_count = Counter(prefixes).most_common(1)[0]
            repeated_prefix_ratio = repeated_count / len(prefixes)

        risks = []
        if len(paragraphs) < cfg["min_paragraphs"]:
            risks.append("TOO_FEW_PARAGRAPHS")
        if len(sentences) < cfg["min_sentences"]:
            risks.append("TOO_FEW_SENTENCES")
        if sentence_cv < cfg["min_sentence_cv"]:
            risks.append("LOW_SENTENCE_LENGTH_VARIATION")
        if paragraph_cv < cfg["min_paragraph_cv"]:
            risks.append("LOW_PARAGRAPH_LENGTH_VARIATION")
        if repeated_prefix_ratio > cfg["max_repeated_paragraph_prefix_ratio"]:
            risks.append("REPEATED_PARAGRAPH_OPENING")

        return {
            "status": "FLAG_STRUCTURE_RISK" if risks else "PASS",
            "automatic_failure": False,
            "paragraphs": len(paragraphs),
            "sentences": len(sentences),
            "sentence_length_cv": round(sentence_cv, 4),
            "paragraph_length_cv": round(paragraph_cv, 4),
            "repeated_paragraph_prefix": repeated_prefix,
            "repeated_paragraph_prefix_ratio": round(repeated_prefix_ratio, 4),
            "risks": risks,
        }

    def evaluate_prose(self, text: str, candidate_name: str = "candidate") -> dict[str, Any]:
        culture = self.culture_deletion_test(text)
        exposition = self.exposition_detector(text)
        ambiguity = self.ambiguity_preservation(text)
        structure = self.structural_variation(text)
        blockers = []
        if exposition["automatic_failure"]:
            blockers.append("EXPLICIT_EXPOSITION")
        if ambiguity["automatic_failure"]:
            blockers.append("AMBIGUITY_CLOSURE")
        flags = []
        if culture["status"] != "PASS":
            flags.append("CULTURE_MUSEUM_RISK")
        if structure["status"] == "FLAG_STRUCTURE_RISK":
            flags.append("STRUCTURE_VARIATION_RISK")
        if blockers:
            status = "REJECT_BEFORE_BLIND_READ"
        elif flags:
            status = "READY_WITH_HUMAN_FLAGS"
        else:
            status = "READY_FOR_BLIND_READ"
        return {
            "candidate": candidate_name,
            "status": status,
            "automatic_literary_pass": False,
            "automatic_winner": False,
            "blockers": blockers,
            "human_flags": flags,
            "culture_not_museum": culture,
            "explicit_exposition": exposition,
            "ambiguity_preservation": ambiguity,
            "structural_variation": structure,
            "note": (
                "Machine evaluators may block explicit exposition or explicit ambiguity closure. "
                "Culture deletion and structure metrics are review flags only; literary adequacy "
                "still requires human review and a blinded read."
            ),
        }

    def poetry_screen(self, candidates: dict[str, str]) -> dict[str, Any]:
        cfg = self.data["poetry"]
        expected = cfg["lane_labels"]
        if list(candidates) != expected:
            raise ValueError(f"Poetry lane requires candidates in exact order {expected}")
        tokens = {}
        results = []
        seen_text_hashes = set()
        duplicate_content = False
        for label, text in candidates.items():
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen_text_hashes:
                duplicate_content = True
            seen_text_hashes.add(digest)
            token = _sha_token(cfg["blind_prefix"], text)
            tokens[label] = token
            lines = [x.strip() for x in text.splitlines() if x.strip()]
            evidence_hits = [x for x in cfg["forbidden_evidence_terms"] if x in text]
            exposition_hits = [x for x in cfg["exposition_terms"] if x in text]
            cliche_hits = [x for x in cfg["cliche_observations"] if x in text]
            duplicate_lines = [line for line, count in Counter(lines).items() if count > 1]
            blockers = []
            if evidence_hits:
                blockers.append("EVIDENCE_LABEL_CONTAMINATION")
            if exposition_hits:
                blockers.append("EXPLICIT_EXPOSITION")
            flags = []
            if cliche_hits:
                flags.append("CLICHE_OBSERVATION")
            if duplicate_lines:
                flags.append("DUPLICATE_LINE")
            status = (
                "REJECT_BEFORE_BLIND_READ" if blockers
                else "READY_WITH_HUMAN_FLAGS" if flags
                else "READY_FOR_BLIND_READ"
            )
            results.append({
                "internal_label": label,
                "blind_token": token,
                "status": status,
                "blockers": blockers,
                "human_flags": flags,
                "line_count": len(lines),
                "line_lengths": [len(x) for x in lines],
                "evidence_label_hits": evidence_hits,
                "exposition_hits": exposition_hits,
                "cliche_hits": cliche_hits,
                "duplicate_lines": duplicate_lines,
                "automatic_literary_pass": False,
                "automatic_winner": False,
            })
        if len(set(tokens.values())) != 3:
            duplicate_content = True
        lane_status = (
            "BLOCKED_DUPLICATE_CONTENT" if duplicate_content
            else "BLOCKED" if any(x["status"] == "REJECT_BEFORE_BLIND_READ" for x in results)
            else "READY_FOR_BLIND_READ"
        )
        return {
            "lane": "POETRY_A_B_C",
            "lane_status": lane_status,
            "candidate_results": results,
            "sealed_mapping": {token: label for label, token in tokens.items()},
            "automatic_winner": False,
            "manual_blind_read_required": True,
        }

    def poetry_blind_packet(self, candidates: dict[str, str]) -> dict[str, Any]:
        screen = self.poetry_screen(candidates)
        token_by_label = {
            item["internal_label"]: item["blind_token"]
            for item in screen["candidate_results"]
        }
        blind_candidates = [
            {"token": token_by_label[label], "text": text}
            for label, text in candidates.items()
        ]
        blind_candidates.sort(key=lambda x: x["token"])
        packet = {
            "kind": "POETRY_BLIND_READ",
            "sealed": True,
            "candidates": blind_candidates,
            "questions": [
                "不看来源，只判断诗性语言是否自足、是否有具体物象与内在转折。",
                "是否存在解释剧情、解释判词或替作者总结人生的句子？",
                "是否陈套、熟语堆砌或为了古雅而古雅？",
                "是否愿意把这一稿送入人工终审？",
            ],
            "ranking_rule": "只按匿名token排序，不猜原候选身份。",
        }
        violations = self.blind_output_violations(packet)
        if violations:
            raise ValueError(f"Poetry blind packet leaked metadata: {violations}")
        return packet

    def competition_blind_packet(self, record: dict[str, Any]) -> dict[str, Any]:
        chapter = record["chapter"]
        candidates = []
        for candidate in record.get("candidates", []):
            token = candidate["blind_token"]
            blind_path = (
                self.root / "artifacts" / "43-0" / f"ch{chapter}" / "blind" / f"{token}.md"
            )
            if not blind_path.exists():
                raise FileNotFoundError(f"Missing blind artifact: {blind_path.relative_to(self.root)}")
            text = blind_path.read_text(encoding="utf-8")
            candidates.append({
                "token": token,
                "artifact": str(blind_path.relative_to(self.root)),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            })
        candidates.sort(key=lambda x: x["token"])
        packet = {
            "kind": "LITERARY_BLIND_READ",
            "sealed": True,
            "chapter": chapter,
            "candidates": candidates,
            "questions": self.data["blind_read"]["questions"],
            "ranking_rule": "只按匿名token排名；不得猜测或记录原候选身份映射。",
        }
        violations = self.blind_output_violations(packet)
        if violations:
            raise ValueError(f"Blind packet leaked evidence metadata: {violations}")
        return packet

    def blind_output_violations(self, packet: dict[str, Any]) -> list[str]:
        cfg = self.data["blind_read"]
        forbidden_keys = set(cfg["forbidden_metadata_keys"])
        forbidden_terms = cfg["forbidden_value_terms"]
        violations = []
        for kind, value in _walk_values(packet):
            if kind == "KEY" and value in forbidden_keys:
                violations.append(f"forbidden key: {value}")
            elif kind == "VALUE":
                hits = [term for term in forbidden_terms if term in value]
                if hits:
                    violations.append(f"forbidden value terms {hits}: {value[:80]}")
        return violations

    def validate_integrity(self, competitions: Any) -> list[str]:
        errors: list[str] = []
        if self.data.get("issue") != 5:
            errors.append("literary evaluator suite must be bound to issue #5")
        if self.data.get("authority") != "LITERARY_SCREENING_ONLY":
            errors.append("literary evaluator suite authority drift")
        if self.data.get("automatic_literary_pass") is not False:
            errors.append("literary evaluator suite may not auto-pass literature")
        completion = self.data.get("completion", {})
        required = {
            "culture_not_museum_deletion_test",
            "explicit_exposition_detector",
            "ambiguity_preservation",
            "structural_variation_checks",
            "poetry_abc_lane",
            "blind_output_evidence_separated",
        }
        if set(completion) != required or not all(completion.values()):
            errors.append("issue #5 acceptance flags incomplete")
        if self.data["poetry"].get("automatic_winner") is not False:
            errors.append("poetry lane may not auto-select a winner")
        if self.data["poetry"].get("manual_blind_read_required") is not True:
            errors.append("poetry lane must require human blind read")

        for record in competitions.records.values():
            if record.get("mode") != "PRODUCTION_43_0" or not record.get("candidates"):
                continue
            try:
                packet = self.competition_blind_packet(record)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{record['id']}: blind packet failed: {exc}")
                continue
            leaks = self.blind_output_violations(packet)
            if leaks:
                errors.extend(f"{record['id']}: {x}" for x in leaks)
        return errors


def format_literary_suite(kind: str, payload: dict[str, Any]) -> str:
    if kind == "summary":
        return "\n".join([
            "LITERARY EVALUATOR SUITE v0.5",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"automatic_literary_pass: {str(payload['automatic_literary_pass']).lower()}",
            f"all_acceptance: {str(payload['all_acceptance']).lower()}",
        ])
    if kind == "prose":
        return "\n".join([
            f"LITERARY PROSE SCREEN {payload['candidate']}",
            f"status: {payload['status']}",
            f"blockers: {', '.join(payload['blockers']) or 'none'}",
            f"human_flags: {', '.join(payload['human_flags']) or 'none'}",
            "automatic_literary_pass: false",
        ])
    if kind == "poetry-screen":
        lines = [
            "POETRY A/B/C MACHINE LANE",
            f"lane_status: {payload['lane_status']}",
            "automatic_winner: false",
        ]
        for item in payload["candidate_results"]:
            lines.append(
                f"- {item['internal_label']} / {item['blind_token']}: "
                f"{item['status']} flags={item['human_flags']}"
            )
        return "\n".join(lines)
    if kind in {"poetry-blind", "blind"}:
        lines = [
            f"{payload['kind']}",
            "sealed: true",
            f"candidates: {len(payload['candidates'])}",
        ]
        if "chapter" in payload:
            lines.append(f"chapter: {payload['chapter']}")
        for item in payload["candidates"]:
            lines.append(f"- {item['token']}")
        lines.append(payload["ranking_rule"])
        return "\n".join(lines)
    return str(payload)
