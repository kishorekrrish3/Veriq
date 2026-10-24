"""Unit tests for VERIQ Pydantic schemas.
"""

from app.schemas.evidence import ClaimRecord, EvidenceRecord, ClaimStatus, ClaimCategory
from app.schemas.runs import RunCreate, RunStatus, ModelTier, RoutingDecision


def test_claim_record_schema():
    claim = ClaimRecord(
        claim_id="CLAIM-001",
        title="Syntax Check",
        description="Verify AST parsing",
        category=ClaimCategory.SYNTAX,
        status=ClaimStatus.NOT_RUN,
        timestamp="2026-10-24T00:00:00Z",
    )
    assert claim.claim_id == "CLAIM-001"
    assert claim.status == ClaimStatus.NOT_RUN


def test_evidence_record_schema():
    ev = EvidenceRecord(
        evidence_id="EV-001",
        claim_id="CLAIM-001",
        check_type="ast_parse",
        status=ClaimStatus.VERIFIED,
        exit_code=0,
        duration_ms=12.4,
        timestamp="2026-10-24T00:00:00Z",
    )
    assert ev.status == ClaimStatus.VERIFIED
    assert ev.exit_code == 0


def test_routing_decision_schema():
    rd = RoutingDecision(
        model_id="nvidia/nemotron-mini-4b-instruct",
        tier=ModelTier.FAST,
        trigger="TARGETED_CHANGE",
        reason="Local single-file fix",
        attempt=1,
    )
    assert rd.tier == ModelTier.FAST
    assert rd.total_tokens == 0
