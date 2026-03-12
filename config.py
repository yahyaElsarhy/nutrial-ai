"""
NutriAI - Centralized Configuration
Single source of truth for all settings.
Uses pydantic-settings for type-safe env loading.
Author: Senior AI Engineer
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS CLASS
# ══════════════════════════════════════════════════════════════════════════════

class Settings(BaseSettings):

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME:        str = "NutriAI"
    APP_VERSION:     str = "1.0.0"
    APP_ENV:         str = Field("development", env="APP_ENV")  # development | production
    DEBUG:           bool = Field(True, env="DEBUG")

    # ── Server ────────────────────────────────────────────────────────────────
    HOST:            str = Field("0.0.0.0",  env="HOST")
    PORT:            int = Field(8000,        env="PORT")
    FRONTEND_URL:    str = Field("http://localhost:8501", env="FRONTEND_URL")

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET:      str  = Field("change-me-in-production", env="JWT_SECRET")
    JWT_ALGORITHM:   str  = "HS256"
    JWT_EXPIRE_HOURS: int = Field(24, env="JWT_EXPIRE_HOURS")

    # ── AI Providers ──────────────────────────────────────────────────────────
    GROQ_API_KEY:        Optional[str] = Field(None, env="GROQ_API_KEY")
    OPENROUTER_API_KEY:  Optional[str] = Field(None, env="OPENROUTER_API_KEY")

    # ── Groq Models ───────────────────────────────────────────────────────────
    GROQ_DEFAULT_MODEL:  str = "llama-3.3-70b-versatile"   # diet generation
    GROQ_FAST_MODEL:     str = "llama-3.1-8b-instant"      # chat responses
    GROQ_BASE_URL:       str = "https://api.groq.com/openai/v1"

    # ── OpenRouter Models ─────────────────────────────────────────────────────
    OPENROUTER_DEFAULT_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_BASE_URL:      str = "https://openrouter.ai/api/v1"
    OPENROUTER_APP_REFERER:   str = "https://nutriai.app"

    # ── LLM Parameters ────────────────────────────────────────────────────────
    DIET_TEMPERATURE:    float = 0.2    # low = deterministic & safe for medical
    CHAT_TEMPERATURE:    float = 0.7    # higher = more natural conversation
    DIET_MAX_TOKENS:     int   = 8000   # 15-day plan needs room
    CHAT_MAX_TOKENS:     int   = 1024   # chat replies stay concise
    REQUEST_TIMEOUT:     float = 60.0   # seconds

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list = ["*"]   # lock down in production: ["https://yourdomain.com"]

    class Config:
        env_file         = ".env"
        env_file_encoding = "utf-8"
        case_sensitive   = False    # GROQ_API_KEY == groq_api_key

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def groq_available(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def openrouter_available(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    def available_providers(self) -> list[str]:
        providers = []
        if self.groq_available:       providers.append("groq")
        if self.openrouter_available: providers.append("openrouter")
        return providers


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON — import this everywhere
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache()
def get_settings() -> Settings:
    """
    Cached singleton — reads .env once, reuses everywhere.
    Usage:
        from config import get_settings
        settings = get_settings()
    """
    return Settings()


# Convenience alias
settings = get_settings()