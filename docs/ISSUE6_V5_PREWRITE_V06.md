# Issue #6 — Automate v5.0 Steps 33–42 / Prewrite Harness v0.6

Status: **PASS**

Issue #6 implements the pre-rewrite harness for the v5.0 / v5.2 Step 33–42 planning chain.

The harness is deliberately **staging-only**. It may assemble audited literary-ecology inputs, gap diagnostics, omitted-process plans, and chapter contracts for later Step 43 candidate work, but it cannot create or upgrade evidence.

## Actual execution order

The runtime preserves the later v5.2 execution dependency order rather than pretending that numeric order is the operational order:

`33 → 34 → 35 → 40 → 39 → 38 → 37 → 36 → 41 → 42`

This captures the plan's dependency decisions:

- Step 35 restores formation/social process before literary decoration;
- Step 40 social infrastructure precedes the body/ritual and culture passes that depend on concrete execution chains;
- Step 37 evidence/text identity precedes Step 36 author-level verse competition;
- Step 41 metaphysics/Qingbang follows the text-evidence boundary work;
- Step 42 composes the final prewrite chapter contract.

## Step 33 — corpus ecology profiler

The machine layer exposes six frozen first-80 ecology profiles:

1. chapter frames / chapter-end momentum;
2. poetry and literary-text ecology;
3. cultural practice / arts life;
4. medicine, body, and illness;
5. Buddhist/Daoist/dream/metaphysical systems;
6. social, occupational, ritual, and economic ecology.

The runtime mode is:

`IMPORTED_AUDITED_PROFILE`

It does not silently rescan the first 80 chapters and invent a new baseline. It machine-represents the already audited Step 33 profile conclusions and their registered source documents.

The profile output has:

`authority = STAGING_BASELINE_ONLY`

`evidence_effect = NONE`

## Step 34 — 20 × 12 gap cards

The current Step 34 matrix is encoded for all chapters 81–100 and all twelve dimensions:

- main-process formation;
- secondary plot;
- independent minor-agent line;
- poetry / verse;
- arts / cultural practice;
- medicine / body;
- religion / philosophy;
- ritual / seasonal life;
- economy / occupations;
- comic / folk culture;
- dream / symbol / frame;
- chapter-opening / chapter-ending art.

The four source states are normalized as:

- `SUFFICIENT`
- `THIN`
- `MISSING`
- `NOT_APPLICABLE`

Validation reproduces the frozen aggregate counts, including:

- main process: 11 THIN / 9 MISSING;
- economy: 9 THIN / 11 MISSING;
- comic/folk: 20 SUFFICIENT;
- chapter-frame art: 16 SUFFICIENT / 3 THIN / 1 MISSING.

These remain literary construction diagnostics, not claims about what lost manuscript passages must have existed.

## Step 35 — omitted / compressed process planner

All twenty chapters have a machine-readable formation-process plan.

The frozen matrix carries:

- action;
- intensity;
- core process;
- handoff to later specialist steps;
- candidate scene IDs and titles.

The current imported plan contains **85 candidate scene slots**.

Examples:

- Chapter 86: six slots from “last ordinary sick day” through death, bodily handling, and Baoyu's late arrival;
- Chapter 89: six slots from restricting movement through people/property checks, wage/labor breakup, and relocation;
- Chapter 92: six slots from document recognition through detention-rule learning, Xiaohong's access work, Qianxue's material-care function, and narrowing of the inquiry;
- Chapter 100: five human-world time slices before the external-frame transition.

These are staging candidates, not reconstructed facts.

## Steps 36–41 — machine-bound specialist passes

The harness binds the already migrated specialist runtimes instead of copying their prose into a second authority layer.

### Step 36 — author verse

Uses the current per-chapter author-rhyme policy from Literary Ecology.

No gap status can infer that a chapter “must have a poem”.

### Step 37 — text evidence and G-layer generation

Keeps literary evidence nodes and G-layer generation containers distinct.

`G` remains generation space and can never self-promote into evidence.

### Step 38 — cultural life

Consumes the arts gap plus the front-80 cultural-practice and post-80 cultural-life profiles.

The operating rule is cultural life attached to action/function, not a four-arts quota.

### Step 39 — body / ritual

Consumes body and ritual gap states and exposes only candidate **feasibility** adapters.

Historical adapters remain `FEASIBILITY_ONLY`; they do not create plot facts.

### Step 40 — social infrastructure

Every major-event staging contract exposes the four-chain requirement:

- people;
- money;
- material;
- information.

The Step 35 core formation process is carried forward here.

### Step 41 — metaphysics / dream / Qingbang

Consumes metaphysics and dream-symbol gap states with:

`ambiguity_required = true`

For Chapter 100, the Qingbang boundary remains the current Literary Ecology object, including:

`formal_title_status = OPEN`

The harness cannot turn the formal title, full roster, or generated evaluations into hard evidence.

## Step 42 — twenty machine-readable chapter contracts

The runtime generates exactly twenty contracts:

`prewrite:ch81:v0.6` through `prewrite:ch100:v0.6`.

Each contract combines current machine layers:

- Reconstruction M2 title/status/anchors/constraints;
- timeline context;
- Step 34 12D gap card;
- Step 35 formation-process plan;
- Step 36 author-verse policy;
- Step 37 chapter text ecology;
- Step 38 cultural-life staging pass;
- Step 39 body/ritual staging pass;
- Step 40 social-infrastructure pass;
- Step 41 metaphysical/ambiguity pass;
- chapter P-Lock references;
- registered source references.

The contract explicitly marks upstream hard context as **read-only input**.

## Staging permissions

A Step 42 contract can be wrapped as:

`V5_PREWRITE_STAGING_PACKET`

Allowed outputs:

- scene plan;
- scene-contract draft;
- candidate brief;
- review checklist.

Forbidden outputs:

- evidence node;
- evidence-role change;
- OPEN closure;
- stable ACTIVE overwrite;
- automatic promotion.

The write-permission surface is:

- staging artifacts: **true**
- Evidence Truth: **false**
- Reconstruction Truth: **false**
- OPEN interfaces: **false**
- stable ACTIVE: **false**
- promotion: **false**

The prewrite harness also has:

`automatic_prose_generation = false`

It prepares Step 43; it does not execute Step 43.

## CLI

`rcwh prewrite summary`

`rcwh prewrite corpus [profile-id]`

`rcwh prewrite gap <chapter>`

`rcwh prewrite scenes <chapter>`

`rcwh prewrite step <33..42> [--chapter N]`

`rcwh prewrite contract <chapter>`

`rcwh prewrite stage <chapter>`

## Authority boundary

The complete runtime is locked to:

`authority = STAGING_ONLY`

`evidence_effect = NONE`

`stable_active_effect = NONE`

Stable ACTIVE remains unchanged:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

The implementation does not adjudicate Chapter 89, does not unlock Chapter 92/97, and does not promote Chapter 86-B.

## Validation

The complete PASS-candidate implementation passed GitHub Actions run `37614297127`:

- Full Migration Completion Gate: PASS;
- Step 33 six-profile query: PASS;
- Step 34 20×12 gap query: PASS;
- Step 35 scene-planner query: PASS;
- Step 40 staging query: PASS;
- Step 42 Chapter 100 contract: PASS;
- Chapter 89 staging packet: PASS;
- stable pointer unchanged: PASS;
- `pytest -q`: **221 passed / 0 failed**.

After that successful run, the v0.6 state was advanced from `PASS_CANDIDATE` to `PASS`.
