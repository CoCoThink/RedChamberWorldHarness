# 弱见证使用边界

The Jingcang manuscript is not available for direct inspection in the project source set.

The current source container explains that:

- the manuscript was reportedly found by Mao Guoyao in 1959;
- it was still extant in 1964 and later disappeared;
- Mao copied 150 comments that were absent from the Qi edition into a notebook;
- those transcriptions were published in 1974;
- only Mao is reported to have seen the manuscript, and later researchers have questioned its authenticity.

RCWH therefore records these entries as:

- source type: EARLY_TRANSCRIPT
- source tier: W2_TRANSCRIPT
- claim modality: TRANSCRIPT_WEAK

## Core rule

A W2-only Claim may exist and may corroborate another line of reasoning, but it may **not independently bear a LOCKED Decision**.

Formally:

    W2-only → OPEN / corroboration
    W2-only → LOCKED + MUST   [validation failure]

This is deliberately different from deleting the witness. Weak evidence remains queryable and useful, but cannot silently become hard plot truth.

## First W2 batch

- 毛抄145: 先为对景悼颦儿作引
- 毛抄92: 芸哥仗义探庵
- 毛抄102: 狱庙相逢
- 毛抄98: 妙玉瓜州渡口
- 毛抄144: 证前缘回黛玉逝后诸文
- 毛抄33: 观警幻情榜方知余言不谬

## Important boundaries

### 对景悼颦儿

The transcript is preserved, but RCWH does not use it to force a complete Daiyu death poem, elegy, author, form, or chapter placement.

### 妙玉瓜州渡口

The transcript is not discarded. It remains OPEN. It also does not license an automatic chain such as:

    Guazhou → abduction → sexual coercion → death location

Those are separate Claims and would require separate support.

### 狱庙相逢

It may corroborate the stronger prison / 狱神庙 evidence, but does not independently fix participants, rescue mechanics, or chapter number.

### 证前缘

Because the transcript explicitly says “证前缘回”, RCWH records a T2_W2 axis entry. This is a weak chapter-call witness, not a formal original title.

### 情榜

The W2 phrase “观警幻情榜方知余言不谬” is corroborative only. The current LOCKED Qingbang structure continues to rest on W1 evidence already in the provenance graph.

## Validator invariants

1. EARLY_TRANSCRIPT must use W2_TRANSCRIPT.
2. W2-only Claims must use TRANSCRIPT_WEAK modality.
3. TRANSCRIPT_WEAK Claims may not mix in non-W2 sources.
4. LOCKED Decisions may not contain W2-only basis Claims.
5. T2_W2 axis entries must be backed by W2-only Claims.
6. T2_W2 cannot hard-lock formal-title identity.
