# Post-M8 Repository Governance Audit — 2026-10-07

Status: **PASS**

This audit is a repository-governance gate after Full Migration M8 and before further Chapter 89/92 literary production.

## Canonical branch topology

Authoritative branches:

- `main` — release authority;
- `literary/43-0-resume` — the only live literary-production line;
- `archive/full-migration-v3-final-20261007` — frozen migration archive;
- `export/full-migration-snapshot-20261006` — immutable export snapshot;
- `export/self-contained-20261006` — immutable self-contained export snapshot.

## Obsolete branches

The following are fully absorbed by `main` and have no unique effective work that needs to remain on a live branch:

- `feature/provenance-kernel-v0.2`
- `feature/r4-evidence-core-v0.2-beta`
- `feature/literary-plock-v0.3-alpha`
- `migration/full-v3`
- `release/post-merge-signoff-v3`

They are marked **safe_delete_when_tool_available**.

The current connector does not expose delete-ref/delete-branch, so this audit does not falsely claim they were deleted.

## Divergent literary fork

`literary/43-0-ch89-phase2`

Frozen audited head:

`69d406034960fc656ec1184425ae788ff18b6182`

Disposition:

`QUARANTINED_NON_RUNTIME / DO_NOT_MERGE`

Reasons:

1. it diverges from the canonical literary line;
2. it contains 25 unique commits that overlap/conflict with the canonical Chapter 89 work;
3. it records Chapter 89 human P-Lock/blind-read/adjudication as complete although those human gates are not independently established in the canonical workflow;
4. it advances Chapter 92 to READY_FOR_CANDIDATES, which is not permitted by the canonical current state;
5. its recent CI runs are failing.

The fork is retained only as an audit source until branch deletion/archival is performed with an administrative tool.

### Salvaged infrastructure

The useful architectural idea from the fork was retained without importing its adjudication:

- a dedicated post-M8 `LiteraryProductionRuntime`;
- a typed literary-resume state schema;
- explicit separation between immutable M8 Completion Gate state and live post-M8 literary production;
- CLI query surface for live literary production and quarantine state.

No forked winner/adjudication artifact was imported as authority.

## Canonical literary state

Current Chapter 89:

- full A/B/C candidates: READY;
- six-field regression: PASS;
- machine literary precheck: PASS;
- manual P-Lock: PENDING;
- real blind read: PENDING;
- adjudication: PENDING;
- winner: none.

Chapter 92 and Chapter 97 remain:

`BLOCKED_BY_PREDECESSOR`

Stable ACTIVE remains unchanged:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

## Issue audit

Closed as completed after M8:

- #1 — Import R4 evidence matrix and OPEN-LOCK state;
- #2 — Build provenance-backed source registry.

Retained as genuine partial work:

- #3 — Character knowledge graph and voice profiles;
- #4 — Historical mechanism adapter interface;
- #5 — Literary evaluator suite;
- #6 — Automate v5.0 steps 33–42.

Each retained issue now contains a post-M8 comment separating completed scope from residual acceptance gaps.

## Query surface

`rcwh literary-production summary`

`rcwh literary-production chapter 89`

`rcwh literary-production quarantine`

## Validation

Canonical branch validation at commit `3ba5c5a968e824f038f49edf0ac676cf8cf1e177`:

- Full Migration Completion Gate: PASS;
- post-M8 literary-production runtime: PASS;
- repository literary quarantine: PASS;
- stable pointer unchanged: PASS;
- pytest: **181 passed / 0 failed**.

No literary adjudication or Chapter 92 production was performed during this repository-governance audit.
