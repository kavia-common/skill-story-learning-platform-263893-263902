import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load .env if present (no secrets stored in code)
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DB_HOST: Optional[str] = os.getenv("DB_HOST")
    DB_PORT: Optional[str] = os.getenv("DB_PORT")
    DB_NAME: Optional[str] = os.getenv("DB_NAME")
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    APP_SECRET: Optional[str] = os.getenv("APP_SECRET")
    FRONTEND_ORIGIN: Optional[str] = os.getenv("FRONTEND_ORIGIN")

    # Token expirations
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

    # Connection resiliency tunables
    DB_CONNECT_MAX_RETRIES: int = int(os.getenv("DB_CONNECT_MAX_RETRIES", "10"))
    DB_CONNECT_BACKOFF_SECONDS: float = float(os.getenv("DB_CONNECT_BACKOFF_SECONDS", "1.5"))
    DB_SEED_DEFER: bool = os.getenv("DB_SEED_DEFER", "true").lower() in ("1", "true", "yes")

    def db_url(self) -> str:
        """Return a SQLAlchemy-compatible async PostgreSQL URL.

        Supports common provider formats:
        - postgresql+asyncpg://user:pass@host:port/db
        - postgresql://user:pass@host:port/db
        - postgres://user:pass@host:port/db
        The latter two are normalized to asyncpg driver.
        """
        url = self.DATABASE_URL
        if url:
            # Trim whitespace
            url = url.strip()
            # Many environments provide 'postgres://'; normalize to 'postgresql+asyncpg://'
            if url.startswith("postgresql+asyncpg://"):
                return url
            if url.startswith("postgres://"):
                return "postgresql+asyncpg://" + url[len("postgres://") :]
            if url.startswith("postgresql://"):
                return "postgresql+asyncpg://" + url[len("postgresql://") :]
            # If user already provided another async dialect we respect it
            return url

        # Build from parts if DATABASE_URL not provided
        required_parts = [self.DB_HOST, self.DB_PORT, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]
        if not all(required_parts):
            raise ValueError(
                "Database configuration missing. Provide DATABASE_URL or all of DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD."
            )
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def validate(self):
        """Validate critical environment variables (non-secrets)."""
        missing = []
        if not self.APP_SECRET:
            missing.append("APP_SECRET")
        # FRONTEND_ORIGIN is optional but recommended

        # Validate DB URL composition and driver normalization
        try:
            _ = self.db_url()
        except Exception as e:
            raise ValueError(str(e))
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
