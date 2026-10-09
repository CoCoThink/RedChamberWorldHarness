from __future__ import annotations

from pathlib import Path, PurePosixPath


class AssetError(ValueError):
    """A declared asset cannot be resolved to the expected repository bytes."""


def repository_path(root: Path, relative: str) -> Path:
    """Reject external paths and links, including links that resolve internally."""
    path = PurePosixPath(relative)
    if (
        not relative or path.is_absolute() or ".." in path.parts
        or "\\" in relative or ":" in relative or str(path) != relative
    ):
        raise AssetError(f"unsafe repository path: {relative}")
    root = root.resolve()
    candidate = root.joinpath(*path.parts)
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise AssetError(f"symlink is not an asset: {relative}")
    if not candidate.resolve().is_relative_to(root):
        raise AssetError(f"asset leaves repository: {relative}")
    return candidate
