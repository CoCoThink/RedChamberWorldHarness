"""Corpus v2 handouts do not manufacture independent human evidence."""
import json
import os
import socket
from pathlib import Path
import subprocess
import sys

import pytest

from rcwh.candidate_reviews import canonical_bytes, digest
from rcwh.workflow import review_intake as intake
from test_source_extraction import extraction_repo  # noqa: F401
from test_corpus_dataset import corpus_repo, DATASET  # noqa: F401
from test_corpus_audit import audit_repo  # noqa: F401

import rcwh.workflow.corpus_review_preparation as prep

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def prepared():
    original_connect, original_lookup = socket.socket.connect, socket.getaddrinfo
    def denied(*args, **kwargs):
        raise AssertionError('Review preparation must be offline')
    socket.socket.connect = socket.getaddrinfo = denied
    try:
        return prep.materials(ROOT)
    finally:
        socket.socket.connect, socket.getaddrinfo = original_connect, original_lookup


def test_frozen_v2_materials_cover_chapters_layers_known_header_failures(prepared):
    plan=json.loads(prepared['reading-plan.json'])
    contexts=json.loads(prepared['sample-contexts.json'])['samples']
    samples={r['sample']['segment_id'] for r in contexts}
    assert plan['dataset_ref']=='corpus:front80:v2-candidate'
    assert plan['manifest']['sha256']=='eb4aebb9e38712a988bdead263c12c9c3df00a6f936fb17db755c436e4d66886'
    assert {r['segment']['chapter'] for r in contexts if r['segment']['kind']=='MAIN_TEXT'}==set(range(1,81))
    assert set(plan['samples_by_layer'])=={'MAIN_TEXT','EDITORIAL','ZHIPI','APPENDIX','VARIANT'}
    assert len(samples)==plan['sample_count']==146
    assert not {'selection','review_count','status','verdict','asset_catalog'} & plan.keys()
    assert set(s for stage in plan['stages'] for s in stage['sample_ids'])==samples
    assert sum(len(stage['sample_ids']) for stage in plan['stages'])==len(samples)
    for reader in ('reader1','reader2'):
        opinion=json.loads((ROOT/f'artifacts/agent_research/phase6/corpus/{reader}-opinion-v1.json').read_bytes())
        failures={c['sample_id'] for r in opinion['results'] for c in r.get('sample_checks',[]) if c['verdict']=='FAIL'}
        assert failures <= samples
        assert opinion['independent_human_admission'] is False
    for row in contexts:
        for page in row['page_navigation']:
            assert page['pdf_page_index_zero_based']+1==page['physical_page_one_based']
            assert page['full_pdf']['path'].endswith('original.pdf')
    for name,raw in prepared.items():
        assert (ROOT/prep.OUTPUT/name).read_bytes()==raw


def test_blank_v2_template_fails_before_any_intake(prepared,tmp_path):
    file=tmp_path/'blank.json';file.write_bytes(prepared['human-review-template.json'])
    with pytest.raises(ValueError,match='未填写字段'):
        intake.prepare_registration(ROOT,prep.LANE,file,origin='test:blank-v2')


def test_negative_receipt_changes_live_audit_but_not_issued_materials(audit_repo,monkeypatch,tmp_path):
    root,_,_,_=audit_repo
    monkeypatch.setitem(intake.DATASETS,prep.LANE,DATASET)
    before=prep.materials(root)
    opinion=json.loads(before['human-review-template.json'])
    opinion['reviewer']={'id':'synthetic:v2-negative','kind':'INDEPENDENT_HUMAN','independent_of_builder':True}
    for key in ('main_boundaries_confirmed','unknown_witnesses_acknowledged','unaligned_segments_acknowledged'):
        opinion[key]=True
    for row in opinion['checks']:
        row.update(layer_valid=True,locator_valid=True,context_valid=True,notes='Synthetic test only: inspected fixture context')
    opinion['checks'][0]['context_valid']=False
    opinion['checks'][0]['notes']='Synthetic negative finding retained verbatim'
    file=tmp_path/'negative.json';file.write_bytes(canonical_bytes(opinion))
    report=intake.register(root,prep.LANE,file,origin='test:synthetic-negative-only')
    assert report['status']=='FAIL' and report['registered']
    assert report['lane_report']['findings'][0]['notes']==opinion['checks'][0]['notes']
    assert prep.materials(root)==before
    from rcwh.assets import AssetCatalog
    raw=AssetCatalog.from_repo(root).resolve(report['raw_review']['asset_ref'])
    assert raw.path.read_bytes()==file.read_bytes()


def test_check_and_write_preflight_whole_set(tmp_path,monkeypatch):
    monkeypatch.setattr(prep,'materials',lambda root:{'a.json':b'a','b.json':b'b'})
    (tmp_path/'b.json').write_bytes(b'b')
    with pytest.raises(FileExistsError): prep.prepare(tmp_path,tmp_path)
    assert not (tmp_path/'a.json').exists()
    with pytest.raises(ValueError): prep.prepare(tmp_path,tmp_path,check=True)
    (tmp_path/'a.json').write_bytes(b'a')
    assert prep.prepare(tmp_path,tmp_path,check=True)['status']=='PASS'


def test_cli_accepts_v2_lane_without_changing_v1_mapping():
    import argparse
    from rcwh.application.reviews import add_commands
    parser=argparse.ArgumentParser()
    add_commands(parser.add_subparsers(dest='command'))
    args=parser.parse_args(['reviews','register','corpus-full-v2','opinion.json','--origin','test:receipt'])
    assert args.lane=='corpus-full-v2'
    assert intake.DATASETS['corpus-full']=='corpus:front80:v1-candidate'
    assert intake.selection_path('corpus-full')!=intake.selection_path('corpus-full-v2')


def test_preparation_cli_checks_issued_materials_and_reports_live_audit(prepared):
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT / 'src')
    result = subprocess.run(
        [sys.executable, '-X', 'utf8', str(ROOT / 'tools/prepare_corpus_v2_review.py'),
         '--root', str(ROOT), '--output', str(ROOT / prep.OUTPUT), '--check', '--live-audit'],
        capture_output=True, check=True, env=environment,
    )
    report = json.loads(result.stdout)
    from rcwh.assets import AssetCatalog
    from rcwh.corpus.audit import CorpusAudit

    assert report.pop('live_audit') == CorpusAudit(AssetCatalog.from_repo(ROOT)).summary(
        intake.DATASETS[prep.LANE], rebuild=False)
    assert report == prep.prepare(ROOT, ROOT / prep.OUTPUT, check=True)
    assert report['file_count'] == len(prepared)
