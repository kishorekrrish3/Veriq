"""Health check and provider status API endpoints for VERIQ.
"""

import sys
from fastapi import APIRouter
from app.core.config import settings
from app.services.nebius_client import nebius_client
from app.services.tavily_client import tavily_client
from app.services.sandbox import sandbox_runner

router = APIRouter(tags=["health"])


@router.get("/health")
async def get_health():
    """System health check and runtime environment info."""
    docker_available = sandbox_runner.is_docker_available(refresh=True)
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "tagline": settings.TAGLINE,
        "environment": settings.APP_ENV,
        "python_version": sys.version,
        "sandbox": {
            "docker_available": docker_available,
            "sandbox_mode": "DOCKER_CONTAINER" if docker_available else "ISOLATED_PROCESS_FALLBACK",
            "fallback_allowed": settings.ALLOW_FALLBACK_SANDBOX,
        },
        "modes": {
            "live_inference_configured": settings.is_live_inference_configured,
            "live_research_configured": settings.is_live_research_configured,
            "default_mode": "live" if settings.is_live_inference_configured else "recorded_replay",
        },
    }


@router.get("/providers/status")
async def get_providers_status():
    """Real-time provider connectivity check for Nebius and Tavily."""
    nebius_status = await nebius_client.check_health()
    tavily_status = await tavily_client.check_health()

    return {
        "nebius": nebius_status,
        "tavily": tavily_status,
    }


@router.get("/models")
async def get_models():
    """Catalog of NVIDIA Nemotron models mapped to VERIQ routing tiers."""
    return {
        "tiers": {
            "FAST": {
                "model_id": settings.NEBIUS_MODEL_FAST,
                "description": "Low-latency tier for initial planning and targeted modifications",
                "estimated_pricing": "$0.20 per 1M tokens",
            },
            "STANDARD": {
                "model_id": settings.NEBIUS_MODEL_STANDARD,
                "description": "Primary tier for algorithmic synthesis and multi-file reasoning",
                "estimated_pricing": "$0.70 per 1M tokens",
            },
            "ESCALATION": {
                "model_id": settings.NEBIUS_MODEL_ESCALATION,
                "description": "High-capacity tier for repairing regression test failures",
                "estimated_pricing": "$2.50 per 1M tokens",
            },
        },
        "active_base_url": settings.NEBIUS_BASE_URL,
    }
