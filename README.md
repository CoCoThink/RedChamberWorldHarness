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
rcwh project acceptance
rcwh assets validate
rcwh assets collections
rcwh assets list --role CHAPTER_CARD --chapter 92
rcwh corpus inputs data/corpus/inputs/front80-pilot-v1.json
rcwh corpus verify corpus:front80:v1-candidate --rebuild
rcwh corpus query corpus:front80:v1-candidate --chapter 27 --keyword 红玉
rcwh sources audit
rcwh self-contained check --profile declared-inputs
rcwh sources trace decision:cliff-release:function
rcwh self-contained check --profile asset-storage
rcwh self-contained check --profile release-storage
```

Original handover inputs have been received into the asset catalog. Provenance records now resolve asset IDs directly; extracted ZIPs and chat attachments are not inputs to these APIs. CI verifies repository bytes and compares immutable asset versions with the previous catalog.

Redundant handover copies and unused historical baseline/superseded bodies have been removed. Their checksums and origin records remain in the import audit. The legacy `registry`, `coverage`, and `completion` commands and M1–M8 override chain have been retired; current domain traces resolve and verify asset bytes directly. See the [migration cleanup decision](docs/decisions/0002_RETIRE_MIGRATION_RUNTIME.md) and [historical rule retirement](docs/decisions/0003_RETIRE_HISTORICAL_RULES.md). Operational commands are consolidated in the [search and writing runbook](docs/runbooks/SEARCH_AND_WRITING.md); chapter scope is explicitly configured in `data/project/scope.json`.

`source-content` and `source-locators` are separate checks. All 32 Sources now have fixed carriers and reproducible excerpt spans. The three Cao excerpts were collated against National Palace Museum manuscript 故宮005664; their local text carrier is an explicitly attributed agent transcription derived from the museum's facsimile PDFs. See the [facsimile collation](docs/reviews/CAO_FACSIMILE_VERIFICATION_20261009.md) for original images, corrections and limitations. Independent source acceptance remains pending. The stored extraction environment is CPython 3.12.13, matching CI.

## Status

The reconstruction-infrastructure design is being implemented in stages. Asset storage, physical source tracing, imported baseline verification, explicit state owners and provenance relocation are implemented. The corpus builder, declared input checks, catalog shards, frozen research writing packages and independent review submission APIs are implemented. The full Front80 corpus is a candidate awaiting human layer audit. Open collation of the three Cao passages is complete, with the agent's manuscript readings recorded separately from mechanical transcript checks. Independent source correction reviews and corpus layer audits expose their sources and context; blind review applies only to P9 comparisons of literary originals and revisions. These acceptances, continuous-chapter production and publication remain incomplete. See the [implementation closeout](docs/reviews/CORPUS_CLOSURE_IMPLEMENTATION_20261009.md) for completed engineering, verification results and separate remaining tasks.

See the [complete design](docs/RCWH_红楼梦复原基础设施完整设计_v1.0_20261008.md), [architecture decision](docs/decisions/0001_DOMAIN_FOUNDATION.md), and [foundation runbook](docs/runbooks/FOUNDATION.md). `rcwh project status` reads the selected owners, including the existing literary review gates and implementation progress. `rcwh project acceptance` calculates live admission from the declared inputs; add `--require-complete` to fail while reviews or production inputs remain pending. Source and corpus reviews retain negative findings and block acceptance; a sufficient count of positive submissions cannot erase a selected rejection. See the [current closeout](docs/reviews/REVIEW_CLOSEOUT_20261009.md).

The [source closure and corpus follow-up design](docs/RCWH_来源闭包与语料建设后续设计_v1.1_20261008.md) translates the repository review into implementation batches: unified ingest and source verification, asset discovery, offline closure, Front80 Corpus v1, and exemplar integration. It defines proposed interfaces and acceptance criteria; implementation status remains with the selected project owners.

Daily intake is available through `rcwh assets ingest FILE --origin ORIGIN`, with receipt inspection, classification and interrupted-write recovery. See the [asset intake runbook](docs/runbooks/ASSET_INTAKE.md) for idempotency keys, current binding support and Git tracking.

Deterministic PDF, EPUB, HTML and UTF-8 extraction is available through `rcwh corpus extract`. Locator v2 binds excerpts to fixed extraction units and character spans; `rcwh sources verify-all` rebuilds and checks them against the actual carrier. See the [source locator runbook](docs/runbooks/SOURCE_LOCATORS.md) and [source migration review](docs/reviews/SOURCE_CLOSURE_20261009.md). Successful extraction does not complete source closure or Corpus v1.

Asset roles and collections now provide reading navigation through `rcwh assets list` and `rcwh assets collections`. The Front80 input selection fixes the complete PDF extraction as the main input and the EPUB as a comparison witness: their colophons differ, and the current EPUB extractor omits image glyphs. `rcwh corpus inputs` rebuilds both extractions and checks their registered inventory. See the [input review](docs/reviews/ASSET_DISCOVERY_AND_CORPUS_INPUTS_20261009.md) and [discovery/input runbook](docs/runbooks/ASSET_DISCOVERY_AND_CORPUS_INPUTS.md). The pilot and full Front80 candidate now contain separate text layers; human layer acceptance remains pending.

The catalog now uses ID-based shards selected by `data/catalog/catalog.json`; its disposable index binds every shard and discovery record. Two registered corpus candidates rebuild identically in fresh offline processes. Read the [corpus and review input runbook](docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md), [declared closure runbook](docs/runbooks/DECLARED_INPUT_CLOSURE.md) and [implementation review](docs/reviews/CORPUS_CLOSURE_IMPLEMENTATION_20261009.md). CI requires zero Source locator failures and verifies the Cao facsimile derivation chain; the fixed Source root baseline has no waivers. Full declared closure remains incomplete because independent source reviews are pending. Human review selections are empty; prepared packets and templates are not review results.

## License

No open-source license is granted yet. Add an explicit license only after the repository owner decides how research data, code, and derivative literary text should be licensed.
