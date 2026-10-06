# Changelog

## 0.2.0-beta.6

- Added executable final R4 Evidence Core regression and release manifest.
- Added exact release-shape checks for sources, claims, decisions, implementations, T-axis, literals, H01-H06, and all 28 OPEN-LOCK interfaces.
- Added stable-ACTIVE SHA enforcement across every ACTIVE provenance implementation.
- Final preflight repaired two gaps: Chapter 86 HARD evidence now has a real Source, and Chapter 92 detention/Xiaohong/Qianxue hard interfaces are first-class LOCKED Decisions.
- Added `rcwh regression`.
- Final R4 Evidence Core regression: PASS.


## 0.2.0-beta.5

- Imported the full R4 28-item OPEN-LOCK registry as OL-001..OL-028.
- Added OPEN_LOCKED as a reviewed uncertainty state distinct from PENDING.
- Added machine checks that OPEN decisions remain OPEN/OPEN and current reconstruction choices remain CURRENT/MAY.
- Linked OPEN interfaces to hard anchors, literal constraints, H01-H06 mechanisms, and stable-ACTIVE implementations where available.
- Added anti-hardening tests for Chapter 91 jade identity, Qingbang formal title, Miaoyu W2 Guazhou, and whole-book PC/TG placement.
- Added `rcwh open OL-001..OL-028`.


## 0.2.0-beta.4

- Added H01–H06 historical-feasibility mechanisms from the R4-E review.
- Added HISTORICAL_FEASIBILITY claim authority and FEASIBILITY_ONLY mechanism semantics.
- Added primary-source records for Qing prison rules, mourning/marriage law, imperial-consort mourning, Cao-family confiscation/pawn/housing records, and a 1774 Beijing-region rental contract.
- Added H06 as SECONDARY_SOFT using Mao Liping's Nanbu County archive study.
- Added a hard anti-promotion rule: historical feasibility may not silently support narrative reconstruction Decisions.
- Locked historical boundaries, if introduced later, may compile only to MUST_NOT, never positive plot MUST.
- Added `rcwh mechanism H01..H06`.


## 0.2.0-beta.3

- Added W2 weak-witness handling for Mao Guoyao's Jingcang transcriptions.
- Imported 对景悼颦儿、芸哥仗义探庵、狱庙相逢、妙玉瓜州渡口、证前缘、观警幻情榜.
- Added W2-only lock-bearing prohibition: weak transcript Claims cannot independently support LOCKED Decisions.
- Added T2_W2 machine validation using “证前缘回” as the first weak chapter-call case.
- Added source/transmission checks for EARLY_TRANSCRIPT ↔ W2_TRANSCRIPT.
- Kept Qingbang hard constraints independent from W2 corroboration.


## 0.2.0-beta.2

- Added the R4 literal-target / V-axis contract.
- Added machine validation for NOVEL_EXACT, NAME_EXACT, SOURCE_EXACT, SEM, BOUNDARY, and NEG.
- Imported exact constraints for 《十独吟》, “落叶萧萧，寒烟漠漠”, “好歹留着麝月”, “情情”, and “情不情”.
- Imported “警幻情榜” as SOURCE_EXACT only, explicitly preventing automatic prose-title promotion.
- Added the post-Xiren-marriage boundary for “好歹留着麝月”.
- Added rcwh literal <id>.

## 0.2.0-beta.1

- Began R4 Evidence Core import with the T-axis.
- Added Evidence Role, Modality, Literal Target, and T-axis metadata to provenance claims.
- Added W1_DIRECT / W1_SEEN / W2_TRANSCRIPT / EDITORIAL source tiers.
- Added machine-validated T0/T1/T2/T2-W2/T3/TG title-axis records.
- Added active title implementations for Chapters 88, 90, 91, 92, 95, 98, and 99.
- Added regression rules blocking T2/T3 → hard formal-title promotion.
- Registered project-generated headings as TG with zero evidence authority.

## 0.2.0-alpha

- Added the Source → Claim → Decision → Implementation provenance kernel.
- Added five R4 provenance canaries.
- Added rcwh trace in both forward and reverse directions.
- Separated witness identity from modern source container.
- Replaced ambiguous evidence_proven with all-basis fully_source_backed.
- Separated Decision status from runtime constraint polarity.
- Added minimal resolvable Implementation nodes.
- Added duplicate-source fingerprint checks.

## 0.1.0

- Initial harness kernel.
