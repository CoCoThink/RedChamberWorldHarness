# Issue #4 — Historical Mechanism Adapter Interface v0.4

Status: **PASS**

Issue #4 converts historical/life-process constraints into a reusable scene-evaluation interface while preserving the project rule that historical feasibility never becomes plot evidence.

## Acceptance implemented

The required adapters are defined:

- `medical`
- `household_economy`
- `mourning_marriage`
- `detention`
- `pawnshop`
- `transport_letters`
- `monastic_economy`

A compatibility adapter for the already-used Chapter 89 scene is also retained:

- `confiscation`

Every adapter is locked to:

- `effect = FEASIBILITY_ONLY`
- `plot_authority = NONE`
- `may_create_events = false`

An adapter may reject an implementation as infeasible or overclaimed. It may not create a scene event, choose a plot outcome, close an OPEN question, or promote historical feasibility into Evidence Truth.

## Authority classes

The interface deliberately distinguishes three support classes.

### H-backed

These directly inherit boundaries from existing H01—H06:

- detention → H01
- confiscation → H02
- mourning/marriage → H03 + H04
- pawnshop → H05
- household economy → H05 plus material-life references

For every H-backed adapter, all source mechanism `open` and `cannot_prove` entries are preserved in the effective adapter output.

### Boundary profile

`medical` is implemented as a feasibility boundary profile using the existing body/medicine literary-life material. It is not represented as a new H01—H06 hard historical conclusion.

It can require a scene to contain an operational medicine/care chain and reject explicit historical overclaim. It cannot prove a unique diagnosis, prescription, dosage, doctor timetable, or lost-manuscript wording.

### OPEN research profiles

The current project materials do not establish a comparable H01—H06 hard mechanism for:

- `transport_letters`
- `monastic_economy`

They are therefore defined as `OPEN_RESEARCH`, not silently upgraded.

Their scene result is `PASS_WITH_OPEN` when no overclaim is detected. OPEN questions remain attached to the structured finding.

This gives future scenes a typed interface without pretending the historical research is already complete.

## Structured scene findings

Scene contracts can now declare:

`historical_adapters`

and optional:

`historical_adapter_requirements`

Each adapter returns machine-readable fields including:

- adapter ID;
- PASS / PASS_WITH_OPEN / FAIL;
- reason;
- support class;
- research status;
- H mechanism refs;
- required signal groups and hits;
- missing signal groups;
- historical-overclaim hits;
- effective OPEN questions;
- cannot-prove boundaries;
- `plot_authority = NONE`.

The ordinary `rcwh evaluate` pipeline exposes these findings under evaluators such as:

`historical_adapter:medical`

and:

`historical_adapter:household_economy`.

## Chapter 86 first implementation

`ch86_last_night` is the first concrete adapter implementation, as required by Issue #4.

It now runs:

- medical;
- household_economy.

The medical adapter requires both a medicine/care signal and an active warming/heating/care-process signal.

The household adapter requires both ordinary material-life infrastructure and a concrete care/labor action.

The existing Chapter 86 B candidate passes both adapters.

The adapter regression also proves two negative cases:

1. a scene with no medical/domestic process signals fails;
2. a scene that says the historical record has already proved a unique prescription or necessary death mechanism fails as historical overclaim.

The older minimal Chapter 86 test stub remains valid because “再温一温” is correctly recognized as a household-care action rather than requiring one particular vocabulary item such as “煎药”.

## CLI

`rcwh historical-adapter summary`

`rcwh historical-adapter describe detention`

`rcwh historical-adapter describe transport_letters`

`rcwh historical-adapter scene data/scenes/ch86_last_night.yaml artifacts/43-0/ch86/candidates/ch86_B_light_full.md`

The existing `rcwh mechanism H01`—`H06` commands remain the source-boundary view; the new adapter commands are the downstream scene-feasibility view.

## Boundaries preserved

The project hierarchy remains:

Evidence / Reconstruction → current scene choice → historical feasibility check.

Not:

historical analogy → new Red-Chamber fact.

The adapter runtime therefore never edits R/P/O, never closes OPEN interfaces, and never authorizes literary promotion.

Stable ACTIVE remains unchanged:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

No Chapter 89 adjudication and no Chapter 92 literary production were advanced by Issue #4.

## Validation

The complete candidate implementation passed GitHub Actions run `37599949539`:

- `rcwh validate`: PASS
- adapter CLI smoke: PASS
- Chapter 86 medical + household adapter scene: PASS
- OPEN-research adapter query: PASS
- Full Migration regression: PASS
- stable pointer unchanged: PASS
- `pytest -q`: **199 passed / 0 failed**

After that successful run, the adapter state was advanced from `PASS_CANDIDATE` to `PASS`.
