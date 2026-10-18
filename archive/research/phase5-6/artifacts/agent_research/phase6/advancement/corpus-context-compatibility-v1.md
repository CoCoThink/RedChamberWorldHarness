# 既有corpus上下文兼容性：支持环境下的只读核查

MODEL_SUBAGENT／NONE／RESEARCH_ONLY。协调者据本轮委派模型回报保存。模型以CPython3.12.13、`/tmp/rcwh-venv/bin/python -B`对现有bytes执行只读比较及内存负例；无新产品／登记／catalog写入／PDF重抽取／build／测试套件／资格裁定。本页不是正式可复现build报告，原FAIL均保留。

## 实际结果

- 102个review sample去掉review_context后，全对象均等canonical segment，不只是text hash相等。
- 97个EDITORIAL anchor的review_context逐对象等companion中对应line；另5个MAIN_TEXT的context为`{"selection":"EXEMPLAR"}`。
- 97物理group包含128个不同canonical成员：31双段header（67回异文5＋附录26），66单段page number。anchor集合等所有EDGE_STRIP理由的canonical段，没有漏group或重复位置。
- prefix均`撫琴居` [0,3)，EDITORIAL／WATERMARK_FONT，SHA `cfe5018e0eb7a23437baf9a20024ad84c6b23f2c9dfda40c1fe56726b2c083c5`；suffix [3,13)，SHA `afa42fc61e375e938846891f6e111df66d8a307d4c193a55fa84a5020a66fb25`。
- 对每group检查dataset／extraction／空transforms／scope、anchor text/hash/style/reason、prefix紧邻和同scope、同unit无gap无overlap、整行边界／原抽取重构、finite page-contained bbox和edge band、整行header或page number fullmatch。
- 核71个相关抽取unit的text hash及input binding；manifest／output hash及bytes一致。只核存储几何内部一致，未从PDF新抽bbox。

## 实际格式细节

segments.jsonl第一行是FILE_SCOPE envelope，之后才是12307条SEGMENT；不得把envelope当段索引。

whole_pdf_line_context.text不含LF，但[start,end)包含LF，必须用原抽取text比较，不能strip后冒称exact。

existing_editorial_prefix的外层segment_ref指suffix anchor；prefix_segments内部segment_ref才指prefix。prefix descriptor没有text_sha256，要解析实际canonical prefix核其原hash。

旧companion已有97 group、31split和30个保留title的披露。该30残留title本次未再独立审核。政策参数仍top0.11、bottom0.10、page regex `[0-9]{1,4}`及一条完整book header，不扩定义。

## 18个内存负例

模型报告18/18均拒绝：stale manifest、错dataset、重复group、少group、改policy、sample/context不一致、缺prefix、错prefix ID、prefix gap、prefix kind变、prefix reason变、部分行边界、整行文字变、hash变、bbox不在edge、authority升级、human升级、重复sample。对companion变异同步更新了对应sample context，避免只因两处不等而遮蔽真正结构缺陷。

这些是该模型实际执行的内存诊断，不冒称已加入pytest回归或已经合入正式validator。

## 核查绑定

- `artifacts/agent_research/phase6/corpus/review-samples-v1.json`：`cfa4819f8dd6dd7c92dc1c06c3c8c5f6c61e47b0af99e0b316e659652d15b532`
- 同目录`page-furniture-lines.json`：`e14b07bbe8f2e11c3e1bbbb5e38e48687028a4d11b468d07e848f57ac0e1c522`
- `corpus/front80/v2-candidate/manifest.json`：`eb4aebb9e38712a988bdead263c12c9c3df00a6f936fb17db755c436e4d66886`
- 同目录`segments.jsonl`：`fddf648183770baead283dd80075515a517274c40c18a171237a2399ea9fe6c2`

## 工程决议

对于31split，不创建新corpus／新packet来洗FAIL；已有context的表示能力已核。未来若需要独立纯validator，可接受显式trusted hash及manifest／segments／samples／companion／extraction原bytes，返回内存一致性结论，不自动调用默认rebuild=True的repository loader、不写catalog、不改段text/ID/kind/reason。

全局注册、content-only v3与20包谱系迁移仍未启动。此处兼容观察不是原source／corpus／release门的PASS，更不认证human或独立provider。
