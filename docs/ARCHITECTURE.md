# RCWH Architecture v0.1

## 1. Harness, not knowledge base

RCWH treats reconstruction as a controlled runtime. A language model may propose prose, but the harness decides what state is legal, what a character can know, what objects exist where, which historical mechanisms are available, and which evidence claims can or cannot be promoted.

## 2. Four truth layers

### 2.1 Evidence Truth
What extant sources support. This layer records witness provenance, evidence role, modality, literal target, and placement. It is immutable from downstream prose.

### 2.2 Reconstruction Truth
What the current accepted reconstruction says happened. This is event-sourced and versioned. It can change after literary competition without altering Evidence Truth.

### 2.3 Character Truth
What a character knows, believes, suspects, remembers, misunderstands, or cannot know at a given scene.

### 2.4 Text Truth
Exact wording permissions. `NOVEL_EXACT` may require a string in prose; `SOURCE_EXACT` does not. A critic's phrase is not automatically a novel sentence.

## 3. Event sourcing

World state is derived from an ordered event log rather than hand-editing many status tables. An event has preconditions, effects, evidence links, and implementation status. Replacing one event allows deterministic downstream revalidation.

## 4. Scene contract

A scene contract is an executable writing brief:

- preconditions;
- participating characters and their local knowledge;
- required objects;
- required beats;
- forbidden beats;
- historical adapters invoked;
- P-Locks;
- exit state.

The generator writes inside the contract; evaluators decide whether the candidate can advance.

## 5. Evaluator pipeline

1. Schema validation
2. Evidence evaluator
3. Character-knowledge evaluator
4. Object-state evaluator
5. Timeline evaluator
6. Historical-mechanism evaluator
7. Literary-policy evaluator
8. Ambiguity evaluator
9. Regression evaluator
10. Blind-read/human gate

No single score can override a hard failure.

## 6. Release lanes

- `research`: speculative structured hypotheses.
- `staging`: candidate scene/prose.
- `candidate`: passed hard validators, awaiting literary competition.
- `active`: accepted reconstruction baseline.
- `archive`: superseded but auditable.

Promotion must be explicit and reversible.
