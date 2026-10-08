# R4-F Regression｜R4-G候选正文回归 v1.2 FINAL
## ——PASS

> 候选正文：`第32-A_红楼梦八十回后文学复原_纯读版_v1.4_R4G候选回归版.md`  
> SHA256：`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

# 0. 检查器纠偏记录

本轮保留两次自动检查误报的审计轨迹：

1. v1.0把“**不是我们想见就见的**”误判成自由探视；实际语义正相反。
2. v1.1检查情榜五层时误用“正册/副册”，而当前正文实际采用：
   `正层 / 副层 / 再副层 / 三副 / 四副`。

两次均属于检查器字段/匹配错误，不是正文回归失败。

本v1.2改用与当前正文实际结构一致的检查字段。

# 1. Literal

以下硬原字全部仍在：
- 第90 T0完整两联；
- `花袭人有始有终`；
- `落叶萧萧，寒烟漠漠`；
- `好歹留着麝月`；
- `十独吟`；
- `情情`；
- `情不情`。

> **LITERAL PASS**

# 2. Semantic

第92-B：
- 狱神庙：PASS
- 小红“大得力”：PASS
- 茜雪回流：PASS
- 普通释放：PASS

第97-B：
- 烟味水：PASS
- 灯油/米油“有数”：PASS
- 白瓷盆由专用进入共用：PASS

第100-B：
- 正层 / 副层 / 再副层 / 三副 / 四副：PASS
- 石归青埂峰：PASS
- `石在，字在。`：PASS

> **SEMANTIC PASS**

# 3. Boundary

- 第92没有自由/当然探监权：PASS
- “不是我们想见就见的”明确属于限制句：PASS
- 第97无瓜州：PASS
- 第97无渡口：PASS
- 第100无`警幻情榜`正式榜名：PASS
- 第100无60人：PASS
- 第100无五册：PASS
- 第100仍写“并无总题”：PASS
- `对景悼颦儿 / 仗义探庵 / 狱庙相逢`均未长回正文：PASS

> **BOUNDARY PASS**

# 4. 非目标区完整性

- 81—91：PASS
- 93—96：PASS
- 98—99：PASS

> **NON-TARGET TEXT INTEGRITY PASS**

# 5. 总结论

- Literal：PASS
- Semantic：PASS
- Boundary：PASS
- 非目标区完整性：PASS

> # **R4-F REGRESSION PASS**

`RG-FREG-01 = CLOSED`

当前只剩：
- `RG-GFINAL-01`
- `RG-HFINAL-01`

下一动作：

> **R4-G v2.0｜无WATCH最终文学终审**
