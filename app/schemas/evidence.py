"""Verification Ledger schemas for VERIQ.
Distinguishes between verified proof and unverified assertions.
"""

from enum import Enum
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    """Rigorous classification of engineering claims."""
    VERIFIED = "VERIFIED"       # Specific deterministic check passed
    SUPPORTED = "SUPPORTED"     # External/research evidence supports claim subject to limits
    FAILED = "FAILED"           # A check was run and failed
    UNRESOLVED = "UNRESOLVED"   # Evidence missing, incomplete, or inconclusive
    NOT_RUN = "NOT_RUN"         # The check was not executed


class ClaimCategory(str, Enum):
    """Category of claim made in the engineering workflow."""
    SYNTAX = "SYNTAX"
    IMPORT = "IMPORT"
    REGRESSION_TEST = "REGRESSION_TEST"
    PATCH_INTEGRITY = "PATCH_INTEGRITY"
    RESEARCH_GROUNDING = "RESEARCH_GROUNDING"
    SECURITY_AUDIT = "SECURITY_AUDIT"


class EvidenceRecord(BaseModel):
    """Concrete, inspectable evidence supporting or refuting a claim."""
    evidence_id: str = Field(description="Unique identifier for the evidence entry")
    claim_id: str = Field(description="Associated claim identifier")
    check_type: str = Field(description="Type of check: ast_parse, import_test, pytest, hash_verify, etc.")
    status: ClaimStatus = Field(description="Verification status result of this specific check")
    command: Optional[str] = Field(default=None, description="Exact command executed inside sandbox")
    exit_code: Optional[int] = Field(default=None, description="Subprocess or check exit code")
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds")
    stdout: Optional[str] = Field(default=None, description="Sanitized standard output")
    stderr: Optional[str] = Field(default=None, description="Sanitized standard error")
    file_ref: Optional[str] = Field(default=None, description="Primary file path referenced")
    line_ref: Optional[int] = Field(default=None, description="Specific line number if applicable")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured diagnostics")
    limitations: List[str] = Field(default_factory=list, description="Explicit boundaries and limitations of this check")
    timestamp: str = Field(description="ISO 8601 timestamp")


class ClaimRecord(BaseModel):
    """A specific engineering claim backed by evidence entries."""
    claim_id: str = Field(description="Unique claim ID, e.g. CLAIM-001")
    title: str = Field(description="Short title of the claim")
    description: str = Field(description="Detailed explanation of what is asserted")
    category: ClaimCategory = Field(description="Claim category")
    status: ClaimStatus = Field(description="Current calculated status based on evidence")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of backing evidence")
    file_refs: List[str] = Field(default_factory=list, description="Files affected or inspected")
    limitations: List[str] = Field(default_factory=list, description="Known limits or what this claim does not prove")
    unresolved_questions: List[str] = Field(default_factory=list, description="Remaining risks or unanswered inquiries")
    timestamp: str = Field(description="ISO 8601 timestamp")


class VerificationLedgerSummary(BaseModel):
    """Inspectable Verification Ledger summary."""
    total_claims: int = 0
    verified_count: int = 0
    supported_count: int = 0
    failed_count: int = 0
    unresolved_count: int = 0
    not_run_count: int = 0
    claims: List[ClaimRecord] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
