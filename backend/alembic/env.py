"""
alembic/env.py
──────────────
Alembic environment configuration.

This file is executed by Alembic when running migration commands. It:
  1. Loads the database URL from our app's config (never from alembic.ini).
  2. Imports all SQLAlchemy models so their metadata is available.
  3. Configures both offline mode (generates SQL scripts) and online mode
     (applies migrations directly to the database).

Adding a new model:
  - Add it to app/models/__init__.py.
  - Run: alembic revision --autogenerate -m "your description"
  - Review the generated file in alembic/versions/ before applying it.
  - Run: alembic upgrade head
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make the app package importable from this file ────────────────────────────
# Alembic runs from the backend/ directory, so we add it to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Load app config and models ────────────────────────────────────────────────
from app.config import settings          # Our pydantic-settings config
from app.database import Base            # The shared declarative base
import app.models                        # Registers all models onto Base.metadata

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from our config (not from alembic.ini)
# This is the correct pattern — never put real credentials in alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that Alembic inspects to generate migrations
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Offline mode generates a SQL script rather than connecting to the database.
    Useful for reviewing what SQL will be run, or for DBAs who apply migrations
    manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Online mode connects directly to the database and applies migrations.
    This is the mode used by: alembic upgrade head
    """
    # Create an engine from the config (uses our overridden DATABASE_URL)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool is preferred for migration scripts
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
