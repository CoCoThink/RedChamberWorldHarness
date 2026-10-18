"""Advisory lexical cues, not a narrator classifier or literary acceptance test."""
from __future__ import annotations

import re

_PATTERNS = {
    "inference_certification": re.compile(r"(?:不能|不可|不足以|不得)(?:据此|因此)(?:认定|断定|推断|证明|推定)"),
    "evidence_certification": re.compile(r"(?:并不|并非|不是|不算|不能算作)(?:什么)?(?:凭据|证据|证明)"),
    "knowledge_certification": re.compile(r"(?:并不意味着|并不能证明|不等于)(?:他|她|他们|她们)?(?:已经)?(?:知道|知晓|明白)"),
}
_SENTENCES = re.compile(r"[^。！？\n]+[。！？]?", re.MULTILINE)


def _observation(text: str) -> dict:
    matches = []
    for category, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            sentence = next((item for item in _SENTENCES.finditer(text)
                             if item.start() <= match.start() < item.end()), None)
            matches.append({"category": category, "start": match.start(), "end": match.end(),
                            "text": match.group(), "sentence": sentence.group() if sentence else match.group(),
                            "sentence_start": sentence.start() if sentence else match.start(),
                            "voice": "UNCLASSIFIED"})
    matches.sort(key=lambda item: (item["start"], item["end"], item["category"]))
    characters = sum(not character.isspace() for character in text)
    return {"characters_no_whitespace": characters, "match_count": len(matches),
            "matches_per_1000_characters": round(len(matches) * 1000 / characters, 6) if characters else 0.0,
            "matches": matches}


def narrator_audit(text: str, *, baseline: str | None = None) -> dict:
    observation = _observation(text)
    comparison = None
    if baseline is not None:
        reference = _observation(baseline)
        comparison = {"baseline": reference,
                      "density_delta": round(observation["matches_per_1000_characters"]
                                             - reference["matches_per_1000_characters"], 6)}
    return {"status": "WARN" if observation["matches"] else "NOT_CHECKED",
            "qualification": "FEEDBACK_ONLY", "authority_effect": "NONE",
            "observation": observation, "comparison": comparison,
            "limitation": "Lexical cues only; speaker/narrator attribution, repetition of objects and literary quality "
                          "require actual reading. Quoted denials or necessary limits may be appropriate. "
                          "Lower density is not evidence of improvement; no matches is not PASS."}
