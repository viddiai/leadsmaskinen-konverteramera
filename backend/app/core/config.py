"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Lead Generation Conversion Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_URL: Optional[str] = None  # Public URL for widget (e.g., https://example.railway.app)

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/conversion_analyzer"

    # CORS - comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    REPORT_ACCESS_TOKEN_EXPIRE_HOURS: int = 72

    # Admin credentials (set via environment variables in production)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme123"

    # Email (for sending reports)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@conversion-analyzer.se"

    # Analysis
    SCRAPE_TIMEOUT: int = 30  # seconds
    MAX_PAGE_SIZE: int = 5_000_000  # 5MB max page size

    # Widget
    WIDGET_ALLOWED_DOMAINS: str = "*"  # Comma-separated, or * for all

    # AI/Claude API settings
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_ENABLED: bool = True
    AI_MODEL: str = "claude-sonnet-4-5-20250929"  # Latest Sonnet - high quality
    AI_MAX_TOKENS: int = 1500
    AI_TEMPERATURE: float = 0.7
    AI_FALLBACK_ON_ERROR: bool = True  # Use static templates if AI fails

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
