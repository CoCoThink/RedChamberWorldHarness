# V-axis / literal-target contract

R4 does not treat every quoted source phrase as prose that must be inserted into the reconstructed novel.

The literal-target layer distinguishes:

- NOVEL_EXACT — exact wording is required in the reconstructed novel/list.
- NAME_EXACT — exact work/name string is required, while authorship/form/placement may remain open.
- SOURCE_EXACT — source wording must be preserved in evidence records; it is not automatically novel wording.
- SEM — semantic function is required, not exact wording.
- BOUNDARY — ordering/range/negative-space constraint.
- NEG — explicit negative constraint.

## First literal-core batch

### 《十独吟》

- NAME_EXACT: 十独吟
- BOUNDARY: after Chapter 64
- author / form / complete count / subjects: OPEN
- current Chapter 85 occurrence: Implementation only

### 落叶萧萧，寒烟漠漠

- NOVEL_EXACT
- current Chapter 87 placement: CURRENT, not source-fixed

### 好歹留着麝月

- NOVEL_EXACT
- BOUNDARY: must occur after Xiren has married out
- current Chapter 88 placement: CURRENT

### 情榜 ratings

- 黛玉：情情 — NOVEL_EXACT
- 宝玉：情不情 — NOVEL_EXACT

### 警幻情榜

- SOURCE_EXACT only
- the four characters are preserved because the comment uses them
- they do not force the formal novel-internal total title

## Runtime rules

1. NOVEL_EXACT and NAME_EXACT require an active implementation locator.
2. SOURCE_EXACT alone may not require prose insertion.
3. SEM alone may not become exact wording.
4. BOUNDARY requires its own supported Claim.
5. Exact wording does not inherit current chapter placement.
6. Current prose can satisfy a literal constraint without becoming upstream evidence.

## CLI

Examples:

rcwh literal literal:ten-solitary-chants:name
rcwh literal literal:falling-leaves:cold-smoke
rcwh literal literal:sheyue:keep-sheyue
rcwh literal literal:qingbang:source-phrase

The command shows the literal target, Claims, Sources, Decisions, and current Implementation locator.
