"""Evidence-Driven Model Routing Engine for NVIDIA Nemotron Models on Nebius.
Selects optimal model tier based on task complexity, verification failures, and cost budgets.
"""

from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.schemas.runs import ModelTier, RoutingDecision
from app.core.logging import logger

# Approximate estimated pricing per 1M tokens (for transparency and estimation)
# Nemotron mini: ~$0.20/1M, 70B: ~$0.70/1M, 340B: ~$2.50/1M
TOKEN_PRICING_ESTIMATES = {
    ModelTier.FAST: 0.20 / 1_000_000,
    ModelTier.STANDARD: 0.70 / 1_000_000,
    ModelTier.ESCALATION: 2.50 / 1_000_000,
}


class ModelRouter:
    """Routes requests dynamically based on verified signals and verification history."""

    def select_model(
        self,
        task_description: str,
        affected_files: int = 1,
        attempt: int = 1,
        failure_type: Optional[str] = None,
        is_repair: bool = False,
    ) -> RoutingDecision:
        """Determines the appropriate model tier and returns a populated RoutingDecision."""
        
        # Signal 1: Repeated repair / regression failure -> Escalation Tier
        if is_repair or (failure_type in ("REGRESSION_TEST", "SYNTAX_ERROR") and attempt > 1):
            tier = ModelTier.ESCALATION
            model_id = settings.NEBIUS_MODEL_ESCALATION
            trigger = "VERIFICATION_FAILURE_ESCALATION"
            reason = (
                f"Repair iteration {attempt} required after failure: {failure_type or 'regression'}. "
                f"Escalating to high-capacity Nemotron model ({model_id}) for bounded repair."
            )

        # Signal 2: Complex multi-file or algorithmic task -> Standard Tier
        elif affected_files > 2 or len(task_description) > 350 or "refactor" in task_description.lower():
            tier = ModelTier.STANDARD
            model_id = settings.NEBIUS_MODEL_STANDARD
            trigger = "COMPLEX_SPECIFICATION"
            reason = (
                f"Task complexity warrants standard tier (affected files: {affected_files}, "
                f"description length: {len(task_description)}). Selected {model_id}."
            )

        # Signal 3: Simple targeted fix / planning -> Fast Tier
        else:
            tier = ModelTier.FAST
            model_id = settings.NEBIUS_MODEL_FAST
            trigger = "TARGETED_LOCAL_CHANGE"
            reason = (
                f"Single-file targeted task suitable for fast tier. "
                f"Selected {model_id} for low latency and efficiency."
            )

        logger.info(f"Model Router decision: Tier={tier.value}, Model={model_id}, Trigger={trigger}")

        return RoutingDecision(
            model_id=model_id,
            tier=tier,
            trigger=trigger,
            reason=reason,
            attempt=attempt,
            latency_ms=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
        )

    def calculate_cost(self, tier: ModelTier, total_tokens: int) -> float:
        """Estimates cost based on token count and tier pricing estimate."""
        rate = TOKEN_PRICING_ESTIMATES.get(tier, 0.70 / 1_000_000)
        return round(total_tokens * rate, 6)


model_router = ModelRouter()
