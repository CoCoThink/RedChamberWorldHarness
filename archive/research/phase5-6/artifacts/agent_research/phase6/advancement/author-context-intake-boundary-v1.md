# policy阅读作者context边界核查

MODEL/NONE。只读定位报告的协调摘要；不是已完成的author-context registry／资格消费者，不授provider或独立性认证。

## 实际选版与谱系

release request-v1仍选81长v1、86长v1、91窄v2。81 selected draft c376af1f…父f036aaf4…、run af66dc64…，principal `session:phase6-reviser-ch81-context1`。86 selected draft 57752b02…父22e3b6ba…、run af1970d2…，principal `session:phase6-reviser-ch86-context1`。91 selected draft d5ea23de…父84133900…、run90e9bf3d…，principal `session:phase6-main-narrow-reviser-ch91`。完整hash／绑定由原request与draft提供，不以本页缩写充正式binding。

86窄v2是另版coordinator revision，当前未选入。不能因最新disclosure存在就替换选择。draft大对象内task／inputs还会有旧principal／run；只沿顶层authors、run、parent走真实谱系，不递归搜到任何principal就当直接作者。

现有`load_draft`／`verify_session_draft`会正常fresh核prepared、run／candidate／package／parent等一致性；不能为了新身份表跳过该验证。但其session labels仍是声明，四个真实长v1作者context会有多个章级labels，不能当20独立作者。

## 尚未闭合

受限定位已确认已有session lineage helper和disclosure格式不统一（revision／version等差异），但未恢复全部四context成员的精确声明映射。不得由章号、principal后缀或模型名生成context ID，也不能把主协调者86／91两次编辑算两个独立作者。

协调者随后按精确disclosure字段补查，另存`declared-author-context-inspection-v1.json`及可重算工具：85显式声明与81–84同session、90与86–89同context、95与91–94同context、100声明此前完整96–99同author session，故可保留四个long-v1声明组。该补查还按顶层parent追20章所选谱系，核draft/run/candidate绑定；未执行fresh renderer。短父稿context成员仍未完整映射，四个local group key不是认证runtime context ID，identity_eligibility继续PENDING_INCOMPLETE_MAPPING。

后续映射应显式绑定每个author_run、exact session_id、实际context声明和disclosure；unknown映射仍unknown。候选／父稿／修订者／协调者全部排除正向同行资格，重复reader context／alias不多计人数，false隔离不改true。必须先有完整真实mapping才可建正向资格consumer。

当前`policy_readings`仅保存reader原声明／raw receipt并汇总全部负面，不做positive count；identity_eligibility继续PENDING_NOT_IMPLEMENTED。未收任何真实policy阅读，实际registry为空。此界限防止先实现计数、后补伪造context。
