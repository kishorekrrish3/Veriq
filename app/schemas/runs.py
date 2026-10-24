"""Run execution models, state machine schemas, and routing telemetry for VERIQ.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.evidence import VerificationLedgerSummary, ClaimStatus


class ModelTier(str, Enum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    ESCALATION = "ESCALATION"


class RunStatus(str, Enum):
    CREATED = "CREATED"
    RESEARCHING = "RESEARCHING"
    PLANNING = "PLANNING"
    GENERATING_PATCH = "GENERATING_PATCH"
    VALIDATING_PATCH = "VALIDATING_PATCH"
    EXECUTING_CHECKS = "EXECUTING_CHECKS"
    REPAIRING = "REPAIRING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class RoutingDecision(BaseModel):
    """Detailed evidence-driven routing record."""
    model_id: str
    tier: ModelTier
    trigger: str
    reason: str
    attempt: int = 1
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Optional[float] = None


class PatchFileChange(BaseModel):
    file_path: str
    action: str = "modify"  # "modify", "create", "delete"
    old_content: Optional[str] = None
    new_content: str
    diff: Optional[str] = None


class RunCreate(BaseModel):
    task_id: Optional[str] = None
    title: str = Field(description="Task title")
    description: str = Field(description="Task specification or bug report")
    sample_name: str = Field(default="calculator")
    enable_research: bool = Field(default=True)
    max_repair_attempts: int = Field(default=1)
    mode: str = Field(default="auto", description="'live', 'replay', or 'auto'")


class RunResponse(BaseModel):
    run_id: str
    task_title: str
    task_description: str
    status: RunStatus
    execution_mode: str  # "live" or "replay"
    created_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    unified_diff: Optional[str] = None
    changed_files: List[str] = Field(default_factory=list)
    routing_history: List[RoutingDecision] = Field(default_factory=list)
    ledger_summary: Optional[VerificationLedgerSummary] = None
    final_outcome: str = ""
    error_message: Optional[str] = None


class BenchmarkTaskResult(BaseModel):
    task_id: str
    task_name: str
    baseline_passed: bool
    baseline_latency_ms: float
    baseline_tokens: int
    baseline_cost_usd: float
    routed_passed: bool
    routed_tier_used: str
    routed_latency_ms: float
    routed_tokens: int
    routed_cost_usd: float
    repair_triggered: bool
    repair_successful: bool


class BenchmarkComparison(BaseModel):
    benchmark_id: str
    created_at: str
    task_count: int
    baseline_pass_rate: float
    routed_pass_rate: float
    baseline_avg_latency_ms: float
    routed_avg_latency_ms: float
    baseline_total_tokens: int
    routed_total_tokens: int
    tasks: List[BenchmarkTaskResult] = Field(default_factory=list)
    conclusions: List[str] = Field(default_factory=list)
