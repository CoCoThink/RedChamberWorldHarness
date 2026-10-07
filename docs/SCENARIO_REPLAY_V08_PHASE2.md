# Scenario Replay v0.8 — P2 Counterfactual World Replay

Status: **PASS / SHADOW_ONLY**

P2 turns the P1 scenario bundles into executable counterfactual world states without modifying canonical M3, R4 Evidence, OPEN, stable ACTIVE, or Chapter 89 literary adjudication.

## Runtime equation

`M3 current-world baseline + hypothesis deltas = scenario replay`

The M3 baseline is used as a **reference implementation surface only**. It is not a prior probability and receives no search bonus.

## What is replayed

All ten P1 seed scenarios are replayed chapter-by-chapter across 81–100. Hypothesis deltas can alter only scenario-local state:

- marriage phase;
- Jia-mu life/authority scenario;
- post-confiscation residence;
- detention causal annotation;
- Fengjie protection-capacity state;
- snow-jade and sent-jade identity assumptions;
- Miaoyu Guazhou W2 route;
- Zhen Baoyu encounter mode;
- Chapter 99/100 Baoyu-departure distribution.

Scenario-local locations are explicitly namespaced as `SCN-LOC-*` and never enter canonical M3.

## Hard conflict detectors

P2 emits blockers for:

- `TIMELINE_CONTRADICTION`;
- `RESOURCE_IMPOSSIBILITY`;
- `OBJECT_TELEPORTATION`;
- `RELATION_STATE_CONFLICT`;
- `KNOWLEDGE_LEAK`;
- invalid scenario-local location references.

Historical burden, mourning burden, W2 dependence, object-chain complexity and terminal chapter capacity are emitted as **PRESSURE**, not as Evidence and not as automatic rejection.

## Invariants

- current-C replay must be bit-for-bit equal to M3 world snapshots;
- no replay may change Evidence or close OPEN;
- no replay writes stable ACTIVE;
- no replay decides Chapter 89;
- no single total score;
- no automatic winner.

P2 PASS requires all ten curated P1 seed scenarios to replay without hard blockers. Pressure is allowed and is intentionally preserved for P3 Pareto evaluation.

## Final P2 gate

Result: **PASS**.

Validation run: `37638097185`

- `rcwh validate`: PASS;
- full repository tests: **246 passed / 0 failed**;
- all 10 P1 seed scenarios replayed across chapters 81–100;
- hard replay blockers: **0**;
- current-C replay equals canonical M3 snapshots exactly;
- PRESSURE findings remain non-authoritative inputs for P3;
- stable ACTIVE unchanged;
- Chapter 89 remains `IN_REVIEW` with manual P-Lock / independent blind read still pending;
- Chapters 92 / 97 remain blocked by predecessor.

Next gate: **P3_PARETO_EVALUATION**.
