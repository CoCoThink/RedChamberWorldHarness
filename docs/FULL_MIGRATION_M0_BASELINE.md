# Full Migration M0 Baseline Report

Status: **PASS**

Date: 2026-10-07

This report freezes the pre-migration baseline for `RCWH_SelfContained_FullMigration_v3.0`. It does not advance Chapter 89/92/97 literary construction and does not promote any stable prose candidate.

## Package integrity

Source package:

`RCWH_SelfContained_FullMigration_v3.0_20261006(1).zip`

SHA256:

`a20117a23a0a93aaeed33eb0fb7849c05921d85457feba191b1632fe375868c0`

The ZIP contains 718 file entries. The content manifest contains 717 content rows; the one additional file is the manifest itself.

Validation of all 717 manifest rows:

- missing files: 0
- SHA256 mismatches: 0
- nested `.zip` files: 0

The literal SHA256 of `06_MANIFESTS/CONTENT_MANIFEST_SHA256.csv` is:

`5637053f701f14c9bfe9295ab058818659cf902b996bbdc05c54eec338c74c5a`

`PACKAGE_SUMMARY.json` declares:

`8f46480a6b48bb8b6b3cb3126fbeaaa7dfadd5f72e65a99d0fe4237a92ad2dc8`

That value is exactly the SHA256 of the manifest with the `06_MANIFESTS/PACKAGE_SUMMARY.json` row excluded. This is the non-recursive digest and avoids a summary→manifest→summary self-reference. Therefore this is not an integrity failure.

## Stable ACTIVE freeze

Stable body:

`02_CURRENT_RUNTIME/IMPLEMENTATION/第32-A_红楼梦八十回后文学复原_纯读版_v1.4_稳定ACTIVE基线.md`

Expected SHA256:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

Actual SHA256:

`4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

Result: **PASS / FROZEN**

The Chapter 86 B candidate remains deferred. Stable ACTIVE promotion is frozen until the Full Migration Completion Gate passes.

## GitHub baseline

Repository:

`CoCoThink/RedChamberWorldHarness`

Recorded baseline:

- `main`: `0ffd5a3aa8ec311c5af39be5fc511b22d6484788`
- PR #9 head: `02eda38d8fc478e0dcefc1422356168a03c7a338`
- PR #9 branch: `feature/literary-plock-v0.3-alpha`
- Full Migration branch: `migration/full-v3`

Before M0 changes, `migration/full-v3` was byte-history identical to the PR #9 head: ahead 0 / behind 0.

The live PR #9 validation workflow at the recorded head was **SUCCESS**.

## Harness validation

The self-contained `04_HARNESS_REPO_PR9/` snapshot was tested directly.

Pre-M0 suite:

- `rcwh validate`: PASS
- `pytest -q`: **79 passed / 0 failed**

M0 adds three migration freeze tests. With those tests present locally:

- `pytest -q`: **82 passed / 0 failed**

The new guards assert:

1. stable ACTIVE remains pinned to SHA `4645...`;
2. Completion Gate remains false during migration;
3. Chapter 89 remains at Phase 1 only;
4. Chapters 92 and 97 remain blocked;
5. the Chapter 86 promotion candidate cannot mutate stable ACTIVE.

## Literary-construction freeze

During M1→M8:

- Chapter 89 continuation: **FROZEN**
- Chapter 92 pressure test: **FROZEN**
- Chapter 97 pressure test: **FROZEN**
- other 81–100 literary construction: **FROZEN**
- existing Chapter 89 Phase 1 artifacts: preserve as history/fixture only

This freeze remains active until M8 Completion Gate explicitly releases it.

## M0 result

All M0 gates pass:

- content manifest verified;
- no nested ZIP;
- stable ACTIVE SHA verified and frozen;
- existing Harness tests pass;
- live GitHub baseline recorded;
- migration branch established from exact PR #9 head;
- literary continuation frozen by regression tests.

Next milestone: **M1 — Current Authority / Registry migration**.
