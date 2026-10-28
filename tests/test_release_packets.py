"""Prepared research-edition packets bind live inputs and validate (read-only)."""
import json
from pathlib import Path

import pytest

from rcwh.assets import AssetError
from rcwh.workflow.agent_panel import verify_packet
from rcwh.workflow.release_packets import _write_immutable

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / "data/agent_release/research-81-100-v1"
SELECTION = ROOT / "data/agent_release/selection-81-100-v2.json"


def test_edition_request_binds_verified_packets_for_all_twenty_chapters():
    request = json.loads((EDITION / "request.json").read_bytes())
    assert [row["chapter"] for row in request["chapters"]] == list(range(81, 101))
    assert all(row["mode"] == "AGENT_CANDIDATE" for row in request["chapters"])
    for row in request["chapters"]:
        assert row["rebind_receipt"]["path"] == f"data/agent_release/rebind-v4/receipts/ch{row['chapter']}.json"
        for ref in [row["panel"], *row["source_reviews"], *row["corpus_reviews"]]:
            packet = verify_packet(ROOT, ref["packet"])
            assert ref["subject_id"] in {s["id"] for s in packet["subjects"]}
    assert "archive/" not in (EDITION / "request.json").read_text()
    book = verify_packet(ROOT, request["book_review"]["packet"])
    spans = [s["chapters"] for s in book["subjects"]]
    assert spans == [list(range(81, 88)), list(range(87, 93)), list(range(92, 98)), list(range(97, 101))]
    assert request["book_review"]["subject_ids"] == [s["id"] for s in book["subjects"]]
    assert all(s["scope"] == "BOOK" and s["review_policy"] == "ADVISORY" for s in book["subjects"])
    assert all(len((ROOT / s["binding"]["path"]).read_bytes()) <= 197 * 1024 for s in book["subjects"])


def test_rebound_selection_uses_v4_packages_with_disclosure_receipts():
    selection = json.loads(SELECTION.read_bytes())
    assert selection["id"] == "selection:81-100:v2"
    for row in selection["chapters"]:
        chapter = row["chapter"]
        assert row["writing_package"]["path"] == f"data/writing/packages/ch{chapter}-agent-research-v4.json"
        draft = json.loads((ROOT / row["draft"]["path"]).read_bytes())
        assert draft["package"] == row["writing_package"] and draft["parent"] is None
        assert draft["candidate"] == row["candidate"]
        receipt = json.loads((ROOT / f"data/agent_release/rebind-v4/receipts/ch{chapter}.json").read_bytes())
        assert receipt["current"]["draft"] == row["draft"]
        assert receipt["prose_identical_to_previous"] == (chapter != 86)
        package = json.loads((ROOT / row["writing_package"]["path"]).read_bytes())
        assert package["exemplar_set"]["path"] == "data/writing/exemplars/ch89-research-v3.json"
        assert not any(s["source_ref"].startswith("src:history:cao:1728:") and not s["source_ref"].endswith(":npm005664")
                       for s in package["sources"])
    ch86 = next(r for r in selection["chapters"] if r["chapter"] == 86)
    assert "叫了声二叔" not in (ROOT / ch86["candidate"]["path"]).read_text(encoding="utf-8")


def test_cao_archive_sources_are_disclosed_as_agent_transcription():
    from rcwh.graph import ProvenanceGraph
    from rcwh.history import HistoricalMechanismRegistry
    graph = ProvenanceGraph.from_repo(ROOT)
    for key in ("inventory-seal", "pawn-tickets", "family-housing"):
        source = graph.sources[f"src:history:cao:1728:{key}:npm005664"]
        assert "代理目读校录" in source["bibliography"]["citation"] and "二百八十六" not in source["bibliography"]["citation"]
    claim = graph.claims["claim:history:h05:pawn-as-cashflow"]
    assert claim["modality"] == "INFERENCE"
    assert claim["support"][0]["source"].endswith(":npm005664")
    registry = HistoricalMechanismRegistry.from_repo(ROOT)
    assert registry.mechanisms["H05"]["verdict"] == "PASS-WITH-CAUTION"
    assert registry.validate_integrity(graph) == []


def test_packets_are_immutable_once_written(tmp_path):
    _write_immutable(tmp_path, "p.json", {"a": 1})
    _write_immutable(tmp_path, "p.json", {"a": 1})  # identical bytes: no-op
    with pytest.raises(AssetError, match="different bytes"):
        _write_immutable(tmp_path, "p.json", {"a": 2})


def test_chapter_packet_is_unchanged_when_another_chapter_is_revised(tmp_path):
    from rcwh.workflow.release_packets import chapter_packets
    def binding(value):
        return _write_immutable(tmp_path, f"{value}.json", {"text": value})
    rows = {ch: {"candidate": binding(f"candidate-{ch}"), "writing_package": binding(f"package-{ch}")} for ch in (81, 82)}
    subjects = [{"id": f"chapter-{ch}", "scope": "CANDIDATE", "binding": row["candidate"]} for ch, row in rows.items()]
    before = chapter_packets(tmp_path, subjects, rows, "coordinator")
    rows[82]["candidate"] = binding("candidate-82-revised")
    subjects[1]["binding"] = rows[82]["candidate"]
    after = chapter_packets(tmp_path, subjects, rows, "coordinator")
    assert after[81] == before[81] and after[82] != before[82]


def test_explicit_cross_chapter_context_changes_only_dependent_packets(tmp_path):
    from rcwh.workflow.release_packets import chapter_packets
    _write_immutable(tmp_path, 'schemas/agent_packet.schema.json',
                     (ROOT / 'schemas/agent_packet.schema.json').read_bytes())
    def binding(value):
        return _write_immutable(tmp_path, f"{value}.json", {"text": value})
    rows = {ch: {'candidate': binding(f'candidate-{ch}'), 'writing_package': binding(f'package-{ch}')}
            for ch in (81, 82, 83)}
    rows[81]['review_context_chapters'] = {'contract-81-1': [82]}
    subjects = [{'id': f'chapter-{ch}', 'scope': 'CANDIDATE', 'binding': row['candidate']}
                for ch, row in rows.items()]
    subjects.append({'id': 'contract-81-1', 'scope': 'CONTRACT', 'binding': binding('contract')})
    before = chapter_packets(tmp_path, subjects, rows, 'coordinator')
    packet = verify_packet(tmp_path, before[81])
    assert rows[82]['candidate'] in packet['subjects'][-1]['context']
    assert rows[82]['candidate'] not in packet['subjects'][0]['context']
    rows[82]['candidate'] = binding('candidate-82-new')
    subjects[1]['binding'] = rows[82]['candidate']
    after = chapter_packets(tmp_path, subjects, rows, 'coordinator')
    assert after[81] != before[81] and after[82] != before[82]
    assert after[83] == before[83]


@pytest.mark.parametrize('declared', [{'unknown': [82]}, {'chapter-81': [84]}, {'chapter-81': [81]}])
def test_invalid_cross_chapter_context_is_refused(tmp_path, declared):
    from rcwh.workflow.release_packets import chapter_packets
    ref = _write_immutable(tmp_path, 'candidate.json', {'test': True})
    rows = {81: {'candidate': ref, 'review_context_chapters': declared}, 82: {'candidate': ref}}
    with pytest.raises(AssetError, match='cross-chapter review context'):
        chapter_packets(tmp_path, [{'id': 'chapter-81', 'scope': 'CANDIDATE', 'binding': ref}], rows, 'coordinator')


def test_current_source_assignments_include_bound_context_and_every_original_image():
    from rcwh.workflow.review_campaign import _load, MAX_IMAGES, MAX_IMAGE_BYTES
    plan = _load(ROOT, "data/agent_release/research-81-100-v2/review-campaign-v1.json")
    source_jobs = [j for j in plan["jobs"] if j["kind"] == "SOURCE"]
    assert source_jobs and all(len(j.get("inspect_images", [])) <= MAX_IMAGES for j in source_jobs)
    for job in source_jobs:
        assert job["reading_bytes"] <= plan["max_read_bytes"] and job.get("image_bytes", 0) <= MAX_IMAGE_BYTES
        packet = json.loads((ROOT / job["packet"]["path"]).read_bytes())
        for subject in (s for s in packet["subjects"] if s["id"] in job["subjects"]):
            assert subject["evidence"] in job["read_in_full"]
            evidence = json.loads((ROOT / subject["evidence"]["path"]).read_bytes())
            assert evidence["contexts"] and evidence["carrier"]["sha256"]
            assert all(image["binding"] in job.get("inspect_images", []) for image in evidence["images"])


def test_full_edition_has_no_failures_and_only_missing_reviews_pending():
    from rcwh.workflow.agent_release import AgentRelease
    report = AgentRelease(ROOT).evaluate("data/agent_release/research-81-100-v2/request.json")
    assert report["findings"] == [] and report["status"] in {"PENDING", "PASS"}
    assert all(not c["findings"] for c in report["chapters"])
    allowed = {"CANDIDATE_PEERS", "COORDINATOR_DECISION", "CHAPTER_SAFETY_POLICY", "CONTRACT_PEERS",
               "SOURCE_PEERS", "CORPUS_PEERS"}
    assert all(set(c["pending"]) <= allowed for c in report["chapters"])


@pytest.mark.parametrize('change', ['none', 'binding', 'context', 'coordinator'])
def test_shared_review_reuse_requires_identical_full_subject_and_coordinator(tmp_path, change):
    from copy import deepcopy
    from rcwh.workflow.release_packets import reuse_shared_review_inputs
    from rcwh.candidate_reviews import canonical_bytes, digest
    import shutil
    shutil.copytree(ROOT / 'schemas', tmp_path / 'schemas')
    def store(path, value):
        raw = value if isinstance(value, bytes) else canonical_bytes(value)
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return {'path': path, 'sha256': digest(raw)}
    source = {'id': 'src:test', 'text': 'old', 'text_sha256': digest(b'old')}
    subject = {'id': 'source:test', 'scope': 'SOURCE', 'source_ref': 'src:test',
               'binding': store('source.json', source), 'context': []}
    packet = {'schema_version': 1, 'packet_kind': 'AGENT_REVIEW_PACKET', 'id': 'old',
              'coordinator_session_id': 'coordinator', 'subjects': [subject],
              'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'}
    old_ref = {'packet': store('old.json', packet), 'subject_id': 'source:test'}
    previous = {'chapters': [{'chapter': 81, 'source_reviews': [old_ref]}]}
    store('request.json', previous)
    packet = deepcopy(packet)
    packet['id'] = 'new'
    if change == 'binding':
        packet['subjects'][0]['binding'] = store('new-source.json', {**source, 'text': 'new', 'text_sha256': digest(b'new')})
    if change == 'context':
        packet['subjects'][0]['context'] = [store('context.txt', b'new context')]
    if change == 'coordinator':
        packet['coordinator_session_id'] = 'another-coordinator'
    current_ref = {'packet': store('new.json', packet), 'subject_id': 'source:test'}
    current = {'chapters': [{'chapter': 81, 'source_reviews': [current_ref]}]}
    reused = reuse_shared_review_inputs(tmp_path, current, 'request.json')
    assert bool(reused) == (change == 'none')
    assert current['chapters'][0]['source_reviews'][0] == (old_ref if change == 'none' else current_ref)


@pytest.mark.parametrize('change', ['none', 'prose', 'span', 'context', 'coordinator', 'subject_id'])
def test_book_reuse_requires_complete_same_reading_despite_edition_paths(tmp_path, change):
    from copy import deepcopy
    import shutil
    from rcwh.workflow.release_packets import reuse_shared_review_inputs

    shutil.copytree(ROOT / 'schemas', tmp_path / 'schemas')
    store = lambda path, value: _write_immutable(tmp_path, path, value)
    old_subjects = [
        {'id': 'book-81-82', 'scope': 'BOOK', 'chapters': [81, 82],
         'binding': store('old/81-82.md', b'prose 81 and 82'), 'review_policy': 'ADVISORY'},
        {'id': 'book-82-83', 'scope': 'BOOK', 'chapters': [82, 83],
         'binding': store('old/82-83.md', b'prose 82 and 83'), 'review_policy': 'ADVISORY'}]
    packet = {'schema_version': 1, 'packet_kind': 'AGENT_REVIEW_PACKET', 'id': 'old-edition:book',
              'coordinator_session_id': 'coordinator', 'subjects': old_subjects,
              'authority_effect': 'NONE', 'usage': 'RESEARCH_ONLY'}
    old_ref = {'packet': store('old/packet.json', packet), 'subject_ids': [s['id'] for s in old_subjects]}
    retained_packet_bytes = (tmp_path / old_ref['packet']['path']).read_bytes()
    store('old/request.json', {'chapters': [], 'book_review': old_ref})
    current_packet = deepcopy(packet)
    current_packet['id'] = 'new-edition:book'
    for i, s in enumerate(current_packet['subjects']):
        s['binding'] = store(f'new/{i}.md', (tmp_path / old_subjects[i]['binding']['path']).read_bytes())
    if change == 'prose':
        current_packet['subjects'][1]['binding'] = store('new/changed.md', b'changed final chapter')
    elif change == 'span':
        current_packet['subjects'][1]['chapters'] = [82, 83, 84]
    elif change == 'context':
        current_packet['subjects'][1]['context'] = [store('new/extra.txt', b'new requirements')]
    elif change == 'coordinator':
        current_packet['coordinator_session_id'] = 'another coordinator'
    elif change == 'subject_id':
        current_packet['subjects'][1]['id'] = 'book-another-id'
    current_ref = {'packet': store('new/packet.json', current_packet),
                   'subject_ids': [s['id'] for s in current_packet['subjects']]}
    current = {'chapters': [], 'book_review': current_ref}
    reused = reuse_shared_review_inputs(tmp_path, current, 'old/request.json')
    assert len(reused) == (2 if change == 'none' else 0)
    assert current['book_review'] == (old_ref if change == 'none' else current_ref)
    # Reuse retains the actual old packet; it does not reattribute old opinions.
    assert (tmp_path / old_ref['packet']['path']).read_bytes() == retained_packet_bytes
    if change == 'none':
        (tmp_path / 'old/81-82.md').write_bytes(b'corrupt retained prose')
        with pytest.raises((ValueError, AssetError), match='stale bound file'):
            reuse_shared_review_inputs(tmp_path, {'chapters': [], 'book_review': current_ref}, 'old/request.json')
