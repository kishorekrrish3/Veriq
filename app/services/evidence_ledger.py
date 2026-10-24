"""Verification Ledger Service for VERIQ.
The core differentiator: maintains traceable, inspectable claims backed by concrete evidence.
Enforces the fundamental principle: 'Code is generated. Proof is earned.'
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from app.schemas.evidence import (
    ClaimRecord,
    EvidenceRecord,
    ClaimStatus,
    ClaimCategory,
    VerificationLedgerSummary,
)
from app.storage.repositories import LedgerRepository


class EvidenceLedger:
    """Manages the lifecycle, evidence linkage, and status calculation of engineering claims."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.claims: Dict[str, ClaimRecord] = {}
        self.evidence: Dict[str, EvidenceRecord] = {}

    def register_claim(
        self,
        claim_id: str,
        title: str,
        description: str,
        category: ClaimCategory,
        file_refs: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
        unresolved_questions: Optional[List[str]] = None,
    ) -> ClaimRecord:
        """Registers a new claim, defaulting to NOT_RUN."""
        record = ClaimRecord(
            claim_id=claim_id,
            title=title,
            description=description,
            category=category,
            status=ClaimStatus.NOT_RUN,
            evidence_ids=[],
            file_refs=file_refs or [],
            limitations=limitations or [],
            unresolved_questions=unresolved_questions or [],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.claims[claim_id] = record
        LedgerRepository.save_claim(self.run_id, record)
        return record

    def attach_evidence(self, evidence: EvidenceRecord) -> None:
        """Attaches an evidence record to its designated claim and updates claim status."""
        self.evidence[evidence.evidence_id] = evidence
        LedgerRepository.save_evidence(self.run_id, evidence)

        claim_id = evidence.claim_id
        if claim_id in self.claims:
            claim = self.claims[claim_id]
            if evidence.evidence_id not in claim.evidence_ids:
                claim.evidence_ids.append(evidence.evidence_id)

            # Inherit limitations from evidence
            for lim in evidence.limitations:
                if lim not in claim.limitations:
                    claim.limitations.append(lim)

            # Recalculate claim status based on all attached evidence
            claim.status = self._calculate_claim_status(claim)
            LedgerRepository.save_claim(self.run_id, claim)

    def _calculate_claim_status(self, claim: ClaimRecord) -> ClaimStatus:
        """Calculates claim status deterministically from backing evidence.
        Considers the latest evidence record for each check type (allowing bounded repair
        to resolve previous failures while preserving historical records).
        """
        if not claim.evidence_ids:
            return ClaimStatus.NOT_RUN

        backing_records = [self.evidence[eid] for eid in claim.evidence_ids if eid in self.evidence]
        if not backing_records:
            return ClaimStatus.NOT_RUN

        # Group by check_type to evaluate latest result for each check
        latest_by_type: Dict[str, EvidenceRecord] = {}
        had_prior_failure = False

        for ev in backing_records:
            if ev.status == ClaimStatus.FAILED:
                had_prior_failure = True
            # Since records are appended in chronological order, latter replaces former
            latest_by_type[ev.check_type] = ev

        latest_records = list(latest_by_type.values())

        # If any latest check failed, the claim is FAILED
        if any(ev.status == ClaimStatus.FAILED for ev in latest_records):
            return ClaimStatus.FAILED

        # If any latest check is UNRESOLVED
        if any(ev.status == ClaimStatus.UNRESOLVED for ev in latest_records):
            return ClaimStatus.UNRESOLVED

        # If all latest deterministic checks passed
        if all(ev.status == ClaimStatus.VERIFIED for ev in latest_records):
            if had_prior_failure:
                repair_note = "Resolved after regression repair iteration."
                if repair_note not in claim.limitations:
                    claim.limitations.append(repair_note)
            return ClaimStatus.VERIFIED

        # Research or heuristic support
        if any(ev.status == ClaimStatus.SUPPORTED for ev in latest_records):
            return ClaimStatus.SUPPORTED

        return ClaimStatus.UNRESOLVED

    def get_summary(self) -> VerificationLedgerSummary:
        """Computes summary statistics and returns all claims and evidence."""
        claims_list = list(self.claims.values())
        evidence_list = list(self.evidence.values())

        counts = {
            ClaimStatus.VERIFIED: 0,
            ClaimStatus.SUPPORTED: 0,
            ClaimStatus.FAILED: 0,
            ClaimStatus.UNRESOLVED: 0,
            ClaimStatus.NOT_RUN: 0,
        }
        for c in claims_list:
            counts[c.status] = counts.get(c.status, 0) + 1

        return VerificationLedgerSummary(
            total_claims=len(claims_list),
            verified_count=counts[ClaimStatus.VERIFIED],
            supported_count=counts[ClaimStatus.SUPPORTED],
            failed_count=counts[ClaimStatus.FAILED],
            unresolved_count=counts[ClaimStatus.UNRESOLVED],
            not_run_count=counts[ClaimStatus.NOT_RUN],
            claims=claims_list,
            evidence=evidence_list,
        )
