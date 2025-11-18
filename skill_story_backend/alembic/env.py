import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import application models metadata
# We import SQLModel and metadata from our db module.
from sqlmodel import SQLModel
from src.api.modules.db import SQLModel as _SQLModel  # noqa: F401
from src.api.modules.db import User, Story, Episode, Choice, JournalEntry  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide target metadata for 'autogenerate' support
target_metadata = SQLModel.metadata


def _resolve_db_url() -> str:
    """Resolve a synchronous SQLAlchemy URL for Alembic runs.

    Prefers ALEMBIC_DB_URL. If absent, converts DATABASE_URL to sync form by removing '+asyncpg'.
    """
    alembic_url = os.getenv("ALEMBIC_DB_URL")
    if alembic_url:
        return alembic_url.strip()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        # Attempt parts
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        if all([host, port, name, user, password]):
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        raise RuntimeError(
            "Alembic requires ALEMBIC_DB_URL or DATABASE_URL/DB_* to be set for migrations."
        )
    # Normalize async to sync for Alembic
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + database_url[len("postgresql+asyncpg://") :]
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    if database_url.startswith("postgresql://"):
        return database_url
    # last resort: return as-is
    return database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _resolve_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _resolve_db_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
