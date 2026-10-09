"""Observable prose features, kept separate from literary judgements."""
from collections import Counter
import re

from ..candidate_reviews import digest


def style_diagnostics(text: str, poetry: list[str] | None = None) -> dict:
    heading = re.search(r"^\s*第[^\n]*回[ \t]+([^\n]+)", text, re.MULTILINE)
    title = heading.group(1).strip() if heading else None
    halves = re.split(r"\s+|[；;]", title) if title else []
    halves = [h for h in halves if h]
    lengths = [len(re.findall(r"[\u3400-\u9fff]", h)) for h in halves]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    quoted = re.findall(r"[“「]([^”」]*)[”」]", text)
    narrative = re.sub(r"[“「][^”」]*[”」]", "", text)
    markers = {s: len(re.findall(re.escape(s), narrative)) for s in ("话说", "且说", "却说", "原来", "不在话下", "欲知后事")}
    addresses = Counter(re.findall(r"[一-鿿]{0,2}(?:姑娘|奶奶|太太|老爷|姐姐|妹妹|二爷|哥儿|嫂子)", "\n".join(quoted)))
    poem_reports = []
    for poem in poetry or []:
        verses = [v.strip() for v in re.split(r"[，。；！？\n]", poem) if v.strip()]
        poem_reports.append({"text_sha256": digest(poem.encode()), "verses": verses,
                             "line_lengths": [len(re.findall(r"[\u3400-\u9fff]", v)) for v in verses],
                             "rhyme_and_tonal_pattern": "PENDING_EXPERT_READING", "voice": "PENDING_EXPERT_READING"})
    return {"report_kind": "COMPUTED_CHECK", "scope": "STYLE_OBSERVATIONS", "status": "OBSERVED",
            "candidate_sha256": digest(text.encode()), "character_count": len(text),
            "title_track": {"title": title, "halves": halves, "han_lengths": lengths,
                            "equal_length": len(lengths) == 2 and lengths[0] == lengths[1],
                            "semantic_parallelism": "PENDING_READING", "chapter_function": "PENDING_READING"},
            "prose_track": {"paragraph_lengths": [len(p) for p in paragraphs], "quoted_utterances": len(quoted),
                            "narrator_markers": markers, "address_forms": dict(addresses),
                            "address_relationship_consistency": "PENDING_ATTRIBUTED_READING"},
            "poetry_track": poem_reports, "reference_distribution": "UNAVAILABLE_UNTIL_CORPUS_AUDITED",
            "literary_quality_verified": False, "authority_effect": "NONE"}
