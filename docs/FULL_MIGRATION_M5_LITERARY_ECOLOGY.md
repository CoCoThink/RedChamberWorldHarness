# Full Migration M5 — Literary Ecology Runtime

Status: **PASS**

M5 converts the Literary Ecology layer from Markdown-only reference use into a structured, queryable cultural/textual runtime. It does not alter stable ACTIVE prose and does not resume Chapter 81—100 literary construction.

## Runtime delivered

The M5 runtime exposes thirteen structured dimensions:

1. front-80 character voice;
2. front-80 chapter grammar;
3. front-80 poetry/ci/qu/verse ecology;
4. qin/qi/calligraphy/painting/theatrical and literary life;
5. medicine/body writing;
6. Buddhism/Daoism/dream/philosophical systems;
7. social occupations/ritual/economy;
8. material life/domestic labor;
9. narrative techniques;
10. post-80 twelve-dimensional gap tracking;
11. G-layer character writing and author-rhyme decisions;
12. post-80 social process/occupational world;
13. poetry/letters/list-text/document/voice ecology.

It additionally provides:

- 18 front-80 voice profiles with post-80 drift prohibitions;
- 16 narrative-technique nodes;
- 15 evidence/text-function nodes;
- complete Chapter 81—100 text-ecology entries;
- complete Chapter 81—100 author-rhyme decisions;
- G01—G16 generation decisions;
- structured Qingbang boundaries;
- structured Ten Duyin evidence/current-C separation;
- structured Xu Zhuangzi material-text interface;
- Daiyu-death text-interface separation;
- direct source tracing to document SHA/path metadata.

## Evidence / generation separation

M5 keeps evidence-backed text existence or function separate from reconstruction and generation.

### Ten Duyin

Locked:

- the title `《十独吟》` exists in the later-text evidence;
- it is after Chapter 64;
- it stands in a comparison relation with `《五美吟》`.

Not locked:

- author;
- exact poetic form;
- exactly ten poems;
- ten persons;
- exact chapter;
- absolute post-80 placement.

The Chapter-85 / Daiyu solution remains a current-C working model only.

### Qingbang

Locked:

- terminal Qingbang function;
- the level system includes 正 / 副 / 再副 / 三副 / 四副;
- known evaluation literals are exactly `宝玉情不情` and `黛玉情情`.

Open:

- whether “警幻情榜” is the formal in-text title;
- complete rosters;
- every level having twelve names;
- a total of sixty;
- almost all other evaluations;
- Baoyu's exact formal placement within the list structure.

### Xu Zhuangzi

Locked:

- Baoyu did not see the poem at the Chapter-21 moment;
- that non-seeing is explicitly a future-step interface.

Open:

- whether Baoyu later personally reads it;
- exact later carrier;
- exact later chapter.

The current material-text route remains replaceable C-level implementation.

### G layer

M5 does not manufacture a lost-poem inventory from literary convenience. The current G-layer policy preserves, among other decisions:

- no Baoyu farewell text before departure;
- no independent long Daiyu elegy;
- no Fengjie death poem/confession text;
- no terminal poem in the current Chapter-100 solution.

P-Lock protects literary quality and boundary discipline; it is not evidence that any generated text belonged to the lost manuscript.

## Query surface

Examples:

`rcwh literary-ecology summary`

`rcwh literary-ecology dimension voice`

`rcwh literary-ecology voice daiyu`

`rcwh literary-ecology technique TECH-06`

`rcwh literary-ecology evidence A01`

`rcwh literary-ecology chapter 92`

`rcwh literary-ecology qingbang`

`rcwh literary-ecology ten-du-yin`

`rcwh literary-ecology xu-zhuangzi`

`rcwh literary-ecology daiyu`

`rcwh literary-ecology g G07`

`rcwh literary-ecology search 十独吟`

`rcwh literary-ecology trace evidence A01`

The CI migration smoke step now exercises Reconstruction, World, Object and Literary Ecology query surfaces together.

## Registry and traceability

M5 registers 27 additional P0 Literary Ecology source documents and reuses two existing World/Literary source documents, for 29 directly participating source documents in the Literary Ecology runtime.

The total DocumentRegistry / ContentHashRegistry cardinality is now:

- **65 documents**
- **65 SHA256 content-hash records**

Object, World, Reconstruction and Literary Ecology nodes continue to resolve through the same registry; no duplicate document identity is created for reused sources.

## Validation

The first complete M5 query/runtime head `fedbc762dac78219e4081a13bded3e4173bff1b8` passed:

- `rcwh validate`;
- migration runtime smoke queries;
- R4 Evidence Core regression;
- Literary Harness / P-Lock / competition checks;
- Promotion Regression;
- `STABLE_POINTER_UNCHANGED`;
- `pytest -q`: **132 passed**.

The final M5 status commits change migration metadata only.

## Completion boundary

M5 satisfies the runnable Literary Ecology query requirement, but it deliberately keeps:

`p0_full_coverage = false`

because M5 is not the final P0 semantic-coverage sweep. M7 must still prove that all effective P0 results are machine represented at the required coverage level, and M8 must close the overall Completion Gate.

Current invariants remain:

- CURRENT Markdown-only islands: **0**;
- stable ACTIVE changed: **false**;
- Completion Gate ready: **false**.
