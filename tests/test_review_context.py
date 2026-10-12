"""Context versioning tests; no synthetic opinions are real review evidence."""
from copy import deepcopy

import pytest

from rcwh.candidate_reviews import canonical_bytes, context_sha256, digest
from rcwh.competition import git_blob_sha
from rcwh.review_context import prepare_manifest
from test_literary_inputs import writing_repo
from test_corpus_dataset import corpus_repo
from test_source_extraction import extraction_repo


def bind(root, path, value):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value)
    target.write_bytes(raw)
    return {"path": path, "sha256": digest(raw)}


def record(root, package):
    text = "这是合成候选，不是实际文学评审。".encode()
    (root / "candidate.txt").write_bytes(text)
    return {"id": "fixture:context", "chapter": 89, "context_version": 2,
            "writing_package": {"path": package, "sha256": digest((root / package).read_bytes())},
            "baseline": {"sha256": "0" * 64}, "plock_ref": "fixture:lock",
            "review_protocol": bind(root, "reviews/protocol.json", {"questions": ["fixture"]}),
            "candidates": [{"id": "fixture:A", "blind_token": "anonymous:A",
                "artifact": {"kind": "REPO_FILE", "path": "candidate.txt", "git_blob_sha": git_blob_sha(text)},
                "authors": [{"kind": "HUMAN", "principal_id": "author:A", "source_id": "author:source"}]}]}


def prepare(root, value):
    import shutil
    from pathlib import Path
    shutil.copyfile(Path(__file__).resolve().parents[1] / "schemas/review_context_manifest.schema.json",
                    root / "schemas/review_context_manifest.schema.json")
    value["context_manifest"] = bind(root, "reviews/context.json", prepare_manifest(root, value))


def test_v2_unrelated_submission_does_not_change_semantic_context(writing_repo):
    root, _, package, _, _ = writing_repo
    value = record(root, package)
    prepare(root, value)
    before = context_sha256(root, value)
    bind(root, "data/provenance/audits/selection.json", {"reviews": ["new opinion"]})
    bind(root, "data/project/closure_roots.json", {"records": ["changed review digest"]})
    assert context_sha256(root, value) == before


def test_v2_changed_or_omitted_inputs_are_rejected(writing_repo):
    root, _, package, _, _ = writing_repo
    value = record(root, package)
    prepare(root, value)
    manifest = prepare_manifest(root, value)
    manifest["inputs"].pop()
    value["context_manifest"] = bind(root, "reviews/context.json", manifest)
    with pytest.raises(ValueError, match="INCOMPLETE_CONTEXT"):
        context_sha256(root, value)
    prepare(root, value)
    (root / "data/world/version.json").write_bytes(b'{"changed":true}')
    with pytest.raises(ValueError, match="identity mismatch"):
        context_sha256(root, value)


def test_v1_algorithm_is_preserved_and_versions_cannot_be_silently_swapped(writing_repo):
    root, _, package, _, _ = writing_repo
    value = record(root, package)
    value.pop("context_version")
    before = context_sha256(root, value)
    bind(root, "data/provenance/audits/selection.json", {"reviews": []})
    assert context_sha256(root, value) != before
    explicit = deepcopy(value)
    explicit["context_version"] = 1
    assert context_sha256(root, explicit) == context_sha256(root, value)
    explicit["context_version"] = 9
    with pytest.raises(ValueError, match="unsupported"):
        context_sha256(root, explicit)


def test_v2_authorship_and_protocol_content_are_bound(writing_repo):
    root, _, package, _, _ = writing_repo
    value = record(root, package)
    prepare(root, value)
    before = context_sha256(root, value)
    value["candidates"][0]["authors"][0]["principal_id"] = "different author"
    assert context_sha256(root, value) != before
    value["review_protocol"] = bind(root, "reviews/protocol.json", {"questions": ["changed"]})
    assert context_sha256(root, value) != before
