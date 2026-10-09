# P9 配对盲评准备

blind-pairs.zip 包含20对匿名 A/B 文本，原稿和修订稿的位置各半；只将它和 human-review-template.json 提供给独立评审者。至少两位评审者分别回填，每对提交偏好、四个维度的1—5分及具体理由。engineering_feel 的高分表示工程痕迹较明显，其他维度高分表示较好。

coordinator-mapping.json 仅供协调者；不交给评审者。其不可变登记副本与盲包已被 data/evaluation/paired_selection.json 绑定。当前 reviews 为空，实际状态为 PENDING；此目录不含任何伪造或代理充任的人工结果。

接收原始意见、结构化回填与失效规则见 docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md。评审信号不自动产生胜者或 ACTIVE 变更。
