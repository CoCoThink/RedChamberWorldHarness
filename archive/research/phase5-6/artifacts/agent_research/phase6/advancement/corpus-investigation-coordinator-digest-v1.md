# P2 corpus负面调查：协调摘要

MODEL_SUBAGENT／NONE／RESEARCH_ONLY。本页据委派模型最终只读回报整理，不是协调者独立重做抽取、正式CorpusAudit、新build或人审通过。原完整回报留在会话中；模型未创建原始报告文件。未修改旧意见／产品，未执行新测试／重建／登记／评估。

## 结论与处置

1. 两份v2原FAIL指向同一组31独特页眉位置（5异文、26附录），共62条负面sample checks，不是62个不同缺陷。
2. 模型逐项核查确认：31处都是一个物理行分成两个相邻EDITORIAL段：`撫琴居` [0,3)保留WATERMARK_FONT理由，`红楼梦脂评汇校本 \n` [3,13)为DECLARED_RUNNING_HEADER_LINE_IN_EDGE_STRIP。全文与来源coverage齐全，未发现这31处层分类错误／漏字／MAIN_TEXT污染。
3. 旧review-samples已经带whole_pdf_line_context和prefix_segments，旧page-furniture-lines已经披露31处拆段。因此“此前没有完整行／prefix上下文”不成立。canonical dataset没有持久group对象，是可能的API增强，不自动证明验收合同被违反。两份原FAIL仍有效保留，不能靠换packet或再找PASS清除。
4. 另有**30处不在该31项投诉集合内**的重复页眉，仍并入VARIANT／APPENDIX。若产品要承诺这些层content-only，则是实际待处理残留；现有契约是否承诺这种纯度须先明确，不先宣布v3必需。
5. 80份MAIN_TEXT视图及segment_refs在v1/v2相同；5639条MAIN_TEXT核心记录除dataset／method元数据外相同。全carrier字符映射仅535 APPENDIX→EDITORIAL、94 VARIANT→EDITORIAL，MAIN_TEXT和ZHIPI无字符层变更。以上是模型只读产品比较，不是locked rebuild或文学通过。
6. reader2观察文件有49/102条old_kind映射错误，包括8条负面；reader1的102条映射均合实际span。错误不能撤销共同拆段事实，也不授权编辑原意见。将来如修正，以追加raw-span crosswalk处理。

## 绑定与版本

相对根：`/mnt/d/Code/RedChamberWorldHarness`。

- O1 `artifacts/agent_research/phase6/corpus/reader1-opinion-v1.json` SHA256 `584ea51882eaf7c24b55e495f900e7b4bb08a487e8ec56a2d8ea137021d84dc7`；隔离false。
- O2 `artifacts/agent_research/phase6/corpus/reader2-opinion-v1.json` SHA256 `a2f098bcb7089f076cdafa79da4bc1bf3632fed7e0041a72f227c83938b1b679`；隔离true／NOT_PROVEN，不认证。
- 登记record分别为`data/agent_panel/records/d80b04c08329806ab07f9856b67c91f5b0d35acc8a7b56f5a1800dcb53621e1c.json`、`163223b4092aa8921cd3e63fd28ffeadb2020528c12e1d8a1635a031dc7dbaec.json`；模型报告raw SHA及投影一致。
- packet SHA `ec0f732bb5ff37ddee99efdd3ce3809b614d981ea8e2d1d6bef3ae2598bcc30b`；review-samples SHA `cfa4819f8dd6dd7c92dc1c06c3c8c5f6c61e47b0af99e0b316e659652d15b532`。
- `corpus/front80/v2-candidate/manifest.json` SHA `eb4aebb9e38712a988bdead263c12c9c3df00a6f936fb17db755c436e4d66886`。
- S2 `corpus/front80/v2-candidate/segments.jsonl` SHA `fddf648183770baead283dd80075515a517274c40c18a171237a2399ea9fe6c2`。
- S1 `corpus/front80/v1-candidate/segments.jsonl` SHA `bf2d6d7e988e798444aad9ef62de54fba970edd9df72f5be4c94ccaf18f770a6`。
- 31 suffix共同text SHA `afa42fc61e375e938846891f6e111df66d8a307d4c193a55fa84a5020a66fb25`；各自独立位置，不以同hash去掉30项。
- `page-furniture-lines.json` SHA `e14b07bbe8f2e11c3e1bbbb5e38e48687028a4d11b468d07e848f57ac0e1c522`；`dataset-map-v1-to-v2.json` SHA `9f678d145b8394d55803950da9e20da87685c6c326ca2bf4a31c58e2eb38e8a2`，均在上述phase6/corpus目录。

## 31项逐位置crosswalk（模型核查回报）

ID列省略共同`hlm80:`前缀；v2前缀段总是同section前一p号、S2前一行，[0,3)。suffix [3,13)，原抽取manifest `asset:sha256:1c9dee98f867ea07dade7b69b2b8d3987c5046ddb51e1e377c5e306fd26ba900`。O行定位两原opinion的sample check起点。每行结论相同：拆段事实成立，v2两段均EDITORIAL，非MAIN_TEXT分类错误。

|物理页|v2 ID|S2行|按span对应v1 ID|S1行|O行|
|---:|---|---:|---|---:|---:|
|917|chapter:67:p00040|10889|chapter:67:p00040|10889|59|
|919|chapter:67:p00048|10897|chapter:67:p00046|10895|77|
|921|chapter:67:p00056|10905|chapter:67:p00052|10901|95|
|923|chapter:67:p00064|10913|chapter:67:p00058|10907|113|
|925|chapter:67:p00072|10921|chapter:67:p00064|10913|131|
|1111|appendix:all:p00008|12099|appendix:all:p00006|12086|167|
|1113|appendix:all:p00016|12107|appendix:all:p00012|12092|185|
|1115|appendix:all:p00024|12115|appendix:all:p00018|12098|203|
|1117|appendix:all:p00032|12123|appendix:all:p00024|12104|221|
|1119|appendix:all:p00040|12131|appendix:all:p00030|12110|239|
|1121|appendix:all:p00048|12139|appendix:all:p00036|12116|257|
|1123|appendix:all:p00056|12147|appendix:all:p00042|12122|275|
|1125|appendix:all:p00064|12155|appendix:all:p00048|12128|293|
|1129|appendix:all:p00078|12169|appendix:all:p00058|12138|323|
|1131|appendix:all:p00086|12177|appendix:all:p00064|12144|341|
|1133|appendix:all:p00094|12185|appendix:all:p00070|12150|359|
|1135|appendix:all:p00102|12193|appendix:all:p00076|12156|377|
|1137|appendix:all:p00110|12201|appendix:all:p00082|12162|395|
|1139|appendix:all:p00118|12209|appendix:all:p00088|12168|413|
|1141|appendix:all:p00126|12217|appendix:all:p00094|12174|431|
|1143|appendix:all:p00134|12225|appendix:all:p00100|12180|449|
|1145|appendix:all:p00142|12233|appendix:all:p00106|12186|467|
|1147|appendix:all:p00150|12241|appendix:all:p00112|12192|485|
|1149|appendix:all:p00158|12249|appendix:all:p00118|12198|503|
|1151|appendix:all:p00166|12257|appendix:all:p00124|12204|521|
|1153|appendix:all:p00174|12265|appendix:all:p00130|12210|539|
|1155|appendix:all:p00182|12273|appendix:all:p00136|12216|557|
|1157|appendix:all:p00190|12281|appendix:all:p00142|12222|575|
|1159|appendix:all:p00198|12289|appendix:all:p00148|12228|593|
|1161|appendix:all:p00206|12297|appendix:all:p00154|12234|611|
|1163|appendix:all:p00214|12305|appendix:all:p00160|12240|629|

97个家具group＝31双段页眉＋66单段页码，另5个MAIN_TEXT范例；102核心sample去review_context后均与canonical段一致。旧context确能精确重构group。

## 单列的30处残留title行

不是上表31投诉位置。模型报告这些五种字符串已在旧companion的intentionally_retained_top_titles披露。

|完整重复标题|物理页|v2含该header的记录p号|
|---|---|---|
|第六十七回 馈土物颦卿念故里 讯家童凤姐蓄阴谋|918,920,922,924,926|chapter:67:00043/51/59/67/75|
|附录一 《红楼梦》各抄本收藏者序跋|1110,1112|appendix:all:00003/11|
|附录二 存世脂评系统《红楼梦》版本简介|1116,1118,1120,1122,1124,1126|appendix:all:00027/35/43/51/59/67|
|附录三 毛国瑶抄录靖藏本批语一百五十条|1128,1130,1132,1134,1136,1138,1140|appendix:all:00073/81/89/97/105/113/121|
|《红楼梦脂评汇校本》校读札记|1144,1146,1148,1150,1152,1154,1156,1158,1160,1162|appendix:all:00137/145/153/161/169/177/185/193/201/209|

完整ID应展开为`hlm80:<section>:p<五位数>`，缩写尾号按同五位宽补全。现有记录会跨物理页合并，不能仅按p号相等推v1映射。phase5曾指出1110[0,19)的附录页眉，v2仍并在APPENDIX p00003；因此不能说全部历史家具问题已修完。

## reader2 old_kind错误

49项构成：21 null→APPENDIX、20 EDITORIAL→APPENDIX、4 EDITORIAL→VARIANT、4 null→VARIANT。8条负面是ch67 p00072及appendix p00166/174/182/190/198/206/214；其真实v1对象见逐位置表。原观察错误为null，不能当作旧版没有该文本。原raw／opinion保持，不从ID序号相等推同物。

其他历史争议：79章物理1097前置隐URL／页码在80回标题之前，属既有heading-to-heading scope，不证80正文误归；49回`[麂]`为原版(old)[new]记法，不是工具擅改。模型读了phase5 adjudication并比产品，本轮未重新渲染1097／666，不能冒称新页图复核。phase5是reader1 PENDING／reader2 FAIL，不称又一对FAIL。

## 最小工程决议（未执行）

- **对31拆段本身**：不要求改classifier或必建v3。保留两reason链及原FAIL。若需要canonical group便利，可先定显式绑定v2的只读context规范，但不能把旧已有context重新包装成新独立证据，也不能自动清原FAIL。
- **若明确选择content-only VARIANT／APPENDIX**：可在另版v3 config仅增五条已核完整title，继续whole-line／edge-strip／variant-or-appendix guard；不按小字一刀切，不合并watermark，不改MAIN_TEXT。需实际兼容实验及catalog／全20包谱系成本披露后才决定真实登记／迁移。
- 两臂隔离实验尚未执行：A仅对97旧group做绑定／连续性负测；B可选v3双compile要求仅30行mask变化、31split和66页码仍保留、5639 MAIN_TEXT／4653 ZHIPI不动、80视图与refs不变、内容小字与标题不误判、全carrier coverage和ID churn逐项列出。
- 当前20包全共享corpus v2及ch89-research-v2 exemplar。实验需分别检旧20prepared仍有效与新v3包真实输入变化；即使MAIN_TEXT相同也不能把旧稿换绑当消费v3。未经实际影响确认不推进全20新谱系。

## 实际已读与限制

模型声明看了物理917–926、1110–1163页图，并对917–927、1109–1163做抽取／几何核对；916仅几何。31争议全部包含。全文读两opinion、全部FAIL和v1/v2行／span／fonts／bbox、80 MAIN_TEXT视图及全字符层映射；未逐页读完整80回或附录语义。

本轮直接PDF抽取使用系统CPython3.14／PyMuPDF1.27.2.3，不是声明支持的locked3.12；这些是诊断观察，不能作为正式重建验证。未跑canonical build、全suite、validate或发布evaluate，无新资格PASS。后续正式工程实验必须使用支持的Python3.12环境且先解决当前执行权限阻塞。
