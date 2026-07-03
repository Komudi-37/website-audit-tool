"""
Application configuration settings.
"""
import os
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    APP_NAME: str = "AI-Powered Website Audit Tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    VERCEL_URL: str = ""
    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    class Config:
        env_file = ".env"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Allow overriding ALLOWED_ORIGINS from environment variable
        env_origins = kwargs.get("ALLOWED_ORIGINS") or os.environ.get("ALLOWED_ORIGINS")
        if env_origins and not env_origins.strip().startswith("["):
            self.ALLOWED_ORIGINS = [origin.strip() for origin in env_origins.split(",")]
settings = Settings()
