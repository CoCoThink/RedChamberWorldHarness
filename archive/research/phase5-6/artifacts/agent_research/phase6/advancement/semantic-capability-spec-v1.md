# P3 semantic capability audit and minimal specification v1

## Status and authorization boundary

- Classification: **MODEL_SUBAGENT / NONE**. Research specification and read-only observations, not human review, provider authentication, literary adoption, evidence admission, or release authorization.
- Approved plan read: `/home/guan/.claude/plans/valiant-doodling-rabin.md`, especially P3 and the confirmation boundaries. The follow-up instruction authorized creation of this new file only. No existing code/schema/data was edited; no delegation, release build, commit, snapshot replication, or full evaluation was performed. In particular, the coordinator's denied full-snapshot operation was not retried here.
- This document specifies proposed behavior; none of the proposed consumers, schemas, records, or tests below has been implemented or executed. Existing fixed PENDING / NOT_CHECKED results remain in force.
- Repository root for every relative locator below: `/mnt/d/Code/RedChamberWorldHarness`.

## 1. Actual selection and reproducible inventory

Inventory was computed by parsing the actual release request, then each selected package's `plan` bindings and policy. It was not inferred from directory sizes, editor summaries, or an assumed latest revision.

Selection authority for this audit:

- `artifacts/agent_research/phase6/revisions-v2/release-evaluation/request-v1.json`
- Actual file SHA256: `9a2da8de544bbaa1e83e2984dc7db4cb142fc4423892a12673284c22bf66f47b`.
- Historical evaluation: `artifacts/agent_research/phase6/revisions-v2/release-evaluation/report-v3.json`.
- Reading-only selection: `artifacts/agent_research/phase6/revisions-v2/continuity-reading-selection-v1.json`. It selects 86 v1 and 91 v2, not the available 86 narrow v2. It does not grant adoption or release.
- Every selected package is `data/writing/packages/ch{chapter}-agent-research-v3.json`.
- Every selected policy is `data/promotion/policies/agent/ch{chapter}.v1.json`.
- Verified current policy/package/candidate bindings: **20/20 each**, zero mismatches. Verified all package plan bindings: zero mismatches. All 20 policies also passed `validate_agent_policy` re-derivation against current frozen inputs.

Exact selected contracts and policy coverage:

| Chapter | Policy anchors | Forbidden rows | Semantic root obligations | Contract count | Selected IDs and revisions |
|---|---:|---:|---:|---:|---|
| 81 | 0 | 1 | 9 | 3 | 81-S1.v2, 81-S2.v2, 81-S3.v2 |
| 82 | 0 | 1 | 9 | 2 | 82-S1.v2, 82-S2.v2 |
| 83 | 0 | 1 | 9 | 3 | 83-S1.v2, 83-S2.v2, 83-S3.v2 |
| 84 | 0 | 1 | 9 | 4 | 84-S1.v2, 84-S2.v2, 84-S3.v2, 84-S4.v2 |
| 85 | 1 | 1 | 11 | 3 | 85-S1.v2, 85-S2.v2, 85-S3.v2 |
| 86 | 2 | 4 | 17 | 6 | 86-S1.v2, 86-S2.v2, 86-S3.v2, 86-S4.v2, 86-S5.v2, 86-S6.v2 |
| 87 | 1 | 1 | 14 | 5 | 87-S1.v2, 87-S2.v2, 87-S3.v2, 87-S4.v2, 87-S5.v2 |
| 88 | 2 | 1 | 19 | 5 | 88-S1.v2, 88-S2.v2, 88-S3.v2, 88-S4.v2, 88-S5.v2 |
| 89 | 1 | 4 | 16 | 6 | 89-S1.v2, 89-S2.v2, 89-S3.v2, 89-S4.v2, 89-S5.v2, 89-S6.v2 |
| 90 | 1 | 1 | 13 | 3 | 90-S1.v2, 90-S2.v2, 90-S3.v2 |
| 91 | 0 | 1 | 15 | 4 | 91-S1.v2, 91-S2.v2, 91-S3.v2, 91-S4.v2 |
| 92 | 0 | 5 | 25 | 6 | 92-S1.v2, 92-S2.v2, 92-S3.v2, 92-S4.v2, 92-S5.v2, 92-S6.v2 |
| 93 | 0 | 1 | 11 | 5 | 93-S1.v2, 93-S2.v2, 93-S3.v2, 93-S4.v2, 93-S5.v2 |
| 94 | 0 | 1 | 11 | 6 | 94-S1.v2, 94-S2.v2, 94-S3.v2, 94-S4.v2, 94-S5.v2, 94-S6.v2 |
| 95 | 0 | 1 | 14 | 3 | 95-S1.v2, 95-S2.v2, 95-S3.v2 |
| 96 | 0 | 1 | 12 | 4 | 96-S1.v2, 96-S2.v2, 96-S3.v2, 96-S4.v2 |
| 97 | 3 | 5 | 18 | 4 | 97-S1.v2, 97-S2.v2, 97-S3.v2, 97-S4.v2 |
| 98 | 0 | 1 | 19 | 3 | 98-S1.v3, 98-S2.v3, 98-S3.v3 |
| 99 | 0 | 1 | 13 | 5 | 99-S1.v4, 99-S2.v4, 99-S3.v4, 99-S4.v4, 99-S5.v4 |
| 100 | 3 | 5 | 25 | 5 | 100-S1.v3, 100-S2.v3, 100-S3.v3, 100-S4.v3, 100-S5.v3 |
| **Total** | **14** | **38** | **289** | **85** | **85 distinct selected paths** |

Exact path expansion: first 72 contracts, chapters 81–97, are `data/planning/contracts/agent-final-v1/{ID}.{revision}.json`; final 13, chapters 98–100, are `data/planning/contracts/agent-final-v2/{ID}.{revision}.json`. No `88-S3b` seed exists under `data/planning`.

Policy obligation kind counts:

- CURRENT_IMPLEMENTATION 91; FORBIDDEN_DRIFT 38; CROSS_CHAPTER_CONTEXT 100; SEMANTIC 5; DECISION_BOUNDARY 31; PLOCK_REVIEW 5; TERMINAL_PLACEMENT 3; LEGACY_BOOK_SCOPE_NOT_PROJECTED 1; TITLE_BOUNDARY 14; SOURCE_ONLY 1. Sum **289**.
- The 38 forbidden rows repeat obligations already represented by FORBIDDEN_DRIFT; do not count them as 38 additional independent checks.
- CROSS_CHAPTER_CONTEXT means five distinct rules repeated into all 20 chapter policies. All five require a bound selected-book context; repetition does not create 100 independent protections/readings.
- Five mandatory P-Locks: 86, 89, 92, 97, 100. Their nested `required_features` total **20**. A single PLOCK_REVIEW checkbox must not hide those 20 feature checks.
- Anchor modes: CONTAINS 12, HEADING_CONTAINS 1, HEADING_EXACT 1. Anchor presence is not a semantic verdict.

Contract obligation/input counts:

| Category | Count | Actual status/detail |
|---|---:|---|
| Required beats | 280 | 197 with `id`, 83 without `id` |
| Forbidden beats | 219 | 140 with `id`, 79 without `id` |
| Total beat rows | 499 | 337 use id/description/grounding/scope/status shape; 162 use description/epistemic/source_records/citations/boundary shape |
| Entry targets | 140 | KNOWN 41, UNKNOWN 99 |
| Preconditions | 94 | KNOWN 12, UNKNOWN 80, PENDING 2 |
| Exit targets | 151 | PENDING 30, UNKNOWN 121; **zero KNOWN** |
| Total state-comparison slots | 385 | 53 KNOWN, 332 UNKNOWN/PENDING |
| Unresolved entries | 812 | Spread across all 85 contracts |
| World event refs | 15 | 14 contracts have nonempty lists |
| Object-transition refs | 24 | 15 contracts have nonempty lists |
| Knowledge-event refs | 2 | One contract has a nonempty list |
| Entry checkpoints | 85 | CHAPTER_ENTRY 20, UNKNOWN 65 |
| Participant status | 85 | KNOWN 26, PENDING 58, UNKNOWN 1 |
| Explicit NARRATIVE_ONLY_NOT_EXECUTABLE contracts | 13 | All selected chapter 98–100 contracts |

These are coverage slots, not validated narrative events or independent facts. Minimum contract reading inventory is **499 beat + 385 condition = 884 slots**, plus function, identity, order, knowledge/context boundaries and 812 unresolved entries. State slots with unknown values cannot receive an executable PASS.

## 2. Recomputed current capability, not a new release evaluation

Read-only direct calls were made to `validate_agent_policy`, `evaluate_agent_policy`, and `inspect_contract` for the actual selected inputs. Python bytecode writing was disabled for local runtime imports. No full AgentRelease evaluation or snapshot was run.

- Policy structure/binding: **20 PASS**.
- Actual selected candidate anchor status: **19 PASS / 1 FAIL (86 v1)**. Its two P-Lock exact anchors are missing. Semantic status: **20 PENDING**. The available 86 narrow v2 has anchor PASS but safety/semantics PENDING; it is not substituted into the selection.
- Contract declared tier: **85 PENDING / 0 PASS / 0 FAIL**.
- Deterministic tier: **20 PENDING / 65 NOT_CHECKED / 0 PASS / 0 FAIL**.
- Prose semantic tier: **85 NOT_CHECKED / 0 PASS**.
- Deterministic subchecks include **53 state MATCH/PASS**, **57 state UNKNOWN/PENDING**, **20 incomplete replay coverage**, **20 unresolved/draft-incomplete replay**, **65 unsupported local entry checkpoints**, and **4 unbound knowledge checkpoints**. Fifty-three comparison successes are not 53 executable contracts; no contract has aggregate replay PASS.
- All 85 have `CONTRACT_UNRESOLVED`; declaration checker reports 332 unknown state slots and 59 unresolved participant sets; one required state field is empty.

Historical `report-v3` has policy 19 PENDING/1 FAIL, contract peers 20 PENDING, writing package 19 PASS/1 FAIL, corpus peers 19 FAIL/1 PENDING, source peers 20 PENDING. Its chapter 86 input operation fails on three unresolved dependent source assets before exposing its advisory reports and supplemental gate. Consequently report-v3 contains only **79 advisory reports**, not the 85 actual selected contracts. The direct inventory above includes the six omitted 86 contracts.

Supplemental scope is **four package dependencies (86/87/89/95), one shared selected source set, three source records, three claim records, one byte-bound reading ref**. Historical evaluation exposes the supplemental PENDING gate for only three chapters because 86 exits the input operation early. Do not infer that only three packages use supplemental records.

## 3. Existing consumers and their exact meanings

### 3.1 Policy

`src/rcwh/agent_policies.py` derives all frozen rule inputs, verifies input bytes/projection/pointers by re-derivation, and checks actual chapter headings and literal anchors. `review_refs` are byte-checked only. Declared policy status PASS has no safety effect. Free text, forbidden drift, title placement, terminal function, unfinished writing, object chains, P-Lock features and cross-chapter restrictions remain semantic obligations.

`src/rcwh/workflow/agent_release.py`, `_policy` lines 304–338:

- The agent policy branch checks anchors and mandatory P-Lock machine readiness, then returns PENDING at line 324. This is intentionally conservative missing dedicated candidate-protection semantics, not permission to remove PENDING.
- The legacy chapter-policy branch has a different explicit changed-set/book-string/P-Lock contract. Its behavior must remain unchanged. It is not a fallback for a 20-chapter agent release.
- A new research policy consumer may satisfy the missing semantics only if it actually reads the exact selected candidate against every obligation and preserves the machine failures and P-Lock protections. It cannot use old review-ref bytes, general literary PASS, editor declarations or substring counts as that reading.

### 3.2 Advisory contracts and release gate

`src/rcwh/planning/contracts.py`:

- `inspect_contract` distinguishes declared compatibility, deterministic world-state replay, and prose-supported semantic replay. The final tier is hard-coded NOT_CHECKED in `_report`.
- World/objects/knowledge and referenced records must be bound. Declaration and scene planning records cannot serve as physical state basis. A model reading cannot inject entry or exit values.
- Current deterministic replay supports only order-1, explicit previous-chapter entry and registered event prefixes. For later scenes it returns NOT_CHECKED instead of manufacturing scene-local state.
- It suppresses `entry_state` overrides before projecting runtime state. A future consumer must preserve that safeguard: `SceneStateProjector.entry` otherwise accepts local declared overrides.
- Replay checks actual registered effect paths, object from-state/movement, event prefixes, explicit knowledge scene and comparisons. Unchanged exit values without a bound transition do not receive inferred persistence PASS.
- World effects supported by this checker are character effects, not arbitrary `global.*` or `relations.*` writes; those require explicitly designed support, not ignored effects.

`src/rcwh/workflow/admission.py`, `chapter_scope(..., plan_contracts=True)`, selects actual package-bound overlays and retains legacy executable scenes. Chapters 86/89/92 cannot replace required executable coverage with overlays alone. Existing executable files are `data/scenes/ch86_last_night.yaml`, `ch89_confiscation_message.yaml`, `ch92_delivery_gate.yaml`.

`src/rcwh/workflow/agent_release.py`, `_inputs` lines 216–238, requires exact package/contract peer subjects in the candidate's packet AND all three advisory tiers PASS. Clearing only prose semantics therefore does not clear CONTRACT_PEERS for these 85 contracts. Explicit NARRATIVE_ONLY cannot be converted to executable PASS or skipped as not applicable.

`src/rcwh/planning/checking.py` checks seed/source-list order and explicit predecessor consistency. A PASS there is declaration consistency, not execution of the separate editor narrative index.

`src/rcwh/generation/render.py` keeps agent overlays advisory and separate from executable legacy scenes; non-executable research seeds become SCENE_SKELETON entries. `generation/writing.py:feedback_report` deliberately marks skeletons PENDING and does not execute them.

### 3.3 Existing semantic lane: reusable mechanics, not a drop-in consumer

`src/rcwh/evaluation/semantics.py` provides:

- Rebuilt request identity, canonical contract hash, candidate UTF-8 hash and frozen entry/authors context hash.
- Exact Unicode code-point `[start,end)` evidence and quote equality.
- Separation of ACTUAL from NEGATED/HYPOTHETICAL/DREAM/METAPHOR/QUOTED; physical effects require action/narration, not mere speech/thought.
- Required/forbidden beats, chronological final state, knowledge acquisition with prior actual observable/communication source, coverage and unresolved checks.
- Authorship/producer constraints and actual execution-trace verification for its MODEL lane.

Existing callers: `evaluate.py:evaluate_scene_text`, `evaluation/candidates.py:candidate_semantics` (competition; imported by `competition.py`), `generation/writing.py:feedback_report`, `application/evaluation.py` semantic prepare/run/check, and `workflow/review_intake.py`. `candidate_semantics` uses legacy YAML scene contracts, not all advisory contracts. `registered_reading` returns the first matching legacy record, not all negatives: do not reuse that selection behavior for a new research aggregate.

Compatibility limits:

1. Existing `make_request` expects every beat to have `id`; **162/499 selected beat rows do not**. Contract schema permits arbitrary beat objects. Null/unknown advisory exits also cannot be treated as established targets.
2. Existing MODEL semantic lane requires verified author/model family and extractor trace; author sessions here are `SESSION_AUTHORED_NOT_PROVIDER_VERIFIED`. Their `SESSION_AUTHOR_RUN` records are not the legacy `candidate_model_run` contract. Relabeling or inventing provider traces would be invalid.
3. Existing semantic context binds entry/authors, not this complete policy/package/selection/narrative-decision universe.
4. Existing checker cannot establish that a natural-language event label faithfully interprets its quote. Exact quotes are auditable anchors, not semantic truth proofs.

Therefore reuse pure binding/span/state concepts; create a separately named research record and validator. Do not expand legacy/human qualification or import new research records into `data/evaluation/scene_readings.json`.

### 3.4 Supplemental evidence

`src/rcwh/provenance/research_inputs.py:ResearchSourceInputs.report` intentionally returns PENDING evidence with PASS integrity, never graph supersession. Reading refs prove bytes only; derivative text does not establish facsimile fidelity or historical authority. `src/rcwh/literary_inputs.py` preserves SUPPLEMENTAL_RESEARCH_EVIDENCE_PENDING; production rejects these research source sets. `workflow/agent_release.py:214` fixes SUPPLEMENTAL_SOURCE_EVIDENCE to PENDING after integrity checking.

A policy/contract semantic reader has **no authority to clear this gate**. Original meaning would require a dedicated source-scope/evidence consumer: exact source-set/claim/dependency bindings; carrier/derivative/original identity distinctions; appropriate locator and actual context review; precise claim-support limits; valid negative precedence; no historical-feasibility-to-narrative-event upgrade. The selected set itself does not implement that protocol. Whether P1 can establish a sufficient research evidence path without changing the original gate remains **unconfirmed**. Keep this gate PENDING; do not treat absence of human qualification as automatic N/A. Do not globally merge sidecars or satisfy the original three chapter-86 carrier dependencies by a string-ref hit.

## 4. Four concrete runtime input gaps

### 88: missing post-marriage seed

Five actual seeds/contracts cover S1–S5; **88-S3b does not exist**. The cards require a completed marriage followed by a short return/thanks and the hard quote “好歹留着麝月”. Existing contracts explicitly mark that gap. A literal hit in a premarital scene is not completion or correct placement.

Minimal future input: a new versioned scene/plan/contract selection that explicitly represents marriage completion, return event, intended addressee/knowledge context and its actual candidate spans, with a supported local entry and exit if execution is claimed. Preserve old five seeds and negatives. This does not authorize adding the sixth seed now or inventing full wedding world history.

### 98: personal carrier versus messenger

Selected `data/planning/contracts/agent-final-v2/98-S3.v3.json` and `data/planning/decisions/phase6-ch98-v1.json` choose personal carriage by 甄宝玉 of the same mis-taken package. Frozen `data/objects/m4.json` OT98-04.to.holder and OT98-05.from.holder are **zhen_messenger**. The new contract removes OT98-04/05 as support and binds only OT98-01/02/03 earlier context. No new personal transport event exists.

Minimal future input: an explicitly selected, versioned object/world route with legitimate from-state, personal carrier identity, movement/delivery/receipt and package continuity. Do not alias messenger to 甄宝玉 or reinterpret delivery responsibility as personal transport. Keep snow-jade identity and full historical custody OPEN. Old messenger route and old failures remain preserved. New input would entail a new package and honest preparation/generation lineage, not rebinding existing prose.

### 99: source index, presentation order, runtime chronology

Selected v4 contract orders remain S1,S2,S3,S4,S5; `entry_from` follows that source index. `data/planning/decisions/phase6-ch99-v1.json` separately declares presentation **S1,S2,S5,S3,S4**, S4 the final domestic shot. Neither inspect/check_selected executes that decision. W99's chapter-level temple/monk terminal state is not proof of travel, first arrival or the exact moment of ordination.

Minimal future interface: bound sequence decision plus distinct source index, presentation index, chronological event order and scene checkpoint references. Require a bijection over selected scenes; do not rewrite seed.order or source predecessor. Check actual S5 presentation before S3/S4 and no temple cut after S4; do not transfer reader knowledge of S5 to 贾芸/宝钗/麝月. Actual travel/admission and knowledge transmission remain unknown unless independently supplied as new runtime inputs.

### 100: frame identity and stone endpoint

Selected `100-S5.v3` has participants `[]`, status UNKNOWN: no bindable registered frame actors, **not no narrative actors**. 警幻 and 空空道人 are grounded narrative role names but lack runtime registry IDs. The stone endpoint is an explicit C terminal obligation, not satisfied by a title or transcription alone. OT100-01 changes only frame_status to RETURNED_TO_ESSENCE_QINGGENG_FRAME, with movement NONE and earthly holder/location UNKNOWN; selected object/world refs are not complete chapter-entry prefixes.

Minimal future interface: separate human, 太虚 and 青埂 frame segments; typed narrative mentions with nullable registry_id; explicit frame-state evidence/transition and local checkpoint support if replay is claimed. Never generate placeholder identities to pass an entity check, turn listed names into present actors, infer heavenly-to-earthly knowledge, or convert frame return into physical jade transport. A prose semantic reading can recognize a stated frame endpoint while actor binding and executable replay stay PENDING. Supporting a new frame actor/runtime schema must be separately reviewed before any implementation.

## 5. Minimal dedicated research semantic schema and API (proposed)

Proposed module: `src/rcwh/evaluation/research_semantics.py`. Proposed independent schema: `schemas/research_semantic_reading.schema.json` and request/manifest definitions in it. These names do not exist as a result of this audit.

Use one validator with two explicit subject kinds: POLICY_PROTECTION and ADVISORY_CONTRACT_PROSE. Do not make it a source-evidence validator. An optional pure narrative observation product would be named RESEARCH_NARRATIVE_CONSISTENCY, never AgentRelease PASS; adopting that different output requires the plan's separate confirmation.

### 5.1 Request

Strict JSON, duplicate/nonfinite keys rejected, `additionalProperties:false` at every structured level:

```
ResearchSemanticRequestV1 {
  schema_version: 1,
  kind: "RESEARCH_SEMANTIC_REQUEST",
  subject_kind: "POLICY_PROTECTION" | "ADVISORY_CONTRACT_PROSE",
  chapter: integer,
  selection: FileBinding,
  candidate: FileBinding,
  draft: FileBinding,
  writing_package: FileBinding,
  policy: FileBinding | null,
  contract: FileBinding | null,
  context_inputs: FileBinding[],
  authors: DeclaredActor[],
  author_contexts: BoundContextDisclosure[],
  obligation_manifest: Obligation[],
  scene_scope: BoundSceneScope | null,
  prompt_sha256, schema_sha256, validator_version,
  request_sha256, context_sha256, obligation_manifest_sha256,
  qualification: "MODEL", authority_effect: "NONE", evidence_effect: "NONE",
  independent_human_admission: false
}
```

`FileBinding={path,sha256}` checks raw bytes under repository confinement. `context_inputs` includes selected policy input files, package/seed/plan and all consulted source records/citations, world/object/knowledge inputs, narrative decision, author/reviser lineage/disclosures, selected-book chapter map for cross-chapter obligations, prompt/schema and coverage-manifest version. Bind only actually used dependencies; do not cause accidental global catalog invalidation. Request rebuilding must reconstruct all these bindings from the explicit selection and reject a dropped dependency. Frozen selection changes stale context; merely changing an opinion does not silently mutate substantive context.

Candidate offsets are Unicode code points in the exact UTF-8 decoded candidate, without newline/punctuation/Unicode normalization. File SHA is over exact bytes. Structured rule values use an explicitly versioned canonical-JSON hash; do not confuse it with file SHA.

`DeclaredActor` includes principal_id, source_id, session_id, context_id, kind fixed MODEL, declared model label if known, raw execution or submitted-file binding, execution_basis and disclosure. Unknown model/provider stays unknown. All authors/revisers from the bound lineage are included, not just the latest author. Shared real context must be disclosed even when chapter session labels differ.

### 5.2 Obligations: immutable addressing and complete expansion

```
Obligation {
  key: subject-file-sha + "#" + JSON-pointer,
  source_binding, pointer, canonical_value_sha256,
  declared_id: string | null,
  category,
  original_value,
  scope: CHAPTER | SELECTED_BOOK | SOURCE_BOUNDARY | FRAME_SEGMENT,
  required_context: binding-key[],
  mandatory: true,
  parent_key: key | null,
  facets: BoundFacet[]
}
```

Derive keys from exact path/hash/pointer, not model-generated IDs. Preserve all 499 beat rows, including the 162 without id; pointer keys also prevent collisions across scenes. Required/forbidden/state/knowledge target namespaces are distinct. Duplicate IDs or canonical state targets within their declared namespace must fail or be explicitly disambiguated by immutable pointer, never overwritten in a dict.

Policy manifest must contain all **289 roots**, 14 anchor observations and **20 nested required-feature checks**, with explicit parent mappings; this is 289 roots plus feature expansion, not 309 independent root rules. All 38 forbidden rows are crosswalked to their already-counted root obligations. Expand every structured sub-obligation and require a rationale for every normative free-text clause. Keep original prose attached; a model-generated decomposition cannot silently drop a clause. A catch-all `PASS for whole policy` is forbidden. For a complex root whose decomposition or interpretation remains uncertain, root stays UNKNOWN/PENDING.

Policy handling by kind:

- CURRENT_IMPLEMENTATION: keep must_keep, hard boundary, risk and current-placement versus historical-authority distinctions; actual candidate evidence, not declarations.
- FORBIDDEN_DRIFT: quoted counterexamples plus full-scope absence examination; no substring bans substituted for semantic prohibitions.
- PLOCK_REVIEW: all required_features separately; relevant exact-anchor mode/function/sequence/contrast/density, upstream limits and forbidden drift. For 86, independently examine medicine/stove chain, late mundane misunderstanding, unfinished revision rather than completed death poem, care-before-symbol, both exact anchors and terminal function.
- CROSS_CHAPTER_CONTEXT: selected-book bindings or explicit bounded unknown. A chapter-local reader cannot attest a whole trajectory from chapter-local text alone.
- TERMINAL_PLACEMENT: inspect the terminal scene and any following prose, not universal character-level suffix matching. 89's same-scene response is not automatically a forbidden tail; 100's explanatory coda is materially different.
- TITLE_BOUNDARY: T0/T1 exact authority versus TG/T2/T3 working choices; no new exact-title constraint from a baseline title.
- SOURCE_ONLY: verify boundary, neither require insertion nor automatically ban a matching phrase. Do not override the legacy explicit book sentinel.
- DECISION_BOUNDARY/SEMANTIC: required meaning, mode, epistemic/open-placement scope. UNKNOWN modes remain unknown.
- LEGACY_BOOK_SCOPE_NOT_PROJECTED: explicit book-scope boundary acknowledgement, no application of a single-chapter legacy changed-set gate to the 20-chapter agent selection. Keep legacy behavior separately unchanged; any applicable book claim requires bound book evidence rather than chapter-only attestation.

Contract manifest contains the **884 beat/condition slots**, all functions and unresolved entries, participants/required_objects/references, declared predecessors/checkpoints, knowledge interfaces, selected chapter-card obligations and decision/order boundaries. Chapter-card coverage must expose missing 88-S3b rather than declaring completeness merely because five contracts were read. Unknown exits are UNKNOWN entries, never scalar values to be matched. Do not assert all 812 unresolved items resolved through one prose reading.

### 5.3 Submitted reading

```
ResearchSemanticReadingV1 {
  kind: "RESEARCH_SEMANTIC_READING",
  request_sha256, candidate_sha256, subject_sha256,
  context_sha256, obligation_manifest_sha256,
  reader: DeclaredActor,
  context_isolation: {asserted:boolean, verification:"NOT_PROVEN", disclosures:...},
  read_scope: {candidate_intervals: Span[], context_bindings: FileBinding[]},
  checks: [{obligation_key,
            finding: "SUPPORTED"|"VIOLATED"|"UNKNOWN",
            evidence: Evidence[], counterevidence: Evidence[],
            examined_scope: Span[], explanation:string,
            unresolved: string[]}],
  events: ResearchEvent[],
  unknowns: ...,
  qualification:"MODEL", authority_effect:"NONE", evidence_effect:"NONE",
  independent_human_admission:false,
  raw_submission: FileBinding
}
```

No submitted overall PASS field. `Evidence` binds a source file/hash and exact `[start,end,quote]`; rule evidence may additionally use a checked JSON pointer/value hash. Candidate positive evidence must come from actual candidate prose, not the prompt, title alone, chapter card, model reasoning or another candidate. Validate all quotations, including counterevidence. Scope intervals must be in range; complete-reading claims must cover the full required candidate/context rather than just evidence snippets. Negative absence claims require explicit full-scope examination and rationale; they are attributed semantic judgements, not algorithmic proof of absence.

`ResearchEvent` contains stable local id, presentation position, explicitly declared chronological order/partial-order links, bound scene/segment, actor mention plus nullable registry_id, ACTION/NARRATION/DIALOGUE/THOUGHT mode, ACTUAL/NEGATED/HYPOTHETICAL/DREAM/METAPHOR/QUOTED scope, spans, obligation refs, observation/communication source and intended recipients, and supported runtime-event refs if any. `FRAME_SEGMENT` is a domain boundary, not a physical movement. A named narrative role with null registry_id is representable in a prose observation; it cannot satisfy an executable participant binding.

All extracted effects are **observations only**, never authoritative state writes. Deterministic replay remains a separate computation from registered runtime events. Later chronological actual change wins only within a declared timeline; presentation order alone cannot reorder causal changes or knowledge acquisition. Ambiguous order produces UNKNOWN rather than an invented time.

### 5.4 Pure APIs and output

```
build_research_semantic_request(root, *, selection, chapter,
    subject_kind, subject, candidate, draft, writing_package) -> Request

validate_research_semantic_reading(root, request, reading) -> ReadingCheck

aggregate_research_semantics(root, request, *, registered_readings) -> ComputedReport
```

Builder/validator/aggregate are read-only. Intake, if later approved, stores exact raw original JSON plus content-addressed receipt/envelope and an append-only index. No external model/API is called by validation. Actual session/file submissions are acceptable research custody evidence with their truthful execution basis; they are not relabeled as provider-verified extraction traces.

Computed report includes integrity_status, coverage_status, identity_eligibility, semantic_status, per-obligation findings, all reading refs, active_negatives, historical_negative_crosswalk, pending reasons, evidence/authority NONE, qualification MODEL, independence_basis DECLARED_IDENTITIES_AND_CONTEXT_DISCLOSURES_NOT_AUTHENTICATED, automatic_literary_pass false, independent_human_admission false. For contracts it also returns **the three tiers independently**. Never return executable PASS solely because semantic_status is PASS.

### 5.5 Identity/context and negative precedence

- Minimum research positive rule proposed: two complete attributed readings on the same exact request/manifest/context, distinct declared reader IDs AND distinct sessions AND distinct actual contexts, neither author/reviser nor coordinator. Count via matching, not raw receipt count. A repeated identity, reused context, duplicate alias, missing author lineage, or unasserted/contradicted isolation cannot fill a positive slot. This is local declared research independence only, not authenticated external independence.
- Do not change `asserted:false` to true. Unknown or contaminated isolation remains PENDING. Same model family by itself is not proof of independent context or of its absence; disclose family without importing legacy provider-verification claims. If the intended original gate requires stronger external independence than can be honestly established, stop at PENDING rather than silently weaken it.
- Inspect **all** registered raw records/receipts for the subject; no first-match/latest/favorable-only lookup. A new packet with identical subject bytes cannot hide existing valid negative evidence. Missing receipts, altered raw output, conflicting duplicate fields or bad binding is an integrity FAIL, not a removable unfavorable opinion.
- Any valid same-subject applicable VIOLATED finding or computed machine/deterministic FAIL dominates positive counts and coordinator ADOPT. Negative evidence is retained even when the reader cannot count positively for independence; self-review cannot clear its own failure. Unsupported/malformed allegations are reported as integrity/qualification findings, not converted into fabricated proof of a narrative violation.
- Context differences cannot erase a negative about unchanged candidate+rule bytes; preserve it as active unless a substantive changed input is explicitly crosswalked. New candidate/rule versions create new subjects, not retroactive acquittal. Preserve old FAILs and explicit per-negative applicability mapping; unresolved mappings keep PENDING.
- Precedence: integrity or supported substantive failure => FAIL; otherwise missing evidence/coverage/identity/context/state => PENDING; PASS only when every required dimension passes with no valid negative. No majority vote, score, model label, or coordinator narrative overrides a valid FAIL.

## 6. Consumer decisions preserving original gate meaning

| Existing gate/tier | Could genuinely satisfy original meaning | Must stay blocked/PENDING in present selection |
|---|---|---|
| Agent CHAPTER_SAFETY_POLICY | Existing anchor/P-Lock machine checks plus complete dedicated exact-candidate protection readings, bound context, every mandatory obligation, truthful eligible research identity and no valid negatives | All 20 until implemented and actually read; 86 v1 remains FAIL. Narrow 86 v2 needs explicit new research selection and full review, not automatic replacement |
| Declared contract compatibility | Valid selected bytes, grounded participants/state/references, justified complete declarations; no unresolved obligations left falsely marked known | 85 PENDING, 812 unresolved entries; unknown state is not resolved by reader opinion |
| Deterministic contract replay | Real selected entry checkpoints, registered continuous legal event prefixes or explicitly implemented checkpoint chains, lawful effects/from-states, explicit exits and knowledge acquisition | 20 PENDING + 65 NOT_CHECKED. No automatic NARRATIVE_ONLY exception; future support must use versioned real inputs, not model-injected state |
| Prose-supported contract semantics | Dedicated bound complete candidate/contract readings, actual events/evidence/order/knowledge guards, no active negatives | 85 NOT_CHECKED today. A separate research prose result may pass while original deterministic tier stays blocked |
| CONTRACT_PEERS | Original three tiers all PASS AND exact package/contracts peer coverage in candidate packet | All 20 chapter gates PENDING. Literary/editorial panel PASS cannot replace replay |
| SUPPLEMENTAL_SOURCE_EVIDENCE | Dedicated source/evidence protocol and consumer proving exact support scope at the intended research level; complete dependencies, correct carrier identities, binding/context review, all negatives preserved | Four dependencies PENDING; current integrity product cannot grant evidence readiness. P3 semantic reading cannot clear this gate |
| Legacy/human semantics, production, stable | Only their existing genuine qualification/protocol inputs | Unchanged; new research records confer no human/provider qualification or stable authority |

Minimum implementation sequence after specification review: (1) pure manifest/request/binding validator and real selected-inventory regression fixtures; (2) dedicated research reading intake/aggregation, retaining exact raw records and negative precedence; (3) candidate-bound policy consumer; (4) separately scoped contract prose consumer; (5) only justified versioned runtime checkpoint/input extensions for actual selected needs. Do not add 85 invented event systems to fill a table. Do not wire supplemental evidence to policy semantics. Any gate-meaning change, separately branded narrative output, global dependency registration or new-package migration cost requires the plan's explicit confirmation.

## 7. Concrete negative/compatibility test design

Proposed tests; **not run**. Real fixture bases should be selected bytes above plus temporary versioned minimal worlds, not mocks that return PASS from every inspect call.

1. Exact inventory: 20 policies/85 contracts/72+13 directories; 289 roots/20 P-Lock features/499 beats/385 condition slots; no dropped 86 contracts when old input evaluation fails early.
2. Remove one policy input/obligation/P-Lock feature/forbidden mapping => coverage/binding rejection. Mutate declared policy status or review_refs to PASS => no semantic promotion.
3. Delete one of the 162 id-less beats => manifest mismatch; all id-less beats receive pointer keys. Duplicate semantic ID/canonical target cannot overwrite another check.
4. Change candidate, policy, contract, seed, package, world input, prompt/schema, narrative decision, author disclosure or selected-book chapter bytes => stale request/reading rejection.
5. Quote copied from prompt/card/baseline/wrong candidate => reject; wrong pointer/value hash, byte-vs-code-point offset, out-of-range span, normalized punctuation/newline or forged quote => reject. Valid Chinese/multibyte and CRLF examples retain exact offsets.
6. Empty evidence, partial read scope, unexamined root/clause, unresolved ignored, fake full-reading claim or unknown rule mode => no PASS.
7. Same principal/source/session/context as author or reviser, coordinator as peer, alias readers, same context under different labels, absent lineage or false isolation => cannot count positively. Two honest distinct research contexts do not turn into human/provider identities.
8. Missing/altered raw response/receipt, edited envelope, duplicate JSON fields/nonfinite values, path traversal/symlink escape => integrity FAIL.
9. Valid negative plus two positives/ADOPT => FAIL; negative from another packet for same subject bytes stays visible; same-byte repacket/latest-positive-only selection rejected. Old-version negative retained with explicit crosswalk, never silently deleted.
10. Required event only NEGATED/DREAM/HYPOTHETICAL/METAPHOR/QUOTED => not an ACTUAL required beat. Forbidden hypothetical is not an actual violation; ambiguous modality stays UNKNOWN.
11. Dialogue/thought claiming a death/location change does not establish a physical exit. Later chronological contradiction defeats earlier state assertion; presentation order cannot masquerade as chronology.
12. Unknown fact/actor/object registry, unknown/null/UNSPECIFIED as a value, empty participants with UNKNOWN, absent exit state => no executable PASS.
13. Knowledge assertion before actual observation/communication, source event after acquisition, narrator-only fact, missing recipient, or S5 reader knowledge leaked to household => reject/violation. Bound fact registry does not imply all characters know its facts.
14. Declared entry matches itself but disagrees with runtime => reject; no model effect or prose interpretation mutates runtime state. Local scene without actual checkpoint stays NOT_CHECKED.
15. Nonprefix, skipped or reordered events; unsupported effect path; object from-state mismatch; unexplained movement; persistence without transition; detached predecessor snapshot => no replay PASS.
16. 86 selected v1 exact-anchor loss remains FAIL. Narrow v2 literal repair alone remains PENDING. Preserve all four feature checks, especially unfinished writing; require chain/late arrival/care chronology and terminal restraint rather than restoring only two sentences.
17. 89 same-scene reply after bucket question is not automatically failed as a suffix violation. 100 explanatory coda after “石在，字在。” can violate semantic terminal restraint even when anchors match.
18. SOURCE_ONLY phrase occurrence is neither an insertion requirement nor automatic local ban; T1 partial heading cannot become invented full exact title; generated TG title cannot acquire source authority. Legacy exact book sentinel remains unchanged.
19. Five cross-book rules require complete selected-book bindings; chapter-only claims cannot count as full trajectory coverage. Legacy book-scope boundary is not silently applied as a 20-chapter changed-set policy.
20. 88 hard quote before marriage/without post-marriage return does not cover missing 88-S3b. Five read contracts cannot fabricate sixth-seed coverage.
21. 98 same package personally carried versus frozen messenger transition: aliasing/renaming or OT98-04/05 citations cannot prove personal carriage. Removing those refs alone does not create new transport. Preserve snow-jade OPEN and package identity limits.
22. 99 preserve source S1–S5 and presentation S1,S2,S5,S3,S4; reject S5 after terminal S4, copied source predecessor as runtime state, instantaneous departure-to-temple inference, or knowledge leakage through presentation order.
23. 100 title/transcription alone does not establish explicit stone endpoint; narrative role name does not create registry identity; names on榜 are not active cast; no human knowledge leakage; frame_status change does not set earthly holder/location/transport.
24. Thirteen NARRATIVE_ONLY contracts plus all favorable model readings => original CONTRACT_PEERS still PENDING if deterministic/declared tiers are not PASS. No N/A/skip/automatic green conversion.
25. Supplemental integrity/locator PASS, added reading_ref or source carrier string hit => still no evidence-readiness PASS; stale/invalid binding remains FAIL. Do not resolve chapter86 old carriers by sidecar name matching.
26. Default old `chapter_scope`, legacy semantic request/check behavior, old registered readings/human intake, legacy policy changed-set behavior, prepared requests, catalog graph, stable/current and historical negatives remain byte/behavior compatible. Read-only validator must write no files and call no provider.

## 8. Unconfirmed and intentionally unresolved

- No proposed dedicated research semantic reading has been collected or qualified by this audit; no present candidate received a new semantic PASS.
- The 884 contract slots are complete row-level inventory, not a finalized atomization of every free-text clause; complex-rule interpretation/decomposition must retain originals and fail closed on uncertainty.
- No facsimile fidelity/source-support qualification, full-source review, supplemental gate protocol, or chapter86 original-carrier closure was established here.
- No new actor IDs, local scene checkpoints, missing seed, personal return route or chronological knowledge events were created or proved. Frame actors remain unregistered.
- Whether the current research environment can honestly satisfy two complete distinct-context positive readings is not established. Existing asserted=false disclosures remain false.
- Existing 86 v2 availability does not alter request-v1 or the reading selection. Its literal PASS is not a complete P-Lock/unfinished-writing/terminal/literary verdict.
- Full suite, catalog validation, 4112-input/325-protected-file snapshots and full release evaluate were outside this narrowly authorized audit. The denied snapshot was not worked around. This document makes no new no-drift certification for the whole tree.

**Conclusion:** the actual selection is exactly 20 policies and 85 advisory contracts, with 0 executable/prose aggregate contract PASS and 0 completed policy semantic PASS. A dedicated, fully bound research policy reader can potentially fill the original missing policy capability; a dedicated contract prose reader can fill only its own tier. Runtime unknowns, NARRATIVE_ONLY nonexecution and supplemental evidence readiness remain real blockers. If closing a blocker requires redefining the original gate rather than furnishing its missing proof, preserve PENDING and use the approved blocked-research-archive endpoint.
