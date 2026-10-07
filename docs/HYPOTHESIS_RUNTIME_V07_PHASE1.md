# Hypothesis / Scenario Runtime v0.7 — Phase 1 Core OPEN Expansion

Status: **PASS / SHADOW_ONLY**

Phase 1 expands the H04 proof-of-concept into a book-level reconstruction search surface while leaving the canonical 43-0 literary pipeline untouched.

## Core OPEN coverage

At least two explicit admissible alternatives are now represented for ten structural OPEN interfaces:

- OL-005 — 金玉婚相位（G0/G1/G2）；
- OL-007 — 贾母/主婚权状态（O09-A/B/C）；
- OL-009 — 抄没后居所；
- OL-012 — 宝玉羁押因果接口；
- OL-014 — 凤姐无法保护巧姐的状态；
- OL-011 — 扫雪拾玉同一性；
- OL-018 — 妙玉瓜州 W2 是否采用；
- OL-020 — 甄贾二宝是否现实照面；
- OL-021 — 甄宝玉所送之玉同一性；
- OL-023 — 99→100 悬崖撒手/情榜分工。

These hypotheses remain downstream. They do not close the underlying OPEN interface.

## Scenario bundles

Ten curated seed bundles are provided, including:

- current-C reference with no search/evidence bonus;
- G0 early-marriage route;
- G2 late-marriage route;
- Jia-mu-dead-before-marriage route;
- single-jade chain;
- multi-layer jade chain;
- Fengjie-alive-but-powerless route;
- Miaoyu Guazhou W2 pressure route;
- compact Chapter-100 terminal route;
- minimum-commitment detention/jade route.

P1 does not replay World State yet. Every scenario therefore carries:

`world_replay.status = PENDING_P2`

and every Pareto axis remains:

`UNASSESSED`

## Search discipline

- no single total score;
- no automatic winner;
- current-C is only one scenario and receives no search priority;
- a scenario may not close OPEN;
- mutually exclusive hypotheses may not co-occur;
- W2 remains weak support only;
- no scenario may modify stable ACTIVE or Chapter 89 adjudication state.

## P1 gate

Result: **PASS**.

Gate validation run: `37631350784`

- ten core OPEN interfaces have >=2 alternatives: PASS;
- admissible scenario bundles: **10**;
- current-C has no search/evidence/baseline-convenience bonus: PASS;
- hypothesis/scenario schema validation: PASS;
- `rcwh validate`: PASS;
- full repository tests: **237 passed / 0 failed**;
- canonical Chapter 89 remains `IN_REVIEW`, with manual P-Lock and real blind read still pending;
- Chapters 92 / 97 remain blocked by predecessor;
- stable ACTIVE remains unchanged.

Next gate: **P2_COUNTERFACTUAL_WORLD_REPLAY**.
