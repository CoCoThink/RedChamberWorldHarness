"""High-confidence repeated-padding lint, not a literary-quality evaluator."""
from __future__ import annotations

from collections import Counter
import re

from ..candidate_reviews import digest


def prose_integrity(text: str) -> dict:
    paragraphs = [row.strip() for row in re.split(r"\n\s*\n", text) if row.strip()]
    groups = {}
    for index, paragraph in enumerate(paragraphs):
        if len(paragraph) < 40:
            continue
        normalized = re.sub(r"[0-9]+", "<NUMBER>", paragraph)
        normalized = re.sub(r"第[零〇一二三四五六七八九十百千万两]+", "第<NUMBER>", normalized)
        groups.setdefault(normalized, []).append((index, paragraph))
    clusters = []
    repeated_characters = 0
    for normalized, rows in groups.items():
        if len(rows) < 3:
            continue
        repeated_characters += sum(len(paragraph) for _, paragraph in rows[1:])
        clusters.append({"occurrences": len(rows), "paragraph_indices": [i for i, _ in rows],
                         "normalized_sha256": digest(normalized.encode()),
                         "example": rows[0][1]})
    script_patterns = (
        r"(?m)^\s*(?:from\s+pathlib\s+import\b|import\s+(?:json|hashlib|re)\b)",
        r"(?m)^\s*(?:expanded\s*=\s*\[|for\s+\w+(?:\s*,\s*\w+)*\s+in\s+(?:enumerate|range)\()",
        r"\.(?:write_text|write_bytes)\(|\.open\(['\"](?:xb|wb)['\"]\)",
        r"(?m)^\s*print\(['\"](?:FROZEN|PRE_SAVE_MEASURE)",
    )
    script_hits = [pattern for pattern in script_patterns if re.search(pattern, text)]
    total = sum(map(len, paragraphs))
    ratio = repeated_characters / total if total else 0
    findings = ["REPEATED_NUMERIC_OR_IDENTICAL_PARAGRAPH_TEMPLATE"] if clusters else []
    if script_hits:
        findings.append("GENERATION_SCRIPT_LEAKED_IN_PROSE")
    return {"status": "FAIL" if script_hits or clusters and ratio >= .15 else "WARN" if clusters else "PASS",
            "scope": "REPEATED_PARAGRAPH_PADDING_LINT", "candidate_sha256": digest(text.encode()),
            "paragraph_count": len(paragraphs), "repeated_characters": repeated_characters,
            "repeated_character_fraction": ratio, "clusters": clusters,
            "findings": findings, "script_signals": script_hits,
            "literary_quality_verified": False, "authority_effect": "NONE"}
