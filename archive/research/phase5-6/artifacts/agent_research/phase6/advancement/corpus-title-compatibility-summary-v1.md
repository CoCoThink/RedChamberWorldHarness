# 五种残留页眉的隔离corpus候选实验

MODEL/NONE／RESEARCH_ONLY。实验在独立Linux副本执行，主仓库没有build、register、catalog写入、旧产品修改或20包换绑；旧31 split FAIL及所有旧负面保留。脚本：`tools/experiment_corpus_furniture.py`；结果目录：`artifacts/agent_research/phase6/advancement/corpus-title-compatibility-v1/`。

## 实际三次compile

- baseline：使用未改v2 config，86/86产品精确匹配、manifest exact、mismatches=[]；8.72s。
- candidate-first：新dataset/config、schema_version仍2，仅加入已从旧companion确认的五种残留完整title strings；86产品、8.40s。
- candidate-second：同候选配置、独立进程重跑，manifest/products canonical exact；8.64s。
- 总实验129.33s；CPython3.12.13；临时副本已清，原树input no drift=true。

## 精确实验结论

五种标题实际出现次数为：校读札记10、67回running title5、附录一2、附录二6、附录三7，共30 intervals。30处均按原始`(extraction, unit, start, end)` mask由VARIANT或APPENDIX→EDITORIAL；没有按segment ID顺序比较。

- MAIN_TEXT：5639 old/new记录，逐对象去dataset_ref后相等。
- ZHIPI：4653 old/new记录，逐对象去dataset_ref后相等。
- 80章chapter text与segment_refs不变。
- 原31 split groups与66 page-number furniture保持不变。
- carrier比较846186字符。
- old segments12307，candidate12337；224个exact-locator segments发生ID位移。按层字节统计：APPENDIX→APPENDIX32043、APPENDIX→EDITORIAL471、EDITORIAL→EDITORIAL1852、VARIANT→EDITORIAL125、VARIANT→VARIANT7879。
- 除dataset身份变化外4个产品改变：segments.jsonl、alignment.jsonl、editorial_tags.jsonl、quality_report.json；86个raw products因dataset identity改变而变化。
- candidate两个独立进程canonical manifest/products完全一致。

## 输入迁移影响

20个现有包均绑定共享`corpus:front80:v2-candidate`和`ch89-research-v2` exemplar；旧prepared binding出现3427次，当前无mismatch。实验未创建新exemplar／package，未调用fresh renderer/import、未生成新谱系，故没有generation cost估计。

采用candidate必须另建v3 exemplar／20个新版包，并按真实新输入重新准备、写作和披露；不能因MAIN_TEXT和5个选读segment正文相同而把旧稿说成消费v3。ID位移会影响derived alignment／tags／source links，需在新包前逐项迁移核对。此实验不替用户确认global catalog登记或全20谱系重写。

## 资格边界

`status=EXPERIMENT_CHECKS_SATISFIED_NOT_QUALIFICATION`。工程条件说明这一小范围classifier候选可重建且不改MAIN_TEXT，但不等人工corpus通过、source authority、文学质量或release PASS；原corpus FAIL不因30个新变更被洗掉。若不承担4产品和20谱系迁移成本，可保留v2并把content-only诉求记录为未采用；不能再做同字节packet替换获取PASS。
