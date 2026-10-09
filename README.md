# RedChamberWorldHarness (RCWH)

A narrative-world harness for the post-80-chapter reconstruction of *Dream of the Red Chamber* (《红楼梦》).

RCWH loads evidence, world and character state, object ledgers, scene contracts, and literary policies, then validates candidate prose before it can become an accepted reconstruction.

> Evidence is the floor, not the ceiling.

Generated scenes may develop underdetermined areas through character, historical mechanisms, chapter structure, and literary fitness. A reconstruction choice must never silently become historical evidence. Evidence Truth, Reconstruction Truth, Character Truth, and Text Truth remain separate.

## Quick start

Use CPython 3.12 (`>=3.12,<3.13`). CPython 3.12.13 is the reference build environment; CI also verifies compatibility with 3.12.3. The extraction recipe and reference dependencies are declared in `requirements/extraction.lock.json`. Rebuild checks compare actual output bytes and locator mappings; Python, dependency, and code versions are recorded as execution observations.

```bash
python -m pip install -e '.[dev]'
rcwh validate
rcwh project status
rcwh project acceptance
rcwh evaluate data/scenes/ch86_last_night.yaml examples/ch86_candidate_stub.txt
pytest -q
```

The example scene has no independent semantic reading, so `evaluate` returns PENDING (exit code 2).

`data/project/current.json` selects the current state owners; `data/project/scope.json` declares chapter scope. `project acceptance` computes engineering checks, review status, and production admission from actual inputs. Add `--require-tracked --require-complete` for strict acceptance.

Source carriers, deterministic extraction, corpus candidates, asset navigation, and independent review submission APIs are implemented. Source correction reviews, corpus layer audits, and P9 literary comparisons still need independent submissions. Continuous-chapter production, adoption, and publication require their own gates. See the [review runbook](docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md) for submission and acceptance rules.

Chapter competition now derives qualification from bound opinions and author/reviewer identities, using the same result for promotion. Hand-entered PASS flags remain declarations. The historical Chapter 86 winner remains visible, while its current promotion is PENDING (exit code 2). See the [chapter review runbook](docs/runbooks/CHAPTER_COMPETITION_REVIEWS.md). Scene checks now require attributed, hash-bound semantic readings and replay actual exit/knowledge changes. Lexical checks are lint; missing semantic readings return PENDING. See [semantic operations](docs/runbooks/SEMANTIC_SCENE_REVIEW.md).

## Repository layout

| Directory | Purpose |
|---|---|
| `sources/`, `research/` | Fixed source assets and versioned research |
| `corpus/` | Reproducible extractions and versioned text layers |
| `data/catalog/` | Asset identities, origins, and reading collections |
| `data/provenance/` | Sources, Claims, Decisions, and Implementations |
| `data/project/` | Selected state owners and input scope |
| `data/research/`, `data/evaluation/` | Causal alternatives, frozen trials, attributed readings and diagnostics |
| Other `data/` directories | World, characters, objects and scene contracts |
| `releases/` | Stable baseline and immutable release manifest |
| `artifacts/`, `archive/` | Candidates, original reviews, and import audits |
| `docs/` | Architecture contracts and operational runbooks |
| `src/rcwh/`, `schemas/`, `tests/` | Runtime, schemas, and regression checks |

## Find and verify inputs

```bash
rcwh assets list --role CHAPTER_CARD --chapter 92
rcwh assets collections
rcwh assets validate --require-tracked
rcwh sources verify-all --require-tracked
rcwh sources audit
rcwh sources trace decision:cliff-release:function
rcwh corpus verify corpus:front80:v1-candidate --rebuild
rcwh corpus query corpus:front80:v1-candidate --chapter 27 --keyword 红玉
rcwh self-contained check --profile declared-inputs --require-tracked
```

Asset checks verify bytes and identity. Source locator checks verify reproducible excerpts. Independent source review evaluates the evidence interpretation; corpus review evaluates text classification. P9 blind review compares literary originals and revisions. Prepared review packets do not count as submitted opinions.

## Consecutive research trial

```bash
rcwh pilot summary
rcwh pilot export /tmp/chapter-reading-round-1
rcwh diagnostics characters --character zijuan
rcwh diagnostics style data/evaluation/pilot85_87/drafts/medical-86.txt
rcwh diagnostics corpus-focus
rcwh delivery materialize source-review-v2 /tmp/source-review-v2
```

The 85–87 trial contains two causal routes and a direct-writing example, nine short drafts in total. The example has prior Harness exposure and is not a valid control. Two independent whole-sequence readings, fresh control runs and revision/review remain pending. See the [trial runbook](docs/runbooks/CONSECUTIVE_CHAPTER_TRIAL.md).

31.04 MiB of duplicate delivery copies were removed after byte comparison. Registered bundles still materialize offline; [attachment preparation](docs/runbooks/DELIVERY_STORAGE.md) creates checked local files without publishing. Git history retains prior copies.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [complete design](docs/RCWH_红楼梦复原基础设施完整设计_v1.0_20261008.md)
- [Source and corpus design](docs/RCWH_来源闭包与语料建设后续设计_v1.1_20261008.md)
- [Foundation operations](docs/runbooks/FOUNDATION.md) and [search and writing](docs/runbooks/SEARCH_AND_WRITING.md)
- [Asset intake](docs/runbooks/ASSET_INTAKE.md) and [navigation and corpus inputs](docs/runbooks/ASSET_DISCOVERY_AND_CORPUS_INPUTS.md)
- [Source extraction and locators](docs/runbooks/SOURCE_LOCATORS.md) and [Cao manuscript collation](docs/reviews/CAO_FACSIMILE_VERIFICATION_20261009.md)
- [Declared input closure](docs/runbooks/DECLARED_INPUT_CLOSURE.md) and [corpus and review inputs](docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md)
- [Evaluation refactor implementation and remaining reviews](docs/architecture/EVALUATION_REFACTOR_PLAN.md#92-后续实施与真实验收边界2026-10-09)
- [Actual verification reports and prepared trial packets](artifacts/analysis/evaluation-refactor-20261009/README.md)

Historical migration rules have been retired. The [migration decision](docs/decisions/0002_RETIRE_MIGRATION_RUNTIME.md) and [rule retirement decision](docs/decisions/0003_RETIRE_HISTORICAL_RULES.md) describe the retained boundaries. Current progress comes from selected owners and live checks; Git history holds past implementation narratives.

## License

The owner chose to defer licensing on 2026-10-09. No new license is granted. See the [rights inventory and licensing proposal](docs/architecture/RIGHTS_AND_LICENSING.md).
