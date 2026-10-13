"""Pure, bounded author advice from an already computed 1..78 reference.

This is not a new reference computation, an audit, or a backtest mode. The full
analytical profile remains coordinator-side and unchanged. No corpus access,
exemplar retrieval, candidate measurement, rounding, or vocabulary pruning is
performed here. Unsupported profiles and overflow fail rather than truncate.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import re

from .style import ADDRESS_SUFFIXES, NARRATOR_MARKERS
from .style_reference import DECLARED_WORDS, FEATURE_SET, TOP_BIGRAMS


MAX_SUPPORT_BYTES = 64000
SUPPORT_POLICY = "style-reference-aggregate-support:v1"
STATISTIC_COLUMNS = ("count", "rate_per_10k_han", "q1", "median", "q3")
EDITING_RULE = (
    "Descriptive aggregate and interquartile editing advice only, not a literary "
    "threshold, truth, or evidence of superiority. Quotation is not speaker "
    "attribution; source audit and subset caveats still apply."
)
_INCLUDED = list(range(1, 79))
_SCOPE = {
    "included_chapters": _INCLUDED, "excluded_chapters": [79, 80],
    "audit_scope": "WHOLE_DATASET_NOT_INDEPENDENT_SUBSET_AUDIT",
    "subset_audit_status": "NOT_SEPARATELY_AUDITED",
    "readiness_scope": "SOURCE_DATASET",
    "feature_selection_scope": "INCLUDED_CHAPTERS_ONLY",
}
_FEATURE_POLICY = {
    "declared_words": list(DECLARED_WORDS),
    "word_list_basis": "EXPLORATORY_DEVISED_AFTER_VIEWING_CURRENT_BASELINE",
    "address_forms": "SHARED_REGEX_MATCHES_GROUPED_BY_SUFFIX",
    "rate_denominator": "LAYER_HAN_CHARACTERS", "rate_scale": 10000,
    "bigram_selection": "TOP_300_PER_LAYER_BY_REFERENCE_COUNT_THEN_LEXICAL_ORDER",
    "minimum_reference_bigram_count": 5,
    "minimum_nonzero_candidate_bigram_count": 3,
    "zero_candidate_counts_retained": True,
    "boundaries": "NO_CROSS_PARAGRAPH_SEGMENT_CHAPTER_QUOTE_OR_NON_HAN_BIGRAMS",
    "unknown_region_policy": "EXCLUDED_FROM_BOTH_LAYER_DENOMINATORS",
    "quotation_limitations": "QUOTED_TEXT_IS_NOT_PROOF_OF_SPEECH; SEGMENT_CONTINUATIONS_ARE_NOT_JOINED",
    "holdout_policy": {
        "corpus_features": "EXCLUDED_CHAPTERS_NOT_USED",
        "declared_words": "EXPLORATORY_FIXED_LIST_NOT_TARGET_BLIND_PREREGISTRATION",
    },
}
_GROUPS = {"narrator_markers": NARRATOR_MARKERS, "address_forms": ADDRESS_SUFFIXES,
           "declared_words": DECLARED_WORDS}
_ISSUE_CODES = {"UNCLOSED_QUOTE", "UNMATCHED_CLOSING_QUOTE", "MISMATCHED_CLOSING_QUOTE"}
_METHOD = "NESTED_QUOTATION_HEURISTIC_NOT_SPEAKER_ATTRIBUTION"
_QUANTILE_METHOD = "LINEAR_INTERPOLATION"


def _invalid(field: str) -> None:
    raise ValueError(f"INVALID_STYLE_SUPPORT_PROFILE: {field}")


def _keys(value, required, field: str, optional=()) -> None:
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        _invalid(field)


def _integer(value, field: str) -> int:
    if type(value) is not int or value < 0:
        _invalid(field)
    return value


def _number(value, field: str, *, nullable=False):
    if value is None and nullable:
        return value
    if type(value) not in (int, float) or value < 0:
        _invalid(field)
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        _invalid(field)
    return value


def _canonical_bytes(value: dict) -> bytes:
    # Repository canonical_bytes convention, additionally rejecting NaN/Infinity.
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def support_metadata(support: dict) -> dict:
    """Return canonical UTF-8 size/hash without embedding a self-referential hash.

    These bind the supplied JSON bytes only; they do not verify provenance or
    constitute an audit. The byte ceiling covers the support, not a whole request.
    """
    if not isinstance(support, dict) or support.get("support_policy") != SUPPORT_POLICY:
        raise ValueError("UNSUPPORTED_STYLE_SUPPORT")
    raw = _canonical_bytes(support)
    return {"support_bytes": len(raw), "support_sha256": hashlib.sha256(raw).hexdigest()}


def _record(record, *, chapters, han_characters, field: str) -> tuple[list, list[int]]:
    _keys(record, ("count", "rate_per_10k_han", "chapter_distribution"), field)
    count = _integer(record["count"], field + ".count")
    rate = _number(record["rate_per_10k_han"], field + ".rate", nullable=han_characters == 0)
    distribution = record["chapter_distribution"]
    _keys(distribution, ("minimum", "q1", "median", "q3", "maximum", "defined_chapters",
                         "total_chapters", "quantile_method", "chapters"), field + ".distribution")
    if (distribution["quantile_method"] != _QUANTILE_METHOD
            or _integer(distribution["total_chapters"], field + ".total_chapters") != len(chapters)):
        _invalid(field + ".distribution_metadata")
    rows = distribution["chapters"]
    if not isinstance(rows, list) or len(rows) != len(chapters):
        _invalid(field + ".chapter_rows")
    denominators, rates, counts = [], [], []
    for chapter, row in zip(chapters, rows):
        _keys(row, ("chapter", "han_characters", "count", "rate_per_10k_han"), field + ".chapter_row")
        if type(row["chapter"]) is not int or row["chapter"] != chapter:
            _invalid(field + ".chapter_scope")
        denominator = _integer(row["han_characters"], field + ".chapter_han_characters")
        row_count = _integer(row["count"], field + ".chapter_count")
        row_rate = _number(row["rate_per_10k_han"], field + ".chapter_rate", nullable=denominator == 0)
        if (denominator == 0 and row_count != 0
                or row_rate != (row_count * 10000 / denominator if denominator else None)):
            _invalid(field + ".chapter_rate_count")
        denominators.append(denominator)
        counts.append(row_count)
        if row_rate is not None:
            rates.append(row_rate)
    if (sum(denominators) != han_characters or sum(counts) != count
            or rate != (count * 10000 / han_characters if han_characters else None)):
        _invalid(field + ".aggregate_rate_count")
    defined = _integer(distribution["defined_chapters"], field + ".defined_chapters")
    if defined != len(rates):
        _invalid(field + ".defined_chapters")
    rates.sort()
    for key, fraction in (("minimum", 0), ("q1", .25), ("median", .5), ("q3", .75), ("maximum", 1)):
        value = _number(distribution[key], field + "." + key, nullable=defined == 0)
        expected = None
        if rates:
            position = (len(rates) - 1) * fraction
            lower = int(position)
            upper = min(lower + 1, len(rates) - 1)
            expected = rates[lower] + (rates[upper] - rates[lower]) * (position - lower)
        if value != expected:
            _invalid(field + "." + key)
    return [count, rate, distribution["q1"], distribution["median"], distribution["q3"]], denominators


def compact_author_support(profile: dict, max_bytes: int = MAX_SUPPORT_BYTES) -> dict:
    """Project a supported full v1 profile; fail closed before returning overflow.

    The scope must explicitly include exactly chapters 1..78 and exclude 79/80.
    Identities are metadata, not a fixed dataset/manifest or proof of source
    custody. Every named feature and every selected bigram (up to 300 per layer,
    as in reference_profile) is retained. A lower byte ceiling may be requested;
    the hard 64,000-byte ceiling cannot be increased. Layer chapter denominators
    can differ, including an empty layer with null rates and quartiles.
    """
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_SUPPORT_BYTES:
        raise ValueError("INVALID_STYLE_SUPPORT_MAX_BYTES")
    _keys(profile, ("dataset_ref", "manifest_sha256", "readiness", "human_audit_status", "provisional",
                    "human_audit", "feature_set", "feature_policy", "chapter_count", "main_text_segment_count",
                    "segmentation", "layers", "reference_scope", "verdict", "authority_effect", "evidence_effect"),
          "profile")
    if profile["feature_set"] != FEATURE_SET or profile["feature_policy"] != _FEATURE_POLICY:
        _invalid("unsupported_feature_set_or_policy")
    # JSON comparison distinguishes bool/float substitutions in policy constants.
    if _canonical_bytes(profile["feature_policy"]) != _canonical_bytes(_FEATURE_POLICY):
        _invalid("unsupported_feature_policy_types")
    scope = profile["reference_scope"]
    if scope != _SCOPE or _canonical_bytes(scope) != _canonical_bytes(_SCOPE):
        _invalid("reference_scope_requires_1_through_78_and_explicit_79_80_exclusion")
    if _integer(profile["chapter_count"], "chapter_count") != len(_INCLUDED):
        _invalid("chapter_count")
    _integer(profile["main_text_segment_count"], "main_text_segment_count")
    if not isinstance(profile["dataset_ref"], str) or not re.fullmatch(r"corpus:[A-Za-z0-9][A-Za-z0-9._:-]*", profile["dataset_ref"]):
        _invalid("dataset_ref")
    if not isinstance(profile["manifest_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", profile["manifest_sha256"]):
        _invalid("manifest_sha256")
    if (profile["readiness"] != "CANDIDATE_PENDING_HUMAN_AUDIT"
            or profile["authority_effect"] != "NONE" or profile["evidence_effect"] != "NONE"
            or profile["verdict"] is not None):
        _invalid("source_readiness_or_authority")
    audit = profile["human_audit"]
    if not isinstance(audit, dict) or not {"status", "scope", "review_count", "authority_effect"} <= audit.keys():
        _invalid("human_audit")
    if (profile["human_audit_status"] not in ("PENDING", "PASS", "FAIL")
            or audit["status"] != profile["human_audit_status"]
            or audit["scope"] != "CORPUS_HUMAN_LAYER_AUDIT" or audit["authority_effect"] != "NONE"
            or type(profile["provisional"]) is not bool
            or profile["provisional"] != (audit["status"] != "PASS")):
        _invalid("human_audit_status_or_provisional")
    _integer(audit["review_count"], "human_audit.review_count")
    _keys(profile["layers"], ("narration", "dialogue"), "layers")
    layers = {}
    for name, source in profile["layers"].items():
        _keys(source, ("han_characters", "features", "top_han_bigrams"), name)
        han = _integer(source["han_characters"], name + ".han_characters")
        _keys(source["features"], _GROUPS, name + ".features")
        bigrams = source["top_han_bigrams"]
        if (not isinstance(bigrams, dict) or len(bigrams) > TOP_BIGRAMS
                or any(not isinstance(word, str) or not re.fullmatch(r"[㐀-鿿]{2}", word) for word in bigrams)):
            _invalid(name + ".top_han_bigrams")
        layer = {"han_characters": han, "total_chapters": len(_INCLUDED), "features": {}, "top_han_bigrams": {}}
        denominators = None
        for group, words in [*source["features"].items(), ("top_han_bigrams", bigrams)]:
            if group != "top_han_bigrams":
                _keys(words, _GROUPS[group], name + "." + group)
            target = {}
            for word, record in words.items():
                field = name + "." + group + "." + word
                values, row_han = _record(record, chapters=_INCLUDED, han_characters=han, field=field)
                if denominators is None:
                    denominators = row_han
                elif row_han != denominators:
                    _invalid(field + ".inconsistent_layer_denominators")
                if group == "top_han_bigrams" and values[0] < _FEATURE_POLICY["minimum_reference_bigram_count"]:
                    _invalid(field + ".minimum_reference_bigram_count")
                target[word] = values
            if group == "top_han_bigrams":
                layer[group] = target
            else:
                layer["features"][group] = target
        layer["defined_chapters"] = sum(value > 0 for value in denominators)
        layers[name] = layer
    segmentation = profile["segmentation"]
    _keys(segmentation, ("method", "status", "unknown_han_characters", "unknown_han_fraction", "issues"), "segmentation")
    issues = segmentation["issues"]
    if not isinstance(issues, list):
        _invalid("segmentation.issues")
    issue_counts = Counter()
    for issue in issues:
        if not isinstance(issue, dict) or not isinstance(issue.get("code"), str) or issue["code"] not in _ISSUE_CODES:
            _invalid("segmentation.issue_code")
        if type(issue.get("chapter")) is not int or issue["chapter"] not in _INCLUDED:
            _invalid("segmentation.issue_scope")
        issue_counts[issue["code"]] += 1
    unknown = _integer(segmentation["unknown_han_characters"], "segmentation.unknown_han_characters")
    total = unknown + sum(layer["han_characters"] for layer in layers.values())
    fraction = _number(segmentation["unknown_han_fraction"], "segmentation.unknown_han_fraction", nullable=total == 0)
    if (fraction != (unknown / total if total else None) or segmentation["method"] != _METHOD
            or segmentation["status"] != ("QUOTE_ISSUES_PRESENT" if issues else "BALANCED_QUOTES")):
        _invalid("segmentation.metadata")
    support = {
        "schema_version": 1, "kind": "STYLE_REFERENCE_AGGREGATE_SUPPORT", "support_policy": SUPPORT_POLICY,
        "read_only": True, "advisory": True, "literary_quality_verified": False, "editing_rule": EDITING_RULE,
        **{key: deepcopy(profile[key]) for key in ("dataset_ref", "manifest_sha256", "feature_set", "feature_policy",
                                                   "reference_scope", "readiness", "human_audit_status", "provisional",
                                                   "chapter_count", "main_text_segment_count")},
        "human_audit": {key: audit[key] for key in ("status", "scope", "review_count", "authority_effect")},
        "statistic_columns": list(STATISTIC_COLUMNS), "quantile_method": _QUANTILE_METHOD,
        "layers": layers,
        "segmentation": {"method": segmentation["method"], "status": segmentation["status"],
                         "unknown_han_characters": unknown, "unknown_han_fraction": fraction,
                         "issue_count": len(issues), "issue_counts_by_code": dict(sorted(issue_counts.items()))},
        "verdict": None, "authority_effect": "NONE", "evidence_effect": "NONE",
    }
    size = support_metadata(support)["support_bytes"]
    if size > max_bytes:
        raise ValueError(f"STYLE_SUPPORT_BYTE_LIMIT_EXCEEDED: {size} > {max_bytes}")
    return support
