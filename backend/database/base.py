"""Database session management and base configuration.

Uses the unified sync engine from db/DBFactory (NullPool + WAL + busy_timeout).
"""
from sqlalchemy.ext.declarative import declarative_base

# Base class for ORM models
Base = declarative_base()

# Reuse the single shared engine from db/DBFactory
from db.DBFactory import engine, Session as SessionLocal  # unified sync engine


def get_session():
    """Get a new database session."""
    return SessionLocal()


def create_all_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(engine)
