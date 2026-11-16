"""Freeze or check offline human reading materials for the chapter-86 v2 corpus.

Review receipt is deliberately separate: issued materials never bind selection
contents, live audit verdicts, review counts, or entire asset catalog shards.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import socket

from rcwh.assets import AssetCatalog
from rcwh.candidate_reviews import bound_data, canonical_bytes, digest
from rcwh.corpus.audit import CorpusAudit
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import ExtractionRepository, validate
from rcwh.workflow.review_intake import DATASETS, selection_path

LANE = "corpus-full-v2"
OUTPUT = "data/writing/corpus-v2-review"


def materials(root: Path) -> dict[str, bytes]:
    catalog = AssetCatalog.from_repo(root)
    corpus = CorpusRepository(catalog)
    dataset = DATASETS[LANE]
    selected = json.loads((root / selection_path(LANE)).read_bytes())
    validate(root, selected, "corpus_audit_selection")
    if selected['dataset_ref'] != dataset:
        raise ValueError("Wrong selected dataset")
    protocol = bound_data(root, selected['protocol'])
    validate(root, protocol, 'corpus_audit_protocol')
    binding = corpus.registry()[dataset]
    if (protocol['dataset_ref'], protocol['manifest_sha256']) != (dataset, binding['manifest_sha256']):
        raise ValueError('Wrong protocol dataset or manifest')
    manifest, products = corpus.load(dataset, rebuild=False)
    segments = [json.loads(line) for line in products['segments.jsonl'].splitlines()[1:]]
    index = {s['segment_id']: i for i, s in enumerate(segments)}
    samples = protocol['samples']
    identities = [s['segment_id'] for s in samples]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate protocol sample')
    if any(s['segment_id'] not in index or segments[index[s['segment_id']]]['text_sha256'] != s['text_sha256'] for s in samples):
        raise ValueError('Stale protocol sample')
    covered = [segments[index[s]] for s in identities]
    if {s['chapter'] for s in covered if s['kind'] == 'MAIN_TEXT'} != set(manifest['build_config']['document']['chapters']):
        raise ValueError('Missing MAIN_TEXT chapter')
    if {s['kind'] for s in segments if s['text'].strip()} - {s['kind'] for s in covered}:
        raise ValueError('Missing text layer')

    def file_binding(path):
        return {'path': path, 'sha256': digest((root / path).read_bytes())}

    resolved_assets = {}
    def asset_binding(ref):
        if ref not in resolved_assets:
            asset = catalog.resolve(ref)
            resolved_assets[ref] = {'asset_ref': ref, 'path': asset.relative_path, 'sha256': asset.sha256}
        return resolved_assets[ref]

    extraction_refs = sorted({s['locator']['extraction_ref'] for s in covered})
    extractions = {}
    extraction_units = []
    for ref in extraction_refs:
        extraction, units = ExtractionRepository(catalog).load(ref, rebuild=False)
        extractions[ref] = units
        extraction_units.append(asset_binding(extraction['output']['asset_ref']))
    contexts = []
    pages = {}
    for sample in samples:
        i = index[sample['segment_id']]
        segment = segments[i]
        neighbors = [s for s in segments[max(0,i-1):i+2] if s['section_ref'] == segment['section_ref']]
        navigation = []
        for span in segment['locator']['spans']:
            ref = segment['locator']['extraction_ref']
            unit = extractions[ref][span['unit_ref']]
            page = int(span['unit_ref'].rsplit(':',1)[1])
            key = ref + '/' + span['unit_ref']
            pages[key] = unit
            navigation.append({'physical_page_one_based': page, 'pdf_page_index_zero_based': page-1,
                               'full_pdf': asset_binding(segment['asset_ref']), 'viewer_fragment': '#page='+str(page),
                               'unit_ref': span['unit_ref'], 'extraction_text_sha256': unit['text_sha256'],
                               'start': span['start'], 'end': span['end'],
                               'exact_span_text': unit['text'][span['start']:span['end']]})
        contexts.append({'sample': sample, 'segment': segment, 'adjacent_segments': neighbors,
                         'page_navigation': navigation})
    template = {'dataset_ref': dataset, 'manifest_sha256': protocol['manifest_sha256'],
                'protocol_sha256': selected['protocol']['sha256'],
                'reviewer': {'id': None, 'kind': 'INDEPENDENT_HUMAN', 'independent_of_builder': None},
                'main_boundaries_confirmed': None, 'unknown_witnesses_acknowledged': None,
                'unaligned_segments_acknowledged': None,
                'checks': [{'segment_id': s['segment_id'], 'layer_valid': None, 'locator_valid': None,
                            'context_valid': None, 'notes': None} for s in samples]}
    files = {'human-review-template.json': canonical_bytes(template),
             'sample-contexts.json': canonical_bytes({'samples': contexts}),
             'extraction-pages.json': canonical_bytes(pages)}
    stages = []
    # Small chapter groups make staged human reading practical. A final opinion
    # still must include every protocol sample; these are not partial submissions.
    for start in range(1,81,10):
        rows = [r for r in contexts if r['segment']['chapter'] in range(start,start+10)]
        name = f'stages/chapters-{start:02d}-{start+9:02d}.json'
        files[name] = canonical_bytes({'samples':rows})
        stages.append({'path':name,'sample_ids':[r['sample']['segment_id'] for r in rows]})
    rows = [r for r in contexts if r['segment']['chapter'] is None]
    for offset in range(0,len(rows),20):
        name = f'stages/appendix-{offset//20+1:02d}.json'
        part = rows[offset:offset+20]
        files[name] = canonical_bytes({'samples':part})
        stages.append({'path':name,'sample_ids':[r['sample']['segment_id'] for r in part]})
    config = manifest['build_config']
    plan = {'schema_version':1,'scope':'CORPUS_V2_HUMAN_READING_MATERIALS','dataset_ref':dataset,
            'protocol': selected['protocol'], 'manifest':asset_binding(binding['manifest_ref']),
            'build_config':file_binding(config['path']),
            'build_inputs':file_binding(config['document']['inputs']['path']),
            'dependencies':[asset_binding(d['asset_ref']) for d in manifest['dependencies']],
            'products':{name:asset_binding(record['asset_ref']) for name,record in sorted(manifest['products'].items())},
            'extraction_units':extraction_units,'sample_count':len(samples),
            'samples_by_layer':dict(sorted(Counter(s['kind'] for s in covered).items())),
            'minimum_reviewers':protocol['minimum_reviewers'],'stages':stages,
            'materials':[{ 'path':name,'sha256':digest(raw)} for name,raw in sorted(files.items())],
            'submission_policy':'Complete final submission required; preserve false findings and notes. Stages are reading aids only.',
            'page_convention':'Physical PDF pages are one based; PDF API indexes are zero based. Printed page labels may differ.',
            'authority_effect':'NONE','automatic_literary_pass':False}
    files['reading-plan.json'] = canonical_bytes(plan)
    return files


def prepare(root: Path, output: Path, *, check: bool = False) -> dict:
    files = materials(root)
    if check:
        mismatches = [name for name,raw in files.items() if not (output/name).is_file() or (output/name).read_bytes()!=raw]
        if mismatches:
            raise ValueError('Reading materials differ: '+', '.join(mismatches))
    else:
        # Never silently overwrite issued review materials or staged reader work.
        existing = [name for name in files if (output/name).exists()]
        if existing:
            raise FileExistsError('Use --check for issued materials: '+', '.join(existing))
        for name,raw in files.items():
            path=output/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
    return {'status':'PASS','scope':'READING_MATERIAL_REPRODUCTION','file_count':len(files),'authority_effect':'NONE'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--live-audit',action='store_true',help='Print current audit separately; never freeze it in reading materials')
    args=parser.parse_args(); root=args.root.resolve()
    def denied(*args,**kwargs): raise RuntimeError('Network forbidden during review preparation')
    socket.create_connection=socket.getaddrinfo=socket.socket.connect=socket.socket.connect_ex=denied
    result=prepare(root,args.output or root/OUTPUT,check=args.check)
    if args.live_audit:
        result['live_audit']=CorpusAudit(AssetCatalog.from_repo(root)).summary(DATASETS[LANE],rebuild=False)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
