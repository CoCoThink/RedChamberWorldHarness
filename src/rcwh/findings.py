"""Shared finding severities: evidence is the floor, literary advice is not a gate.

Only a violation of evidence-layer hard locks or of byte/structure integrity is
BLOCKING. B-grade constraints warn; C-grade author preferences, P-Lock anchors
and planning-card details are ADVISORY and may be replaced with a recorded
reason. Checks that are not implemented report INFO and never hold a gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

BLOCKING, WARNING, ADVISORY, INFO = "BLOCKING", "WARNING", "ADVISORY", "INFO"
SEVERITIES = (BLOCKING, WARNING, ADVISORY, INFO)

# Reasons a gate may wait. NOT_IMPLEMENTED never holds a gate; NEEDS_OWNER only
# applies to stable/ACTIVE adoption, never to research editions.
INPUT_MISSING, NEEDS_REVIEWER, NEEDS_OWNER, NOT_IMPLEMENTED = (
    "INPUT_MISSING", "NEEDS_REVIEWER", "NEEDS_OWNER", "NOT_IMPLEMENTED")
HOLDING_REASONS = {"research": {INPUT_MISSING, NEEDS_REVIEWER},
                   "stable": {INPUT_MISSING, NEEDS_REVIEWER, NEEDS_OWNER}}

# Internal evidence (R layer) witnessed directly: the only basis for a hard lock.
INTERNAL_SOURCE_TYPES = {"NOVEL_TEXT", "EARLY_COMMENT"}
FIRST_HAND_TIERS = {"W1_DIRECT", "W1_SEEN"}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    basis: str = ""
    reason: str | None = None
    replaceable: bool = False

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown finding severity: {self.severity}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def gate_status(findings: Iterable[Finding | dict] = (), pending: Iterable[str] = (),
                scope: str = "research") -> str:
    """FAIL only on BLOCKING; PENDING only for reasons that hold this scope."""
    if any(_severity(f) == BLOCKING for f in findings):
        return "FAIL"
    if set(pending) & HOLDING_REASONS[scope]:
        return "PENDING"
    return "PASS"


def combine(statuses: Iterable[str]) -> str:
    """Aggregate already-computed gate statuses: FAIL > PENDING > PASS."""
    statuses = list(statuses)
    if "FAIL" in statuses:
        return "FAIL"
    if not statuses or "PENDING" in statuses:
        return "PENDING"
    return "PASS"


def _severity(finding: Finding | dict) -> str:
    return finding.severity if isinstance(finding, Finding) else finding.get("severity", BLOCKING)


def claim_is_internal_first_hand(graph: Any, claim_id: str) -> bool:
    """A-W1: supported by at least one first-hand novel/early-comment witness."""
    claim = graph.claims.get(claim_id)
    if claim is None or claim.get("status") != "SUPPORTED" or graph.claim_is_w2_only(claim_id):
        return False
    for edge in claim.get("support", []):
        source = graph.sources.get(edge["source"])
        if source and source.get("type") in INTERNAL_SOURCE_TYPES and source.get("tier") in FIRST_HAND_TIERS:
            return True
    return False


def severity_for_decision(graph: Any, decision_id: str | None) -> str:
    """BLOCKING for an eligible LOCKED MUST/MUST_NOT on A-W1 claims; else softer.

    Locked decisions resting on historical feasibility or non-internal evidence
    warn; CURRENT/OPEN choices and unknown decisions are author preferences.
    """
    if graph is None or not decision_id or decision_id not in graph.decisions:
        return ADVISORY
    decision = graph.decisions[decision_id]
    if decision.get("status") != "LOCKED" or decision.get("constraint") not in {"MUST", "MUST_NOT"}:
        return ADVISORY
    if not graph.decision_lock_eligible(decision_id):
        return WARNING
    claims = decision.get("based_on", [])
    if claims and all(claim_is_internal_first_hand(graph, c) for c in claims):
        return BLOCKING
    return WARNING


def strongest(severities: Iterable[str], default: str = ADVISORY) -> str:
    present = set(severities)
    return next((s for s in SEVERITIES if s in present), default)
