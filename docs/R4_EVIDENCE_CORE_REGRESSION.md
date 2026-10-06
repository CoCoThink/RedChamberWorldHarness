# R4 Evidence Core final regression — v0.2-beta.6

## Result

**FINAL PASS**

Stable ACTIVE prose baseline:

- file: `第32-A_红楼梦八十回后文学复原_纯读版_v1.4_稳定ACTIVE基线.md`
- SHA256: `4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

## Preflight findings corrected before PASS

The final regression was not treated as a ceremonial green check. Two provenance gaps were found and repaired first.

### 1. Legacy Chapter 86 HARD evidence had no source reference

The v0.1 compatibility evidence record `CH86_DAIYU_DEATH_DIRECTION` still had:

`source_ref: null`

It is now linked to a first-class source node based on the Jimao Chapter 18 comment:

`《离魂》……伏黛玉死……乃通部书之大过节、大关键。`

The hard Daiyu-death direction is also represented in the main Source → Claim → Decision → Implementation graph.

### 2. Chapter 92 R4 hard interfaces were not yet first-class Decisions

The governing R4 release says Chapter 92 hard-locks:

- detention / 狱神庙 function;
- Xiaohong's later “大得力” function;
- Qianxue return.

Before the final regression these were partly present only as title evidence, historical implementation, or prose summary.

They are now explicit provenance nodes:

- `decision:prison:baoyu-interface`
- `decision:xiaohong:great-help`
- `decision:qianxue:prison-return`

with W1 source backing and stable-ACTIVE implementation locators.

## Release-shape snapshot

- Sources: 32
- Claims: 72
  - SUPPORTED: 42
  - NOT_ESTABLISHED: 30
- Decisions: 53
  - LOCKED: 18
  - CURRENT: 14
  - OPEN: 21
- Implementations: 28
- T-axis records: 15
- Literal constraints: 6
- Historical mechanisms: 6
- OPEN-LOCK interfaces: 28

Source types:

- EARLY_COMMENT: 14
- EARLY_TRANSCRIPT: 6
- HISTORICAL_PRIMARY: 11
- SECONDARY_RESEARCH: 1

## Gates

The executable regression runs ten release gates:

1. **PROVENANCE**
   - supported graph integrity;
   - no duplicate provenance fingerprint;
   - all legacy HARD evidence has a resolvable Source;
   - EARLY_COMMENT sources have W1 tier.

2. **ROLE_T_AXIS**
   - exact T0/T1/T2/T2_W2/T3/TG release map.

3. **MODALITY_W2**
   - six W2 transcript sources;
   - W2-only claims are TRANSCRIPT_WEAK;
   - no LOCKED Decision can rest on W2-only basis.

4. **LITERAL_TARGET**
   - exact six literal constraints;
   - SOURCE_EXACT cannot become required prose;
   - NAME_EXACT/NOVEL_EXACT retain implementation requirements.

5. **PLACEMENT_CURRENT**
   - all 14 implementation/placement choices remain CURRENT/MAY.

6. **IMPLEMENTATION_STABLE_ACTIVE**
   - all ACTIVE implementation locators point to the same stable-v1.4 file and SHA.

7. **SEMANTIC_HARD_ANCHORS**
   - all 18 LOCKED Decisions are fully source-backed and lock-eligible.

8. **BOUNDARY_OPEN_LOCK**
   - exactly OL-001..OL-028;
   - 21 OPEN Decisions remain OPEN/OPEN;
   - current choices do not harden.

9. **HISTORICAL_H01_H06**
   - H01 PASS-WITH-CAUTION;
   - H02 PASS;
   - H03 PASS-BOUNDARY;
   - H04 PASS;
   - H05 PASS;
   - H06 PASS-SOFT;
   - historical feasibility remains non-narrative.

10. **RELEASE_SHAPE**
    - exact node and status counts match the release manifest.

## Command

```bash
rcwh regression
```

A release-ready branch must print:

`R4 EVIDENCE CORE REGRESSION: PASS`

and every gate must be PASS.

## Scope boundary

This is the final regression for the **R4 Evidence Core**.

It does not claim that literary P-Locks, world simulation, character voice, object continuity, or the full 43–52 literary production pipeline have been fully machine-imported. Those belong to later RCWH infrastructure layers.

The Evidence Core's responsibility is narrower and now frozen:

> source provenance, evidence role, modality, literal target, placement authority, historical feasibility, weak-witness limits, OPEN uncertainty, and stable implementation traceability.
