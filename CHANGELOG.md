# Changelog

## 0.2.0-beta.1

- Began R4 Evidence Core import with the T-axis.
- Added Evidence Role, Modality, Literal Target, and T-axis metadata to provenance claims.
- Added W1_DIRECT / W1_SEEN / W2_TRANSCRIPT / EDITORIAL source tiers.
- Added machine-validated T0/T1/T2/T2-W2/T3/TG title-axis records.
- Added active title implementations for Chapters 88, 90, 91, 92, 95, 98, and 99.
- Added regression rules blocking T2/T3 → hard formal-title promotion.
- Registered project-generated headings as TG with zero evidence authority.

## 0.2.0-alpha

- Added the Source → Claim → Decision → Implementation provenance kernel.
- Added five R4 provenance canaries: 悬崖撒手、甄宝玉送玉、凤姐扫雪拾玉、十独吟、情榜.
- Added `rcwh trace` in both forward and reverse directions.
- Separated witness identity from modern source container.
- Replaced ambiguous `evidence_proven` with all-basis `fully_source_backed`.
- Separated Decision status from runtime constraint polarity.
- Added minimal resolvable Implementation nodes.
- Added duplicate-source fingerprint checks.

## 0.1.0

- Initial harness kernel.
- Four-layer truth model.
- Evidence, character, object, event, and scene-contract schemas.
- Event-sourced world-state runtime.
- Basic text evaluator.
- Chapter 86 acceptance slice.
- CI validation.
