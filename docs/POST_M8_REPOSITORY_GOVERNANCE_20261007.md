# Post-M8 Repository Governance Audit — 2026-10-07

Status: **ACTIVE / CLEAN**

This document is the current repository-governance view after Full Migration M8 and completion of Issues #1–#6. Historical milestone documents remain audit records, but they are not current operational instructions.

## Canonical authority

- `main` — release authority.
- `literary/43-0-resume` — only live literary-production line.
- `archive/full-migration-v3-final-20261007` — frozen M8 archive.
- `export/full-migration-snapshot-20261006` and `export/self-contained-20261006` — immutable export history.

## Obsolete branches

The following are fully absorbed or otherwise non-current and are safe to delete when an administrative branch-delete tool is available:

- `feature/provenance-kernel-v0.2`
- `feature/r4-evidence-core-v0.2-beta`
- `feature/literary-plock-v0.3-alpha`
- `migration/full-v3`
- `release/post-merge-signoff-v3`

## Quarantined divergent fork

`literary/43-0-ch89-phase2`

Frozen audited head:

`69d406034960fc656ec1184425ae788ff18b6182`

Disposition:

`QUARANTINED_NON_RUNTIME / DO_NOT_MERGE`

Its Chapter 89 adjudication, blind-read claim, and Chapter 92 advancement are not authority. Only reviewed infrastructure ideas were reimplemented on the canonical branch.

## Completed issue audit

All repository issues #1–#6 are complete:

1. R4 evidence matrix / OPEN-LOCK state.
2. Provenance-backed source registry.
3. Character knowledge graph and voice profiles.
4. Historical mechanism adapter interface.
5. Literary evaluator suite.
6. v5.0 Steps 33–42 prewrite automation.

No issue remains open in the current governance registry.

## Current literary gate

Chapter 89 is still the active literary gate:

- full A/B/C candidates: READY;
- six-field regression: PASS;
- machine literary precheck: PASS;
- manual P-Lock: PENDING;
- real blind read: PENDING;
- adjudication: PENDING;
- winner: none.

Chapter 92 and Chapter 97 remain:

`BLOCKED_BY_PREDECESSOR`

Issue #6 prewrite automation is staging-only and does not change this gate.

## Stable ACTIVE

Stable ACTIVE remains unchanged:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

No current governance or automation layer may overwrite stable ACTIVE without a separate explicit promotion path.

## Current operational next step

Do not reopen migration work and do not treat prewrite staging as evidence.

The next literary action is:

`CH89_MANUAL_PLOCK_THEN_REAL_BLIND_READ`

Only after Chapter 89 is genuinely adjudicated may Chapter 92 leave `BLOCKED_BY_PREDECESSOR`.

## Current machine capabilities

The canonical branch now contains runnable layers for:

- provenance / R4 Evidence Core / OPEN-LOCK;
- Reconstruction and World State;
- object network;
- Literary Ecology;
- Character Truth and scene knowledge;
- historical feasibility adapters;
- literary evaluator suite;
- competition / P-Lock / blind-read separation;
- v5.0 Steps 33–42 prewrite staging.

The v0.6 prewrite harness remains:

`authority = STAGING_ONLY`

`evidence_effect = NONE`

`stable_active_effect = NONE`

`automatic_prose_generation = false`

`automatic_promotion = false`

## Documentation authority rule

Current operational truth should be taken from machine data/runtime plus the newest issue-completion documents. Versioned older design documents and migration milestone notes are audit history only.

Superseded standalone documents that duplicated current machine state have been removed from the live docs tree before the self-contained handover package was built.
