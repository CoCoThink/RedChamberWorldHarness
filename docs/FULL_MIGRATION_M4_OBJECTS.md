# Full Migration M4 — Object Network Runtime

Status: **PASS**

M4 converts key post-80 material objects from scattered chapter notes into a queryable continuity network. It does not alter stable ACTIVE prose and does not resume Chapter 81—100 literary construction.

## Runtime delivered

- 17 modeled object nodes;
- 29 replayable object transitions;
- explicit holder/location/status state;
- explicit movement modes for every location change;
- one OPEN identity edge separating the Chapter-91 snow jade from the Tongling jade;
- two containment relations;
- object-level source tracing to registered documents and Reconstruction evidence nodes;
- continuity validation that blocks implicit teleportation.

## Critical jade discipline

The runtime deliberately keeps two nodes:

- `OBJ-TONGLING-JADE`
- `OBJ-SNOW-JADE-91`

Their relation is:

`MAY_BE_SAME_AS / OPEN_LOCKED_NONMERGE`

Therefore the Chapter-91 snow object cannot silently become the Tongling jade. The current-C Chapter-98 mistaken-package route is represented only as a replaceable implementation of R16/R18. At Chapter 99, the earthly route is explicitly set to UNKNOWN instead of inventing an abandonment ritual. At Chapter 100 only the outer-frame identity state changes to `RETURNED_TO_ESSENCE_QINGGENG_FRAME`; no physical transport path is fabricated.

## Other continuity chains

M4 also models:

- Wei Ruolan's large golden qilin appearance;
- Chapter-86 medicine bowl temperature continuity;
- Tanchun travel chests;
- post-confiscation bedding relocation;
- permitted winter-clothes retrieval;
- Chapter-92 detention delivery package;
- Fengjie legacy household-control bundle;
- Qiaojie transfer bundle;
- Chapter-95 rice, charcoal, old felt and pawnable jacket;
- Chapter-97 nunnery lamp oil;
- Chapter-98 Zhen visitor package;
- Chapter-100 Jia Lan official robe.

These nodes are downstream World/Reconstruction implementations. Their presence does not promote C-level detail to original-manuscript fact.

## Query surface

Examples:

`rcwh object summary`

`rcwh object get OBJ-TONGLING-JADE --chapter 98`

`rcwh object history OBJ-TONGLING-JADE`

`rcwh object jade --chapter 91`

`rcwh object location S07 92`

`rcwh object continuity`

`rcwh object trace OBJ-TONGLING-JADE`

The trace command resolves object and transition source references back to registered document SHA/path metadata and Reconstruction R nodes.

## Validation

The first complete M4 runtime head `e63bf12be655252e354abdc048b0d31bc59b3d35` passed:

- `rcwh validate`
- R4 Evidence Core regression
- literary/P-Lock/competition/promotion regression
- stable pointer regression
- `pytest -q`: **120 passed**

The final status commits are metadata/documentation only.

## Completion boundary

M4 achieves a runnable Object Network and explicit no-teleport checking, but the overall Full Migration Completion Gate remains closed. M5 is responsible for Literary Ecology / text-object / literary-output relationships; M7 remains responsible for the final P0 semantic-coverage sweep.
