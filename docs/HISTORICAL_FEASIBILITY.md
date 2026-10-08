# Historical feasibility contract — H01–H06

R4-E historical material answers one question only:

> Can the current reconstruction mechanism plausibly operate in a Qing historical world?

It does **not** answer:

> Did Cao Xueqin necessarily write this exact scene?

RCWH encodes this distinction as:

    Claim.authority_scope = HISTORICAL_FEASIBILITY
    HistoricalMechanism.effect = FEASIBILITY_ONLY

## Core asymmetry

Historical evidence can rule out or warn against a mechanism when the proposed scene conflicts with a source boundary. It cannot force a positive plot merely because the plot is historically possible.

Therefore:

    historically feasible != plot required
    ALLOW != MUST

If a future hard historical boundary is compiled into a Decision, it must be explicit:

    domain = HISTORICAL_BOUNDARY
    status = LOCKED
    constraint = MUST_NOT

A locked historical boundary may never become positive `MUST`.

## H01 — detention / access / prison-god space

Verdict: PASS-WITH-CAUTION.

Primary law supports controlled visits for specified relatives, inspected transfer of food, restrictions on outsiders, and “牵连待质” as a detention context. Gazetteer evidence shows some prisons contained a 狱神庙.

This does not grant an old servant an automatic right of access. The active Qianxue scene remains acceptable only because it is written as an occasional requested barrier-contact that can be refused or stopped.

## H02 — confiscation / sealing / inventory

Verdict: PASS.

The 1728 Cao archive directly records managers detained for questioning and property being checked, inventoried, and sealed. RCWH treats this as a close historical mechanism analogue, not a template proving Jia-family crime, scope, or exact procedure.

## H03 — mourning / marriage timing

Verdict: PASS-BOUNDARY.

The Qing code shows mourning could constrain marriage. Court ritual separately shows consort deaths had their own mourning rules for imperial kin and affines.

The only safe conclusion is that Yuanfei's death can delay marriage. No single 27-day, 100-day, nine-month, or other formula is imported as the unique novel timeline.

## H04 — post-confiscation housing / rental / marriage authority

Verdict: PASS.

The Qing marriage code supports senior-kin marriage authority. The Cao archive shows limited housing could remain available to a confiscated family. A 1774 Beijing-region rental contract demonstrates a formal rental mechanism.

None of these sources proves the active borrowed courtyard, rented side-yard, room count, rent, or exact Jia/Wang/Xue negotiation.

## H05 — continuing poverty / pawn / rent / food

Verdict: PASS.

The Cao archive records more than a hundred pawn tickets among residual household property. Together with rental-contract evidence, this makes ongoing pawn/rent cashflow a plausible decline mechanism.

The source does not prove the active blue jacket, “two and a half bowls,” coal quantity, rent, or any specific price.

## H06 — natal-family aid

Verdict: PASS-SOFT.

This is intentionally weaker. It relies on modern scholarship analyzing 124 Qing Nanbu County cases. The study supports continuing natal-family ties and possible aid, while also emphasizing limits imposed by poverty and circumstance.

Because region, class, and period differ from Baochai's reconstruction context, RCWH does not infer either:

- “the Xue family must continuously support her”; or
- “a married daughter can no longer receive natal-family help.”

Aid amount, frequency, duration, and even whether it occurs remain OPEN.

## Scene adapter interface

Scene contracts declare `historical_adapters` and optional `historical_adapter_requirements`. Results include adapter ID, support class, research status, H references, required signals and hits, missing signals, overclaims, OPEN questions and cannot-prove boundaries. Adapters use `FEASIBILITY_ONLY`, `plot_authority = NONE`, and `may_create_events = false`.

Detention, confiscation, mourning/marriage, pawnshop and household economy inherit their H-backed boundaries. The medical adapter is a body/care boundary profile, not a new hard historical conclusion: it cannot establish a unique diagnosis, prescription, dose, doctor timetable or lost wording. Transport/letters and monastic economy remain `OPEN_RESEARCH`; `PASS_WITH_OPEN` retains those questions.

The Chapter 86 scene exercises medical care and household labor signals, including warming medicine. These checks reject absent processes and explicit historical overclaims; they do not require a single preferred phrase. Adapter commands describe and evaluate downstream feasibility; `mechanism` exposes the underlying source boundaries.

```bash
rcwh historical-adapter summary
rcwh historical-adapter describe detention
rcwh historical-adapter describe transport_letters
rcwh historical-adapter scene data/scenes/ch86_last_night.yaml artifacts/43-0/ch86/candidates/ch86_B_light_full.md
```

## Source mechanism CLI

    rcwh mechanism H01
    rcwh mechanism H03
    rcwh mechanism H06

The command exposes the historical Claims and Sources, what the mechanism merely allows, what it rejects as a historical assertion, what remains open, what it cannot prove, and which current prose implementations are being checked.
