# P3原始policy阅读记录保存与全量声明汇总

MODEL/NONE。新增`evaluation/policy_readings.py`与`tests/test_policy_readings.py`；仍未接release、未收真实读者意见，不授语义／人类／provider资格。测试全部为tmp隔离合成提交，实际项目registry尚未填入意见。

## 当前行为

- 本地仓库内显式FILE intake，原始JSON字节原样保存到固定`data/evaluation/policy_evidence/raw/`，canonical request独立保存到requests，receipt独立保存到receipts。所有文件按内容寻址、no-replace追加，重复raw+request不因origin不同新增意见。
- 汇总扫描完整固定registry，拒非预期entry、重复receipt、伪／旧hash、unreceipted payload、symlink路径。caller不能给有利receipt子集。写入持nonblocking OS锁；中途失败留下的orphan会明确阻塞，不自动删记录“修复”。dry-run不建registry／锁文件。
- 同candidate bytes＋policy bytes的负面声明跨selection/context保留；改变真正subject则保留历史负面，未有显式适用crosswalk即PENDING。未实现的适用裁定不能默认清除。
- 若旧validator／schema／依赖已变、历史request不能按当前代码复放，整体完整性明确FAIL，但原始负面声明仍显示，并写replay unavailable，不以stale名义静默丢失。raw／request自己损坏仍是完整性错误，不伪装成已证正文违例。
- 原machine anchor FAIL维持FAIL；引用精确的VIOLATED只是有归属的原始声明，不能由此模块自动裁真。正面计数、author-context资格和语义拆分未实施，所有语义／release资格始终PENDING。

## 当前测试

定向63 passed（41.31秒），包括16项custody、43项policy evidence、4项现有release policy guard。覆盖原字节／dry-run／幂等origin、负面与正面并存、false隔离负面保留、same bytes换selection、改bytes历史适用pending、损坏raw／receipt／orphan／缺receipt／重复receipt／额外index、旧context复放失败仍见负面、writer锁、symlink和bool请求篡改。没有实际模型语义意见或认证provider调用。

本批代码模型复核及作者context形状核查仍待回报；此记录不预报其结论。所有工程结果须在修正完后统一完整快照，不追计入checkpoint23。
