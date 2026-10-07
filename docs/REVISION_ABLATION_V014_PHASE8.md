# Cross-route Revision Ablation v0.14 — P8

Status: **PASS / SHADOW_ONLY**

P8 takes the P7 blind-review findings as revision controls rather than route-selection evidence.

All twenty P6 microdrafts receive a paired revision. Every pair keeps the same scenario, P4/P5 probe, chapter-window cell and P5 primary focalizer. P8 is not permitted to change fabula, close OPEN, rebind the route, or turn an experimental revision into canonical prose.

The ablation asks one narrow question:

> Can the literary defects identified by the blind reviewer be reduced without changing the underlying reconstruction route?

The treatment applies RT-01..RT-09 from P7: remove named omissions; reduce convenient interruptions; stop using unopened packages as generic suspense; strengthen relation-specific voices; concentrate scene weight in one action / practical sentence / irregular material fact; and repair the route-specific ledger tendencies of multi-layer jade, minimal-cause-open, late marriage and current-C.

Machine evaluation is deliberately modest. It checks pair binding, anchor preservation (with explicit lexical equivalence where wording itself was the problem), existing literary-suite hard blockers, and whether P7 anti-pattern terms increase or decrease. It does not claim a revision is better literature.

The five drafts P7 identified as most engineered must show strict anti-pattern reduction. Every other pair must at least avoid regression.

Next gate after PASS: **P9_PAIRED_BLIND_REVISION_REVIEW**. P9 should blind the revised texts again and ask an independent reviewer whether the treatment improved literary quality in practice.


## Final P8 gate

Result: **PASS**.

Gate validation run: `37659740928`

- `rcwh validate`: PASS;
- full repository tests before state-close test: **301 passed / 0 failed**;
- revision pairs: **20/20 ABLATION_READY**;
- pair blockers: **0**;
- P7 anti-pattern hits: **23 → 0** under the explicit v0.14 detector;
- the five P7 most-engineered drafts all show strict reduction;
- route / probe / cell / P5 focalizer binding drift: **0**;
- existing literary-suite hard rejects on revised texts: **0**;
- baseline P6 artifacts remain unchanged;
- route winner / elimination / superiority claim: **NONE**;
- Evidence / OPEN / stable ACTIVE / canonical prose effects: **NONE**.

The 23→0 figure is an ablation instrumentation result, not a literary score. It proves only that the specific P7 failure signatures were removed from the paired revisions. Whether the revisions are actually better prose remains reserved for a fresh paired blind review.

Next gate: **P9_PAIRED_BLIND_REVISION_REVIEW**.
