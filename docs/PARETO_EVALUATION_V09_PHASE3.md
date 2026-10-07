# Pareto Evaluation v0.9 — P3 Multi-axis Scenario Comparison

Status: **PASS_CANDIDATE / SHADOW_ONLY**

P3 compares the ten P1/P2 scenario bundles without collapsing reconstruction quality into a single score.

## Eight axes

The runtime uses eight axes:

1. **evidence_fit** — minimize extra commitment beyond hard interfaces;
2. **contradiction_risk** — minimize P2 pressure count;
3. **open_consumption** — minimize scenario-level consumption of OPEN detail;
4. **historical_cost** — minimize mechanism burden from hypothesis metadata;
5. **world_coherence** — minimize P2 pressures that directly affect resources, objects, residence, legal mechanics or W2 route continuity;
6. **chapter_economy** — minimize extra scene/chapter load;
7. **front80_structural_echo** — maximize an explicitly heuristic 1–5 structural-echo grade grounded in Literary Ecology dimensions;
8. **literary_fertility** — maximize an explicitly heuristic 1–5 scene-generation grade.

The last two axes are **HEURISTIC_NOT_EVIDENCE**. They may guide scenario search, but they cannot change Evidence, close OPEN, or promote prose.

## No scalar winner

Dominance is Pareto dominance only:

> A dominates B iff A is no worse on every selected axis and strictly better on at least one.

There is no weighted sum, no average score, no hidden baseline bonus and no automatic winner.

P3 exposes two frontiers:

- **mechanism frontier** — six non-literary axes;
- **full frontier** — all eight axes.

The overlap is the robust frontier; adding the two literary heuristics must remain auditable.

## Authority boundary

P3 is downstream of Evidence → OPEN → Hypothesis → Scenario → Replay. It writes no canonical world state, no stable prose, and no Chapter 89 adjudication state.

Before PASS, repository validation and full CI must succeed.

Next gate after PASS: **P4_SCENARIO_LITERARY_STRESS_TEST**.
