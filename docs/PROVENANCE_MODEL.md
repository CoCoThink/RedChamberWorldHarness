# Provenance model v0.2-alpha

RCWH v0.2 narrows the harness core to one invariant:

> Every constraint that claims evidential authority must be traceable to source text, and every inference between source and prose must remain explicit.

## Four layers

```text
Source
  ↓ supports / contextualizes
Claim
  ↓ resolved as
Decision
  ↓ implemented as
Implementation
```

## Source: witness is not container

A critical review correction is that an uploaded modern collation PDF is not itself the early witness.

Each Source therefore separates:

- `witness`: 庚辰本 / 己卯本 / 戚序本 / other source identity;
- `container`: the fixed file currently used to inspect that witness text;
- `locator`: page/chapter/parsed-line location inside that container;
- `text`: the actual excerpt;
- `text_sha256`: excerpt fingerprint.

A future facsimile or better edition can replace the container while preserving the Claim identity.

## Claim: atomic evidential proposition

A Claim is a single auditable proposition about what a Source supports.

Bad:

> The comment proves that Chapter 99 is formally titled 悬崖撒手 and Baoyu becomes a monk there.

Good:

- a future 悬崖撒手 interface exists;
- Baoyu ultimately abandons wife/maid and becomes a monk;
- formal title is not established;
- Chapter 99 placement is not established;
- exact novel wording is not established.

Statuses:

- `SUPPORTED`
- `CONTESTED`
- `NOT_ESTABLISHED`
- `REFUTED`

## Decision: project treatment, not evidence

Decision status and runtime constraint are deliberately separate.

Status:

- `LOCKED`
- `CURRENT`
- `OPEN`
- `REJECTED`

Constraint:

- `MUST`
- `MUST_NOT`
- `MAY`
- `OPEN`
- `NONE`

Valid combinations in v0.2-alpha:

- `LOCKED → MUST | MUST_NOT`
- `CURRENT → MAY`
- `OPEN → OPEN`
- `REJECTED → NONE`

This fixes a design bug in which every LOCKED decision was implicitly positive and every REJECTED decision was incorrectly treated as a hard prohibition.

A LOCKED decision must have **all** of its basis Claims source-backed and SUPPORTED. One supported Claim cannot hide another unestablished premise.

## Implementation: actual reconstruction state

Implementation is now a real graph node rather than an unresolved string.

The first records point into the stable ACTIVE prose for Chapters 85, 91, 98, 99, and 100.

This allows both directions:

```bash
rcwh trace decision:zhen-sends-jade:same-jade
rcwh trace impl:active:ch98:zhen-jade
```

The second command walks backward:

```text
Implementation
→ Decisions
→ Claims
→ Sources
```

## Non-negotiable rules

1. A LOCKED Decision must trace entirely to SUPPORTED Claims with real Source edges.
2. CURRENT is a reconstruction choice, even when part of its basis is strongly evidenced.
3. OPEN is a legitimate terminal result and never compiles to MUST.
4. Hard negative constraints use `LOCKED + MUST_NOT`; `REJECTED` merely means “not adopted.”
5. Repeated project documents quoting the same witness/locator/text do not create new evidence.
6. Source wording is not automatically novel wording.
7. Event evidence is not automatically title evidence.
8. Reconstruction placement is not automatically source placement.
9. Downstream Implementation can never mutate Source, Claim, or Decision authority.

## Source types

The model keeps source types simple:

- `NOVEL_TEXT`
- `EARLY_COMMENT`
- `EARLY_TRANSCRIPT`
- `HISTORICAL_PRIMARY`
- `SECONDARY_RESEARCH`

Project analysis documents are not Sources. They are migration aids for reconstructing Claim and Decision records.

## Why there is no global “source score”

Authority is relational.

A Qing legal text may strongly support a legal-feasibility Claim but say nothing about Cao Xueqin's plot. A secondary paper may help interpret a manuscript comment but does not become an early witness. A Zhiyanzhai comment may strongly support a future event but not its exact placement.

RCWH therefore asks:

> What does this Source support **for this Claim**?

rather than assigning a universal star rating to the Source.
