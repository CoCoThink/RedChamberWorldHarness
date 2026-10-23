"""Apply the evidenced witness correction after the frozen campaign completes."""
from copy import deepcopy
from pathlib import Path
import json
import yaml
from rcwh.assets import AssetCatalog
from rcwh.assets.ingest import AssetIntake
from rcwh.candidate_reviews import canonical_bytes
from rcwh.corpus.extraction import ExtractionRepository
from rcwh.corpus.locators import SourceLocatorVerifier, source_digest
from rcwh.workflow.review_campaign import status

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / 'source-correction-evidence'
ID = 'src:gengchen:ch27:xiaohong-great-help'
execution = status(ROOT, 'data/agent_release/research-81-100-v1/review-campaign-v3.json')
assert execution['status'] == 'PASS' and not any(j['needs_followup'] for j in execution['jobs'])
file = ROOT / 'data/provenance/sources/r4_core_completion.yaml'
raw = file.read_text()
original_records = yaml.safe_load(raw)['sources']
before = next(s for s in original_records if s['id'] == ID)
assert before['witness']['siglum'] == 'GENGCHEN', 'one-time correction; do not rewrite a corrected source'
source = deepcopy(before)
source['title'] = '甲戌本第二十七回总评——红玉后有宝玉大得力处'
source['witness'] = {'siglum': 'JIAXU', 'label': '甲戌本', 'annotation': '第二十七回回末总评，跨PDF399—400页',
                     'context_units': ['pdf:page:399']}
source['notes'] = ('锁“小红/红玉后有宝玉大得力处”的未来功能，不锁具体帮助方式与回次。'
    '固定汇校PDF399页绿色总评以甲起，400页目标句为其连续段。旧ID含gengchen只作历史稳定标识，不再表示见证归属；'
    '见证以witness的甲戌本为准。旧来源投影及两份BLOCKING意见保留，未将纠错冒充人工准入。')
catalog = AssetCatalog.from_repo(ROOT)
built = ExtractionRepository(catalog).build(source['container']['ref'], {'format': 'PDF', 'pdf_pages': [399, 400]})
catalog = AssetCatalog.from_repo(ROOT)
verifier = SourceLocatorVerifier(catalog)
located = verifier.locate(source, built['manifest_ref'], unit_ref='pdf:page:400')
assert located['status'] == 'PASS', located
source['locator'] = located['locator']
source['locator_verification'] = {'status': 'UNVERIFIED', 'reason': 'Recomputed correction pending report retention.'}
report = verifier.verify(source)
assert report['status'] == 'PASS', report
report_file = OUT / 'corrected-locator-report.json'
report_file.write_bytes(canonical_bytes(report))
receipt = AssetIntake(ROOT).ingest(report_file, origin='review-campaign-20261023:corrected-jiaxu-witness:locator',
                                  kind='REVIEW_RECORD', role='LITERARY_REVIEW')
source['locator_verification'] = {'status': 'VERIFIED',
    'reason': 'Exact excerpt recomputed from fixed carrier; witness correction supported by PDF399/400 images. Model review is not human admission.',
    'report_ref': receipt['asset_ref'], 'report_sha256': receipt['sha256'], 'source_record_sha256': source_digest(source)}
start = raw.index('- id: ' + ID + '\n')
end = raw.find('\n- id: ', start + 1)
end = len(raw) if end < 0 else end + 1
file.write_text(raw[:start] + yaml.safe_dump([source], allow_unicode=True, sort_keys=False, width=100) + raw[end:])
assert [s for s in yaml.safe_load(file.read_text())['sources'] if s['id'] != ID] == [
    s for s in original_records if s['id'] != ID], 'unrelated provenance records changed'
negatives = []
for p in sorted((ROOT / 'data/agent_panel/records').glob('*.json')):
    record = json.loads(p.read_bytes())
    if any(r['subject_id'] == 'source:' + ID and r['verdict'] == 'FAIL' and r.get('severity') == 'BLOCKING'
           for r in record['opinion']['results']):
        negatives.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': p.stem})
assert len(negatives) >= 2
audit = {'before': before, 'after': source, 'before_source_digest': source_digest(before),
         'after_source_digest': source_digest(source), 'retained_blocking_opinions': negatives,
         'extraction': built['manifest_ref'], 'locator_report_receipt': receipt,
         'root_baseline_effect': 'NONE', 'authority_effect': 'NONE', 'human_admission': False}
(OUT / 'correction.json').write_bytes(canonical_bytes(audit))
print(json.dumps({'status': 'PASS', 'source_digest': source_digest(source), 'retained_blockers': negatives}, ensure_ascii=False))
