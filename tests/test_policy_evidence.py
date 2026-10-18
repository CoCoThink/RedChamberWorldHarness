"""Pure evidence validation never turns fabricated fixture readings into admission."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.evaluation.policy_evidence import (
    _components, _full_coverage, _interval, _value, build_policy_evidence_request,
    check_policy_evidence, strict_json,
)
from rcwh.generation.records import binding

ROOT = Path(__file__).resolve().parents[1]
SELECTION = "artifacts/agent_research/phase6/revisions-v2/release-evaluation/request-v1.json"


@pytest.fixture(scope="module")
def request86():
    return build_policy_evidence_request(ROOT, binding(ROOT, SELECTION), 86)


@pytest.fixture
def isolated(tmp_path):
    for directory in ("data/provenance", "data/literals", "data/plocks", "data/implementation_alignment",
                      "data/promotion/policies"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    for relative in ("data/project/scope.json", "schemas/project_scope.schema.json"):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    selection = json.loads((ROOT / SELECTION).read_bytes())
    row = deepcopy(next(row for row in selection["chapters"] if row["chapter"] == 86))
    for key in ("draft", "writing_package"):
        ref = row[key]
        destination = tmp_path / ref["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref["path"], destination)
    # Synthetic text, never a real repaired candidate or evidence of actual reading.
    text = "第八十六回 测试\r\n\r\n药不是还没吃么？再温一温。今儿早起她还说药苦。\r\n那盏药早已冷透，再没有人去温。\r\n"
    (tmp_path / "candidate.txt").write_bytes(text.encode())
    row["candidate"] = binding(tmp_path, "candidate.txt")
    (tmp_path / "selection.json").write_bytes(canonical_bytes({"chapters": [row]}))
    request = build_policy_evidence_request(tmp_path, binding(tmp_path, "selection.json"), 86)
    reading = {"schema_version": 1, "kind": "POLICY_EVIDENCE_READING",
               **{key: request[key] for key in ("request_sha256", "context_sha256", "manifest_sha256")},
               "candidate_sha256": row["candidate"]["sha256"],
               "reader": {"principal_id": "fixture-only", "session_id": "fixture", "context_id": "fixture",
                          "isolation_asserted": False, "disclosures": ["Synthetic unit test, not actual reading."]},
               "read_scope": [{"file": row["candidate"], "start": 0, "end": len(text)}],
               "checks": [{"key": item["key"], "finding": "UNKNOWN", "explanation": "Fixture unknown.",
                           "support": [], "counterevidence": []} for item in request["manifest"]],
               "qualification": "MODEL", "authority_effect": "NONE", "evidence_effect": "NONE"}
    return tmp_path, request, reading, text


def checked(root, request, reading):
    (root / "reading.json").write_bytes(canonical_bytes(reading))
    return check_policy_evidence(root, request, binding(root, "reading.json"))


def test_real20_policy_manifest_complete_roots_roles_features_and_aliases():
    roots = features = anchors = aliases = 0
    for chapter in range(81, 101):
        request = build_policy_evidence_request(ROOT, binding(ROOT, SELECTION), chapter)
        manifest = request["manifest"]
        assert len({row["key"] for row in manifest}) == len(manifest)
        policy = json.loads((ROOT / request["context"]["selected"]["policy"]["path"]).read_bytes())
        actual_roots = [row for row in manifest if row["role"] == "PROJECTED_ROOT"]
        assert [row["value"] for row in actual_roots] == policy["semantic_obligations"]
        for row in manifest:
            assert row["value_sha256"] == digest(canonical_bytes(row["value"]))
            if row["role"] == "FORBIDDEN_ALIAS":
                assert row["crosswalk"]
        roots += len(actual_roots)
        features += sum(row["role"] == "PLOCK_FEATURE" for row in manifest)
        anchors += sum(row["role"] == "ANCHOR_OBSERVATION" for row in manifest)
        aliases += sum(row["role"] == "FORBIDDEN_ALIAS" for row in manifest)
        assert request["semantic_expansion_status"] == "PENDING_ATTRIBUTED_CLAUSE_REVIEW"
    assert (roots, features, anchors, aliases) == (289, 20, 14, 38)


def test_request_hash_preimage_is_explicit_and_not_self_referential(request86):
    payload = {key: value for key, value in request86.items() if key != "request_sha256"}
    assert digest(canonical_bytes(payload)) == request86["request_sha256"]
    assert request86["manifest_sha256"] == digest(canonical_bytes(request86["manifest"]))
    assert request86["context_sha256"] == digest(canonical_bytes(request86["context"]))


def test_full_fixture_checklist_is_not_semantic_or_identity_pass(isolated):
    root, request, reading, _ = isolated
    report = checked(root, request, reading)
    assert report["integrity_status"] == report["declared_structural_coverage"] == "PASS"
    assert report["semantic_status"] == report["status"] == report["release_gate_eligibility"] == "PENDING"
    assert report["identity_eligibility"] == "PENDING_NOT_IMPLEMENTED"
    assert report["independent_human_admission"] is False
    assert report["machine"]["anchor_status"] == "PASS"
    assert report["attributed_checks"] == reading["checks"]


def test_real_selected86_lost_plock_anchors_are_replacement_case_not_fail(isolated, request86):
    root, _, reading, _ = isolated
    raw = (ROOT / request86["context"]["selected"]["candidate"]["path"]).read_bytes()
    (root / "candidate.txt").write_bytes(raw)
    selection = json.loads((root / "selection.json").read_bytes())
    selection["chapters"][0]["candidate"] = binding(root, "candidate.txt")
    (root / "selection.json").write_bytes(canonical_bytes(selection))
    request = build_policy_evidence_request(root, binding(root, "selection.json"), 86)
    for key in ("request_sha256", "context_sha256", "manifest_sha256"):
        reading[key] = request[key]
    reading["candidate_sha256"] = digest(raw)
    reading["read_scope"] = []
    reading["checks"] = []
    report = checked(root, request, reading)
    # The lost ch86 anchors are P-Lock prose (ADVISORY), not evidence literals.
    assert report["machine"]["anchor_status"] == "REPLACEMENT_CASE"
    assert {f["severity"] for f in report["machine"]["graded_findings"]} == {"ADVISORY"}
    assert report["status"] != "FAIL" and report["semantic_status"] == "PENDING"


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}', b'\xff'])
def test_strict_parser_rejects_ambiguous_or_non_utf8_payload(raw):
    with pytest.raises(ValueError):
        strict_json(raw)


@pytest.mark.parametrize("field", ["request_sha256", "context_sha256", "manifest_sha256", "candidate_sha256"])
def test_stale_reading_rejected(isolated, field):
    root, request, reading, _ = isolated
    reading[field] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        checked(root, request, reading)


@pytest.mark.parametrize("target", ["schema_version", "nested_chapter"])
def test_boolean_integer_request_alias_rejected(isolated, target):
    root, request, reading, _ = isolated
    if target == "schema_version":
        request["schema_version"] = True
    else:
        # Numeric equality must not bypass the original canonical preimage.
        row = next(item for item in request["manifest"] if item["role"] == "PROJECTED_ROOT")
        row["value"]["rule"]["chapter"] = 86.0
    with pytest.raises(ValueError, match="stale or altered"):
        checked(root, request, reading)


@pytest.mark.parametrize("ranges", [[(0, 10), (10, 20)], [(0, 11), (9, 20)], [(10, 20), (0, 10)]])
def test_quote_can_cross_union_of_declared_ranges(isolated, ranges):
    root, request, reading, text = isolated
    ref = request["context"]["selected"]["candidate"]
    reading["read_scope"] = [{"file": ref, "start": start, "end": end} for start, end in ranges]
    reading["checks"][0]["support"] = [{"file": ref, "start": 8, "end": 12, "quote": text[8:12]}]
    report = checked(root, request, reading)
    assert report["integrity_status"] == "PASS"
    assert report["semantic_status"] == "PENDING"


def test_quote_cannot_cross_gap_between_declared_ranges(isolated):
    root, request, reading, text = isolated
    ref = request["context"]["selected"]["candidate"]
    reading["read_scope"] = [{"file": ref, "start": 0, "end": 9}, {"file": ref, "start": 10, "end": 20}]
    reading["checks"][0]["support"] = [{"file": ref, "start": 8, "end": 12, "quote": text[8:12]}]
    with pytest.raises(ValueError, match="outside declared read scope"):
        checked(root, request, reading)


def test_manifest_tamper_cannot_drop_child_even_with_rehashed_request(isolated):
    root, request, reading, _ = isolated
    request["manifest"].pop()
    request["manifest_sha256"] = digest(canonical_bytes(request["manifest"]))
    payload = {key: value for key, value in request.items() if key != "request_sha256"}
    request["request_sha256"] = digest(canonical_bytes(payload))
    with pytest.raises(ValueError, match="stale or altered"):
        checked(root, request, reading)


@pytest.mark.parametrize("edit", ["duplicate", "unknown", "missing"])
def test_check_keys_cannot_alias_or_hide_missing_checks(isolated, edit):
    root, request, reading, _ = isolated
    if edit == "missing":
        reading["checks"].pop()
        report = checked(root, request, reading)
        assert report["missing_checks"] and report["declared_structural_coverage"] == "PENDING"
    else:
        if edit == "duplicate":
            reading["checks"].append(deepcopy(reading["checks"][0]))
        else:
            reading["checks"][0]["key"] = "invented-key"
        with pytest.raises(ValueError, match=edit):
            checked(root, request, reading)


def test_exact_unicode_crlf_and_negative_evidence_retained_without_semantic_certification(isolated):
    root, request, reading, text = isolated
    ref = request["context"]["selected"]["candidate"]
    evidence = {"file": ref, "start": 0, "end": 14, "quote": text[:14]}
    reading["checks"][0].update(finding="VIOLATED", counterevidence=[evidence])
    report = checked(root, request, reading)
    assert report["attributed_checks"][0]["finding"] == "VIOLATED"
    assert report["attributed_checks"][0]["counterevidence"] == [evidence]
    assert report["semantic_status"] == "PENDING"
    evidence["quote"] = evidence["quote"].replace("\r\n", "\n")
    with pytest.raises(ValueError, match="quote differs"):
        checked(root, request, reading)


@pytest.mark.parametrize("variant", ["out-of-range", "empty", "boolean", "wrong-file", "outside-scope", "forged"])
def test_invalid_quote_and_scope_rejected(isolated, variant):
    root, request, reading, text = isolated
    ref = request["context"]["selected"]["candidate"]
    evidence = {"file": deepcopy(ref), "start": 0, "end": 2, "quote": text[:2]}
    if variant == "out-of-range":
        evidence["end"] = len(text) + 1
    elif variant == "empty":
        evidence["end"] = 0
    elif variant == "boolean":
        evidence["start"] = False
    elif variant == "wrong-file":
        evidence["file"]["path"] = "reading.json"
    elif variant == "outside-scope":
        reading["read_scope"][0]["start"] = 2
    else:
        evidence["quote"] = "假字"
    reading["checks"][0]["support"] = [evidence]
    with pytest.raises(ValueError):
        checked(root, request, reading)


def test_claimed_support_without_evidence_and_partial_scope_stays_pending(isolated):
    root, request, reading, _ = isolated
    reading["checks"][0]["finding"] = "SUPPORTED"
    reading["read_scope"][0]["start"] = 1
    report = checked(root, request, reading)
    assert report["unsupported_declarations"] and not report["candidate_declared_read_scope_complete"]
    assert report["declared_structural_coverage"] == "PENDING"


@pytest.mark.parametrize("field,value", [("overall_status", "PASS"), ("raw_submission", {}), ("qualification", "INDEPENDENT_HUMAN")])
def test_no_aggregate_pass_self_hash_or_human_upgrade(isolated, field, value):
    root, request, reading, _ = isolated
    reading[field] = value
    with pytest.raises(ValueError, match="invalid policy evidence reading"):
        checked(root, request, reading)


def test_changed_projection_input_or_candidate_invalidates_request(isolated):
    root, request, reading, _ = isolated
    (root / "candidate.txt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="stale"):
        checked(root, request, reading)


def test_all_supported_fixture_declarations_cannot_qualify_semantics(isolated):
    root, request, reading, text = isolated
    ref = request["context"]["selected"]["candidate"]
    for check in reading["checks"]:
        check.update(finding="SUPPORTED", support=[{"file": ref, "start": 0, "end": 2, "quote": text[:2]}])
    report = checked(root, request, reading)
    assert report["declared_structural_coverage"] == "PASS"
    assert report["status"] == report["semantic_status"] == report["release_gate_eligibility"] == "PENDING"
    assert report["identity_eligibility"] == "PENDING_NOT_IMPLEMENTED"


def test_projection_dependency_change_invalidates_request(isolated):
    root, request, reading, _ = isolated
    path = root / "data/plocks/r4_literary.yaml"
    path.write_bytes(path.read_bytes() + b"\n# byte-only change\n")
    with pytest.raises(ValueError, match="invalid selected policy"):
        checked(root, request, reading)


def test_duplicate_selection_and_missing_book_candidate_rejected(isolated):
    root, _, _, _ = isolated
    selected = json.loads((root / "selection.json").read_bytes())
    selected["chapters"].append(deepcopy(selected["chapters"][0]))
    (root / "duplicate.json").write_bytes(canonical_bytes(selected))
    with pytest.raises(ValueError, match="duplicate"):
        build_policy_evidence_request(root, binding(root, "duplicate.json"), 86)
    selected["chapters"][1]["chapter"] = 87
    selected["chapters"][1]["candidate"] = {"path": "absent.txt", "sha256": "0" * 64}
    (root / "missing.json").write_bytes(canonical_bytes(selected))
    with pytest.raises(FileNotFoundError):
        build_policy_evidence_request(root, binding(root, "missing.json"), 86)


def test_detached_raw_binding_and_symlink_escape_rejected(isolated):
    root, request, reading, _ = isolated
    (root / "reading.json").write_bytes(canonical_bytes(reading))
    ref = binding(root, "reading.json")
    (root / "reading.json").write_bytes(canonical_bytes(reading) + b" ")
    with pytest.raises(ValueError, match="stale"):
        check_policy_evidence(root, request, ref)
    (root / "alias.json").symlink_to(root / "reading.json")
    with pytest.raises(ValueError, match="symlink"):
        check_policy_evidence(root, request, {"path": "alias.json", "sha256": digest((root / "reading.json").read_bytes())})


def test_builder_and_checker_write_no_files(isolated):
    root, request, reading, _ = isolated
    (root / "reading.json").write_bytes(canonical_bytes(reading))
    before = {str(path.relative_to(root)): digest(path.read_bytes()) for path in root.rglob("*") if path.is_file()}
    rebuilt = build_policy_evidence_request(root, request["context"]["selection"], 86)
    check_policy_evidence(root, rebuilt, binding(root, "reading.json"))
    after = {str(path.relative_to(root)): digest(path.read_bytes()) for path in root.rglob("*") if path.is_file()}
    assert after == before


def test_pointer_escaping_and_no_negative_index(tmp_path):
    (tmp_path / "x.json").write_bytes(b'{"a/b":{"~":[10,20]}}')
    ref = binding(tmp_path, "x.json")
    assert _value(tmp_path, ref, "/a~1b/~0/1") == 20
    for pointer in ("/a~1b/~0/-1", "/a~1b/~0/01", "/a~2b"):
        with pytest.raises(ValueError):
            _value(tmp_path, ref, pointer)


def test_structural_expansion_is_lossless_not_semantic_atomization():
    value = {"a/b": ["one and two", {"~": []}], "metadata": False}
    assert list(_components(value, "/root")) == [
        ("/root/a~1b/0", "one and two"), ("/root/a~1b/1/~0", []), ("/root/metadata", False)]
    assert _full_coverage([(2, 4), (0, 2)], 4)
    assert not _full_coverage([(0, 1), (2, 4)], 4)
    with pytest.raises(ValueError):
        _interval({"start": True, "end": 2}, "abcd")
