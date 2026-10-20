"""Overlapping, byte-bounded continuity readings of the exact current prose."""
from __future__ import annotations

from pathlib import Path

from ..assets import AssetError
from ..generation.records import bound_bytes
from .agent_panel import verify_packet

DEFAULT_LIMIT = 197 * 1024


def partition(chapters: list[int], prose: dict[int, str], limit: int) -> list[list[int]]:
    """Greedily fill segments; repeat one whole chapter at every boundary.

    A seam is indivisible: fail if even its two chapters cannot fit. Byte counts
    are measured UTF-8, not a claim about the eventual reader's tokenizer.
    """
    if limit < 1 or not chapters:
        raise AssetError("positive continuity reading budget and chapters required")
    groups, start = [], 0
    while start < len(chapters):
        end, size = start, 0
        while end < len(chapters) and size + len(prose[chapters[end]].encode()) <= limit:
            size += len(prose[chapters[end]].encode())
            end += 1
        if end == start or (end == start + 1 and len(chapters) > 1):
            raise AssetError(f"continuity seam cannot fit reading budget near chapter {chapters[start]}")
        groups.append(chapters[start:end])
        if end == len(chapters):
            break
        start = end - 1
    return groups


def subjects(root: Path, ref: dict, *, book: bytes | None = None,
             chapters: list[int] | None = None) -> list[dict]:
    """Verify complete seam coverage and exact segment bytes, with legacy support."""
    packet = verify_packet(root, ref["packet"])
    rows = packet["subjects"]
    if any(s["scope"] != "BOOK" or s["review_policy"] != "ADVISORY" for s in rows):
        raise AssetError("continuity packet must contain only advisory BOOK subjects")
    if "subject_id" in ref:  # Archived single-book packets remain verifiable.
        if len(rows) != 1 or rows[0]["id"] != ref["subject_id"]:
            raise AssetError("invalid legacy book review subject")
        if book is not None and bound_bytes(root, rows[0]["binding"]) != book:
            raise AssetError("book review does not bind the assembled current edition")
        return rows
    if [s["id"] for s in rows] != ref["subject_ids"]:
        raise AssetError("continuity segment subject coverage mismatch")
    covered = []
    for index, row in enumerate(rows):
        span = row.get("chapters", [])
        if not span or (len(span) < 2 and (len(rows) > 1 or chapters and len(chapters) > 1)):
            raise AssetError("continuity segment must contain its complete adjacent chapters")
        if index and covered[-1] != span[0]:
            raise AssetError("continuity segments must overlap by exactly one chapter")
        covered.extend(span if index == 0 else span[1:])
    if len(set(covered)) != len(covered) or covered != sorted(covered) or (chapters is not None and covered != chapters):
        raise AssetError("continuity segments have missing, repeated or unordered chapters/seams")
    if book is not None:
        from .agent_release import _split
        _, prose = _split(book.decode(), tuple(covered))
        for row in rows:
            expected = "".join(prose[ch] for ch in row["chapters"]).encode()
            if bound_bytes(root, row["binding"]) != expected:
                raise AssetError("continuity segment differs from the assembled current edition")
    return rows
