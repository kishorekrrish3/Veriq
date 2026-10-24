"""Real-time Run Events schema for VERIQ.
Used for WebSocket/SSE event streaming and audit history.
"""

from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field


class EventType(str, Enum):
    RUN_CREATED = "RUN_CREATED"
    RESEARCH_STARTED = "RESEARCH_STARTED"
    RESEARCH_COMPLETED = "RESEARCH_COMPLETED"
    PLAN_GENERATED = "PLAN_GENERATED"
    MODEL_SELECTED = "MODEL_SELECTED"
    PATCH_GENERATED = "PATCH_GENERATED"
    PATCH_VALIDATED = "PATCH_VALIDATED"
    TESTS_EXECUTED = "TESTS_EXECUTED"
    FAILURE_DETECTED = "FAILURE_DETECTED"
    REPAIR_ATTEMPTED = "REPAIR_ATTEMPTED"
    REPAIR_COMPLETED = "REPAIR_COMPLETED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    REPORT_GENERATED = "REPORT_GENERATED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_CANCELLED = "RUN_CANCELLED"


class RunEvent(BaseModel):
    """An event emitted during run execution."""
    event_id: str = Field(description="Unique event ID")
    run_id: str = Field(description="Run ID")
    event_type: EventType = Field(description="Event classification")
    timestamp: str = Field(description="ISO 8601 timestamp")
    message: str = Field(description="Human-readable event message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
