"""Unit tests for Evidence-Driven Model Routing.
"""

from app.services.model_router import model_router
from app.schemas.runs import ModelTier


def test_fast_tier_routing_for_small_tasks():
    decision = model_router.select_model(
        task_description="Fix boundary condition in divide",
        affected_files=1,
        attempt=1,
        is_repair=False,
    )
    assert decision.tier == ModelTier.FAST
    assert decision.trigger == "TARGETED_LOCAL_CHANGE"


def test_standard_tier_for_complex_tasks():
    long_desc = "Implement complete statistical module with variance, skewness, kurtosis, and multi-file dependencies" * 5
    decision = model_router.select_model(
        task_description=long_desc,
        affected_files=3,
        attempt=1,
        is_repair=False,
    )
    assert decision.tier == ModelTier.STANDARD
    assert decision.trigger == "COMPLEX_SPECIFICATION"


def test_escalation_tier_on_repair_trigger():
    decision = model_router.select_model(
        task_description="Fix regression in factorial",
        affected_files=1,
        attempt=2,
        failure_type="REGRESSION_TEST",
        is_repair=True,
    )
    assert decision.tier == ModelTier.ESCALATION
    assert decision.trigger == "VERIFICATION_FAILURE_ESCALATION"
    assert "nvidia/nemotron-4-340b" in decision.model_id
