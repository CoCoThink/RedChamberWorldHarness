# Full Migration M7 — P0 Coverage Audit

Status: **PASS**

M7 performs the exhaustive P0 semantic-coverage audit required before the Completion Gate. It does not modify stable ACTIVE prose and does not resume Chapter 81—100 literary production.

## Frozen audit base

The audit base is the self-contained handover inventory only.

P0 included assets: **249**

Pre-migration machine coverage:

- FULL: 9
- PARTIAL: 105
- MINIMAL: 1
- NONE: 134

Therefore the original P0 gap set was 240 records.

The exact compact P0 audit inventory is preserved in four immutable repository chunks under `data/coverage/p0_inventory.part*.b64`. After decoding and decompression, its canonical JSON SHA256 is:

`77b70c7785235d976fe1f42665be5aef6668b983170259e019454c0b02238247`

The runtime verifies this digest before accepting the coverage census.

## Final P0 result

After M0→M6 semantic migration and the M7 versioned-reference binding audit:

- P0 total: **249**
- effective FULL: **249**
- PARTIAL: **0**
- MINIMAL: **0**
- NONE: **0**
- unresolved P0 gaps: **0**
- concrete self-contained source paths: **249 / 249**

This does not mean every historical/reference Markdown file was copied into a new database as current runtime truth.

M7 uses four explicit coverage modes:

- `DIRECT_CURRENT_RUNTIME`
- `RAW_SOURCE_AUTHORITY`
- `DIRECT_PREEXISTING_RUNTIME`
- `VERSIONED_REFERENCE_BOUND_TO_EFFECTIVE_RUNTIME`

The last mode is essential: historical and reference versions remain traceable source entities, while their effective semantic results bind to the typed runtime produced by M2–M6. They do not regain CURRENT authority.

## P0 layer census

The 249 P0 records remain frozen at the handover layer counts:

- EVIDENCE: 29
- EVIDENCE_LITERARY: 7
- GOVERNANCE: 5
- IMPLEMENTATION: 12
- LITERARY_ECOLOGY: 60
- LITERARY_EVIDENCE: 21
- LOCK: 18
- MECHANISM: 3
- PLANNING: 13
- RECONSTRUCTION: 49
- SOURCE: 2
- WORLD: 22
- WORLD_LITERARY: 8

Authority census:

- REFERENCE: 233
- CURRENT: 14
- SOURCE_AUTHORITY: 2

The P0 audit therefore preserves authority identity instead of flattening all 249 records into CURRENT.

## CURRENT authority closure

The five CURRENT documents that remained PARTIAL after M6 are now fully represented:

- R4 evidence-role audit matrix;
- current operation-chain index;
- R4 activity-chain state;
- stable ACTIVE release manifest;
- master engineering plan v6.0.

CURRENT runtime semantic coverage is now:

- FULL: **15**
- PARTIAL: **0**
- MINIMAL: **0**
- NONE: **0**

CURRENT Markdown-only islands: **0**

Unresolved authority conflicts: **0**

## Semantic binding surfaces

The M7 audit resolves P0 records into the existing typed runtime rather than creating a second truth system.

Major bindings include:

- Evidence → sources / claims / decisions / title axes / literal constraints;
- Governance → M7 project state and validation policy;
- Implementation → M6 frozen-body alignment;
- OPEN → R4 OPEN-LOCK runtime;
- P-Lock → specialized P-Locks plus M6 20-chapter protection table;
- Historical mechanism → H01—H06 mechanism runtime;
- Reconstruction → M2 plus M6 chapter-plan / scene alignment;
- World → M3 plus M4 object continuity where relevant;
- Literary Ecology / Literary Evidence / Planning → M5;
- World-Literary interfaces → World + Literary Ecology + Object runtime;
- Raw sources → immutable source-authority inventory records.

Each P0 source record retains a concrete `01_PRIMARY_SOURCES/`, `02_CURRENT_RUNTIME/`, or `03_VALID_HISTORY/` self-contained path.

## Negative archive

M7 also freezes the negative/archive layer as machine fixtures.

The following cannot regain runtime authority:

- stable ACTIVE v4.0 revoked release;
- invalid Phase3 v1.0;
- invalid Phase6 v1.0;
- invalid Phase7 v1.0 / v1.1;
- rejected five-book / sixty-person Qingbang completion;
- rejected formal-title promotion of “凤姐扫雪拾玉”;
- rejected formal-title promotion of “寒冬噎酸虀 / 雪夜围破毡”;
- rejected formal-title promotion of “甄宝玉送玉”;
- rejected formal-title promotion of “狱神庙慰宝玉”;
- losing Chapter-86 competition drafts and Chapter-89 Phase-1 pressure fixtures.

Negative/archive state has `stable_active_effect = NONE`.

## Query surface

Examples:

`rcwh coverage summary`

`rcwh coverage layer RECONSTRUCTION`

`rcwh coverage target literary.voice_corpus`

`rcwh coverage target world.object_flow.jade`

`rcwh coverage document 4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

`rcwh coverage gaps`

`rcwh coverage regression`

Expected gap result:

`M7 P0 GAPS: 0`

## Full Migration regression

The M7 regression requires all of the following simultaneously:

- P0 249/249 FULL;
- CURRENT 15/15 FULL;
- CURRENT Markdown islands = 0;
- unresolved authority conflicts = 0;
- Reconstruction queryable;
- World queryable;
- Object continuity PASS;
- Literary Ecology queryable;
- Implementation Alignment PASS;
- Evidence Core PASS;
- stable ACTIVE unchanged;
- literature freeze active;
- negative archive non-runtime.

The first complete M7 candidate passed this regression and the full repository suite:

- `rcwh validate`: PASS;
- Coverage query smoke: PASS;
- `rcwh coverage gaps`: 0;
- `rcwh coverage regression`: PASS;
- R4 Evidence Core: PASS;
- Promotion Regression: PASS;
- `STABLE_POINTER_UNCHANGED`: PASS;
- `pytest -q`: **157 passed**.

## M7 / M8 boundary

M7 closes semantic coverage but does **not** sign the Completion Gate.

The following remain intentionally false/pending:

- `coverage_report_signed_off = false`
- `completion_gate_ready = false`
- literature freeze = **active**

M8 owns final coverage signoff, Completion Gate evaluation, release/branch finalization, and the explicit decision whether literary production may resume.
