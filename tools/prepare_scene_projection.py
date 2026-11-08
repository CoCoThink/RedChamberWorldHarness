"""Prepare a new research package with explicit scene inputs; never generate prose."""
import argparse
import json
import tempfile
from pathlib import Path

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.records import append_bytes, binding
from rcwh.generation.render import PromptRenderer
from rcwh.generation.scene_projection import create_projection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    for name in ('base-package', 'output-package', 'id', 'query'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(); root = args.root.resolve()
    package = json.loads(repository_path(root, args.base_package).read_bytes())
    query = json.loads(repository_path(root, args.query).read_bytes())
    if package['id'] == args.id or args.base_package == args.output_package or package['chapter'] != query['chapter']:
        raise ValueError('scene projection requires a new identity/path and matching chapter')
    result = create_projection(root, query)
    package.update(id=args.id, world=[result['projection']], purpose=package['purpose'] +
                   ' SCENE_INPUT_PROJECTION v1 mechanism pilot; scope completeness unreviewed; no new prose.')
    target = repository_path(root, args.output_package)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.json') as stage:
        stage.write(canonical_bytes(package)); stage.flush()
        PromptRenderer(root).draft(Path(stage.name).relative_to(root).as_posix(), package['chapter'])
        append_bytes(root, args.output_package, canonical_bytes(package))
    print(json.dumps({**result, 'package': binding(root, args.output_package), 'status': 'PASS',
                      'scope': 'MATERIAL_INTEGRITY_ONLY_NOT_REVIEWED_WRITING', 'authority_effect': 'NONE'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
