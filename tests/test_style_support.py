"""Pure numerical fixtures; optional frozen-profile parse, never a corpus rebuild."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
import pytest

from rcwh.candidate_reviews import canonical_bytes
from rcwh.evaluation.style import ADDRESS_SUFFIXES, NARRATOR_MARKERS
from rcwh.evaluation import style_reference as sr
from rcwh.evaluation.style_support import compact_author_support, support_metadata


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/style_support.schema.json").read_bytes())
VALIDATOR = Draft202012Validator(SCHEMA)
FROZEN_PACKET = ROOT / (
    "artifacts/agent_research/phase5/backtest/session-v1/author-packets/"
    "e32233948b0aac2f3a505082d7047de4d32899a24525b93c082bb10f1838a193.json"
)
GROUPS = {"narrator_markers": NARRATOR_MARKERS, "address_forms": ADDRESS_SUFFIXES,
          "declared_words": sr.DECLARED_WORDS}


def _record(denominators, seed):
    counts = [(chapter + seed) % 5 if han else 0 for chapter, han in enumerate(denominators, 1)]
    rows = [{"chapter": chapter, "han_characters": han, "count": count,
             "rate_per_10k_han": count * 10000 / han if han else None}
            for chapter, (han, count) in enumerate(zip(denominators, counts), 1)]
    count, han = sum(counts), sum(denominators)
    return {"count": count, "rate_per_10k_han": count * 10000 / han if han else None,
            "chapter_distribution": sr._distribution(rows)}


def _profile(*, empty_dialogue=False, bigrams=300, dataset="corpus:fixture-numeric:version-7"):
    layers = {}
    for index, name in enumerate(("narration", "dialogue")):
        # Different defined-chapter counts and changing denominators. Scope is
        # still exactly 1..78; no assumption that all 78 rates are defined.
        denominators = [(10000 * (1 + chapter % 3)) if chapter % (7 + index) else 0
                        for chapter in range(1, 79)]
        if name == "dialogue" and empty_dialogue:
            denominators = [0] * 78
        features = {group: {word: _record(denominators, seed) for seed, word in enumerate(words)}
                    for group, words in GROUPS.items()}
        selected = {} if not sum(denominators) else {
            chr(0x4e00 + seed) + chr(0x5000 + seed): _record(denominators, seed)
            for seed in range(bigrams)}
        selected = dict(sorted(selected.items(), key=lambda item: (-item[1]["count"], item[0])))
        layers[name] = {"han_characters": sum(denominators), "features": features, "top_han_bigrams": selected}
    unknown = 13
    total = unknown + sum(layer["han_characters"] for layer in layers.values())
    return {
        "dataset_ref": dataset, "manifest_sha256": "a" * 64,
        "readiness": "CANDIDATE_PENDING_HUMAN_AUDIT", "human_audit_status": "FAIL", "provisional": True,
        "human_audit": {"status": "FAIL", "scope": "CORPUS_HUMAN_LAYER_AUDIT", "review_count": 2,
                        "authority_effect": "NONE", "audit_notes": "MUST_NOT_REACH_AUTHOR",
                        "samples": [{"chapter": 79, "text": "HELDOUT_PRIVATE_SENTINEL"}]},
        "feature_set": sr.FEATURE_SET,
        "feature_policy": deepcopy(SCHEMA["properties"]["feature_policy"]["const"]),
        "reference_scope": deepcopy(SCHEMA["properties"]["reference_scope"]["const"]),
        "chapter_count": 78, "main_text_segment_count": 164,
        "segmentation": {
            "method": "NESTED_QUOTATION_HEURISTIC_NOT_SPEAKER_ATTRIBUTION",
            "status": "QUOTE_ISSUES_PRESENT", "unknown_han_characters": unknown,
            "unknown_han_fraction": unknown / total,
            "issues": [{"code": code, "chapter": chapter, "segment_id": "PRIVATE_LOCATOR_SENTINEL",
                        "offset": 999, "quote": "“", "audit_notes": "MUST_NOT_REACH_AUTHOR"}
                       for code, chapter in (("UNCLOSED_QUOTE", 1), ("UNCLOSED_QUOTE", 78),
                                             ("MISMATCHED_CLOSING_QUOTE", 4))],
        },
        "layers": layers, "verdict": None, "authority_effect": "NONE", "evidence_effect": "NONE",
    }


@pytest.fixture
def profile():
    return _profile()


def _records(value):
    for name, layer in value["layers"].items():
        for group, words in [*layer["features"].items(), ("top_han_bigrams", layer["top_han_bigrams"])]:
            for word, record in words.items():
                yield (name, group, word), record


def _assert_all_statistics_equal(profile, support):
    source = dict(_records(profile))
    compact = dict(_records(support))
    assert source.keys() == compact.keys()
    for key, record in source.items():
        distribution = record["chapter_distribution"]
        expected = [record["count"], record["rate_per_10k_han"],
                    distribution["q1"], distribution["median"], distribution["q3"]]
        assert compact[key] == expected
        assert [type(value) for value in compact[key]] == [type(value) for value in expected]
    for name, layer in profile["layers"].items():
        for group in GROUPS:
            assert list(support["layers"][name]["features"][group]) == list(layer["features"][group])
        assert list(support["layers"][name]["top_han_bigrams"]) == list(layer["top_han_bigrams"])
    return len(source)


def _assert_no_details(support):
    forbidden = {"text", "raw_prose", "excerpt", "title", "segment_id", "offset", "quote", "expected",
                 "audit_notes", "samples", "chapters", "chapter_distribution", "chapter_order",
                 "chapter_han_characters", "counts", "rates_per_10k_han", "minimum", "maximum"}

    def visit(value):
        if isinstance(value, dict):
            assert not value.keys() & forbidden
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(support)
    serialized = canonical_bytes(support)
    for sentinel in (b"MUST_NOT_REACH_AUTHOR", b"HELDOUT_PRIVATE_SENTINEL", b"PRIVATE_LOCATOR_SENTINEL"):
        assert sentinel not in serialized


def test_complete_projection_exact_metadata_numbers_and_bound(profile):
    before = canonical_bytes(profile)
    support = compact_author_support(profile)
    VALIDATOR.validate(support)
    assert _assert_all_statistics_equal(profile, support) == 674
    assert support["statistic_columns"] == ["count", "rate_per_10k_han", "q1", "median", "q3"]
    for key in ("dataset_ref", "manifest_sha256", "feature_set", "feature_policy", "reference_scope",
                "readiness", "human_audit_status", "provisional", "chapter_count", "main_text_segment_count"):
        assert support[key] == profile[key]
    assert support["human_audit"] == {key: profile["human_audit"][key]
                                      for key in ("status", "scope", "review_count", "authority_effect")}
    assert support["layers"]["narration"]["defined_chapters"] == 67
    assert support["layers"]["dialogue"]["defined_chapters"] == 69
    assert support["quantile_method"] == "LINEAR_INTERPOLATION"
    assert support["advisory"] is support["read_only"] is True
    assert support["literary_quality_verified"] is False
    assert support["verdict"] is None and support["authority_effect"] == support["evidence_effect"] == "NONE"
    assert support["segmentation"]["issue_count"] == 3
    assert support["segmentation"]["issue_counts_by_code"] == {"UNCLOSED_QUOTE": 2, "MISMATCHED_CLOSING_QUOTE": 1}
    assert support["segmentation"]["status"] == "QUOTE_ISSUES_PRESENT"
    _assert_no_details(support)
    raw = canonical_bytes(support)
    assert len(raw) <= 64000
    assert support_metadata(support) == {"support_bytes": len(raw), "support_sha256": hashlib.sha256(raw).hexdigest()}
    assert canonical_bytes(profile) == before


def test_deterministic_isolated_result_and_generic_source_identity(profile):
    first = compact_author_support(profile)
    assert canonical_bytes(first) == canonical_bytes(compact_author_support(deepcopy(profile)))
    profile["dataset_ref"] = "corpus:another-fixture:v9"
    profile["manifest_sha256"] = "b" * 64
    second = compact_author_support(profile)
    assert second["dataset_ref"] == profile["dataset_ref"]
    assert second["manifest_sha256"] == profile["manifest_sha256"]
    assert first["layers"] == second["layers"]
    second["feature_policy"]["declared_words"].append("MUTATED")
    second["reference_scope"]["included_chapters"].clear()
    second["layers"]["narration"]["features"]["declared_words"]["了"][0] = -99
    assert len(profile["feature_policy"]["declared_words"]) == 22
    assert profile["reference_scope"]["included_chapters"] == list(range(1, 79))
    assert profile["layers"]["narration"]["features"]["declared_words"]["了"]["count"] >= 0


@pytest.mark.parametrize("status", ["PENDING", "PASS", "FAIL"])
def test_live_audit_status_is_preserved_without_a_gate(profile, status):
    profile["human_audit_status"] = profile["human_audit"]["status"] = status
    profile["provisional"] = status != "PASS"
    support = compact_author_support(profile)
    assert support["human_audit_status"] == support["human_audit"]["status"] == status
    assert support["provisional"] == (status != "PASS")
    assert support["readiness"] == "CANDIDATE_PENDING_HUMAN_AUDIT"
    assert support["reference_scope"]["subset_audit_status"] == "NOT_SEPARATELY_AUDITED"
    assert support["verdict"] is None


def test_empty_layer_nulls_and_smaller_selected_vocabulary():
    profile = _profile(empty_dialogue=True, bigrams=4)
    support = compact_author_support(profile)
    VALIDATOR.validate(support)
    assert _assert_all_statistics_equal(profile, support) == 78
    dialogue = support["layers"]["dialogue"]
    assert dialogue["han_characters"] == dialogue["defined_chapters"] == 0
    assert dialogue["total_chapters"] == 78 and dialogue["top_han_bigrams"] == {}
    for words in dialogue["features"].values():
        assert all(record == [0, None, None, None, None] for record in words.values())


def test_all_empty_zero_and_null_segmentation():
    profile = _profile(bigrams=0)
    for layer in profile["layers"].values():
        layer["han_characters"] = 0
        for words in layer["features"].values():
            for word in words:
                words[word] = _record([0] * 78, 0)
    profile["segmentation"].update(issues=[], status="BALANCED_QUOTES", unknown_han_characters=0,
                                     unknown_han_fraction=None)
    support = compact_author_support(profile)
    VALIDATOR.validate(support)
    assert support["segmentation"]["unknown_han_fraction"] is None
    assert support["segmentation"]["issue_count"] == 0
    assert support["segmentation"]["issue_counts_by_code"] == {}
    assert support["layers"]["narration"]["features"]["declared_words"]["的"] == [0, None, None, None, None]


@pytest.mark.parametrize("max_bytes", [0, -1, 64001, True, 64000.0, None, "64000"])
def test_invalid_limits_reject_without_input_changes(profile, max_bytes):
    before = canonical_bytes(profile)
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_MAX_BYTES"):
        compact_author_support(profile, max_bytes)
    assert canonical_bytes(profile) == before


def test_canonical_utf8_bound_is_inclusive_and_never_truncates(profile):
    support = compact_author_support(profile)
    size = len(canonical_bytes(support))
    ascii_size = len((json.dumps(support, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())
    assert ascii_size > size
    assert canonical_bytes(compact_author_support(profile, size)) == canonical_bytes(support)
    before = canonical_bytes(profile)
    with pytest.raises(ValueError, match="STYLE_SUPPORT_BYTE_LIMIT_EXCEEDED"):
        compact_author_support(profile, size - 1)
    assert canonical_bytes(profile) == before
    # A supported metadata label may make support too big; do not silently drop
    # statistics, source identity, or audit metadata to force it below the cap.
    profile["dataset_ref"] = "corpus:" + "fixture" * 10000
    with pytest.raises(ValueError, match="STYLE_SUPPORT_BYTE_LIMIT_EXCEEDED"):
        compact_author_support(profile)


@pytest.mark.parametrize("scope", [None, {},
    {"included_chapters": list(range(1, 79))},
    {"included_chapters": list(range(1, 81)), "excluded_chapters": []},
    {"included_chapters": list(range(1, 79)), "excluded_chapters": [79]},
    {"included_chapters": list(range(1, 78)), "excluded_chapters": [79, 80]},
])
def test_scope_must_be_defined_and_exact(profile, scope):
    profile["reference_scope"] = scope
    with pytest.raises(ValueError, match="reference_scope"):
        compact_author_support(profile)


@pytest.mark.parametrize("field", ["reference_scope", "human_audit_status", "provisional", "feature_policy", "manifest_sha256"])
def test_required_metadata_cannot_be_hidden(profile, field):
    del profile[field]
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_PROFILE"):
        compact_author_support(profile)


@pytest.mark.parametrize("value", [None, [], "profile", {"layers": {}}])
def test_unsupported_inputs_reject(value):
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_PROFILE"):
        compact_author_support(value)


@pytest.mark.parametrize("change", [
    lambda p: p.update(feature_set="unrecognized:v2"),
    lambda p: p["feature_policy"].update(rate_scale=100),
    lambda p: p["feature_policy"].update(zero_candidate_counts_retained=1),
    lambda p: p["feature_policy"].update(raw_prose="PRIVATE"),
    lambda p: p.update(chapter_count=True),
    lambda p: p.update(verdict="PASS"),
    lambda p: p.update(authority_effect="PROMOTE"),
    lambda p: p.update(provisional=False),
    lambda p: p["human_audit"].update(status="PASS"),
    lambda p: p["human_audit"].update(review_count=-1),
    lambda p: p["reference_scope"]["included_chapters"].__setitem__(0, True),
    lambda p: p["reference_scope"].update(excluded_chapters=[80, 79]),
    lambda p: p["reference_scope"].update(subset_audit_status="PASS"),
    lambda p: p["segmentation"].update(status="BALANCED_QUOTES"),
    lambda p: p["segmentation"].update(unknown_han_fraction=float("nan")),
    lambda p: p["segmentation"]["issues"][0].update(chapter=79),
    lambda p: p["segmentation"]["issues"][0].update(code="UNSUPPORTED_QUOTE_ISSUE"),
    lambda p: p["layers"]["narration"]["features"]["declared_words"].pop("了"),
    lambda p: p.update(raw_prose="PRIVATE"),
])
def test_invalid_profiles_reject(profile, change):
    change(profile)
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_PROFILE"):
        compact_author_support(profile)


@pytest.mark.parametrize("location, value", [
    (("count",), -1), (("count",), True), (("rate_per_10k_han",), None),
    (("rate_per_10k_han",), float("nan")), (("rate_per_10k_han",), float("inf")),
    (("chapter_distribution", "q1"), None), (("chapter_distribution", "median"), float("-inf")),
    (("chapter_distribution", "q3"), "1.0"), (("chapter_distribution", "defined_chapters"), 78),
    (("chapter_distribution", "total_chapters"), 77),
    (("chapter_distribution", "quantile_method"), "UNSUPPORTED"),
])
def test_invalid_or_missing_statistics_reject(profile, location, value):
    record = profile["layers"]["narration"]["features"]["declared_words"]["了"]
    target = record
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_PROFILE"):
        compact_author_support(profile)
    del target[location[-1]]
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_PROFILE"):
        compact_author_support(profile)


@pytest.mark.parametrize("change", [
    lambda r: r.update(count=r["count"] + 1),
    lambda r: r.update(rate_per_10k_han=r["rate_per_10k_han"] + 1),
    lambda r: r["chapter_distribution"].update(median=1.2345),
    lambda r: r["chapter_distribution"]["chapters"].pop(),
    lambda r: r["chapter_distribution"]["chapters"][0].update(chapter=79),
    lambda r: r["chapter_distribution"]["chapters"][0].update(rate_per_10k_han=None),
    lambda r: r["chapter_distribution"]["chapters"][0].update(count=-1),
])
def test_chapter_rows_and_aggregate_stats_must_agree(profile, change):
    record = profile["layers"]["narration"]["features"]["declared_words"]["了"]
    change(record)
    with pytest.raises(ValueError, match="INVALID_STYLE_SUPPORT_PROFILE"):
        compact_author_support(profile)


def test_cross_feature_layer_denominators_must_agree(profile):
    layer = profile["layers"]["narration"]
    denominators = [row["han_characters"] for row in layer["features"]["declared_words"]["了"]["chapter_distribution"]["chapters"]]
    denominators[0], denominators[1] = denominators[1], denominators[0]
    layer["features"]["declared_words"]["了"] = _record(denominators, 1)
    with pytest.raises(ValueError, match="inconsistent_layer_denominators"):
        compact_author_support(profile)


def test_no_additional_or_invalid_bigram_can_enter_support(profile):
    layer = profile["layers"]["narration"]
    layer["top_han_bigrams"]["extra-token"] = deepcopy(next(iter(layer["top_han_bigrams"].values())))
    with pytest.raises(ValueError, match="top_han_bigrams"):
        compact_author_support(profile)


@pytest.mark.parametrize("path", [
    ("text",), ("human_audit", "audit_notes"), ("segmentation", "segment_id"),
    ("layers", "narration", "chapters"),
])
def test_new_schema_rejects_author_detail_fields(profile, path):
    support = compact_author_support(profile)
    target = support
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "UNSAFE"
    with pytest.raises(ValidationError):
        VALIDATOR.validate(support)


def test_schema_rejects_missing_features_columns_or_authority(profile):
    support = compact_author_support(profile)
    mutations = [lambda p: p["layers"]["narration"]["features"]["address_forms"].pop("姑娘"),
                 lambda p: p["statistic_columns"].reverse(),
                 lambda p: p.update(authority_effect="PASS"),
                 lambda p: p.update(verdict="PASS"),
                 lambda p: p.update(advisory=False)]
    for mutate in mutations:
        altered = deepcopy(support)
        mutate(altered)
        with pytest.raises(ValidationError):
            VALIDATOR.validate(altered)


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.skipif(not FROZEN_PACKET.is_file(), reason="optional existing frozen 1..78 profile packet")
def test_existing_frozen_profile_metadata_only_exact_674_and_unchanged_bytes(monkeypatch):
    # Read the frozen packet only to extract its numerical profile. Do not print
    # request content, shared task, prose, issue locators, or private audit notes.
    before = FROZEN_PACKET.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()
    packet = json.loads(before)
    task = json.loads(packet["request"]["messages"][0]["content"])
    profile = task["workflow_support"]["style_reference"]
    profile_before = canonical_bytes(profile)

    def forbidden(*args, **kwargs):
        pytest.fail("support projection must not load or rebuild corpus, audit, or generation")

    monkeypatch.setattr(sr, "reference_profile", forbidden)
    monkeypatch.setattr(sr.CorpusRepository, "load", forbidden)
    monkeypatch.setattr(sr.CorpusAudit, "summary", forbidden)
    support = compact_author_support(profile)
    VALIDATOR.validate(support)
    assert _assert_all_statistics_equal(profile, support) == 674
    assert all(len(layer["top_han_bigrams"]) == 300 for layer in support["layers"].values())
    assert len(canonical_bytes(support)) <= 64000
    assert support["reference_scope"]["included_chapters"] == list(range(1, 79))
    assert support["reference_scope"]["excluded_chapters"] == [79, 80]
    expected_counts = dict(sorted(Counter(issue["code"] for issue in profile["segmentation"]["issues"]).items()))
    assert support["segmentation"]["issue_counts_by_code"] == expected_counts
    assert support["segmentation"]["issue_count"] == len(profile["segmentation"]["issues"])
    assert support["segmentation"]["status"] == profile["segmentation"]["status"]
    for key in ("dataset_ref", "manifest_sha256", "feature_set", "feature_policy", "reference_scope",
                "readiness", "human_audit_status", "human_audit", "provisional"):
        assert support[key] == profile[key]
    _assert_no_details(support)
    assert canonical_bytes(profile) == profile_before
    after = FROZEN_PACKET.read_bytes()
    assert after == before and hashlib.sha256(after).hexdigest() == before_hash
