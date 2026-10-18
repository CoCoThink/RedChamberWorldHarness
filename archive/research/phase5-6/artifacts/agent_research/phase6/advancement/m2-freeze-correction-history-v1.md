# M2冻结工具纠错记录

MODEL/NONE。用户已选择保留v2、不迁移20包，执行输入冻结和最多三章文学pilot。

## 真实错误与更正

1. 初次递归搜所有path/sha对象，把task中旧EXTRACTION_CONTENT_REBUILD报告的registered_toolchain锁ce2435…当作当下文件约束，遇当前37b863…即停止。后又把这些68次历史引用记成pilot阻塞，属于工具／解释错误，不是新发现的正文或prepared缺陷。
2. 独立只读核查按session._verify_prepared_request的明确边界检查全部20份inputs＋template/package/parent/feedback，共3427次出现，stale／missing为0。68次旧lock引用均在保存的registered_toolchain或toolchain_diff.registered；不能改成当前hash，那会伪造历史。fresh renderer仍照旧验证完整task，只允许原有两处Python观察leaf变化；本更正不新增豁免。
3. 产品报告是86项list；最初错用其长度作为区间数，已写入的v1记interval_count86，正确是interval-change-mask30。v1与其freeze digest原样保留，由v2显式引用并说明不再作当前依据。
4. 几次准备脚本失败还包括错误读取product-churn.analysis、package-impact.new_package_or_lineage_calls，以及首个测试假设JSON字典数字章号按数值排序；均只改本轮新脚本／测试，没有改原实验或旧输入。未生成成功输出的尝试不算成功冻结。

## 当前v2边界

`m2-input-freeze-v2/freeze.json`＋`input-inventory.json`按直接验证输入记录3427次、0stale，单列68条带JSON pointer的历史诊断。范围为字节冻结／研究版本选择，不冒称fresh renderer已跑或新稿已消费。

release原选86v1／91v2不变；pilot另选正常登记的86窄v2作父，95／99长v1作父。三者均保持原v3 package和v2 exemplar，后续真实新编辑请求／fresh／import不可省。现有source、corpus、policy、contract资格未闭合继续独立报告。
