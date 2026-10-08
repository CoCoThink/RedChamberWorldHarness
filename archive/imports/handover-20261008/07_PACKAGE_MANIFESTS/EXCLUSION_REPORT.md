# Exclusion Report

本报告记录本次导出中**主动不进入最终包**的内容。原则：删除冗余/错误入口，不破坏独立历史证据。

| 路径/来源 | 类别 | 原因 |
|---|---|---|
| `01_CURRENT_REPOSITORY/.github/workflows/export_current_repo.yml` | `EXPORT_ONLY_TEMP` | Temporary workflow used solely to export current main; not present on main. |
| `00_从这里开始/SHA256SUMS.txt` | `SUPERSEDED_MANIFEST` | Old package checksum manifest superseded by this handover package manifest. |
| `05_HANDOVER_AND_INVENTORY/00_CURRENT_REPOSITORY_STATE_v4.0.json` | `SUPERSEDED_HANDOVER_STATE` | Superseded by 2026-10-08 handover/current-state files. |
| `05_HANDOVER_AND_INVENTORY/03_PACKAGE_POLICY_v4.0.json` | `SUPERSEDED_HANDOVER_STATE` | Superseded by 2026-10-08 handover/current-state files. |
| `00_HANDOVER_SELF_CONTAINED_v4.0(2).md` | `SUPERSEDED_HANDOVER` | Replaced by this handover document. |
| `RCWH_SelfContained_Handover_v4.0_20261007(1).zip` | `SOURCE_CONTAINER_NOT_NESTED` | Useful contents extracted; ZIP itself omitted. |
| `红楼梦探佚_截至第32步_v5.0启动前_精简过程文档体系_v2.0(3).zip` | `SOURCE_CONTAINER_NOT_NESTED` | Useful contents extracted; ZIP itself omitted. |
| `RedChamberWorldHarness_main_snapshot.zip` | `SOURCE_CONTAINER_NOT_NESTED` | Repository tree extracted; ZIP itself omitted. |
| `image(1).png` | `OUTDATED_SCREENSHOT` | Outdated branch-list screenshot; no unique research content. |
| `rcwh_phase0_work/` | `REDUNDANT_SCRATCH_TREE` | Partial scratch repository files superseded by 01_CURRENT_REPOSITORY. |

## 说明

- 输入的三个 ZIP（旧 self-contained、截至第32步包、GitHub Actions repo snapshot）都只作为构建容器，最终包不嵌套它们。
- 旧 self-contained 的旧 handover、旧 repo 快照、旧 manifest 不再保留；有价值的 CURRENT/VALID_HISTORY/Inventory 已抽取。
- 历史版本若 SHA 不同且有独立审计意义，继续保留，但不代表 CURRENT。
- Step32 v2 本身已经做过一次“冗余、错误、过期内容”清理；本次不恢复其已排除的中间正文、重复 ZIP、临时缓存和旧禁写治理。
