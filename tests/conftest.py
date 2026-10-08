import hashlib
from pathlib import Path

import pytest

from rcwh.assets.catalog import repository_path
from rcwh.workflow import ProjectState


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def production_unchanged():
    """Experiments must preserve the selected state, whatever its current stage."""
    project = ProjectState.from_repo(ROOT)
    release = project.release()
    paths = [ROOT / "data/project/current.json"]
    paths.extend(repository_path(ROOT, path) for path in project.data["owners"].values())
    paths.append(release.catalog.resolve(release.data["text_asset_ref"]).path)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    yield
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths} == before
