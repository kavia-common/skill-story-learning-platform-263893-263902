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

    def db_url(self) -> str:
        """Return a SQLAlchemy-compatible async PostgreSQL URL."""
        if self.DATABASE_URL:
            # Ensure async driver scheme for SQLAlchemy 2.x
            if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                return self.DATABASE_URL
            if self.DATABASE_URL.startswith("postgres://"):
                return "postgresql+asyncpg://" + self.DATABASE_URL[len("postgres://") :]
            if self.DATABASE_URL.startswith("postgresql://"):
                return "postgresql+asyncpg://" + self.DATABASE_URL[len("postgresql://") :]
            return self.DATABASE_URL
        # Build from parts if DATABASE_URL not provided
        if not all([self.DB_HOST, self.DB_PORT, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]):
            raise ValueError(
                "Database configuration missing. Provide DATABASE_URL or all of DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD."
            )
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def validate(self):
        """Validate critical environment variables."""
        missing = []
        if not self.APP_SECRET:
            missing.append("APP_SECRET")
        if not self.FRONTEND_ORIGIN:
            # FRONTEND_ORIGIN is recommended; not strictly required to run
            pass
        # DB validated via db_url call
        try:
            _ = self.db_url()
        except Exception as e:
            raise ValueError(str(e))
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
