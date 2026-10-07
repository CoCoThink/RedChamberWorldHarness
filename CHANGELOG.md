# Changelog

## 0.3.0-alpha.8

- Started the real 43-0 Chapter 89 pressure test while retaining stable ACTIVE v1.4 as the common baseline.
- Added an exact early-confiscation pressure excerpt and a whole-chapter functional map.
- Identified the primary risk as repeated rule demonstration before relocation, not historical infeasibility.
- Added B light-compression and C strong-compression lower-bound trials.
- Kept the Chapter 89 P1 ending and the shared-well / small-stove / cart-cost / labor-cost domestic mechanisms outside the Phase 1 edit zone.
- Advanced Chapter 89 through BASELINE_EXCERPT, STRUCTURAL_REORDER, and SMALL_TRIAL only.
- Chapter 86 B remains a deferred promotion-regression PASS candidate; stable ACTIVE remains unchanged.


## 0.3.0-alpha.7

- Embedded the adjudicated Chapter 86 B winner into a complete 81–100 promotion candidate.
- Added explicit promotion regression with competition eligibility, stable-baseline identity, 20-chapter structure, per-chapter non-target integrity, R4-F sentinels, frozen Evidence Core, P-Lock, and stable-pointer checks.
- Verified the allowed diff set is exactly Chapter 86; Chapters 81–85 and 87–100 retain their stable-v1.4 chapter SHA256 values.
- Promotion regression PASS does not mutate stable ACTIVE; a separate explicit release action is still required.
- Added `rcwh promotion promotion:ch86:b:v1-5-candidate`.


## 0.3.0-alpha.6

- Froze the independent Chapter 86 blind review before candidate mapping was revealed.
- Blind results: BR-41 PASS, BR-73 PASS, BR-26 PASS (edge).
- Revealed mapping after freeze: BR-41=A, BR-73=B, BR-26=C.
- Adjudicated Chapter 86 as WINNER-B / REVISE-B because BR-73 was explicitly judged the best balance of illness-day texture and pacing.
- Marked ch86-B as PROMOTION_CANDIDATE only; stable ACTIVE remains unchanged.
- Advanced Chapter 89 to READY_FOR_CANDIDATES while Chapters 92 and 97 remain blocked.
- Closed Issue #10 and stopped the no-longer-needed blind-review monitor.


## 0.3.0-alpha.5

- Promoted the Chapter 86 Phase 1 trials into three full-chapter production candidates.
- Added immutable candidate identity for A/B/C using Git blob SHA and source commit.
- Completed candidate-level six-field regression: A/B/C all PASS without changing upstream evidence identity.
- Completed Chapter 86 human P-Lock regression: A/B/C all retain the protected floor; C is flagged for literary-cleanliness risk rather than falsely failed by the lock layer.
- Added a full anonymous blind-read packet under BR-41 / BR-73 / BR-26.
- Kept blind read honestly PENDING because no independent reviewer has yet reviewed the anonymized packet.
- Stable ACTIVE remains unchanged and no candidate is adjudication-eligible.


## 0.3.0-alpha.4

- Started the first real 43-0 production run on Chapter 86.
- Added an exact stable-baseline pressure excerpt for the afternoon-to-late-arrival segment.
- Added a functional structure map identifying A4-A6 illness/logistics density as the primary pressure point.
- Added B light-compression and C strong-compression trial variants as separate artifacts.
- Advanced the Chapter 86 production ledger through BASELINE_EXCERPT, STRUCTURAL_REORDER, and SMALL_TRIAL.
- Kept six-field regression, P-Lock regression, blind read, adjudication, and promotion pending.
- Stable ACTIVE prose remains unchanged.


## 0.3.0-alpha.3

- Added the Competition / Review Ledger for 43-0 pressure tests.
- Frozen the production order at Chapters 86 → 89 → 92 → 97 with only Chapter 86 initially active.
- Added auditable candidate identity using repository path + Git blob SHA + source commit or stable-ACTIVE file/SHA.
- Added exact candidate six-field gates: Provenance, Role, Modality, Target, Placement, Implementation.
- Added explicit human P-Lock and blinded-read gates.
- A machine-ready candidate is never automatically adjudication-eligible.
- A winner can only become PROMOTION_CANDIDATE; competition records can never overwrite stable ACTIVE.
- Added a non-production Chapter 86 fixture demonstrating READY / REPLACEMENT / REJECT paths.
- Added `rcwh competition <id>`.


## 0.3.0-alpha.2

- Added the first Candidate Literary Evaluator.
- Added non-numeric candidate states: READY_FOR_BLIND_READ, REPLACEMENT_CASE, REJECT_BEFORE_BLIND_READ, and INFRASTRUCTURE_BLOCKED.
- Added protected P1 anchor checks, including terminal-position checks.
- Added narrow explicit-drift blockers and diagnostic feature-signal groups for Chapters 86, 89, 92, 97, and 100.
- Added observation-only term counts so procedural or interpretive vocabulary can be surfaced without fake scoring.
- Every evaluation explicitly keeps automatic_literary_pass=false and promotion_eligible=false.
- Added multi-candidate `rcwh literary-evaluate` CLI for A/B/C pressure-test workflows.


## 0.3.0-alpha.1

- Began the Literary Harness on top of the frozen v0.2 R4 Evidence Core.
- Added a downstream P-Lock registry with zero evidence authority.
- Imported five high-risk literary protection locks for Chapters 86, 89, 92, 97, and 100.
- Added current P1 anchors for the Chapter 86 cold-medicine ending, Chapter 89 water-bucket ending, Chapter 97 dialogue boundaries, and Chapter 100 “石在，字在。” ending.
- Added anti-reverse-promotion validation: Decisions may never use P-Locks as evidence.
- Kept the complete v0.2 R4 Evidence Core regression green and unchanged.
- Added `rcwh plock <id>`.


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
