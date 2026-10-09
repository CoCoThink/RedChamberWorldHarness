# 交付副本与登记原件

本次移除了22个未登记的重复交付文件，共32,551,643字节（31.04 MiB）。每个文件先与已登记 ZIP 的成员或已登记原件逐字节比较；恢复绑定见 `data/project/delivery.json`。登记的不可变原件、历史包和 Git 历史均保留。

```bash
rcwh delivery summary
rcwh delivery materialize source-review-v2 /tmp/source-review-v2
rcwh delivery materialize corpus-review /tmp/corpus-review
rcwh delivery materialize input-inventory /tmp/input-inventory
rcwh delivery attachments /tmp/rcwh-release-attachments
```

物化到新目录，验证登记资产 SHA，拒绝危险 ZIP 路径、重复成员及软链接。所有源材料仍可离线恢复，阅读包的旧原始 README 和空白表也从 ZIP 恢复。附件准备保留登记文件原字节，生成 manifest，状态为 NOT_PUBLISHED；没有上传 release 或新增许可。

artifact 的展开阅读目录保留导航说明及小文件；完整阅读前先运行物化命令。去重后目录约20.4 MiB，加入本次核验报告、匿名小样和作者任务后约21.7 MiB，原先约51.5 MiB。Git历史仍含旧副本，clone体积不会仅因当前删除就同幅下降。后续若外置登记原件，必须先提供受 SHA 约束的物化和离线闭包；不能直接替换为 LFS 指针造成已有 Source 断链。

活跃文档采用领域名称，历史协议、资产 ID、schema 名称及评审记录中原有阶段号保持追溯意义。研究状态的十份小文件已合并到 `data/research/`，内容原字节未变，路径映射见 `data/project/layout_changes.json`。冻结 P6/P7/P8 实验原件和 hash 绑定继续保持，不借目录整理补授评审效力。
