# RedChamberWorldHarness (RCWH)

A narrative-world harness for the post-80-chapter reconstruction of *Dream of the Red Chamber* (《红楼梦》).

RCWH is not a story generator by itself. It is the runtime around a generator: it loads evidence, world state, character knowledge, object state, scene contracts, and literary policies; then it validates candidate prose before anything can become an accepted reconstruction.

## Why this exists

The v5.0 reconstruction plan explicitly shifts from “evidence-safe minimalism” to full literary completion: hard evidence remains binding, but underdetermined areas may be generated from character, Qing-era mechanisms, chapter structure, and literary fitness. RCWH turns that methodology into an executable harness.

The central rule is:

> Evidence is the floor, not the ceiling.

And the engineering corollary is:

> A generated scene may be literarily free, but it must never silently upgrade a reconstruction choice into historical evidence.

## v0.1 goals

RCWH v0.1 establishes six executable layers:

1. **Evidence Graph** — witness/provenance, role, modality, literal target, placement, OPEN-LOCK.
2. **World State** — timeline, locations, household economy, institutions, current reconstruction truth.
3. **Character State** — capabilities, resources, knowledge, desires, taboos, voice, trajectory.
4. **Object Ledger** — ownership, holder, location, state transitions, symbolic-policy constraints.
5. **Scene Contract Runtime** — preconditions, required beats, forbidden beats, exit state, P-Locks.
6. **Evaluator Suite** — evidence, knowledge, object, timeline, mechanism, literary, ambiguity, and regression checks.

The first acceptance scenario is Chapter 86, because it simultaneously exercises illness, time, character knowledge, domestic labor, medicine, objects, poetic restraint, death, and P-Lock behavior.

## Repository layout

```text
.
├── config/                  # Harness/kernel configuration
├── data/
│   ├── evidence/            # Evidence truth
│   ├── characters/          # Character state
│   ├── objects/             # Object ledger
│   ├── events/              # Event-sourced reconstruction truth
│   └── scenes/              # Scene contracts
├── docs/                    # Architecture and plan mapping
├── evaluators/              # Human-readable evaluator specs
├── policy/                  # Literary and release policy
├── schemas/                 # JSON Schemas
├── src/rcwh/                # Executable runtime
├── tests/                   # Regression tests
└── .github/workflows/       # CI validation
```

## Truth model

RCWH keeps four kinds of truth separate:

- **Evidence Truth**: what extant witnesses actually support.
- **Reconstruction Truth**: what happens in the current reconstruction implementation.
- **Character Truth**: what each character can know, infer, misremember, or not know.
- **Text Truth**: what exact strings are required, allowed, source-only, or forbidden in prose.

A sentence can be true in the reconstruction while remaining open at the evidence layer.

## Quick start

```bash
python -m pip install -e .
python -m rcwh.cli validate
python -m rcwh.cli evaluate data/scenes/ch86_last_night.yaml examples/ch86_candidate_stub.txt
pytest -q
```

## Status

`v0.1-design`: architecture + schemas + a runnable Chapter 86 acceptance slice.

This repository is intended to become the execution harness for steps 33–52 of the literary completion plan, not a replacement for the evidence archive itself.

## License

No open-source license is granted yet. Add an explicit license only after the repository owner decides how research data, code, and derivative literary text should be licensed.
