"""Main API Router aggregator for VERIQ.
"""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.tasks import router as tasks_router
from app.api.runs import router as runs_router
from app.api.benchmarks import router as benchmarks_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(runs_router)
api_router.include_router(benchmarks_router)
