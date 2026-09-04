"""
database.py
───────────
Database connectivity for the application.

Sets up:
  - A SQLAlchemy engine connected to PostgreSQL using the DATABASE_URL from config.
  - A session factory (SessionLocal) for creating database sessions.
  - A declarative Base class that all SQLAlchemy models inherit from.
  - A get_db() dependency for FastAPI routes to receive and auto-close sessions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# The engine manages the connection pool to PostgreSQL.
# pool_pre_ping=True causes SQLAlchemy to test each connection before use,
# which prevents "connection closed" errors after idle periods.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# ── Session factory ───────────────────────────────────────────────────────────
# autocommit=False  — we control transactions explicitly (commit/rollback)
# autoflush=False   — we flush manually before queries when needed
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
# All SQLAlchemy model classes inherit from Base.
# Base.metadata holds the full schema, which Alembic reads for migrations.
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that yields a database session for the duration of a
    request and ensures the session is always closed afterwards, even on error.

    Usage in a route:
        @router.get("/example")
        def example_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
