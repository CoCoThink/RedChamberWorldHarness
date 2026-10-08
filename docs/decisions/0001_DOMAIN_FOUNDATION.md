# ADR 0001：先切换资产与证据来源领域

日期：2026-10-08。状态：已实施资产与来源基础；后续领域分阶段切换。

## 问题

原运行数据引用不存在的包内路径，内部 SHA 声明相符不能证明原件存在；历史状态散落在阶段文件，展开 repo 还会污染测试发现。

## 决定

1. 普通 Git 保存当前原件，按目录保护原始字节。
2. catalog 记录实体身份和 origins，不授予证据权威。
3. `data/provenance` 直接引用 asset，不使用长期路径兼容层。
4. imported release 只承认原有 baseline 并核对原件，保留完整证据闭包尚未完成的状态。
5. `data/project/current.json` 选择状态 owner；当前旧 world/literary owner 作为过渡，不通过 M1—M8 加载顺序推断当前状态。
6. Source/Asset/Project 及现有领域接口直接引用资产。旧 registry、encoded inventory 和完成门已退出运行；旧格式曾仅由一次性导入器的私有函数读取，迁移完成后该导入器也已退役。
7. 全量设计保持 IN_PROGRESS；局部通过不等同完整复原基础设施完成。

## 退出条件

world/planning 等领域转换并通过语义、行为和生产闭环验收后，删除对应旧加载器与固定历史计数测试的运行职责。
