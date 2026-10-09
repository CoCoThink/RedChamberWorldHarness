# RedChamberWorldHarness (RCWH)

A narrative-world harness for the post-80-chapter reconstruction of *Dream of the Red Chamber* (《红楼梦》).

RCWH loads evidence, world and character state, object ledgers, scene contracts, and literary policies, then validates candidate prose before it can become an accepted reconstruction.

> Evidence is the floor, not the ceiling.

Generated scenes may develop underdetermined areas through character, historical mechanisms, chapter structure, and literary fitness. A reconstruction choice must never silently become historical evidence. Evidence Truth, Reconstruction Truth, Character Truth, and Text Truth remain separate.

## Quick start

Use CPython 3.12.13 to rebuild the registered source extractions; their dependency and extraction rules are fixed in `requirements/extraction.lock.json`.

```bash
python -m pip install -e '.[dev]'
rcwh validate
rcwh project status
rcwh project acceptance
rcwh evaluate data/scenes/ch86_last_night.yaml examples/ch86_candidate_stub.txt
pytest -q
```

`data/project/current.json` selects the current state owners; `data/project/scope.json` declares chapter scope. `project acceptance` computes engineering checks, review status, and production admission from actual inputs. Add `--require-tracked --require-complete` for strict acceptance.

Source carriers, deterministic extraction, corpus candidates, asset navigation, and independent review submission APIs are implemented. Source correction reviews, corpus layer audits, and P9 literary comparisons still need independent submissions. Continuous-chapter production, adoption, and publication require their own gates. See the [review runbook](docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md) for submission and acceptance rules.

## Repository layout

| Directory | Purpose |
|---|---|
| `sources/`, `research/` | Fixed source assets and versioned research |
| `corpus/` | Reproducible extractions and versioned text layers |
| `data/catalog/` | Asset identities, origins, and reading collections |
| `data/provenance/` | Sources, Claims, Decisions, and Implementations |
| `data/project/` | Selected state owners and input scope |
| Other `data/` directories | World, characters, objects, scenes, and evaluation inputs |
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

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [complete design](docs/RCWH_红楼梦复原基础设施完整设计_v1.0_20261008.md)
- [Source and corpus design](docs/RCWH_来源闭包与语料建设后续设计_v1.1_20261008.md)
- [Foundation operations](docs/runbooks/FOUNDATION.md) and [search and writing](docs/runbooks/SEARCH_AND_WRITING.md)
- [Asset intake](docs/runbooks/ASSET_INTAKE.md) and [navigation and corpus inputs](docs/runbooks/ASSET_DISCOVERY_AND_CORPUS_INPUTS.md)
- [Source extraction and locators](docs/runbooks/SOURCE_LOCATORS.md) and [Cao manuscript collation](docs/reviews/CAO_FACSIMILE_VERIFICATION_20261009.md)
- [Declared input closure](docs/runbooks/DECLARED_INPUT_CLOSURE.md) and [corpus and review inputs](docs/runbooks/CORPUS_AND_REVIEW_INPUTS.md)

Historical migration rules have been retired. The [migration decision](docs/decisions/0002_RETIRE_MIGRATION_RUNTIME.md) and [rule retirement decision](docs/decisions/0003_RETIRE_HISTORICAL_RULES.md) describe the retained boundaries. Current progress comes from selected owners and live checks; Git history holds past implementation narratives.

## License

No open-source license is granted yet. The repository owner must decide how to license research data, code, and derivative literary text.
