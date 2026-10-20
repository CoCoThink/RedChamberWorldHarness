"""Every seam is read inside a bounded segment of exact current chapter bytes."""
from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from rcwh.workflow.book_review import partition, subjects
from rcwh.workflow.release_packets import _packet, _write_immutable

ROOT = Path(__file__).resolve().parents[1]


def test_overlap_partitions_every_seam_without_truncating_a_chapter():
    chapters = list(range(81, 101))
    prose = {ch: "章" * 10 for ch in chapters}
    groups = partition(chapters, prose, 210)
    assert groups == [list(range(81, 88)), list(range(87, 94)), list(range(93, 100)), [99, 100]]
    seams = {pair for span in groups for pair in zip(span, span[1:])}
    assert seams == set(zip(chapters, chapters[1:]))
    assert all(len("".join(prose[ch] for ch in span).encode()) <= 210 for span in groups)


def test_an_indivisible_seam_over_budget_is_rejected():
    with pytest.raises(ValueError, match="seam cannot fit"):
        partition([81, 82], {81: "甲" * 10, 82: "乙" * 10}, 59)


@pytest.fixture
def segments(tmp_path):
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    chapters = [81, 82, 83]
    prose = {ch: f"# 第{ch}回 测试\n\n这是第{ch}回的正文。\n\n" for ch in chapters}
    rows = []
    for span in ([81, 82], [82, 83]):
        binding = _write_immutable(tmp_path, f"segment-{span[0]}.md", "".join(prose[ch] for ch in span).encode())
        rows.append({"id": str(span[0]), "scope": "BOOK", "chapters": span,
                     "binding": binding, "review_policy": "ADVISORY"})
    ref = {"packet": _write_immutable(tmp_path, "packet.json", _packet("test", "book", "coordinator", rows)),
           "subject_ids": [row["id"] for row in rows]}
    return tmp_path, ref, ("前言\n" + "".join(prose.values())).encode(), chapters, rows


def test_current_segments_bind_exact_prose_and_all_seams(segments):
    root, ref, book, chapters, rows = segments
    assert subjects(root, ref, book=book, chapters=chapters) == rows


@pytest.mark.parametrize("change", ["gap", "extra-overlap", "omitted-subject", "stale-prose"])
def test_incomplete_or_stale_continuity_coverage_is_invalid(segments, change):
    root, ref, book, chapters, rows = segments
    rows = deepcopy(rows)
    if change == "gap":
        rows[1]["chapters"] = [83]
    elif change == "extra-overlap":
        rows[1]["chapters"] = [81, 82, 83]
    elif change == "omitted-subject":
        ref["subject_ids"].pop()
    else:
        rows[1]["binding"] = _write_immutable(root, "stale.md", b"wrong current prose")
    ref["packet"] = _write_immutable(root, "changed-packet.json", _packet("test", "book", "coordinator", rows))
    with pytest.raises(ValueError):
        subjects(root, ref, book=book, chapters=chapters)
