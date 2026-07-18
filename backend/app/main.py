"""
FastAPI application entry point.
"""
import sys
import asyncio

# Playwright requires the Selector event loop on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.limiter import limiter
from app.core.database import init_db
from app.routes.health import router as health_router
from app.routes.audit import router as audit_router
from app.routes.export import router as export_router

setup_logging()
logger = logging.getLogger("audit_tool")

_MAX_BODY_SIZE = 2 * 1024 * 1024   # 2 MB


def create_app() -> FastAPI:
    """Application factory."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("\n========== FASTAPI LIFESPAN START ==========")
        print(f"Event loop policy in lifespan: id={id(asyncio.get_event_loop_policy())}, type={type(asyncio.get_event_loop_policy()).__name__}")
        try:
            loop = asyncio.get_running_loop()
            print(f"Running loop: id={id(loop)}, type={type(loop).__name__}")
        except RuntimeError:
            print("No running loop in lifespan")
        print("============================================\n")
        init_db()
        logger.info("%s v%s started", settings.APP_NAME, settings.APP_VERSION)
        logger.info("Docs available at http://localhost:8000/docs")
        yield

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Website Audit Tool API",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Body size limit ───────────────────────────────────────────────────────
    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})
        return await call_next(request)

    # ── Security headers ─────────────────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Rate limiting ─────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

    screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    app.mount("/screenshots", StaticFiles(directory=screenshots_dir), name="screenshots")

    return app


app = create_app()