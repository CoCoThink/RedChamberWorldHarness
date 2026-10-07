# Competition / Review Ledger — v0.3-alpha.3

The 43-0 pressure test is governed by a fixed sequence:

```
baseline excerpt
→ structural reorder
→ small trial
→ six-field regression
→ P-Lock regression
→ blind read
```

Pressure drafts are stored separately and may not overwrite stable ACTIVE.

A new stable body requires a competition winner plus six-field regression, P-Lock regression, and blind-read pass.

## Production queue

The repository now contains four production records in fixed order:

1. Chapter 86 — ready for candidates
2. Chapter 89 — blocked by predecessor
3. Chapter 92 — blocked by predecessor
4. Chapter 97 — blocked by predecessor

Only one production competition may be active at a time.

The records intentionally contain no invented literary candidates yet.

## Candidate identity

Repository candidates use:

- path;
- Git blob SHA;
- source commit.

A stable-baseline candidate may instead use the stable file reference and SHA256.

Candidate provenance is not evidence provenance.

## Six-field gate

Every candidate carries:

- PROVENANCE
- ROLE
- MODALITY
- TARGET
- PLACEMENT
- IMPLEMENTATION

Each is NOT_RUN / PASS / FAIL. All six must PASS before adjudication eligibility.

## P-Lock and blind-read gates

READY_FOR_BLIND_READ still needs human P-Lock PASS.

REPLACEMENT_CASE needs explicit REPLACEMENT_ACCEPTED.

Blind review requires PASS and `reviewer_blinded = true`.

A/B/C labels are separate from blind tokens.

## Adjudication

Allowed outcomes:

- PENDING
- KEEP_BASELINE
- WINNER
- NO_WINNER

A fully eligible winner becomes only:

`PROMOTION_CANDIDATE`

There is no PROMOTED state in this layer.

`stable_active_effect = SEPARATE_PROMOTION_ONLY`

so the Competition Ledger cannot overwrite stable ACTIVE.

## Harness fixture

`examples/competitions/ch86_evaluator_demo.yaml` uses the existing evaluator examples:

- A → READY_FOR_BLIND_READ
- B → REPLACEMENT_CASE
- C → REJECT_BEFORE_BLIND_READ

Its evidence and human gates are intentionally unrun. It is not the real Chapter 86 competition.

## CLI

```bash
rcwh competition comp:43-0:ch86:pressure-test
```

The initial record should show no candidates, PENDING adjudication, NOT_ELIGIBLE promotion, and no stable mutation.

## Next operational step

Infrastructure is now sufficient to start the real Chapter 86 pressure test. The next step is to create separate Chapter 86 baseline/A/B/C artifacts and advance:

```
BASELINE_EXCERPT
→ STRUCTURAL_REORDER
→ SMALL_TRIAL
```

before the candidate-specific six-field, P-Lock and blind-read gates are recorded.
