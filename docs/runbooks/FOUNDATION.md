# 资产与来源基础操作

## 安装与当前状态

```bash
python -m pip install -e '.[dev]'
rcwh project status
rcwh validate
pytest -q
```

数据按仓库根目录解析。其他工作目录使用 `rcwh --root /path/to/repo ...`。

## 资产与追溯

```bash
rcwh assets summary
rcwh assets validate
rcwh assets resolve asset:primary:hlm:zhihui:v3.1416:pdf
rcwh assets history
rcwh assets history --list
rcwh sources trace decision:cliff-release:function
rcwh self-contained check --profile asset-storage
rcwh self-contained check --profile release-storage
```

## 已知缺口

```bash
rcwh self-contained check --profile source-content
rcwh self-contained check --profile source-locators
```

这两项目前返回非零：12 条 bibliography-only Source 尚无本地载体；导入的页码/行号未建立对齐验证。保留这些失败用于推动来源和语料工作，不能把它们改成静默警告后宣称完成。

## 导入与历史记录

一次性交接导入已完成，旧 `assets import-handover` 命令和专用解码器已退役；日常资产解析与验证只读取当前仓库。迁移过程及原始绑定保存在审计报告。

保留的接收清单位于 `archive/imports/handover-20261008/`；首次导入去向见 `artifacts/migration/handover-20261008/import_report.json`。首次导入对未被接收文档或历史 P0 映射引用的旧 baseline/superseded 材料只保留摘要和出处。当前资产与历史规模分别用 `assets summary`、`assets history` 查询；数量是整理结果，不是后续运行约束。

历史版本整理见[执行记录](../reviews/HISTORICAL_ASSET_CLEANUP_20261008.md)与[研究提取笔记](../../research/notes/history-20261008.md)。`data/catalog/history.json` 指向不可变历史包；包内记录原 ID、SHA、出处、别名和相对保留原件的逐行差异。`assets history --list` 从账本生成版本索引；`assets validate` 同时验证所有旧稿的复原 SHA。历史包不授予证据或当前实施权限；`assets resolve` 不接受退役 ID。

旧交接入口、旧状态文件和包内验证脚本已经退役。重复的 TXT 校验清单由保留的 CSV 按原行序精确重建，历史记录用 `SHA256_MANIFEST_CSV` 声明这一复原步骤，再核验原 SHA；无需再存一份完整 TXT。旧排除清单通过 `CSV_PROJECTION` 从路径总表筛选字段和行，保持原顺序、BOM 与换行后核验原 SHA。

```bash
rcwh assets history R4_证据角色审计矩阵_v1.6_R4F_PASS.md
rcwh assets history <完整旧资产ID> --restore-to /tmp/historical.md
```

历史文件名引用通过该显式接口查询；同名多版本须用完整 ID 区分。复原命令只写新文件，不覆盖、不入库或采纳。导入原件和发布清单保留原字节；引用修复新建派生资产，并更新当前运行数据。已有 Git 基线的不可变校验仍拒绝直接删除原资产，本轮精简发生在首次目录提交前。

`registry`、`coverage`、`completion` 旧命令已删除。实体存储使用 `assets validate`，来源追溯使用 `sources trace`，当前进度使用 `project status`；旧 M8 PASS 不构成这些检查的通行证。`object trace`、`literary-ecology trace`、`implementation trace` 直接核验资产字节，接受完整资产 ID，不接受旧文档 ID 或摘要前缀。

## 干净检出与版本保护

```bash
rcwh assets validate --require-tracked
rcwh assets validate --require-tracked --base-ref <previous-commit>
```

工作树中新文件在加入 Git 前会被 `--require-tracked` 拒绝。CI 对当前资产核对字节，并与上一版目录比较，拒绝原 ID 下更换内容。路径移动可保留版本；内容更正创建新 ID。

原始资产不批量转码或转换换行。要规范化则保留原件，登记新的派生资产。

## 独立检出演练

```bash
python tools/verify_foundation_checkout.py
```

工具将待评审工作树物化到临时 Git 仓库，使用自动 CRLF 配置重新 clone，移除交接包可见性，在禁止 socket 连接与 DNS 的 CLI 环境下运行上述检查及匿名包／整书候选导出，并执行 `.github/workflows/validate.yml` 中实际配置的全部校验 shell 步骤，包括预期失败退出码；随后运行全部测试。`workflow_checks` 单独记录 CI 步骤结果。命令检查用 `check_status` 记录是否达到预期退出码；`status` 仅保存命令自身返回的状态，不为描述性摘要补造 PASS。仅使用已经安装的依赖，不修改当前仓库的索引或提交历史。

报告位于 `artifacts/migration/handover-20261008/verification_report.json`，首轮删除记录位于同目录的 `cleanup_report.json`，历史规则清理记录为 `rules_cleanup_report.json`。source-content/source-locators 按实际来源结果记录通过或失败，不要求缺口集合等于旧迁移快照；缺载体应失败，补齐后应允许通过。
