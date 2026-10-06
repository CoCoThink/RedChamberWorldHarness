# Provenance model v0.2-alpha

RCWH v0.2 deliberately narrows the harness core to one invariant:

> Every constraint that claims evidential authority must be traceable to source text, and every inference between source and prose must remain explicit.

## Four layers

```text
Source
  ↓ supports / contextualizes
Claim
  ↓ resolved as
Decision
  ↓ implemented as
World / Scene / Prose
```

### Source

A source is the original material being relied on: extant novel text, early commentary, early transcript, historical primary material, or secondary research.

Project Markdown is **not** automatically a Source. R4 matrices and plans are analysis products used to reconstruct Claims and Decisions.

### Claim

A Claim is an atomic proposition about what a Source supports.

Bad:

> The comment proves that Chapter 99 is formally titled 悬崖撒手 and Baoyu becomes a monk there.

Good:

- a future 悬崖撒手 interface exists;
- Baoyu ultimately abandons wife/maid and becomes a monk;
- formal title is not established;
- Chapter 99 placement is not established;
- exact novel wording is not established.

### Decision

A Decision records current project treatment.

Statuses are intentionally small:

- `LOCKED`: a non-negotiable reconstruction constraint.
- `CURRENT`: the present model, reversible.
- `OPEN`: audit result is underdetermination, not unfinished work.
- `REJECTED`: explicitly not adopted.

The runtime permission compiler maps them to:

- `LOCKED → MUST`
- `CURRENT → MAY`
- `OPEN → OPEN`
- `REJECTED → MUST_NOT`

### Implementation

Events, scene contracts, object states, and prose are downstream implementation.

Implementation is allowed to be generative. It must never write back into Evidence Truth.

## Non-negotiable rules

1. A `LOCKED` Decision must trace to at least one `SUPPORTED` Claim with a real Source edge.
2. A `CURRENT` Decision is never displayed as “evidence proven.”
3. An `OPEN` Decision can never compile to `MUST`.
4. Repeated project documents quoting the same comment do not create additional evidence.
5. Source wording is not automatically novel wording.
6. Event evidence is not automatically title evidence.
7. Placement chosen by the reconstruction is not automatically source placement.

## Source container note

The current canary Sources point into the project’s copy of *红楼梦脂评汇校本*. That PDF is a modern collation container. RCWH records the early witness represented by the quoted comment while explicitly refusing to treat modern editorial matter as the witness itself.

A future source registry may add facsimile-level or edition-level identities without changing the Source → Claim → Decision model.
