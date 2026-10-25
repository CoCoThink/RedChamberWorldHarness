"""Record an actual committed-payload clone result without claiming final CI."""
from pathlib import Path
import json
import subprocess
from rcwh.generation.records import binding

R = Path(__file__).resolve().parents[3]
O = Path(__file__).resolve().parent


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
    assert head == '7f66947135df1fe27969aa50e839e73277a4f39d'
    report = json.loads((O / 'committed-clone-verification.json').read_bytes())
    assert report['status'] == report['release_status'] == report['cloned_build']['status'] == report['cloned_build']['release_status'] == 'PASS'
    reproduction = report['cloned_build']['committed_release']
    assert reproduction['status'] == 'PASS' and reproduction['book'] == 'EXACT_BYTES'
    assert reproduction['manifest'] == 'EXACT_EXCEPT_NAMED_RUNTIME_OBSERVATIONS'
    index = json.loads((O / 'human-final-release-index.json').read_bytes())
    for key in ('request', 'manifest', 'book'):
        assert index[key] == binding(R, index[key]['path'])
    manifest = json.loads((R / index['manifest']['path']).read_bytes())
    assert report['request_sha256'] == manifest['request_sha256']
    assert report['cloned_build']['text'] == manifest['output']['text']
    result = {'status': 'PASS', 'scope': 'ACTUAL_COMMITTED_PAYLOAD_CLONE_REPRODUCTION',
              'tested_commit': head,
              'verification': binding(R, (O / 'committed-clone-verification.json').relative_to(R).as_posix()),
              'verification_tool': binding(R, 'tools/verify_agent_release.py'),
              'clone_build_allow_pending_argument': True, 'clone_release_status': 'PASS',
              'committed_book': reproduction['book'], 'manifest_comparison': reproduction['manifest'],
              'runtime_observation_paths': reproduction['runtime_observation_paths'],
              'request': index['request'], 'manifest': index['manifest'], 'book': index['book'],
              'final_head_ci': 'MUST_BE_VERIFIED_AFTER_FINAL_PUSH_NOT_CLAIMED_HERE',
              'authority_effect': 'NONE', 'P9_credit': False}
    target = O / 'committed-clone-custody.json'
    assert not target.exists()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    path = O / 'EXECUTION_REPORT.md'
    text = path.read_text()
    assert 'COMMITTED_CLONE_PENDING' in text
    text = text.replace('COMMITTED_CLONE_PENDING：先提交产物，再从已提交HEAD做克隆复现并补记录，最后推送最终提交、等待双版本CI。',
        '产物提交 `7f66947135df1fe27969aa50e839e73277a4f39d` 的真实克隆重建已PASS：读本EXACT_BYTES，manifest严格一致（仅允许已列明的忠实运行时观察差异），重建仍为PASS。工具内部命令确实带 `--allow-pending`，没有隐去该参数；已提交版是PASS且会严格对比门控/意见/作者/绑定，任何降级不符都会失败，因此本次未以该参数接受PENDING。详见 [克隆输出](committed-clone-verification.json) 和 [已测提交保管记录](committed-clone-custody.json)。\n\n'
        '最后一笔提交只补验收证据、脚本与文档，不改冻结正文、请求、意见和发布产物。最终HEAD推送后由GitHub再次执行双版本验证（包括克隆重建及全量pytest）；本文件不把提交前的状态冒充最终CI结果。可按[本分支CI](https://github.com/CoCoThink/RedChamberWorldHarness/actions?query=branch%3Aresearch%2Fv3-20261025)与最终提交SHA核对，交付回复给出实际最终运行链接。')
    path.write_text(text)
    plan = R / 'docs/plans/POST80_V3_REVISION_20261025.md'
    text = plan.read_text().replace('正在完成已提交HEAD克隆复现与最终推送CI。',
        '已提交产物克隆复现通过，最终推送后CI按最终HEAD另行核验。')
    plan.write_text(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
