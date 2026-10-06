# R4 Evidence Core — v0.2-beta

v0.2-alpha established the provenance kernel. v0.2-beta begins importing reviewed R4 evidence into that kernel.

The first batch is deliberately narrow: **T-axis / title-role evidence**.

## Why T-axis first

The most damaging historical failure mode in the project was not usually “missing a clue.” It was upgrading the wrong kind of clue:

- event phrase → formal chapter title;
- draft label → original heading;
- source wording → novel-exact wording;
- current chapter placement → source placement.

The T-axis exists to prevent those promotions mechanically.

## Imported evidence-side classes

- **T0** — complete future heading text with strong direct witness.
- **T1** — partial heading text explicitly called 正文标目.
- **T2** — draft label / manuscript call / critic's “X一回”.
- **T2-W2** — weak transcript-only chapter call. Not imported in this first batch.
- **T3** — event / scene / future phrase without formal-title authority.
- **TG** — project-generated working heading.

## First batch

Evidence-side:
- T0 薛宝钗借词含讽谏，王熙凤知命强英雄
- T1 花袭人有始有终
- T2 狱神庙慰宝玉
- T2 悬崖撒手
- T2 误窃
- T3 凤姐扫雪拾玉
- T3 甄宝玉送玉
- T3 寒冬噎酸虀，雪夜围破毡

Current generated headings are also registered as TG for Chapters 88, 91, 92, 95, 98, and 99.

## Runtime invariants

1. T0 wording may be LOCKED while its current chapter number remains CURRENT/MAY.
2. T1 locks only the witnessed partial heading, not a reconstructed full heading.
3. T2/T3 may never hard-lock formal-title identity.
4. TG has no evidence Claim references.
5. An active heading may embed a T1/T2 fragment without the whole heading inheriting that evidence class.
6. Source → Claim → Decision → Implementation remains the only authority direction.

## Next import batches

1. future exact lines / work titles / future speech;
2. W2 weak witnesses;
3. H01–H06 historical feasibility boundaries;
4. 28 OPEN decisions;
5. full R4 regression against stable ACTIVE prose.
