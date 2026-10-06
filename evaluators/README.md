# Evaluator specifications

Each evaluator returns `PASS`, `WARN`, or `FAIL` plus structured findings.

- `evidence`: contradiction, role promotion, literal-target misuse.
- `knowledge`: character knows/says/acts beyond local knowledge.
- `object_state`: holder/location/status continuity.
- `timeline`: order, season, duration, message travel, illness progression.
- `mechanism`: legal/medical/ritual/economic feasibility.
- `voice`: character differentiation and known speech habits.
- `exposition`: textbook speech and explicit self-interpretation.
- `culture_function`: cultural detail must change character, scene, conflict, or texture.
- `ambiguity`: do not close OPEN-LOCK through narration.
- `regression`: compare candidate exit state against downstream assumptions.

v0.1 implements the first hard checks and exposes hooks for the rest.
