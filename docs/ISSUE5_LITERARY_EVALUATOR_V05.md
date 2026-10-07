# Issue #5 — Literary Evaluator Suite v0.5

Status: **PASS**

Issue #5 adds a reusable literary-screening layer downstream of Evidence, Reconstruction, World, Character Truth, Historical Adapters, and P-Lock.

It does **not** replace human literary judgment and does **not** auto-promote any candidate.

## Acceptance implemented

### 1. Culture-not-museum deletion test

The suite scans culture-bearing spans and constructs a deletion variant for review.

It distinguishes culture terms that are attached to:

- concrete action;
- material use;
- interpersonal friction;
- dialogue/relation work;

from spans that are primarily display-like.

Display-only spans are returned as:

`FLAG_MUSEUM_RISK`

not as automatic literary failure.

This is deliberately conservative: the machine can identify likely “文化展览馆” risk, but cannot prove that a passage lacks literary life.

### 2. Explicit exposition detector

High-confidence interpretive closure such as explicit authorial explanation, philosophical summary, or direct “this proves/this means” statements can block a candidate before blind read.

The result is:

`FAIL_EXPLICIT_EXPOSITION`

and the integrated candidate evaluator converts that hard blocker into:

`REJECT_BEFORE_BLIND_READ`

Ordinary narrative connective words are not automatically rejected.

### 3. Ambiguity preservation

The suite contains explicit guards for currently OPEN literary/evidence interfaces, including examples such as:

- author/form/count questions around 《十独吟》;
- formal title and roster size of the 情榜;
- whether Baoyu must later personally read 《续庄子》;
- whether “落叶萧萧，寒烟漠漠” must be poetry;
- whether “黛玉逝后宝钗之文字” means Baochai-authored text.

Downstream prose that explicitly closes these questions as unique facts is blocked as:

`FAIL_AMBIGUITY_CLOSURE`

The evaluator therefore protects OPEN as a reviewed conclusion rather than treating it as unfinished work.

### 4. Structural variation checks

Long-form prose receives non-authoritative structural diagnostics:

- paragraph count;
- sentence count;
- sentence-length coefficient of variation;
- paragraph-length coefficient of variation;
- repeated paragraph-opening ratio.

Mechanical uniformity is returned as:

`FLAG_STRUCTURE_RISK`

not automatic failure.

This avoids turning statistics into a substitute for literary criticism.

### 5. Poetry candidate A/B/C lane

A dedicated poetry lane now accepts exactly three internal candidates:

`A / B / C`

The machine lane checks:

- evidence-label contamination;
- explicit exposition;
- cliché observations;
- duplicate lines;
- line-count / line-length observations.

It never selects a winner:

`automatic_winner = false`

and never grants literary adequacy:

`automatic_literary_pass = false`

A clean lane becomes:

`READY_FOR_BLIND_READ`

Three non-canonical test fixtures are stored only under `examples/literary/` to exercise this interface.

### 6. Blind-read output separated from evidence labels

The suite now produces sealed blind packets independently from the competition/evidence ledger.

For production competitions, a blind packet contains only:

- chapter;
- anonymous token;
- anonymous blind artifact path;
- content SHA;
- literary review questions;
- anonymous ranking instruction.

It does **not** expose:

- A/B/C candidate labels;
- candidate IDs;
- origin;
- P-Lock IDs;
- six-field results;
- evidence regression state;
- machine expected status;
- adjudication eligibility.

The blind-output validator recursively rejects forbidden metadata keys and evidence-label leakage.

For Chapter 89, the safe blind surface exposes only:

- `BR-14`
- `BR-58`
- `BR-91`

and their `artifacts/43-0/ch89/blind/` files.

The A/B/C mapping remains outside the blind packet.

## Integration with existing evaluator

`evaluate_literary_candidate(...)` now includes a `literary_suite` result.

The v0.5 suite may add a hard pre-blind blocker only for high-confidence cases such as explicit exposition or explicit ambiguity closure.

Culture-deletion and structural-variation findings remain human-review flags.

Existing P-Lock anchors, feature signals, six-field regression, human P-Lock review, and human blind read remain separate gates.

## CLI

`rcwh literary-suite summary`

`rcwh literary-suite prose <text-file>`

`rcwh literary-suite blind <competition-id>`

`rcwh literary-suite poetry-screen <A-file> <B-file> <C-file>`

`rcwh literary-suite poetry-blind <A-file> <B-file> <C-file>`

The `poetry-screen` command is an internal machine view and may display internal A/B/C labels.

The `poetry-blind` command emits only the anonymized review packet.

## Authority boundary

This suite has:

`authority = LITERARY_SCREENING_ONLY`

It cannot:

- revise Witness / Evidence Role / Modality;
- close OPEN interfaces;
- turn literary preference into lost-manuscript evidence;
- alter Character Truth;
- create historical facts;
- auto-pass a P-Lock;
- auto-select a poetry winner;
- adjudicate a chapter competition;
- overwrite stable ACTIVE.

Stable ACTIVE remains:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

Chapter 89 remains in manual P-Lock / real blind-read pending state. Chapter 92 and Chapter 97 remain blocked by predecessor.

## Validation

The complete candidate implementation passed GitHub Actions run `37611754908`:

- Full Migration Completion Gate: PASS;
- v0.5 suite CLI smoke: PASS;
- Chapter 89 blind-packet isolation: PASS;
- poetry A/B/C machine lane: PASS;
- poetry blind packet: PASS;
- stable pointer unchanged: PASS;
- `pytest -q`: **211 passed / 0 failed**.

After this validation, the v0.5 suite state was advanced from `PASS_CANDIDATE` to `PASS`.
