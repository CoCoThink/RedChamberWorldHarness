# P3外部绑定清单锚点切片

日期2026-10-18。MODEL/NONE。新增`evaluation/policy_inventory.py`及独立schema、18项回归；不接release、不更改原policy reading summary默认行为。真实reading registry仍为空，没有保存虚构意见或声称可信owner已经选定清单。

## 实际能力

- `build_policy_inventory(root, previous=None)`在共享锁下扫描完整固定registry，返回包含所有bundle及其raw/request/receipt三成员精确hash的内存清单。调用方另行冻结其原bytes，不由函数修改owner或catalog。
- `check_policy_inventory(root, anchor, request=None)`要求显式path/hash锚点，不搜索latest。校验完整链、唯一排序bundle、三个精确成员路径；后继必须包含每个前继条目且bytes绑定不变。读取锚点／成员须regular、仓库内无symlink。
- 删除整负面bundle能由既有锚点检出缺失三成员；无法凭hash重造原始负面，保留缺失错误而不捏造意见。新增bundle相对旧锚点为unexpected，需形成新后继检查点；不能选择有利幸存子集覆盖原清单。
- 严格schema禁止人类／authority升级和额外PASS字段。schema_version明确int，拒bool；空／畸形锚点返回FAIL。原语义／身份／release资格一律PENDING，观察checkpoint的完整性PASS不外推。

## 信任边界

锚点的可信绑定由选择owner／独立保留记录提供，不因文件名、模型生成或函数参数自动权威。没有独立owner锚点时，默认汇总仍报告PENDING_NO_INDEPENDENT_EXPECTED_BUNDLE_ANCHOR；此功能不能阻止调用者丢弃旧锚点另编第一份清单，也不能证明第一份冻结前未发生删除。若发布要求不可回滚全局历史，需要更强owner／保存协议，不能宣称本切片解决。

本轮只建纯验证接口与合成fixtures，不在实际owner建立清单。P3语义原子、author父稿context资格、跨规则适用、合同runtime和真实专门阅读仍开放；不为得到PASS放宽任何原门。

## 代码复核及测试

限定只读模型复核发现：`check_policy_inventory(root,None)`原遍历返回空链后[0]会IndexError。已对入口null明确拒绝，同时保留previous:null合法终止；新增None／空dict／list／额外binding字段负测和FIFO锚点拒绝。

最新定向93 passed（65.14秒），覆盖18inventory＋28custody＋43evidence＋4原release guards，diff check通过。测试包含负面与正面并存后整包删、后继遗漏／改member／重复／乱序／bool、旧anchor bytes／receipt变化、新bundle追加、首冻结前不可追溯限制和同writer锁。没有真实意见或human/provider认证。

本批最终完整Linux验证另建checkpoint25，不能追计入24。历史24仍1769 passed／1 skipped、4178输入无漂移；不回写。
