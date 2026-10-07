# Issue #3 — Character Knowledge Graph and Voice Profiles v0.3

Status: **PASS**

Issue #3 acceptance is implemented on the canonical post-M8 literary branch without changing stable ACTIVE.

## Acceptance

### Per-scene epistemic state

The first slice covers exactly:

- Baoyu
- Daiyu
- Zijuan
- Baochai
- Xiaohong
- Qianxue

Each scene exposes four explicit buckets:

- `knows`
- `believes`
- `suspects`
- `does_not_know`

Current scenes:

- `ch86_last_night`
- `ch89_confiscation_message`
- `ch92_delivery_gate`

Absence from `knows` is not treated as ignorance unless `does_not_know` is explicit.

### Event-driven updates

Knowledge changes are replayed as scene events rather than edited as a static final state.

Examples:

- Zijuan moves from not knowing the exact death moment to knowing it only when the death event occurs.
- Xiaohong enters Chapter 92 without detention delivery-rule knowledge.
- `K92-XIAOHONG-ASKS-GATE-RULES` moves that rule into `knows`.
- Whole-case knowledge remains explicitly unavailable, preventing Xiaohong from becoming a universal information source.

### Omniscience validator

Scene contracts now support:

- `knowledge_checkpoint`
- `knowledge_guards`
- `voice_profile_hooks`

The ordinary scene evaluator invokes the Character Knowledge runtime. A contract can therefore reject dialogue or action that asserts a fact the actor does not know at the declared checkpoint.

The regression suite contains both dialogue and action leakage cases and requires them to fail.

This is a contract-driven validator, not a claim of general natural-language mind reading.

### Voice / speaker masking hooks

Source-backed M5 voice profiles are bridged for:

- Baoyu
- Daiyu
- Zijuan
- Baochai
- Xiaohong

The hooks expose source-backed traits, relation shifts, and explicit post-80 forbidden drift. They can reject declared forbidden voice patterns, but they never automatically declare a speaker identity.

Qianxue is deliberately represented as:

`SPARSE_ABSTAIN`

because the current M5 machine voice corpus contains no dedicated Qianxue profile. The runtime therefore refuses to invent a stable voice fingerprint from missing evidence.

### Query surface

`rcwh knowledge summary`

`rcwh knowledge scene ch92_delivery_gate --checkpoint K92-XIAOHONG-ASKS-GATE-RULES`

`rcwh knowledge character ch86_last_night zijuan --checkpoint K86-ZIJUAN-SEES-RAPID-DECLINE`

`rcwh knowledge voice xiaohong`

`rcwh knowledge voice qianxue`

`rcwh knowledge mask <character> <text-file>`

`rcwh knowledge guard <scene-contract> <text-file>`

## Boundaries

Character Truth remains downstream of Evidence / Reconstruction / World.

A current scene knowledge state does not prove lost-manuscript fact. Voice masking hooks do not turn stylistic resemblance into authorship or identity proof.

Stable ACTIVE remains:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

No Chapter 89 adjudication and no Chapter 92 literary production are performed by Issue #3.

## Validation

First complete candidate CI run `37598471460` passed:

- `rcwh validate`: PASS
- knowledge query smoke: PASS
- scene omniscience guard smoke: PASS
- stable pointer unchanged: PASS
- `pytest -q`: **190 passed / 0 failed**

After this validation, the machine state was advanced from PASS_CANDIDATE to PASS.
