"""
core/config.py
─────────────
All environment configuration via Pydantic Settings.
Reads from .env automatically. Type-safe. Zero surprises.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────
    ENV: str = "development"
    APP_NAME: str = "HaDir HRMS API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str                    # postgresql+asyncpg://user:pass@host/db
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300           # 5 minutes default cache

    # ── JWT ───────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Cloudflare R2 (S3-compatible) ─────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET_NAME: str = "hadir-uploads"
    R2_PUBLIC_URL: str = "https://cdn.hadir.id"

    # ── Firebase (push notifications) ─────────────────────
    FIREBASE_CREDENTIALS_JSON: str = ""  # path to service account JSON

    # ── Resend (transactional email) ──────────────────────
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@hadir.id"
    EMAIL_FROM_NAME: str = "HaDir HRMS"

    # ── Sentry ────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Indonesia-specific constants ──────────────────────
    DEFAULT_TIMEZONE: str = "Asia/Jakarta"
    WORKING_DAYS_DIVISOR: int = 26      # UU Ketenagakerjaan standard

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()