# Chapter 86 corpus v2 human audit preparation

The actual chapter 86 package uses `corpus:front80:v2-candidate`. Its independent human audit is **PENDING** with no opinions registered. This implementation adds `corpus-full-v2` alongside the unchanged v1 `corpus-full` lane; neither a reading handout nor model research grants production admission. Evidence Truth, OPEN-LOCKs, prose, timeline and character knowledge do not change.

The new protocol `data/corpus/audit-protocols/front80-v2-candidate-v1.json` is bound by SHA-256 `04b8054ed132ac9ef940d70df53dea03f1f26f2a520238195ba097c9ebf9d5f3` to manifest `eb4aebb9e38712a988bdead263c12c9c3df00a6f936fb17db755c436e4d66886`. Its empty selection is `data/corpus/audits/378efea7ab7ce743bb9f4b9f1445f72dee182f11a04beaa74b8a52ac83b2ce94.json`. The 146 samples include 80 MAIN_TEXT samples (one in each chapter), every available text layer, and all 31 split-header locations marked FAIL in the historical reader opinions together with their preceding prefix segments. The layer totals are `{"APPENDIX": 1, "EDITORIAL": 63, "MAIN_TEXT": 80, "VARIANT": 1, "ZHIPI": 1}`. The original v1 protocol/selection and both original model opinions remain unchanged; these model opinions are research evidence and were not converted into human attestations.

`reading-plan.json` binds only the selected protocol and exact corpus/material bytes. It deliberately excludes mutable selection bytes, live opinion count/verdict and catalog shards. `sample-contexts.json` includes exact segments and adjacent segments; `extraction-pages.json` includes full fixed extraction text for sampled pages. Navigation gives the full original PDF path/hash, one-based physical page, zero-based PDF API index, exact offsets and text; printed page labels may differ. Read the original full PDF at those pages, including both pieces of split headers and their full line context. All data remain candidate representations requiring human judgment. Unknown annotation witnesses (162), unaligned segments (7,559) and unestablished carrier edition equivalence must remain visible.

The plan groups reading into eight groups of ten chapters plus appendix groups of at most 20 samples. These files support staged human work; the selected protocol requires at least one independent human to deliver a complete final submission with all 146 checks. No token count was measured and this is not an unsegmented model assignment. `human-review-template.json` leaves identity, independence attestation, all judgments and notes unfilled. Preserve false judgments and their explanations. Intake registers a valid negative opinion and returns FAIL; approval counts cannot erase it.

Reproduce the issued bytes offline with:

```sh
PYTHONPATH=src /home/guan/rcwh-review-venv/bin/python tools/prepare_corpus_v2_review.py --check
PYTHONPATH=src /home/guan/rcwh-review-venv/bin/python tools/prepare_corpus_v2_review.py --check --live-audit
```

The second command prints current audit state separately from frozen materials. To prepare a fresh copy use `--output /tmp/rcwh-corpus-v2-review` without `--check`; an existing material file blocks overwrite. The tool forbids network/DNS calls. Check mode compares every regenerated file. Appending an opinion does not change issued read materials; changing the selected protocol or actual corpus bytes requires new materials.

After receiving an actual complete human original, preflight and register it with:

```sh
PYTHONPATH=src /home/guan/rcwh-review-venv/bin/rcwh reviews register corpus-full-v2 ACTUAL_ORIGINAL.json --origin 'actual receipt origin' --dry-run
PYTHONPATH=src /home/guan/rcwh-review-venv/bin/rcwh reviews register corpus-full-v2 ACTUAL_ORIGINAL.json --origin 'actual receipt origin'
```

Integration handoff: `closure-references.json` lists exact new protocol, selection and reading-material bindings for root to integrate into `data/project/closure_roots.json`; this task does not edit the closure. Keep both v1 and v2 datasets/lane evidence where required. Intake automatically updates an already registered selection closure binding after valid receipt. Parent integration must also update runbook links and use this explicit v2 lane for the chapter 86 package. Live audit summaries must remain outside frozen reading plans.

Validation: **161 tests passed** with the supported Python environment. All 86 v2 corpus products rebuilt exactly offline; historical builder-code and source-record metadata differ, reported separately without rewriting the manifest or materials. Validation evidence is retained in `test-results.txt`, `verification.json` (offline exact content rebuild) and `live-audit-observation.json` (separate current observation). Tests cover blank templates, wrong dataset/manifest/protocol, missing or duplicated samples, raw byte preservation, negative receipt findings, CLI lane parsing and issued-material stability after a synthetic negative receipt. All human-format submissions used by these tests are synthetic temporary fixtures; no production review was created. Preparation acted as implementation work with the dispatched task, AGENTS.md, CONTRIBUTING.md, corpus contracts and original negative model opinions as context; no independent reader identity or isolation is claimed, and no external model API was called.
