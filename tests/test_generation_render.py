from copy import deepcopy
from pathlib import Path
import shutil

from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import binding
from rcwh.generation.render import PromptRenderer
from test_literary_inputs import writing_repo
from test_corpus_dataset import corpus_repo
from test_source_extraction import extraction_repo

ROOT = Path(__file__).resolve().parents[1]


def test_renderer_equal_task_information_source_text_and_single_package_load(tmp_path, monkeypatch):
    root = tmp_path
    shutil.copytree(ROOT / 'data/writing/prompts', root / 'data/writing/prompts')
    def write(path, value):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(canonical_bytes(value))
    write('package.json', {'chapter': 89})
    write('examples.json', {})
    write('manifest.json', {})
    write('data/world/version.json', {'id': 'world'})
    write('data/project/plan.json', {'id': 'plan'})
    write('data/scenes/test.json', {'id': 'scene', 'chapter': 89, 'participants': []})
    package = {'chapter': 89, 'exemplar_set': binding(root, 'examples.json'),
               'sources': [{'source_ref': 'source'}], 'world': [binding(root, 'data/world/version.json')],
               'plan': [binding(root, 'data/project/plan.json')]}
    report = {'status': 'PASS', 'findings': [], 'scope': 'RESEARCH', 'production_blockers': ['AUDIT_PENDING'],
              'package': package, 'sources': [{'source_id': 'source', 'status': 'PASS'}],
              'exemplars': {'spec': {'manifest_ref': 'asset:sha256:' + 'a'*64, 'dataset_ref': 'dataset'},
                            'segments': [{'text': '例文', 'text_sha256': 'a'*64}]}}
    calls = []
    class Inputs:
        def __init__(self, catalog): pass
        def package(self, path):
            calls.append(path)
            return deepcopy(report)
    class State:
        def __init__(self, *args): pass
        def snapshot(self): return {'values': {'key': 'value'}}
    monkeypatch.setattr('rcwh.generation.render.AssetCatalog.from_repo', lambda root: type('Catalog', (), {
        'resolve': lambda self, ref: type('Asset', (), {'path': root / 'manifest.json'})()})())
    monkeypatch.setattr('rcwh.generation.render.LiteraryInputs', Inputs)
    monkeypatch.setattr('rcwh.generation.render.SceneStateAdapter', State)
    monkeypatch.setattr('rcwh.graph.ProvenanceGraph.from_repo', lambda root: type('Graph', (), {'sources': {'source': {'id': 'source', 'text': '史料原文'}}})())
    renderer = PromptRenderer(root)
    a = renderer.draft('package.json', 89, route='direct')
    b = renderer.draft('package.json', 89, route='harness')
    assert calls == ['package.json']
    assert a['task']['sources'][0]['record']['text'] == '史料原文'
    left, right = deepcopy(a['task']), deepcopy(b['task'])
    left.pop('guidance'); right.pop('guidance')
    assert left == right
    assert renderer.draft('package.json', 89, route='direct')['prompt_sha256'] == a['prompt_sha256']


def test_renderer_accepts_bound_imported_skeleton_without_fake_state(tmp_path, monkeypatch):
    root = tmp_path
    shutil.copytree(ROOT / 'data/writing/prompts', root / 'data/writing/prompts')
    for path, value in {'pkg.json': {}, 'examples.json': {}, 'manifest.json': {},
                        'data/planning/chapters/ch85.json': {'chapter': 85, 'scenes': [{'ref': 'data/planning/scenes/s.json'}]},
                        'data/planning/scenes/s.json': {'chapter': 85, 'id': 's', 'kind': 'SCENE_SKELETON'}}.items():
        file = root / path; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(canonical_bytes(value))
    report = {'status': 'PASS', 'findings': [], 'scope': 'RESEARCH', 'production_blockers': [],
              'package': {'chapter': 85, 'exemplar_set': binding(root, 'examples.json'), 'world': [], 'plan': [], 'sources': []},
              'sources': [], 'exemplars': {'spec': {'manifest_ref': 'asset:sha256:' + 'a'*64, 'dataset_ref': 'dataset'}, 'segments': []}}
    monkeypatch.setattr('rcwh.generation.render.AssetCatalog.from_repo', lambda root: type('Catalog', (), {
        'resolve': lambda self, ref: type('Asset', (), {'path': root / 'manifest.json'})()})())
    monkeypatch.setattr('rcwh.generation.render.LiteraryInputs', lambda catalog: type('Inputs', (), {'package': lambda self, path: report})())
    monkeypatch.setattr('rcwh.graph.ProvenanceGraph.from_repo', lambda root: type('Graph', (), {'sources': {}})())
    rendered = PromptRenderer(root).draft('pkg.json', 85)
    assert rendered['task']['scenes'][0]['entry'] is None
    assert rendered['task']['scenes'][0]['unresolved'] == 'DRAFT_SCENE_NO_EXECUTABLE_STATE_CONTRACT'


def test_real_corpus_manifest_asset_is_bound_as_repository_file(writing_repo, monkeypatch):
    from rcwh.assets import AssetCatalog
    root, _, package_path, examples, _ = writing_repo
    shutil.copytree(ROOT / 'data/writing/prompts', root / 'data/writing/prompts')
    scenes = root / 'data/scenes'
    scenes.mkdir(parents=True)
    (scenes / 'test.json').write_bytes(canonical_bytes({'id': 'test', 'chapter': 89, 'participants': []}))
    monkeypatch.setattr('rcwh.generation.render.SceneStateAdapter', lambda *args: type('State', (), {'snapshot': lambda self: {'values': {}}})())
    preview = PromptRenderer(root).draft(package_path, 89)
    assert examples['manifest_ref'].startswith('asset:sha256:')
    actual = AssetCatalog.from_repo(root).resolve(examples['manifest_ref']).path.relative_to(root).as_posix()
    assert binding(root, actual) in preview['inputs']
    assert all(not ref['path'].startswith('asset:') for ref in preview['inputs'])
