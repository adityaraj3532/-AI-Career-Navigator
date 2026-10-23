from functools import lru_cache
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # Database (PostgreSQL via asyncpg)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "career_navigator"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/career_navigator"

    # Redis Cache & Worker Queue
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Tokens
    JWT_SECRET_KEY: str = "change_this_to_a_secure_random_64_char_secret_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM Gateway
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 15
    GEMINI_MAX_RETRIES: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            key_bytes = self.JWT_SECRET_KEY.encode("utf-8")
            if len(key_bytes) < 32 or "change_this" in self.JWT_SECRET_KEY.lower():
                raise ValueError(
                    "Production requires a secure, non-default JWT_SECRET_KEY of at least 32 bytes (256 bits)."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
