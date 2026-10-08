# R4 Evidence Core regression

## Historical baseline

**v0.2-beta.6 FINAL PASS**。这是历史验收记录；当前结果以 `rcwh regression` 为准。

Stable ACTIVE prose baseline:

- file: `第32-A_红楼梦八十回后文学复原_纯读版_v1.4_稳定ACTIVE基线.md`
- SHA256: `4645da79b1bed76f54be281c50b5df648f599ea41541fb7855685753b6a85320`

## Preflight findings corrected before PASS

The final regression was not treated as a ceremonial green check. Two provenance gaps were found and repaired first.

### 1. Legacy Chapter 86 HARD evidence had no source reference

The v0.1 compatibility evidence record `CH86_DAIYU_DEATH_DIRECTION` still had:

`source_ref: null`

It is now linked to a first-class source node based on the Jimao Chapter 18 comment:

`《离魂》……伏黛玉死……乃通部书之大过节、大关键。`

The hard Daiyu-death direction is represented in the main Source → Claim → Decision → Implementation graph. On 2026-10-08 the redundant v0.1 compatibility record and checker were retired; the graph is now the sole evidence path. The unfinished/death-poem working constraint remains in the scene contract and literary checks, with no evidence authority.

### 2. Chapter 92 R4 hard interfaces were not yet first-class Decisions

The governing R4 release says Chapter 92 hard-locks:

- detention / 狱神庙 function;
- Xiaohong's later “大得力” function;
- Qianxue return.

Before the final regression these were partly present only as title evidence, historical implementation, or prose summary.

They are now explicit provenance nodes:

- `decision:prison:baoyu-interface`
- `decision:xiaohong:great-help`
- `decision:qianxue:prison-return`

with W1 source backing and stable-ACTIVE implementation locators.

## 数据范围

当前节点数量由 `rcwh regression --json` 的 `population` 输出，不作为验收配额。旧数量基线保存在清理审计。已确认的证据锚点继续校验；新增合法节点须满足相同图与权威规则。

## Gates

The executable regression checks these semantic gates:

1. **PROVENANCE**
   - supported graph integrity;
   - no duplicate provenance fingerprint;
   - hard anchors have source-backed Claims and eligible Decisions in the provenance graph;
   - EARLY_COMMENT sources have W1 tier.

2. **ROLE_T_AXIS**
   - the confirmed T0/T1/T2/T2_W2/T3/TG anchor map, allowing valid additions.

3. **MODALITY_W2**
   - W2-only claims are TRANSCRIPT_WEAK;
   - no LOCKED Decision can rest on W2-only basis.

4. **LITERAL_TARGET**
   - confirmed literal constraints, allowing valid additions;
   - SOURCE_EXACT cannot become required prose;
   - NAME_EXACT/NOVEL_EXACT retain implementation requirements.

5. **PLACEMENT_CURRENT**
   - confirmed implementation/placement choices remain CURRENT/MAY.

6. **IMPLEMENTATION_STABLE_ACTIVE**
   - all ACTIVE implementation locators agree with the R4 regression manifest’s stable file and SHA.

7. **SEMANTIC_HARD_ANCHORS**
   - all LOCKED Decisions are fully source-backed and lock-eligible.

8. **BOUNDARY_OPEN_LOCK**
   - confirmed OPEN Decisions remain OPEN/OPEN;
   - current choices do not harden.

9. **HISTORICAL_H01_H06**
   - H01 PASS-WITH-CAUTION;
   - H02 PASS;
   - H03 PASS-BOUNDARY;
   - H04 PASS;
   - H05 PASS;
   - H06 PASS-SOFT;
   - historical feasibility remains non-narrative.

## Command

```bash
rcwh regression
```

A release-ready branch must print:

`R4 EVIDENCE CORE REGRESSION: PASS`

and every gate must be PASS.

## Scope boundary

PASS means the provenance, role, modality, literal-target, placement, weak-witness, OPEN and stable implementation rules hold for the current graph. It does not prove complete local Source content or validated locators, literary quality, adoption or publication. Use the separate self-contained profiles for storage and source closure.
