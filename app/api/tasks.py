"""Task intake and sample repository API endpoints for VERIQ.
"""

from typing import List
from fastapi import APIRouter
from app.schemas.tasks import SampleProjectInfo

router = APIRouter(tags=["tasks"])


@router.get("/samples", response_model=List[SampleProjectInfo])
async def list_sample_projects():
    """Lists preconfigured sample repositories available for autonomous engineering runs."""
    return [
        SampleProjectInfo(
            name="calculator",
            title="Scientific & Statistical Calculator Library",
            description=(
                "Python 3 mathematics and statistics library containing arithmetic operations, "
                "powers, percentages, mean, median, and factorial, backed by a comprehensive pytest suite."
            ),
            files=["calculator.py"],
            test_files=["test_calculator.py"],
        )
    ]
