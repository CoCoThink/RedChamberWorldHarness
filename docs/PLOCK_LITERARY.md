# Literary P-Lock layer — v0.3-alpha

The R4 Evidence Core is now frozen on `main`.

The next harness layer is deliberately downstream:

```
Evidence Core
  ↓
Implementation
  ↓
P-Lock
  ↓
C / G generation
```

A P-Lock protects a literary solution that survived review. It is **not evidence about Cao Xueqin's lost manuscript**.

## Core rule

`P_LOCKED` means:

- this detail or mechanism currently deserves protection against accidental literary regression;
- a replacement may still win;
- replacement requires competition + six-field regression + P-Lock regression + blind read;
- stability never promotes the detail upstream into Source / Claim / Decision truth.

Every P-Lock therefore has:

`authority = LITERARY_PROTECTION_ONLY`

and:

`generation_effect = PROTECT_AGAINST_REGRESSION`

## First high-risk batch

### Chapter 86 — cold medicine

Protect:

- medicine / stove / reheating / cold terminal chain;
- Baoyu arrives too late but still thinks in ordinary illness actions;
- Daiyu's last writing remains revision / deletion / unfinished fragment;
- no completed “death poem” explanatory closure.

Current P1 terminal:

`那盏药早已冷透，再没有人去温。`

### Chapter 89 — confiscation absorbed by small life

Protect:

- large political/administrative event becoming shared-water, clothing, keys, medicine, room, well and bucket life;
- procedure never becomes the chapter's final explanatory voice.

Current P1 terminal:

`谁家的水桶还在井边？`

### Chapter 92 — G-P92-02

Protect:

- procedure density cap;
- Xiaohong's capability through asking correctly, finding people and checking handoff chains;
- Qianxue's old feeling through socks / cold / warmth, not grievance exposition;
- Baoyu's material-life learning;
- ordinary prison time.

### Chapter 97 — G-P97-03

Protect:

- shared water;
- counted lamp oil;
- white porcelain basin dedicated → lent/shared → cleaned → still used;
- no philosophical summary of Miaoyu's “transformation”;
- Xichun remains capable of saying: `谁同你说我件件想得明白？`

### Chapter 100 — G-P100-04

Protect:

- Kongkong Daoist as record-keeper, not second interpreter;
- physical transcription friction;
- no second Qingbang / Li Wan / Jia Lan thematic summary;
- terminal restraint.

Current P1 terminal:

`石在，字在。`

## Why P-Lock is separate from LiteralConstraint

A `LiteralConstraint` is evidence-governed. For example, `情情` may be NOVEL_EXACT because upstream evidence requires it.

A P1 exact anchor such as `石在，字在。` is different:

- it is exact **for the current literary baseline**;
- it is not claimed as lost-original wording;
- it can be replaced only by a winning literary candidate that passes regression.

Conflating these two exactness types would recreate the same reverse-promotion problem that the Evidence Core was built to prevent.

## Validator invariants

1. P-Locks must remain `LITERARY_PROTECTION_ONLY`.
2. P-Locks must point to the stable ACTIVE prose file/SHA.
3. Context refs must resolve, but are context rather than authority.
4. Decisions may never cite a P-Lock as evidence.
5. The v0.2 R4 Evidence Core regression must continue to PASS unchanged.
6. Replacement rule is fixed:
   `COMPETITION_PLUS_SIX_FIELD_PLUS_PLOCK_PLUS_BLIND_READ`.

## CLI

```bash
rcwh plock plock:ch86:cold-medicine
rcwh plock plock:ch92:procedure-density
rcwh plock plock:ch97:miaoyu-object-progression
rcwh plock plock:ch100:record-keeper-ending
```

This is the first Literary Harness slice. It does not yet perform semantic evaluation of arbitrary candidate prose; that evaluator comes next.
