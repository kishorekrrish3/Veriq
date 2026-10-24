"""Task and repository input schemas for VERIQ.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """Specification of an engineering task to be solved."""
    title: str = Field(description="Brief title of the task")
    description: str = Field(description="Detailed instructions, requirements, or bug description")
    repository_type: str = Field(default="sample", description="'sample' or 'custom_upload'")
    sample_name: Optional[str] = Field(default="calculator", description="Name of sample project if sample")
    enable_research: bool = Field(default=True, description="Whether to query Tavily documentation research")
    max_repair_attempts: int = Field(default=1, description="Maximum self-repair iterations")
    verification_profile: str = Field(default="standard", description="'quick', 'standard', or 'exhaustive'")


class TaskResponse(BaseModel):
    task_id: str
    title: str
    description: str
    repository_type: str
    sample_name: Optional[str] = None
    created_at: str


class SampleProjectInfo(BaseModel):
    name: str
    title: str
    description: str
    files: List[str]
    test_files: List[str]
