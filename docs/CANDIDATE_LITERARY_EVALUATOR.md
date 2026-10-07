# Candidate Literary Evaluator — v0.3-alpha.2

The Literary Harness must not pretend that literary judgment is a scalar metric.

This evaluator therefore does **not** produce a score such as 87/100 and never prints “literary PASS”.

Its job is narrower:

1. detect explicit drift signatures that should stop a candidate before blind read;
2. detect loss of currently protected P1 anchors;
3. show whether machine-observable signals for a P-Lock remain present;
4. report neutral observations such as procedure-word counts;
5. force human P-Lock review and blind read before promotion.

## Status model

### READY_FOR_BLIND_READ

No explicit blocker and no protected exact anchor was lost.

This is **not approval**.

The candidate still requires:

- six-field regression;
- human P-Lock review;
- blind read.

### REPLACEMENT_CASE

A protected P1 anchor was changed or moved out of its protected structural position.

This is not automatically wrong. A better replacement is allowed, but it must pass the full replacement rule:

- candidate competition;
- six-field regression;
- P-Lock replacement review;
- human blind read.

The command exits with code 2 so CI or agent workflows can distinguish “possible replacement requiring adjudication” from hard rejection.

### REJECT_BEFORE_BLIND_READ

The text contains an explicit high-confidence drift signature from the evaluation profile, such as:

- Chapter 86 explicitly generating an “绝命诗”;
- explicit philosophical closure like “我终于明白”;
- Chapter 97 explicitly summarizing Miaoyu as “终于明白 / 从此入尘”;
- an explicit supernatural prison-release signature.

These checks are intentionally narrow. Absence of a blocker does not prove literary quality.

### INFRASTRUCTURE_BLOCKED

The frozen R4 Evidence Core regression itself is not green. Literary comparison must stop.

## Signal semantics

Feature signals are **diagnostic only**.

For example, Chapter 86's medicine-chain profile looks for signal groups around:

- medicine;
- reheating;
- stove/fire;
- cold.

If a group is absent, the evaluator reports an incomplete signal. It does **not** automatically fail the candidate, because a candidate may express the same function with different language.

That gap is routed to mandatory human review.

## No automatic promotion

Every result contains:

`automatic_literary_pass = false`

and:

`promotion_eligible = false`

This remains true even for `READY_FOR_BLIND_READ`.

The harness can block obvious regressions and expose likely losses. It cannot replace blind reading.

## CLI

Evaluate one candidate:

```bash
rcwh literary-evaluate plock:ch86:cold-medicine examples/literary/ch86_preserved.txt
```

Compare A/B/C in one call:

```bash
rcwh literary-evaluate plock:ch86:cold-medicine \
  examples/literary/ch86_preserved.txt \
  examples/literary/ch86_replacement_case.txt \
  examples/literary/ch86_blocked.txt
```

Machine meanings:

- exit 0: candidate may proceed to human gates;
- exit 2: replacement case requires explicit adjudication;
- exit 1: blocker or infrastructure failure.

## Architectural boundary

The evaluator consumes the P-Lock layer. It never writes to Source / Claim / Decision.

```
Source → Claim → Decision → Implementation
                              ↓
                           P-Lock
                              ↓
                    Candidate Evaluator
                              ↓
               human review / blind read
```

That one-way direction is mandatory.
