"""VERIQ — FastAPI Application Entrypoint.
Tagline: Code is generated. Proof is earned.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import logger
from app.core.errors import VeriqError
from app.storage.database import init_database
from app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} — {settings.TAGLINE}")
    init_database()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description=f"Evidence-Driven Autonomous Engineering Agent. {settings.TAGLINE}",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    """Ensure static assets always revalidate during development."""
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path in ("/", "/diagram"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Custom exception handler for typed VeriqErrors
@app.exception_handler(VeriqError)
async def veriq_exception_handler(request: Request, exc: VeriqError):
    logger.warning(f"Handled VeriqError on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"error": exc.__class__.__name__, "message": exc.message, "details": exc.details},
    )


# Mount API router
app.include_router(api_router)

# Mount static frontend directory
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serves the VERIQ Developer Workbench application."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        content={
            "app": settings.APP_NAME,
            "tagline": settings.TAGLINE,
            "status": "online",
            "api_docs": "/docs",
        }
    )


@app.get("/diagram", include_in_schema=False)
async def diagram():
    """Serves the VERIQ Architecture & Workflow Execution Flow Diagram."""
    diagram_file = static_dir / "diagram.html"
    if diagram_file.exists():
        return FileResponse(str(diagram_file))
    return JSONResponse(status_code=404, content={"error": "Diagram not found"})
