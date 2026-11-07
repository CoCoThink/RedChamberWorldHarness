"""Create an explicit research package using fresh versioned world material."""
import argparse
import json
import tempfile
from pathlib import Path
from rcwh.candidate_reviews import canonical_bytes
from rcwh.generation.world_projection import create_projection
from rcwh.generation.records import append_bytes, binding
from rcwh.assets.paths import repository_path
from rcwh.assets import AssetCatalog
from rcwh.literary_inputs import LiteraryInputs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--base-package',required=True)
    p.add_argument('--output-package',required=True)
    p.add_argument('--id',required=True)
    p.add_argument('--characters',nargs='+',required=True)
    args=p.parse_args();r=args.root.resolve()
    package=json.loads(repository_path(r,args.base_package).read_bytes())
    if package['id']==args.id or args.base_package==args.output_package:
        raise ValueError('projection requires a new package identity and path')
    result=create_projection(r,package['chapter'],args.characters)
    package.update(id=args.id,world=[result['projection']],purpose=package['purpose']+' WORLD_PROJECTION v1 mechanism pilot; scope completeness and literary qualification remain unreviewed; no new prose generated.')
    # The new package explicitly replaces the base world's bindings. It does not
    # claim that the original package remains current after world edits.
    target=repository_path(r,args.output_package)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,suffix='.json') as stage:
        stage.write(canonical_bytes(package));stage.flush()
        report=LiteraryInputs(AssetCatalog.from_repo(r)).package(Path(stage.name).relative_to(r).as_posix())
        if report['status']!='PASS':
            raise ValueError('projection package failed validation')
        append_bytes(r,args.output_package,canonical_bytes(package))
    print(json.dumps({**result,'package':binding(r,args.output_package),'status':'PASS',
        'scope':'MATERIAL_INTEGRITY_ONLY_NOT_REVIEWED_WRITING','authority_effect':'NONE'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
