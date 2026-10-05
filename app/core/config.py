from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # App Info
    PROJECT_NAME: str = "Classic Legend Crackers E-Commerce API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+pg8000://postgres.diaqqdefxfujlbifxkko:i%2B5ZZ52-K%21E%24xt-@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Security & JWT
    JWT_SECRET_KEY: str = "classic_legend_crackers_ultra_secure_production_secret_key_2026_x928a"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "*",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]

    # Business Defaults
    DEFAULT_DELIVERY_CHARGE: float = 500.0
    FREE_DELIVERY_THRESHOLD: float = 3000.0
    MIN_ORDER_AMOUNT: float = 3000.0

    # Telegram Instant Mobile Alerts (100% Free)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def sanitize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+pg8000://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = v.replace("postgresql://", "postgresql+pg8000://", 1)
            elif v.startswith("postgresql+psycopg2://"):
                v = v.replace("postgresql+psycopg2://", "postgresql+pg8000://", 1)

            # Transform direct IPv6-only db.<ref>.supabase.co to IPv4 dual-stack pooler for Vercel Lambdas
            if "db.diaqqdefxfujlbifxkko.supabase.co" in v:
                v = v.replace("db.diaqqdefxfujlbifxkko.supabase.co", "aws-0-ap-southeast-2.pooler.supabase.com")
                if "postgres:" in v and "postgres.diaqqdefxfujlbifxkko:" not in v:
                    v = v.replace("postgres:", "postgres.diaqqdefxfujlbifxkko:", 1)

            if "@" in v:
                import re
                import urllib.parse
                prefix_match = re.match(r"^([a-zA-Z0-9\+\-\._]+://)([^:]+):(.+)@([^@]+)$", v)
                if prefix_match:
                    proto, user, password, host_part = prefix_match.groups()
                    safe_pwd = urllib.parse.quote(urllib.parse.unquote(password), safe="")
                    return f"{proto}{user}:{safe_pwd}@{host_part}"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()
