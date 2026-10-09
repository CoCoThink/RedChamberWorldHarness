from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from rcwh.assets import AssetCatalog, AssetError, CatalogStore
from rcwh.assets.ingest import AssetIntake
from rcwh.assets.transactions import digest
from rcwh.corpus.dataset import CorpusRepository
from rcwh.corpus.extraction import ExtractionRepository, canonical_bytes
from rcwh.corpus.inputs import CorpusInputs
from rcwh.corpus.locators import SourceLocatorVerifier
from rcwh.cli import main
from test_source_extraction import extraction_repo, write_source
from test_corpus_inputs import samples


ROOT = Path(__file__).resolve().parents[1]
BUILD = "data/corpus/builds/test.json"
INPUTS = "data/corpus/inputs/test.json"
DATASET = "corpus:front80:test:pilot:v1"


@pytest.fixture
def corpus_repo(extraction_repo):
    root = extraction_repo
    for schema in ("corpus_build", "corpus_segment", "corpus_inputs", "corpus_manifest", "corpus_dataset"):
        shutil.copyfile(ROOT / f"schemas/{schema}.schema.json", root / f"schemas/{schema}.schema.json")
    import pymupdf
    pdf = pymupdf.open(); pdf.new_page().insert_text((72, 72), "Edition and style legend")
    for chapter, body in (("一", "甲正文。"), ("二", "乙正文。")):
        page = pdf.new_page()
        page.insert_text((72, 72), f"第{chapter}回", fontname="china-s", fontsize=20)
        page.insert_text((72, 100), body, fontname="china-s", fontsize=14)
        page.insert_text((72, 125), "庚侧批注。", fontname="china-s", fontsize=10, color=(1,0,0))
        page.insert_text((72, 145), "①编者按。", fontname="china-s", fontsize=8)
        if chapter == "二": page.insert_text((72, 180), "附录：第二回 异文。", fontname="china-s", fontsize=10)
    raw_pdf = pdf.tobytes(); font = pdf[1].get_text("dict")["blocks"][1]["lines"][0]["spans"][0]["font"]; pdf.close()
    inputs = {"schema_version":1,"id":"corpus-inputs:test:layers:v1","expected_chapters":[1,2],"pilot_chapters":[1,2],"selection_reason":"Declared test inputs","inventory_report":None}
    for name, raw in (("pdf",raw_pdf),("epub",samples()[1])):
        file = root.parent / f"layers.{name}"; file.write_bytes(raw)
        receipt = AssetIntake(root).ingest(file, origin=f"test:{name}", kind="PRIMARY_TEXT_CONTAINER")
        manifest = ExtractionRepository(AssetCatalog.from_repo(root)).build(receipt["asset_ref"])
        inputs[name] = {"asset_ref":receipt["asset_ref"],"sha256":receipt["sha256"],"extraction_ref":manifest["manifest_ref"],"extraction_sha256":manifest["manifest_ref"].split(":")[-1],"use":"MAIN" if name=="pdf" else "COMPARISON","edition_evidence":["pdf:page:1"] if name=="pdf" else ["epub:OEBPS/version.xhtml"]}
    inputs["pdf"]["body_pages"]=[2,3]
    (root / INPUTS).parent.mkdir(parents=True); (root / INPUTS).write_bytes(canonical_bytes(inputs))
    catalog = AssetCatalog.from_repo(root)
    _, units = ExtractionRepository(catalog).load(inputs["pdf"]["extraction_ref"])
    source={"id":"src:test:corpus","type":"NOVEL_TEXT","title":"actual novel text","witness":{"label":"test"},"container":{"ref":inputs["pdf"]["asset_ref"],"sha256":inputs["pdf"]["sha256"]},"locator":{"legacy":"pending"},"text":"甲正文。","text_sha256":digest("甲正文。".encode()),"locator_verification":{"status":"UNVERIFIED","reason":"pending"}}
    located=SourceLocatorVerifier(catalog).locate(source,inputs["pdf"]["extraction_ref"]); source["locator"]=located["locator"]; write_source(root,source)
    inventory=CorpusInputs(catalog).inventory(INPUTS); report=root.parent/'layer-inventory.json'; report.write_bytes(canonical_bytes(inventory))
    receipt=AssetIntake(root).ingest(report,origin='test:inventory',kind='REVIEW_RECORD'); inputs['inventory_report']={'asset_ref':receipt['asset_ref'],'sha256':receipt['sha256']}; (root/INPUTS).write_bytes(canonical_bytes(inputs))
    config={"schema_version":1,"dataset_ref":DATASET,"scope":"PILOT","inputs":{"path":INPUTS,"sha256":digest((root/INPUTS).read_bytes())},"chapters":[1,2],"appendices":[],"variant_starts":[{"chapter":2,"unit_ref":"pdf:page:3","offset":units['pdf:page:3']['text'].index('附录：'),"expected_prefix":"附录：第二回"}],"layer_policy":{"evidence_units":["pdf:page:1"],"main_color":0,"annotation_colors":[16711680],"annotation_fonts":[font],"main_fonts":[font],"main_size_range":[13,17],"watermark_fonts":[],"witness_labels":{"庚":"庚辰本"}}}
    (root / BUILD).parent.mkdir(parents=True); (root / BUILD).write_bytes(canonical_bytes(config))
    return root, config, inputs


def rows(raw): return [json.loads(line) for line in raw.splitlines()][1:]


def test_layers_reconstruct_raw_input_and_default_query_excludes_annotations(corpus_repo):
    root, config, inputs = corpus_repo
    repository=CorpusRepository(AssetCatalog.from_repo(root)); manifest, products=repository.compile(BUILD)
    segments=rows(products['segments.jsonl']); assert {s['kind'] for s in segments} >= {'MAIN_TEXT','ZHIPI','EDITORIAL','VARIANT'}
    _,units=ExtractionRepository(repository.catalog).load(inputs['pdf']['extraction_ref'])
    for segment in segments:
        reconstructed=''.join(units[s['unit_ref']]['text'][s['start']:s['end']] for s in segment['locator']['spans'])
        assert segment['text']==reconstructed
        assert segment['text_sha256']==digest(reconstructed.encode())
    assert rows(products['annotations.jsonl'])[0]['witness']=='庚辰本'
    quality=json.loads(products['quality_report.json']); assert quality['source_links'][0]['segment_refs']
    assert quality['human_checks']==[] and quality['readiness']=='CANDIDATE_PENDING_HUMAN_AUDIT'
    built=repository.build(BUILD,'corpus/front80/test-pilot-v1')
    repository=CorpusRepository(AssetCatalog.from_repo(root)); assert repository.verify(DATASET)['status']=='PASS'
    query=repository.query(DATASET); assert query['segments'] and all('批注' not in s['text'] and '编者按' not in s['text'] and '异文' not in s['text'] for s in query['segments'])
    segment=query['segments'][0]; assert repository.show(DATASET,segment['segment_id'])['text']==segment['text']
    assert repository.query(DATASET,kind='ZHIPI',keyword='批注')['count']==2
    assert built['authority_effect']=='NONE'
    assert AssetCatalog.from_repo(root).validate()==[]


def test_two_independent_builds_without_cache_have_identical_products(corpus_repo, tmp_path):
    root,_,_=corpus_repo
    one=CorpusRepository(AssetCatalog.from_repo(root)).compile(BUILD)
    shutil.rmtree(root / '.rcwh-cache')
    two=CorpusRepository(AssetCatalog.from_repo(root)).compile(BUILD)
    assert one==two
    for name,raw in one[1].items():
        target=tmp_path/'first'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    for name,raw in two[1].items():
        target=tmp_path/'second'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    assert {p.relative_to(tmp_path/'first').as_posix():digest(p.read_bytes()) for p in (tmp_path/'first').rglob('*') if p.is_file()}=={p.relative_to(tmp_path/'second').as_posix():digest(p.read_bytes()) for p in (tmp_path/'second').rglob('*') if p.is_file()}


@pytest.mark.parametrize('change,error',[
    (lambda c:c['inputs'].update(sha256='0'*64),'STALE_CORPUS_INPUT_CONFIG'),
    (lambda c:c['variant_starts'][0].update(offset=0),'STALE_VARIANT_BOUNDARY'),
    (lambda c:c['variant_starts'][0].update(chapter=1),'VARIANT_OUTSIDE_DECLARED_CHAPTER'),
    (lambda c:c.update(scope='FRONT80_CANDIDATE'),'INCOMPLETE_FRONT80_SCOPE'),
    (lambda c:c.update(appendices=[{'section_ref':'bad','pages':[2,3]}]),'APPENDIX_OVERLAPS'),
])
def test_scope_bindings_fail_closed(corpus_repo,change,error):
    root,config,_=corpus_repo; change(config); (root/BUILD).write_bytes(canonical_bytes(config))
    with pytest.raises(AssetError,match=error): CorpusRepository(AssetCatalog.from_repo(root)).compile(BUILD)


def test_version_overwrite_and_missing_original_fail(corpus_repo):
    root,_,inputs=corpus_repo; repo=CorpusRepository(AssetCatalog.from_repo(root)); repo.build(BUILD,'corpus/front80/test-v1')
    with pytest.raises(AssetError,match='MUST_BE_NEW'): repo.build(BUILD,'corpus/front80/test-v1')
    with pytest.raises(AssetError,match='VERSION_ALREADY_EXISTS'): CorpusRepository(AssetCatalog.from_repo(root)).build(BUILD,'corpus/front80/other')
    catalog=AssetCatalog.from_repo(root); catalog.resolve(inputs['pdf']['asset_ref']).path.unlink()
    with pytest.raises(AssetError,match='missing file'): CorpusRepository(catalog).verify(DATASET)


def test_config_code_and_product_tampering_invalidate_dataset(corpus_repo,monkeypatch):
    root,config,_=corpus_repo; CorpusRepository(AssetCatalog.from_repo(root)).build(BUILD,'corpus/front80/test-v1')
    config['layer_policy']['main_color']=1; (root/BUILD).write_bytes(canonical_bytes(config))
    with pytest.raises(AssetError,match='STALE_CORPUS_BUILD_CONFIG'): CorpusRepository(AssetCatalog.from_repo(root)).verify(DATASET)
    config['layer_policy']['main_color']=0; (root/BUILD).write_bytes(canonical_bytes(config))
    monkeypatch.setattr('rcwh.corpus.dataset.code_digest',lambda *args:'0'*64)
    with pytest.raises(AssetError,match='STALE_CORPUS_BUILD'): CorpusRepository(AssetCatalog.from_repo(root)).verify(DATASET)
    monkeypatch.undo()
    catalog=AssetCatalog.from_repo(root); binding=CorpusRepository(catalog).registry()[DATASET]; manifest=json.loads(catalog.resolve(binding['manifest_ref']).path.read_bytes()); ref=manifest['products']['segments.jsonl']['asset_ref']; catalog.resolve(ref).path.write_bytes(b'forged')
    with pytest.raises(AssetError,match='byte mismatch'): CorpusRepository(catalog).verify(DATASET)


def test_unknown_layer_stays_visible_in_quality_queue(corpus_repo):
    root,config,_=corpus_repo; config['layer_policy']['main_fonts']=['UnknownFont']; (root/BUILD).write_bytes(canonical_bytes(config))
    _,products=CorpusRepository(AssetCatalog.from_repo(root)).compile(BUILD)
    quality=json.loads(products['quality_report.json']); assert quality['unclassified_nonempty']; assert quality['technical_findings']


def test_corpus_cli_dataset_commands(corpus_repo,monkeypatch,capsys):
    root,_,_=corpus_repo
    def run(*args):
        monkeypatch.setattr('sys.argv',['rcwh','--root',str(root),*args])
        with pytest.raises(SystemExit) as result: main()
        payload=json.loads(capsys.readouterr().out); return result.value.code,payload
    assert run('corpus','build','--config',BUILD,'--output','corpus/front80/test-v1')[0]==0
    code,query=run('corpus','query',DATASET,'--chapter','1'); assert code==0 and query['count']
    assert run('corpus','show',DATASET,query['segments'][0]['segment_id'])[0]==0
    assert run('corpus','verify',DATASET,'--rebuild')[0]==0
    assert run('corpus','show',DATASET,'missing')[0]==1
