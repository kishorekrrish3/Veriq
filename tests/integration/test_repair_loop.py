"""Integration test for the autonomous bounded self-repair cycle.
Verifies failure detection, model escalation, and subsequent verification.
"""

import pytest
import uuid
from app.services.orchestrator import orchestrator
from app.storage.repositories import RunRepository
from app.schemas.runs import RunStatus, ModelTier


@pytest.mark.asyncio
async def test_bounded_self_repair_workflow():
    run_id = f"REPAIR-TEST-{uuid.uuid4().hex[:6]}"

    await orchestrator._execute_run(
        run_id=run_id,
        title="Repair Verification Task",
        description="Verify that test failure triggers escalation and repair",
        sample_name="calculator",
        enable_research=True,
        max_repair_attempts=1,
        mode="replay",
    )

    run = RunRepository.get_run(run_id)
    assert run is not None
    assert run.status == RunStatus.COMPLETED

    # Verify routing history has 2 decisions: initial + escalation
    assert len(run.routing_history) == 2
    assert run.routing_history[0].tier == ModelTier.FAST
    assert run.routing_history[1].tier == ModelTier.ESCALATION
    assert run.routing_history[1].trigger == "VERIFICATION_FAILURE_ESCALATION"

    # Verify ledger summary
    assert run.ledger_summary is not None
    assert run.ledger_summary.verified_count >= 4
    assert run.ledger_summary.failed_count == 0
