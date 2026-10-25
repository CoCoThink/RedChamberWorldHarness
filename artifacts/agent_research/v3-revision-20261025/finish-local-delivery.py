"""Bind the actual built edition and completed local checks for handoff."""
from pathlib import Path
from collections import Counter
import json
from rcwh.generation.records import binding

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent


def main():
    audit = json.loads((O / 'actual-execution-verification.json').read_bytes())
    assert audit['status'] == 'PASS'
    request = json.loads((R / 'data/agent_release/research-81-100-v3/request.json').read_bytes())
    manifest = json.loads((R / 'releases/agent/research-81-100-v3/manifest.json').read_bytes())
    assert manifest['status'] == 'PASS' and not manifest['findings']
    assert Counter(v for ch in manifest['chapters'] for v in ch['gates'].values()) == {'PASS': 240}
    lineage = json.loads((O / 'final-writing-lineage.json').read_bytes())
    assert lineage['status'] == 'PASS' and len(lineage['chapters']) == 20
    assert all(ch['historical_integrity']['status'] == ch['current_compatibility']['status'] == 'PASS'
               for ch in lineage['chapters'])
    assets = json.loads((O / 'final-assets-validation.txt').read_bytes())
    assert assets['status'] == 'PASS' and not assets['findings']
    assert (O / 'final-repository-validation.txt').read_text().startswith('PASS:')

    def ref(path):
        return binding(R, path)

    index = {'kind': 'FINAL_RESEARCH_EDITION_HUMAN_HANDOFF_INDEX', 'edition': request['id'],
             'request': ref('data/agent_release/research-81-100-v3/request.json'),
             'manifest': ref('releases/agent/research-81-100-v3/manifest.json'),
             'book': ref('releases/agent/research-81-100-v3/book.md'),
             'candidates': [{'chapter': row['chapter'], 'candidate': row['candidate']} for row in request['chapters']],
             'comparison': ref((O / 'comparison/summary.json').relative_to(R).as_posix()),
             'dispositions': ref((O / 'coordinator-dispositions.json').relative_to(R).as_posix()),
             'source_corpus_material_index': ref((O / 'human-material-index.json').relative_to(R).as_posix()),
             'human_reviews_received': 0, 'P9_credit': False, 'authority_effect': 'NONE',
             'limitation': 'Prepared materials only; neither human review nor publication qualification.'}
    target = O / 'human-final-release-index.json'
    assert not target.exists()
    target.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    result = {'status': 'PASS', 'scope': 'ACTUAL_LOCAL_RESEARCH_BUILD_AND_VALIDATION',
              'build_command': 'PYTHONPATH=src python -m rcwh.cli agent-release build data/agent_release/research-81-100-v3/request.json --json',
              'allow_pending': False, 'release_status': manifest['status'], 'chapter_count': 20,
              'release_gates': {'PASS': 240}, 'findings': [],
              'request': index['request'], 'manifest': index['manifest'], 'book': index['book'],
              'evidence': {name: ref((O / name).relative_to(R).as_posix()) for name in [
                  'actual-execution-verification.json', 'final-writing-lineage.json',
                  'final-assets-validation.txt', 'final-repository-validation.txt']},
              'clone_reproduction': 'SEPARATE_COMMITTED_CLONE_RECEIPT_REQUIRED',
              'final_ci': 'SEPARATE_GITHUB_FINAL_HEAD_RUN_REQUIRED',
              'authority_effect': 'NONE', 'P9_credit': False}
    (O / 'final-local-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    report = O / 'EXECUTION_REPORT.md'
    text = report.read_text()
    assert 'FINAL_TECHNICAL_RESULTS_PENDING' in text
    text = text.replace('FINAL_TECHNICAL_RESULTS_PENDING：协调者决定绑定、正常build、实际执行审计、已提交HEAD克隆复现及最终推送CI在完成后更新。',
        '本地验收已完成：20回协调者决定已绑定；正常build未使用 `--allow-pending`，发布状态PASS，20回/240门PASS、零findings。20回历史谱系与当前输入兼容性均PASS，仓库完整性PASS；资产检查使用 `--require-tracked --base-ref d6cabc7`，462项资产、534来源、零findings。旧v1/v2、world/plan/source及stable树与基线一致。实际启动、原始记录、根阅读声明、19接缝双读与比较绑定均由 [actual-execution-verification.json](actual-execution-verification.json) 核验；这是保管核验，不是机器证明阅读或文学质量。\n\n'
        f"正文 `{index['book']['path']}`，SHA256 `{index['book']['sha256']}`，{(R / index['book']['path']).stat().st_size}字节。最终请求文件SHA256 `{index['request']['sha256']}`。详见 [final-local-validation.json](final-local-validation.json) 和 [最终人工交接索引](human-final-release-index.json)。\n\n"
        'COMMITTED_CLONE_PENDING：先提交产物，再从已提交HEAD做克隆复现并补记录，最后推送最终提交、等待双版本CI。')
    report.write_text(text)
    handoff = O / 'HUMAN_REVIEW_HANDOFF.md'
    handoff.write_text(handoff.read_text() + '\n最终冻结产物另见 [human-final-release-index.json](human-final-release-index.json)，绑定最终请求、manifest、读本、20回候选、实际模型比较与处置台账。原准备索引保持不变。此索引本身不增加人工阅读信用。\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
