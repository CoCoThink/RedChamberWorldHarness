"""Exploratory, quotation-based style observations; never a literary gate.

The declared word list was devised after viewing the current baseline. It is
exploratory, not a preregistered or independently selected literary standard.
Only the corpus-derived bigram vocabulary is selected mechanically.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

from ..assets import AssetCatalog, AssetError
from ..candidate_reviews import digest
from ..corpus.audit import CorpusAudit
from ..corpus.dataset import CorpusRepository
from .style import ADDRESS_SUFFIXES, NARRATOR_MARKERS, address_form_counts, narrator_marker_counts

FEATURE_SET = "style-reference-features:v1"
DECLARED_WORDS = ("了", "的", "因", "只见", "一面", "罢了", "已经", "觉得", "然后", "于是", "心中",
                  "便", "却", "遂", "且", "原来", "不由", "如今", "只是", "果然", "说道", "笑道")
TOP_BIGRAMS = 300
MIN_REFERENCE_BIGRAM_COUNT = 5
MIN_CANDIDATE_BIGRAM_COUNT = 3
MAX_DEVIATIONS = 10
HAN = re.compile(r"[㐀-鿿]")
HAN_RUN = re.compile(r"[㐀-鿿]+")
PARAGRAPH_BREAK = re.compile(r"\n[ \t\r]*\n")
OPEN_QUOTES = {"“": "”", "‘": "’", "「": "」", "『": "』"}
CLOSE_QUOTES = set(OPEN_QUOTES.values())
CHAPTER_HEADING = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?第(?P<number>[0-9０-９零〇一二三四五六七八九十百千两壹贰叁肆伍陆柒捌玖拾佰仟]+)回"
    r"(?P<title>[^\n]*)$", re.MULTILINE)


def _chapter_number(value: str) -> int:
    value = value.translate(str.maketrans("０１２３４５６７８９壹贰叁肆伍陆柒捌玖拾佰仟两〇", "0123456789一二三四五六七八九十百千二零"))
    if value.isdecimal():
        return int(value)
    digits = {c: n for n, c in enumerate("零一二三四五六七八九")}
    if not any(c in "十百千" for c in value):
        return int("".join(str(digits[c]) for c in value))
    total = digit = 0
    for char in value:
        if char in digits:
            digit = digits[char]
        else:
            total += (digit or 1) * {"十": 10, "百": 100, "千": 1000}[char]
            digit = 0
    return total + digit


def candidate_chapters(text: str) -> tuple[list[dict], str]:
    """Remove chapter titles from prose, retaining independent chapter units."""
    headings = list(CHAPTER_HEADING.finditer(text))
    if not headings:
        return [{"chapter": None, "title": None, "text": text}], ""
    chapters = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        chapters.append({"chapter": _chapter_number(match["number"]), "title": match["title"].strip(),
                         "text": text[match.end():end]})
    return chapters, text[:headings[0].start()]


def segment_prose(text: str) -> dict:
    """Split quote runs without joining paragraphs or separate quote runs.

    Newlines inside a paragraph are treated as extraction wrapping. Blank lines
    remain boundaries. Balanced nested quotes stay in the dialogue layer, but
    quotation is not proof of speech or speaker attribution. Malformed quote
    regions are quarantined as unknown instead of confidently relabelled.
    Offsets in issues refer to the original segment, before whitespace removal.
    """
    boundaries = list(PARAGRAPH_BREAK.finditer(text))
    paragraphs = []
    start = 0
    for match in boundaries:
        paragraphs.append((start, match.start()))
        start = match.end()
    paragraphs.append((start, len(text)))
    intervals, issues, unknown = [], [], []
    stack = []
    outer_start = None
    narration_start = 0
    for offset, char in enumerate(text):
        if char in OPEN_QUOTES:
            if not stack:
                intervals.append(("narration", narration_start, offset))
                outer_start = offset
            stack.append((char, offset))
        elif char in CLOSE_QUOTES:
            if not stack:
                issues.append({"code": "UNMATCHED_CLOSING_QUOTE", "offset": offset, "quote": char})
                left = next(left for left, right in paragraphs if left <= offset <= right)
                unknown.append((left, offset + 1))
            elif OPEN_QUOTES[stack[-1][0]] != char:
                issues.append({"code": "MISMATCHED_CLOSING_QUOTE", "offset": offset, "quote": char,
                               "expected": OPEN_QUOTES[stack[-1][0]]})
                intervals.append(("unknown", outer_start, offset + 1))
                stack.clear()
                narration_start = offset + 1
            else:
                stack.pop()
                if not stack:
                    intervals.append(("dialogue", outer_start, offset + 1))
                    narration_start = offset + 1
    if stack:
        for quote, offset in stack:
            issues.append({"code": "UNCLOSED_QUOTE", "offset": offset, "quote": quote})
        intervals.append(("unknown", outer_start, len(text)))
    else:
        intervals.append(("narration", narration_start, len(text)))

    # Quote punctuation itself is a boundary, including nested quotation marks.
    # Consequently no artificial Han bigram spans quotes, removed dialogue,
    # paragraphs, corpus segments, or chapters.
    layers = {name: [] for name in ("narration", "dialogue", "unknown")}
    for layer, left, right in intervals:
        for pleft, pright in paragraphs:
            a, b = max(left, pleft), min(right, pright)
            if a >= b:
                continue
            cuts = {a, b}
            for uleft, uright in unknown:
                if a < uleft < b: cuts.add(uleft)
                if a < uright < b: cuts.add(uright)
            points = sorted(cuts)
            for begin, end in zip(points, points[1:]):
                destination = "unknown" if any(begin < uright and end > uleft for uleft, uright in unknown) else layer
                compact = re.sub(r"\s+", "", text[begin:end])
                for piece in re.split(r"[“”‘’「」『』]", compact):
                    if piece:
                        layers[destination].append(piece)
    return {"layers": layers, "issues": issues,
            "status": "QUOTE_ISSUES_PRESENT" if issues else "BALANCED_QUOTES",
            "method": "NESTED_QUOTATION_HEURISTIC_NOT_SPEAKER_ATTRIBUTION"}


def _empty_layer() -> dict:
    return {"han_characters": 0, "counts": {"narrator_markers": Counter(dict.fromkeys(NARRATOR_MARKERS, 0)),
                                             "address_forms": Counter(dict.fromkeys(ADDRESS_SUFFIXES, 0)),
                                             "declared_words": Counter(dict.fromkeys(DECLARED_WORDS, 0))},
            "bigrams": Counter()}


def _measure(pieces: list[str]) -> dict:
    result = _empty_layer()
    for piece in pieces:
        result["han_characters"] += len(HAN.findall(piece))
        result["counts"]["narrator_markers"].update(narrator_marker_counts(piece))
        addresses = address_form_counts(piece)
        for suffix in ADDRESS_SUFFIXES:
            result["counts"]["address_forms"][suffix] += sum(count for form, count in addresses.items() if form.endswith(suffix))
        result["counts"]["declared_words"].update({word: piece.count(word) for word in DECLARED_WORDS})
        for run in HAN_RUN.findall(piece):
            result["bigrams"].update(run[i:i + 2] for i in range(len(run) - 1))
    return result


def _merge(target: dict, source: dict) -> None:
    target["han_characters"] += source["han_characters"]
    for name in target["counts"]:
        target["counts"][name].update(source["counts"][name])
    target["bigrams"].update(source["bigrams"])


def _rate(count: int, denominator: int) -> float | None:
    return count * 10000 / denominator if denominator else None


def _distribution(rows: list[dict]) -> dict:
    values = sorted(row["rate_per_10k_han"] for row in rows if row["rate_per_10k_han"] is not None)
    def quantile(fraction):
        position = (len(values) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        return values[lower] + (values[upper] - values[lower]) * (position - lower)
    return {"minimum": values[0] if values else None, "q1": quantile(.25) if values else None,
            "median": quantile(.5) if values else None, "q3": quantile(.75) if values else None,
            "maximum": values[-1] if values else None, "defined_chapters": len(values),
            "total_chapters": len(rows), "quantile_method": "LINEAR_INTERPOLATION", "chapters": rows}


def _feature_reference(count: int, aggregate: dict, chapters: dict[int, dict], getter) -> dict:
    return {"count": count, "rate_per_10k_han": _rate(count, aggregate["han_characters"]),
            "chapter_distribution": _distribution([
                {"chapter": chapter, "han_characters": layer["han_characters"], "count": getter(layer),
                 "rate_per_10k_han": _rate(getter(layer), layer["han_characters"])}
                for chapter, layer in sorted(chapters.items())])}


def reference_profile(root: Path, dataset_ref: str, *, exclude_chapters=None) -> dict:
    """Verify immutable bindings; optional holdout exclusion preserves legacy defaults.

    Dataset audit/readiness is never presented as a separately audited subset.
    The declared word vocabulary remains exploratory, not target-blind.
    """
    excluded = sorted(set(exclude_chapters or ()))
    if any(type(chapter) is not int or chapter < 1 for chapter in excluded):
        raise ValueError("INVALID_STYLE_EXCLUDED_CHAPTER")
    catalog = AssetCatalog.from_repo(root)
    corpus = CorpusRepository(catalog)
    binding = corpus.registry()[dataset_ref]
    asset = catalog.resolve(binding["manifest_ref"])
    if asset.sha256 != binding["manifest_sha256"] or digest(asset.path.read_bytes()) != binding["manifest_sha256"]:
        raise AssetError("CORPUS_MANIFEST_BINDING_MISMATCH")
    manifest, products = corpus.load(dataset_ref, rebuild=False)
    audit = CorpusAudit(catalog).summary(dataset_ref, rebuild=False)
    declared_chapters = manifest["build_config"]["document"]["chapters"]
    chapters = [chapter for chapter in declared_chapters if chapter not in excluded]
    measurements = {chapter: {name: _empty_layer() for name in ("narration", "dialogue")} for chapter in chapters}
    aggregate = {name: _empty_layer() for name in ("narration", "dialogue")}
    issues, unknown_han, segment_count = [], 0, 0
    for line in products["segments.jsonl"].splitlines()[1:]:
        segment = json.loads(line)
        if segment["kind"] != "MAIN_TEXT":
            continue
        chapter = segment["chapter"]
        if chapter not in declared_chapters:
            raise AssetError("STYLE_MAIN_TEXT_OUTSIDE_DECLARED_CHAPTERS")
        if chapter in excluded:
            continue
        split = segment_prose(segment["text"])
        segment_count += 1
        issues.extend({**issue, "chapter": chapter, "segment_id": segment["segment_id"]} for issue in split["issues"])
        unknown_han += sum(len(HAN.findall(piece)) for piece in split["layers"]["unknown"])
        for name in aggregate:
            layer = _measure(split["layers"][name])
            _merge(measurements[chapter][name], layer)
            _merge(aggregate[name], layer)
    layers = {}
    for name, total in aggregate.items():
        per_chapter = {chapter: measured[name] for chapter, measured in measurements.items()}
        features = {}
        for group, counts in total["counts"].items():
            features[group] = {word: _feature_reference(count, total, per_chapter, lambda layer, g=group, w=word: layer["counts"][g][w])
                               for word, count in sorted(counts.items())}
        selected = sorted(((word, count) for word, count in total["bigrams"].items() if count >= MIN_REFERENCE_BIGRAM_COUNT),
                          key=lambda row: (-row[1], row[0]))[:TOP_BIGRAMS]
        layers[name] = {"han_characters": total["han_characters"], "features": features,
                        "top_han_bigrams": {word: _feature_reference(count, total, per_chapter, lambda layer, w=word: layer["bigrams"][w])
                                            for word, count in selected}}
    result = {"dataset_ref": dataset_ref, "manifest_sha256": binding["manifest_sha256"],
            "readiness": manifest["readiness"], "human_audit_status": audit["status"],
            "provisional": audit["status"] != "PASS", "human_audit": audit, "feature_set": FEATURE_SET,
            "feature_policy": {"declared_words": list(DECLARED_WORDS),
                               "word_list_basis": "EXPLORATORY_DEVISED_AFTER_VIEWING_CURRENT_BASELINE",
                               "address_forms": "SHARED_REGEX_MATCHES_GROUPED_BY_SUFFIX",
                               "rate_denominator": "LAYER_HAN_CHARACTERS", "rate_scale": 10000,
                               "bigram_selection": "TOP_300_PER_LAYER_BY_REFERENCE_COUNT_THEN_LEXICAL_ORDER",
                               "minimum_reference_bigram_count": MIN_REFERENCE_BIGRAM_COUNT,
                               "minimum_nonzero_candidate_bigram_count": MIN_CANDIDATE_BIGRAM_COUNT,
                               "zero_candidate_counts_retained": True,
                               "boundaries": "NO_CROSS_PARAGRAPH_SEGMENT_CHAPTER_QUOTE_OR_NON_HAN_BIGRAMS",
                               "unknown_region_policy": "EXCLUDED_FROM_BOTH_LAYER_DENOMINATORS",
                               "quotation_limitations": "QUOTED_TEXT_IS_NOT_PROOF_OF_SPEECH; SEGMENT_CONTINUATIONS_ARE_NOT_JOINED"},
            "chapter_count": len(chapters), "main_text_segment_count": segment_count,
            "segmentation": {"method": "NESTED_QUOTATION_HEURISTIC_NOT_SPEAKER_ATTRIBUTION", "issues": issues,
                             "unknown_han_characters": unknown_han,
                             "unknown_han_fraction": unknown_han / (unknown_han + sum(layer["han_characters"] for layer in aggregate.values()))
                             if unknown_han + sum(layer["han_characters"] for layer in aggregate.values()) else None,
                             "status": "QUOTE_ISSUES_PRESENT" if issues else "BALANCED_QUOTES"},
            "layers": layers, "verdict": None, "authority_effect": "NONE", "evidence_effect": "NONE"}
    if excluded:
        result["reference_scope"] = {
            "included_chapters": chapters, "excluded_chapters": excluded,
            "audit_scope": "WHOLE_DATASET_NOT_INDEPENDENT_SUBSET_AUDIT",
            "subset_audit_status": "NOT_SEPARATELY_AUDITED",
            "readiness_scope": "SOURCE_DATASET", "feature_selection_scope": "INCLUDED_CHAPTERS_ONLY",
        }
        result["feature_policy"]["holdout_policy"] = {
            "corpus_features": "EXCLUDED_CHAPTERS_NOT_USED",
            "declared_words": "EXPLORATORY_FIXED_LIST_NOT_TARGET_BLIND_PREREGISTRATION",
        }
    return result


def _comparison(count: int, denominator: int, baseline: dict) -> dict:
    rate = _rate(count, denominator)
    distribution = baseline["chapter_distribution"]
    outside = rate is not None and distribution["minimum"] is not None and not distribution["minimum"] <= rate <= distribution["maximum"]
    # Full per-reference-chapter rows live once in reference_layers. Repeating
    # them for every feature in every candidate chapter makes reports enormous.
    summary = {**baseline, "chapter_distribution": {key: value for key, value in distribution.items() if key != "chapters"}}
    return {"count": count, "rate_per_10k_han": rate, "reference": summary,
            "observations": ["OUTSIDE_FRONT80_CHAPTER_RANGE"] if outside else []}


def _compare_layers(measured: dict, reference: dict) -> dict:
    layers = {}
    for name, layer in measured.items():
        baseline = reference["layers"][name]
        features = {group: {word: _comparison(layer["counts"][group][word], layer["han_characters"], record)
                            for word, record in words.items()} for group, words in baseline["features"].items()}
        deviations = []
        for word, record in baseline["top_han_bigrams"].items():
            count = layer["bigrams"][word]
            if 0 < count < MIN_CANDIDATE_BIGRAM_COUNT:
                continue
            row = _comparison(count, layer["han_characters"], record)
            if row["rate_per_10k_han"] is None or record["rate_per_10k_han"] is None:
                continue
            row.update({"bigram": word, "delta_per_10k_han": row["rate_per_10k_han"] - record["rate_per_10k_han"]})
            deviations.append(row)
        layers[name] = {"han_characters": layer["han_characters"], "features": features,
                        "bigram_deviations": {
                            "higher": sorted((row for row in deviations if row["delta_per_10k_han"] > 0), key=lambda row: (-row["delta_per_10k_han"], row["bigram"]))[:MAX_DEVIATIONS],
                            "lower": sorted((row for row in deviations if row["delta_per_10k_han"] < 0), key=lambda row: (row["delta_per_10k_han"], row["bigram"]))[:MAX_DEVIATIONS]}}
    return layers


def _compact_reference_layers(reference: dict) -> dict:
    """Keep complete chapter values once, in aligned count/rate columns."""
    layers = {}
    for name, layer in reference["layers"].items():
        sample = next(iter(layer["features"]["declared_words"].values()))["chapter_distribution"]["chapters"]
        def compact(record):
            distribution = record["chapter_distribution"]
            rows = distribution["chapters"]
            return {**record, "chapter_distribution": {**distribution, "chapters": {
                "counts": [row["count"] for row in rows],
                "rates_per_10k_han": [row["rate_per_10k_han"] for row in rows]}}}
        layers[name] = {**layer, "chapter_order": [row["chapter"] for row in sample],
                        "chapter_han_characters": [row["han_characters"] for row in sample],
                        "chapter_values_format": "ALIGNED_COLUMNS_IN_CHAPTER_ORDER",
                        "features": {group: {word: compact(record) for word, record in words.items()}
                                     for group, words in layer["features"].items()},
                        "top_han_bigrams": {word: compact(record) for word, record in layer["top_han_bigrams"].items()}}
    return layers


def compare_reference(text: str, reference: dict) -> dict:
    chapters, preamble = candidate_chapters(text)
    aggregate = {name: _empty_layer() for name in ("narration", "dialogue")}
    chapter_reports, all_issues, unknown_han = [], [], 0
    for index, chapter in enumerate(chapters, 1):
        split = segment_prose(chapter["text"])
        measured = {name: _measure(split["layers"][name]) for name in aggregate}
        for name in aggregate:
            _merge(aggregate[name], measured[name])
        unknown = sum(len(HAN.findall(piece)) for piece in split["layers"]["unknown"])
        unknown_han += unknown
        all_issues.extend({**issue, "chapter": chapter["chapter"], "chapter_index": index} for issue in split["issues"])
        chapter_reports.append({"chapter": chapter["chapter"], "title": chapter["title"], "chapter_index": index,
                                "layers": _compare_layers(measured, reference),
                                "segmentation": {"status": split["status"], "issues": split["issues"], "unknown_han_characters": unknown}})
    return {key: value for key, value in reference.items() if key != "layers"} | {
        "reference_layers": _compact_reference_layers(reference),
        "candidate_chapter_count": len(chapters), "chapters": chapter_reports,
        "overall": {"layers": _compare_layers(aggregate, reference)},
        "candidate_segmentation": {"method": "NESTED_QUOTATION_HEURISTIC_NOT_SPEAKER_ATTRIBUTION", "issues": all_issues,
                                   "status": "QUOTE_ISSUES_PRESENT" if all_issues else "BALANCED_QUOTES",
                                   "unknown_han_characters": unknown_han,
                                   "unknown_han_fraction": unknown_han / (unknown_han + sum(layer["han_characters"] for layer in aggregate.values()))
                                   if unknown_han + sum(layer["han_characters"] for layer in aggregate.values()) else None,
                                   "excluded_preamble_han_characters": len(HAN.findall(preamble)),
                                   "chapter_headings_excluded": bool(CHAPTER_HEADING.search(text))},
        "verdict": None, "authority_effect": "NONE", "evidence_effect": "NONE"}
