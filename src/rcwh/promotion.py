from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .competition import CompetitionRegistry
from .io import load_data
from .literary_eval import evaluate_literary_candidate
from .regression import run_r4_evidence_regression
from .contracts import project_chapters, coverage_errors
from .assets import AssetCatalog
from .assets.catalog import repository_path


HEADING_RE = re.compile(r"(?m)^# 第[^\n]+回[^\n]*$")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_chapters(text: str, chapter_ids: tuple[int, ...]) -> dict[int, str]:
    matches = list(HEADING_RE.finditer(text))
    if len(matches) != len(chapter_ids):
        raise ValueError(f"expected {len(chapter_ids)} chapter headings for configured scope, found {len(matches)}")
    result = {}
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[chapter_ids[i]] = text[start:end]
    return result


@dataclass
class PromotionRegistry:
    records: dict[str, dict[str, Any]]

    @classmethod
    def from_repo(cls, root: Path) -> "PromotionRegistry":
        result = {}
        path = root / "data" / "promotions"
        if path.exists():
            for file in sorted(path.glob("*.yaml")):
                doc = load_data(file) or {}
                for item in doc.get("promotions", []):
                    if item["id"] in result:
                        raise ValueError(f"Duplicate promotion id: {item['id']}")
                    result[item["id"]] = item
        return cls(result)

    def build_candidate(self, root: Path, promotion_id: str) -> bytes:
        record = self.records[promotion_id]
        baseline = AssetCatalog.from_repo(root).resolve(record["baseline"]["asset_ref"])
        if baseline.sha256 != record["baseline"]["sha256"]:
            raise ValueError("promotion baseline identity mismatch")
        text = baseline.path.read_bytes().decode("utf-8")
        scope = project_chapters(root)
        chapters = _split_chapters(text, scope)
        replacements = record["candidate"]["replacements"]
        selected = [r["chapter"] for r in replacements]
        if len(selected) != len(set(selected)) or set(selected) != set(record["allowed_changed_chapters"]):
            raise ValueError("promotion replacement scope mismatch")
        for replacement in replacements:
            chapter = replacement["chapter"]
            if chapter not in chapters:
                raise ValueError("promotion replacement outside project scope")
            raw = repository_path(root, replacement["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != replacement["sha256"]:
                raise ValueError("promotion chapter identity mismatch")
            body = raw.decode("utf-8")
            _split_chapters(body, (chapter,))
            chapters[chapter] = body.rstrip("\r\n") + "\n" * replacement["trailing_newlines"]
        prefix = text[:HEADING_RE.search(text).start()]
        raw = (prefix + "".join(chapters[ch] for ch in scope)).encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != record["candidate"]["sha256"]:
            raise ValueError("assembled promotion candidate identity mismatch")
        return raw

    def evaluate(self, root: Path, promotion_id: str) -> dict[str, Any]:
        record = self.records[promotion_id]
        findings = []
        gates = {}

        competitions = CompetitionRegistry.from_repo(root)
        comp = competitions.records.get(record["source_competition"])
        declared_winner = bool(
            comp
            and comp["state"] == "ADJUDICATED"
            and comp["adjudication"]["outcome"] == "WINNER"
            and comp["adjudication"]["winner_candidate_id"] == record["winner_candidate_id"]
            and comp["adjudication"]["promotion_state"] == "PROMOTION_CANDIDATE"
        )
        competition_report = competitions.evaluate_record(root, comp) if comp else None
        eligible = bool(declared_winner and competition_report["adjudication_qualification"] == "PASS")
        pending = bool(declared_winner and competition_report["adjudication_qualification"] == "PENDING")
        gates["COMPETITION_ELIGIBILITY"] = "PASS" if eligible else "PENDING" if pending else "FAIL"
        if not eligible and not pending:
            findings.append("source competition is not an eligible promotion winner")
            if competition_report:
                findings.extend(competition_report["consistency_errors"])

        regression = run_r4_evidence_regression(root)
        gates["EVIDENCE_CORE"] = regression["overall"]
        if regression["overall"] != "PASS":
            findings.append("frozen R4 Evidence Core regression is not PASS")

        try:
            text = self.build_candidate(root, promotion_id).decode("utf-8")
        except (KeyError, OSError, ValueError) as exc:
            findings.append(str(exc))
            return {"id":promotion_id,"overall":"FAIL","gates":gates,"findings":findings}
        actual_sha = _sha256_text(text)
        sha_ok = actual_sha == record["candidate"]["sha256"]
        gates["BASELINE_IDENTITY"] = "PASS" if record["baseline"]["sha256"] == regression["stable_active"]["sha256"] else "FAIL"
        if not sha_ok:
            findings.append(f"candidate SHA mismatch {actual_sha} != {record['candidate']['sha256']}")

        try:
            scope = project_chapters(root)
            mismatch = coverage_errors([int(ch) for ch in record["baseline_chapter_sha256"]], scope, "promotion baseline chapters")
            if mismatch:
                raise ValueError("; ".join(mismatch))
            chapters = _split_chapters(text, scope)
            gates["BOOK_STRUCTURE"] = "PASS"
        except ValueError as exc:
            chapters = {}
            gates["BOOK_STRUCTURE"] = "FAIL"
            findings.append(str(exc))

        non_target_ok = bool(chapters)
        allowed = set(record["allowed_changed_chapters"])
        if chapters:
            for ch, expected_hash in record["baseline_chapter_sha256"].items():
                ch_num = int(ch)
                actual = _sha256_text(chapters[ch_num])
                if ch_num not in allowed and actual != expected_hash:
                    non_target_ok = False
                    findings.append(f"non-target chapter {ch_num} changed")
                if ch_num in allowed and actual == expected_hash:
                    findings.append(f"target chapter {ch_num} did not change")
                    non_target_ok = False
        gates["NON_TARGET_INTEGRITY"] = "PASS" if non_target_ok else "FAIL"

        winner = next((c for c in (comp or {}).get("candidates", []) if c["id"] == record["winner_candidate_id"]), None)
        replacements = record["candidate"]["replacements"]
        source_chapter = repository_path(root, replacements[0]["path"]).read_bytes().decode("utf-8")
        target_matches = bool(chapters) and bool(winner) and len(replacements) == 1 and (
            replacements[0]["chapter"] == comp["chapter"]
            and replacements[0]["path"] == winner["artifact"]["path"]
            and chapters[comp["chapter"]].rstrip() == source_chapter.rstrip()
        )
        if not target_matches:
            findings.append("embedded Chapter 86 does not match adjudicated B candidate")

        hard_strings = [
            "# 第九十回　薛宝钗借词含讽谏　王熙凤知命强英雄",
            "落叶萧萧，寒烟漠漠",
            "好歹留着麝月",
            "悬崖撒手",
            "情情",
            "情不情",
            "正层",
            "副层",
            "再副层",
            "三副",
            "四副",
            "十独吟",
        ]
        r4f_ok = all(x in text for x in hard_strings) and "警幻情榜" not in text
        gates["R4F_HARD_INTERFACES"] = "PASS" if r4f_ok else "FAIL"
        if not r4f_ok:
            findings.append("R4-F hard-interface sentinel mismatch")

        plock_payload = evaluate_literary_candidate(
            root,
            "plock:ch86:cold-medicine",
            chapters.get(86, "") if chapters else "",
            candidate_name="promotion-ch86-B",
        )
        other_plock_anchors = [
            "谁家的水桶还在井边？",
            "从前也有数。",
            "谁同你说我件件想得明白？",
            "石在，字在。",
        ]
        plock_ok = (
            plock_payload["machine_status"] == "READY_FOR_BLIND_READ"
            and all(x in text for x in other_plock_anchors)
        )
        gates["PLOCK"] = "PASS" if plock_ok else "FAIL"
        if not plock_ok:
            findings.append("P-Lock regression failed")

        active_unchanged = regression["stable_active"]["sha256"] == record["baseline"]["sha256"]
        gates["STABLE_POINTER_UNCHANGED"] = "PASS" if active_unchanged else "FAIL"
        if not active_unchanged:
            findings.append("stable ACTIVE pointer changed during promotion regression")

        if not target_matches:
            gates["NON_TARGET_INTEGRITY"] = "FAIL"

        expected = record["checks"]
        for name, value in expected.items():
            if gates.get(name) != value and gates.get(name) != "PENDING":
                findings.append(f"manifest expected {name}={value}, actual={gates.get(name)}")

        pending_checks = [name for name, value in gates.items() if value == "PENDING"]
        overall = "FAIL" if findings or "FAIL" in gates.values() else "PENDING" if pending_checks else "PASS"
        return {
            "id": promotion_id,
            "overall": overall,
            "candidate_sha256": actual_sha,
            "gates": gates,
            "declared_checks": expected,
            "pending_checks": pending_checks,
            "findings": findings,
            "stable_active_mutated": False,
            "release_action": record["release_action"],
        }


def format_promotion(payload: dict[str, Any]) -> str:
    out=[
        f"PROMOTION REGRESSION: {payload['overall']}",
        f"id: {payload['id']}",
        f"candidate_sha256: {payload.get('candidate_sha256')}",
        "stable_active_mutated: false",
        "",
        "GATES",
    ]
    for name,value in payload.get("gates",{}).items():
        out.append(f"- {name}: {value}")
    if payload.get("findings"):
        out.extend(["","FINDINGS"])
        out.extend(f"- {x}" for x in payload["findings"])
    if payload.get("pending_checks"):
        out.extend(["", "PENDING CHECKS"])
        out.extend(f"- {x}" for x in payload["pending_checks"])
    out.extend(["",f"release_action: {payload.get('release_action')}"])
    return "\n".join(out)
