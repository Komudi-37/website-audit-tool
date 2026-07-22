"""
Application configuration settings.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI-Powered Website Audit Tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    VERCEL_URL: str = ""

    # -----------------------------
    # AI Configuration
    # -----------------------------
    AI_PROVIDER: str = "openrouter"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-chat-v3"

    # -----------------------------
    # Performance API
    # -----------------------------
    GOOGLE_PAGESPEED_API_KEY: str = ""
    GOOGLE_PAGESPEED_BASE_URL: str = (
        "https://www.googleapis.com/pagespeedonline/v5"
    )

    # -----------------------------
    # Security APIs
    # -----------------------------
    MOZILLA_OBSERVATORY_BASE_URL: str = (
        "https://http-observatory.security.mozilla.org/api/v1"
    )

    SSL_LABS_BASE_URL: str = (
        "https://api.ssllabs.com/api/v3"
    )

    # -----------------------------
    # CORS
    # -----------------------------
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://website-audit-frontend.vercel.app",
    ]

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        env_origins = (
            kwargs.get("ALLOWED_ORIGINS")
            or os.environ.get("ALLOWED_ORIGINS")
        )

        if env_origins and not env_origins.strip().startswith("["):
            self.ALLOWED_ORIGINS = [
                origin.strip()
                for origin in env_origins.split(",")
            ]


settings = Settings()