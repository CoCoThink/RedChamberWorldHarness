# R4 OPEN-LOCK registry

The R4 release has 28 reviewed unresolved interfaces.

Their state is **OPEN_LOCKED**, not PENDING.

OPEN_LOCKED means:

- review is complete;
- current evidence does not uniquely determine the interface;
- that non-uniqueness is itself a frozen conclusion;
- a current C / PC / format choice may continue to exist;
- the current implementation does not become evidence merely by surviving revisions.

## Why this is a separate registry

A normal `Decision.status = OPEN` says that a particular proposition remains open.

An OPEN interface is broader: it records a reviewed uncertainty boundary that may contain:

- hard anchors that must survive;
- one or more OPEN Decisions;
- one or more CURRENT/MAY implementation choices;
- historical feasibility mechanisms;
- literal constraints;
- explicit prohibitions on hardening.

This lets RCWH represent cases such as:

> “甄宝玉送玉” is hard as an event, face-to-face meeting is current C, same-jade identity is current C, and the exact chapter placement is current C.

without flattening all of those facts into one confidence label.

## Machine invariants

1. The registry must contain OL-001 through OL-028 exactly.
2. Every interface must remain OPEN_LOCKED.
3. `open_decision_refs` must remain OPEN/OPEN.
4. `current_decision_refs` must remain CURRENT/MAY.
5. Hard anchors may be LOCKED, but they do not harden the interface's open fields.
6. Stable prose may implement a current choice without promoting it upstream.
7. An OPEN interface may reopen only on explicit triggers:
   - new direct witness;
   - provenance / role / modality / target / placement regrade;
   - new primary history contradiction;
   - downstream violation.

## Selected examples

### OL-003 — 十独吟 placement

Hard:
- work title;
- after Chapter 64.

Current:
- Chapter 85 display.

Open:
- exact chapter placement.

### OL-011 — 凤姐扫雪拾玉

Hard:
- the future event function.

Open:
- object identity;
- formal-title identity.

Current:
- Chapter 91 placement;
- prose deliberately says 玉样物 rather than 通灵宝玉.

### OL-018 — 妙玉瓜州

The Jingcang/Mao transcript remains W2. Current Chapter 97 does not generate a Guazhou → abduction → coercion → death-location chain.

### OL-024 / OL-025 / OL-026 — 情榜

Hard:
- final Qingbang function;
- five layers;
- 情情 / 情不情.

Open:
- formal total title;
- twelve-per-layer / sixty-total;
- lower complete rosters;
- most ratings.

Current:
- one plain scroll is a format choice, not evidence.

### OL-028 — whole 81–100 placement layer

The project uses 81–100 as a working chapter grid. Except where a source explicitly fixes wording or relative placement, these chapter numbers remain project placement. TG headings remain generated headings.

## CLI

    rcwh open OL-003
    rcwh open OL-011
    rcwh open OL-024
    rcwh open OL-028

The output shows the frozen uncertainty, current model, hard anchors, open/current decisions, historical mechanisms, current implementations, prohibited hardening, and valid reopen triggers.
