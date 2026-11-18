"""Prepare/check current source-audit reading materials offline, without opinions."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from rcwh.assets.paths import repository_path
from rcwh.candidate_reviews import bound_data, canonical_bytes, digest
from rcwh.corpus.locators import SourceLocatorVerifier
from rcwh.provenance import ProvenanceRepository
from rcwh.provenance.audit import SourceAudit
from rcwh.workflow.source_reading import prepare, verify

BASE = 'data/writing/source-review-next'
CHECKS = ('carrier_edition_confirmed', 'excerpt_valid', 'witness_tier_unchanged', 'claim_impact_reviewed')


def documents(root: Path) -> dict[str, bytes]:
    root = root.resolve()
    repository = ProvenanceRepository.from_repo(root)
    audit = SourceAudit(repository)
    audit.summary()  # Reject stale graph, scope, sources or selected reviews.
    selection_path = audit.selection_path
    selected = json.loads((root / selection_path).read_bytes())
    protocol = bound_data(root, selected['protocol'])
    tracked_result = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True, check=True)
    tracked = set(tracked_result.stdout.decode().split('\0'))
    inputs = {}
    docs = {}

    def bind(path):
        path = str(path)
        raw = repository_path(root, path).read_bytes()
        if path not in tracked:
            raise ValueError('untracked review input: ' + path)
        ref = {'path': path, 'sha256': digest(raw)}
        inputs[path] = ref
        return ref

    def write(_root, path, value):
        raw = value if isinstance(value, bytes) else canonical_bytes(value)
        if path in docs and docs[path] != raw:
            raise ValueError('conflicting generated path: ' + path)
        docs[path] = raw
        return {'path': path, 'sha256': digest(raw)}

    # Bind original YAML, not just JSON projections; preserve the graph input history.
    for folder in ('sources', 'claims', 'decisions', 'implementations', 'axes'):
        for path in sorted((root / f'data/provenance/{folder}').glob('*.yaml')):
            bind(path.relative_to(root).as_posix())
    # Selection reviews and live verdicts evolve as readers submit opinions.
    # Freeze the selected protocol, not the mutable intake ledger.
    bind(selected['protocol']['path'])
    bind('requirements/extraction.lock.json')
    for schema in ('source', 'source_audit_protocol', 'source_audit_selection', 'source_audit_review',
                   'locator_v2', 'extraction_manifest', 'extraction_unit', 'source_capture',
                   'source_excerpt_review'):
        bind(f'schemas/{schema}.schema.json')
    seen = set()

    def asset_inputs(value):
        if isinstance(value, dict):
            for item in value.values():
                asset_inputs(item)
        elif isinstance(value, list):
            for item in value:
                asset_inputs(item)
        elif isinstance(value, str) and value.startswith('asset:') and value in repository.catalog.assets and value not in seen:
            seen.add(value)
            asset = repository.catalog.resolve(value)
            bind(asset.relative_path)
            record = repository.catalog.assets[value]
            # Freeze only relevant metadata below; shared catalog shards/layout
            # also change when unrelated assets or reader submissions arrive.
            asset_inputs(record.get('derived_from', []))
            if record['media_type'] == 'application/json':
                asset_inputs(json.loads(asset.path.read_bytes()))

    def read(ref):
        raw = docs.get(ref['path'])
        if raw is None:
            bind(ref['path'])
            raw = repository_path(root, ref['path']).read_bytes()
        if digest(raw) != ref['sha256']:
            raise ValueError('reading input digest mismatch: ' + ref['path'])
        return raw

    verifier = SourceLocatorVerifier(repository.catalog)
    cache = {}
    subjects = []
    for row in protocol['sources']:
        source = repository.graph.sources[row['source_ref']]
        report = repository.source_report(source, locators=True, verifier=verifier)
        if report['status'] != 'PASS':
            raise ValueError('source cannot prepare verified reading evidence: ' + source['id'] + ': ' + str(report['findings']))
        trace = repository.graph.trace(source['id'])
        asset_inputs(trace)
        context = write(root, f'{BASE}/subjects/{digest(source["id"].encode())}.json',
                        {'kind': 'SOURCE_AUDIT_SUBJECT', **row, 'trace': trace,
                         'boundary': 'Current graph impact and prior corrections are inputs to examine, not independent approval.'})
        evidence = prepare(repository.catalog, source, BASE, write, cache)
        material = verify(source, evidence, read)
        for key in ('carrier', 'extraction', 'output'):
            read(material[key])
        subjects.append({**row, 'context': context, 'reading_evidence': evidence,
                         'claim_ids': sorted(c['id'] for c in trace['claims']),
                         'image_count': len(material['images'])})
    template = {'protocol_sha256': selected['protocol']['sha256'],
                'reviewer': {'id': '', 'kind': 'INDEPENDENT_HUMAN', 'independent_of_corrections': None},
                'results': [{'source_ref': row['source_ref'], **{key: None for key in CHECKS}, 'notes': ''}
                            for row in protocol['sources']]}
    template_ref = write(root, f'{BASE}/human-review-template.json', template)
    write(root, f'{BASE}/plan.json', {
        'schema_version': 1, 'kind': 'SOURCE_AUDIT_READING_PLAN',
        'protocol': selected['protocol'],
        'graph_sha256': protocol['graph_sha256'], 'subjects': subjects,
        'asset_records': [repository.catalog.assets[ref] for ref in sorted(seen)],
        'template': template_ref, 'tracked_inputs': [inputs[p] for p in sorted(inputs)],
        'preparation_status': 'PREPARED', 'authority_effect': 'NONE',
        'production_admission': 'NOT_GRANTED',
        'instructions': [
            'Read all subjects: full current Source, bibliography, witness/tier, excerpt and context, carrier and available original images, prior correction and current graph impact.',
            'Follow tracked input paths within this repository; this plan is not a standalone distribution archive. Original carriers may be opened directly.',
            'Do not infer carrier edition or historical authenticity from exact text extraction. Cao agent transcription and the older carrier remain separate records.',
            'An independent human must fill identity, attest independence, and honestly fill each boolean and notes; false conclusions are valid. Nulls and blank strings deliberately prevent template registration.',
            'Keep the filled original JSON bytes and register with rcwh reviews register source opinion.json --origin ACTUAL_ORIGIN. Never turn a scaffold or agent reading into a human opinion.',
            'Review decisions remain PENDING without genuine selected submissions; preparation confers no authority or adoption.'
        ]})
    return docs


def run(root: Path, check: bool = False) -> dict:
    docs = documents(root)
    # Preflight the whole set before any writes; never replace an existing artifact.
    for path, raw in docs.items():
        dest = repository_path(root, path)
        if dest.exists() and dest.read_bytes() != raw:
            raise ValueError('refusing to replace changed reading material: ' + path)
        if check and not dest.is_file():
            raise ValueError('missing reading material: ' + path)
    if not check:
        for path, raw in docs.items():
            dest = repository_path(root, path)
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as handle:
                    handle.write(raw)
    plan = json.loads(docs[f'{BASE}/plan.json'])
    # Mutable selection and verdicts are command diagnostics, never frozen inputs.
    summary = SourceAudit(ProvenanceRepository.from_repo(root)).summary()
    return {'status': 'PASS', 'scope': 'DETERMINISTIC_PREPARATION_ONLY', 'files': len(docs),
            'source_count': len(plan['subjects']), 'review_status': summary['status'],
            'review_count': summary['review_count'], 'audit_summary': summary, 'production_admission': 'NOT_GRANTED',
            'authority_effect': 'NONE'}
