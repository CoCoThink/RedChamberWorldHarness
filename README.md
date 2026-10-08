# RedChamberWorldHarness (RCWH)

A narrative-world harness for the post-80-chapter reconstruction of *Dream of the Red Chamber* (《红楼梦》).

RCWH is not a story generator by itself. It is the runtime around a generator: it loads evidence, world state, character knowledge, object state, scene contracts, and literary policies; then it validates candidate prose before anything can become an accepted reconstruction.

## Why this exists

The v5.0 reconstruction plan explicitly shifts from “evidence-safe minimalism” to full literary completion: hard evidence remains binding, but underdetermined areas may be generated from character, Qing-era mechanisms, chapter structure, and literary fitness. RCWH turns that methodology into an executable harness.

The central rule is:

> Evidence is the floor, not the ceiling.

And the engineering corollary is:

> A generated scene may be literarily free, but it must never silently upgrade a reconstruction choice into historical evidence.

## Narrative runtime

RCWH provides six executable layers:

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
├── sources/                 # Original source files, identified by SHA and asset ID
├── research/                # Versioned project research
├── data/
│   ├── catalog/             # Physical assets and their origin occurrences
│   ├── provenance/          # Sources, Claims, Decisions, Implementations, title axes
│   ├── project/             # State owners, chapter scope and implementation progress
│   ├── evidence/            # Evidence truth
│   ├── characters/          # Character state
│   ├── objects/             # Object ledger
│   ├── events/              # Event-sourced reconstruction truth
│   └── scenes/              # Scene contracts
├── docs/                    # Architecture and plan mapping
├── releases/                # Imported stable baseline and immutable release manifest
├── artifacts/               # Candidates, experiments, reviews and migration audit
├── archive/                 # Import receipts and historical deltas; no implicit policy authority
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

## Assets and current state

```bash
rcwh project status
rcwh assets validate
rcwh sources trace decision:cliff-release:function
rcwh self-contained check --profile asset-storage
rcwh self-contained check --profile release-storage
```

Original handover inputs have been received into the asset catalog. Provenance records now resolve asset IDs directly; extracted ZIPs and chat attachments are not inputs to these APIs. CI verifies repository bytes and compares immutable asset versions with the previous catalog.

Redundant handover copies and unused historical baseline/superseded bodies have been removed. Their checksums and origin records remain in the import audit. The legacy `registry`, `coverage`, and `completion` commands and M1–M8 override chain have been retired; current domain traces resolve and verify asset bytes directly. See the [migration cleanup decision](docs/decisions/0002_RETIRE_MIGRATION_RUNTIME.md) and [historical rule retirement](docs/decisions/0003_RETIRE_HISTORICAL_RULES.md). Operational commands are consolidated in the [search and writing runbook](docs/runbooks/SEARCH_AND_WRITING.md); chapter scope is explicitly configured in `data/project/scope.json`.

`source-content` and `source-locators` are separate checks. They currently fail explicitly: some historical Sources lack local carriers, and imported page/line assertions have not yet been aligned with reproducible extraction output. Storage integrity does not imply complete source closure.

## Status

The reconstruction-infrastructure design is being implemented in stages. Asset storage, physical source tracing, imported baseline verification, explicit state owners and provenance relocation are implemented. Corpus construction, unified world/planning workflows, continuous-chapter editing and final source closure remain in progress.

See the [complete design](docs/RCWH_红楼梦复原基础设施完整设计_v1.0_20261008.md), [architecture decision](docs/decisions/0001_DOMAIN_FOUNDATION.md), and [foundation runbook](docs/runbooks/FOUNDATION.md). `rcwh project status` reads the selected owners, including the existing literary review gates and implementation progress.

## License

No open-source license is granted yet. Add an explicit license only after the repository owner decides how research data, code, and derivative literary text should be licensed.
