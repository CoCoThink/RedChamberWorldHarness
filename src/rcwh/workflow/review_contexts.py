"""Explicit, selected-candidate dependencies for cross-chapter review subjects."""
from ..assets import AssetError


def contexts(row: dict, subjects: list[dict], rows: dict[int, dict]) -> dict[str, list[dict]]:
    declared = row.get('review_context_chapters', {})
    known = {subject['id'] for subject in subjects}
    if not isinstance(declared, dict) or not declared.keys() <= known:
        raise AssetError('cross-chapter review context names an unknown subject')
    base = [row[k] for k in ('candidate', 'writing_package', 'policy') if k in row]
    result = {}
    for subject in subjects:
        chapters = declared.get(subject['id'], [])
        if (not isinstance(chapters, list) or (subject['id'] in declared and not chapters)
                or any(type(ch) is not int or ch == row['chapter'] or ch not in rows
                       or 'candidate' not in rows[ch] for ch in chapters)
                or len(set(chapters)) != len(chapters)):
            raise AssetError('cross-chapter review context must name distinct other selected candidates')
        refs = base + [rows[ch]['candidate'] for ch in chapters]
        result[subject['id']] = list({ref['path']: ref for ref in refs}.values())
    return result
