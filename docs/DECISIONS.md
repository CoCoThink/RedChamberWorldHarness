# Architectural decisions

## ADR-001: Markdown is a view, not the system of record
Canonical harness state is structured YAML/JSON and an event log. Markdown tables may be generated for humans, but editing a table must not silently mutate evidence state.

## ADR-002: Reconstruction truth never promotes evidence truth
A scene can become ACTIVE because it is the best literary implementation. That promotion changes reconstruction state only.

## ADR-003: OPEN is first-class
Unknown-but-audited fields are stored explicitly as OPEN-LOCKED. Null does not mean missing work.

## ADR-004: Hard failures are non-compensatory
A beautiful scene that violates a hard witness, impossible object state, or character knowledge boundary fails. Literary quality cannot average away a hard contradiction.

## ADR-005: Culture has no quota
The v5.0 objective is density and plurality, not a checklist. Cultural detail must declare a dramatic function and survive deletion testing.
