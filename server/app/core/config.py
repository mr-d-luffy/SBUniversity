from functools import lru_cache
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "SiliconBrains University API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v, values):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    DB_POOL_SIZE: int = 3
    DB_MAX_OVERFLOW: int = 0
    DB_ECHO: bool = False

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "sbu-storage"

    @field_validator("SUPABASE_STORAGE_BUCKET")
    @classmethod
    def validate_storage_bucket_name(cls, value: str) -> str:
        bucket = value.strip()
        if not bucket or "://" in bucket or "/" in bucket:
            raise ValueError(
                "SUPABASE_STORAGE_BUCKET must be a bucket name such as 'sbu-storage', "
                "not a Supabase URL or storage endpoint"
            )
        return bucket

    # Clerk Auth
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_JWKS_URL: Optional[str] = None
    CLERK_ISSUER: Optional[str] = None
    CLERK_AUDIENCE: Optional[str] = None
    CLERK_WEBHOOK_SECRET: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Security & Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    ALLOW_DEV_AUTH_BYPASS: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
