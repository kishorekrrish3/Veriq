"""Unit tests for Evidence Ledger status transitions and evidence attachment.
"""

from app.services.evidence_ledger import EvidenceLedger
from app.schemas.evidence import ClaimCategory, ClaimStatus, EvidenceRecord


def test_claim_lifecycle_and_status():
    ledger = EvidenceLedger("RUN-TEST-001")
    claim = ledger.register_claim(
        claim_id="CLAIM-100",
        title="Module Imports",
        description="Verify clean import",
        category=ClaimCategory.IMPORT,
    )
    assert claim.status == ClaimStatus.NOT_RUN

    # Attach verified evidence
    ev = EvidenceRecord(
        evidence_id="EV-100",
        claim_id="CLAIM-100",
        check_type="import_check",
        status=ClaimStatus.VERIFIED,
        exit_code=0,
        timestamp="2026-10-24T00:00:00Z",
    )
    ledger.attach_evidence(ev)

    updated_claim = ledger.claims["CLAIM-100"]
    assert updated_claim.status == ClaimStatus.VERIFIED
    assert "EV-100" in updated_claim.evidence_ids


def test_repair_resolves_earlier_failure():
    ledger = EvidenceLedger("RUN-TEST-002")
    claim = ledger.register_claim(
        claim_id="CLAIM-101",
        title="Pytest Suite",
        description="Run test suite",
        category=ClaimCategory.REGRESSION_TEST,
    )

    # First attempt: failed
    ev_fail = EvidenceRecord(
        evidence_id="EV-FAIL",
        claim_id="CLAIM-101",
        check_type="pytest_check",
        status=ClaimStatus.FAILED,
        exit_code=1,
        timestamp="2026-10-24T00:00:01Z",
    )
    ledger.attach_evidence(ev_fail)
    assert ledger.claims["CLAIM-101"].status == ClaimStatus.FAILED

    # Second attempt (after repair): passed
    ev_pass = EvidenceRecord(
        evidence_id="EV-PASS",
        claim_id="CLAIM-101",
        check_type="pytest_check",
        status=ClaimStatus.VERIFIED,
        exit_code=0,
        timestamp="2026-10-24T00:00:02Z",
    )
    ledger.attach_evidence(ev_pass)
    assert ledger.claims["CLAIM-101"].status == ClaimStatus.VERIFIED
    # Historical failure must remain attached
    assert "EV-FAIL" in ledger.claims["CLAIM-101"].evidence_ids
    assert "EV-PASS" in ledger.claims["CLAIM-101"].evidence_ids
