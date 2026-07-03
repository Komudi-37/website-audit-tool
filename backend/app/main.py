"""
FastAPI application entry point.
"""
import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
print("\n========== BACKEND STARTUP ==========")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"sys.platform: {sys.platform}")
print(f"sys.version_info: {sys.version_info}")
print(f"Event loop policy BEFORE: id={id(asyncio.get_event_loop_policy())}, type={type(asyncio.get_event_loop_policy()).__name__}")
print("====================================\n")

# Python 3.14+ on Windows has issues with WindowsProactorEventLoopPolicy and subprocess
# Use SelectorEventLoopPolicy to avoid NotImplementedError in asyncio.create_subprocess_exec
if sys.platform.startswith("win"):
    if sys.version_info >= (3, 14):
        # In Python 3.14+, use WindowsSelectorEventLoopPolicy for subprocess support
        asyncio.set_event_loop_policy(asyncio._WindowsSelectorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

print(f"Event loop policy AFTER: id={id(asyncio.get_event_loop_policy())}, type={type(asyncio.get_event_loop_policy()).__name__}")
print("====================================\n")

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

_MAX_BODY_SIZE = 10 * 1024  # 10 KB


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