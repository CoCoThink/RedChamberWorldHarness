# Provenance model review — v0.2-alpha

This review was performed before bulk R4 import.

## Verdict

The four-layer model is retained:

> Source → Claim → Decision → Implementation

The initial PR passed CI, but review found four architectural weaknesses that would become dangerous at scale. They have been corrected on the feature branch.

## Finding 1 — witness/container conflation

**Problem:** the first Source schema used `file_ref/file_sha256` as if the modern collation PDF were the early witness.

**Risk:** later imports could accidentally treat two modern copies of the same early comment as two independent sources.

**Correction:** Source now separates `witness` from `container` and fingerprints the quoted text.

## Finding 2 — partial basis could masquerade as fully evidenced

**Problem:** the first `evidence_proven` function returned true when *any* basis Claim was supported.

A future LOCKED Decision could therefore combine one evidenced premise with one unsupported premise and still appear proven.

**Correction:** renamed the concept to `fully_source_backed`; LOCKED Decisions now require **every** basis Claim to be SUPPORTED and source-backed.

## Finding 3 — decision status was incorrectly used as logical polarity

**Problem:** `LOCKED → MUST` and `REJECTED → MUST_NOT` conflated governance status with logical constraint.

**Risk:** a rejected literary option could become a hard prohibition, while a real negative evidence constraint had no clean representation.

**Correction:** added independent `constraint`:
- LOCKED + MUST
- LOCKED + MUST_NOT
- CURRENT + MAY
- OPEN + OPEN
- REJECTED + NONE

## Finding 4 — Implementation was not actually traceable

**Problem:** Decision records pointed to strings such as `prose:active:ch98`, but those IDs were not resolvable graph nodes.

**Correction:** added minimal Implementation records for the five canaries with stable ACTIVE prose SHA and line locators. Trace now works in both directions.

## Canary semantic review

### 悬崖撒手
PASS after review.

The source directly says there is a future “悬崖撒手”一回 and explicitly connects it to abandoning Baochai/Sheyue and becoming a monk. It does not lock Chapter 99, formal title status, or novel-exact wording.

### 甄宝玉送玉
PASS after review.

“伏甄宝玉送玉” supports the future event. Same-jade identity, face-to-face scene form, Chapter 98 placement, and formal title remain non-established.

### 凤姐扫雪拾玉
PASS after review.

“这便是凤姐扫雪拾玉之处” supports a future scene/interface. It does not prove title status, Tongling-jade identity, or Chapter 91 placement.

### 十独吟
PASS after review.

“《五美吟》与后《十独吟》对照” supports title, post-Chapter-64 range, and structural comparison. Author, exact form, full count/text, subjects, and Chapter 85 remain open.

### 情榜
PASS with one provenance correction.

The five-layer/final-chapter source remains a Gengchen brow comment. The “宝玉情不情 / 黛玉情情” passage has now been identified as continuing 己夹 context in the collation rather than left as an unspecified “comment.”

The phrase “警幻情榜” remains source-exact but does not become a locked formal novel-internal title.

## Merge gate

The provenance kernel may proceed to merge only if:

- CI remains green;
- no LOCKED Decision has mixed supported/unestablished premises;
- all five canaries trace to real Implementation nodes;
- OPEN decisions remain OPEN at runtime;
- no duplicate witness/locator/text fingerprint appears.

After merge, v0.2-beta may begin R4 Evidence Core import.
