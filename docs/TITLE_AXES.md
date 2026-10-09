# 回目功能与对仗约束

The project distinguishes **what a phrase is evidence for** from **how the reconstruction currently uses it**.

| Class | Meaning | Formal-title authority |
|---|---|---|
| T0 | complete future heading with strong direct witness | strong |
| T1 | partial heading explicitly identified as 正文标目 | partial only |
| T2 | draft label / manuscript call / “X一回” | not enough by itself |
| T2-W2 | weak-transcript chapter call | weak; never self-bearing |
| T3 | event / scene / future descriptive phrase | none |
| TG | generated working heading | none; project output |

## Key examples

### T0

“薛宝钗借词含讽谏，王熙凤知命强英雄” is source-backed as a complete future heading. The current **Chapter 90** placement is not source-backed and remains reversible.

### T1

“花袭人有始有终” is explicitly called a 正文标目. Only that known part is hard. The other half and Chapter 88 placement are reconstruction choices.

### T2

“狱神庙慰宝玉”, “悬崖撒手”, and “误窃” are preserved as manuscript/chapter-call evidence. RCWH rejects the inference:

> critic says “X一回” → therefore X is a formally recoverable original chapter title.

### T3

“凤姐扫雪拾玉”, “甄宝玉送玉”, and “寒冬噎酸虀，雪夜围破毡” constrain future narrative functions, not headings.

### TG

A generated heading can contain evidence-backed words without becoming evidence.

For example:

> 贾宝玉悬崖撒手去　宝钗麝月共守寒家

is TG as a whole, although it embeds the T2 phrase “悬崖撒手”.

## CLI

Use:

```bash
rcwh trace axis:t0:baochai-fengjie
rcwh trace axis:t2:prison-comfort
rcwh trace axis:t3:fengjie-snow-jade
rcwh trace axis:tg:ch99
```

The trace exposes the Source / Claim / Decision / Implementation boundary instead of flattening them into one “evidence level”.
