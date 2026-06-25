"""
FastAPI application entry point.
"""
import sys
import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.routes.health import router as health_router
from app.routes.audit import router as audit_router
from app.routes.export import router as export_router

# Setup logging before anything else
setup_logging()
logger = logging.getLogger("audit_tool")


def create_app() -> FastAPI:
    """Application factory."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("%s v%s started", settings.APP_NAME, settings.APP_VERSION)
        logger.info("Docs available at http://localhost:8000/docs")
        yield

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Website Audit Tool API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(audit_router)
    app.include_router(export_router)
    import os
    screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")

    return app


app = create_app()
