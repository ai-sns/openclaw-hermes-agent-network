"""
Database Configuration - Async version

Manages SQLAlchemy database connection and session.
Extracted from db/database.py for better organization.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Generator
import logging
import asyncio
import sqlite3
from sqlalchemy import event

from .settings import get_settings

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# SQLAlchemy Base
Base = declarative_base()

# Async database URL
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.database.full_path}"

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.debug,
    connect_args={"timeout": 30}
)


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_on_connect_async(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        try:
            cursor.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        try:
            cursor.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        cursor.close()
    except Exception:
        pass

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync engine: reuse the single shared engine from db/DBFactory (NullPool + WAL + busy_timeout)
from sqlalchemy.orm import sessionmaker, Session
from db.DBFactory import engine as sync_engine  # unified sync engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injection - async DB session

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        yield session


def get_db_sync() -> Session:
    """
    Get a sync DB session (backward compatible)

    Usage:
        db = get_db_sync()
        try:
            # Use db
            db.commit()
        finally:
            db.close()
    """
    return SessionLocal()


# Backward-compatible alias
def get_db_session() -> Session:
    """
    Get a sync DB session (legacy name, backward compatible)

    Deprecated: use get_db_sync() instead
    """
    return get_db_sync()


def get_db_sync_depends() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection - sync DB session (for non-async operations)

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db_sync_depends)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# For backward compatibility, provide a non-generator alias
# But this should not be used in FastAPI Depends
get_db_legacy = get_db  # This overwrites the async generator version, so the original get_db must be renamed
 


# Redefine get_db as an async generator (because it was overwritten above)
async def get_db_async_depends() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injection - async DB session (explicit name)

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_async_depends)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        yield session


# For backward compatibility, make get_db point to the async version
get_db = get_db_async_depends


def init_db():
    """
    Initialize database tables (sync)
    Creates all tables if they don't exist
    """
    try:
        # Import all models to register them to Base
        from backend.database.models import agent, chat, km, map, system

        # Create all tables
        Base.metadata.create_all(bind=sync_engine)

        _ensure_aichat_cfg_goods_service_columns(settings.database.full_path)
        _ensure_map_visit_columns(settings.database.full_path)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def _ensure_aichat_cfg_goods_service_columns(db_path: str) -> None:
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(aichat_cfg)")
        columns = [row[1] for row in cursor.fetchall()]

        changed = False
        if "goods_or_service_description" not in columns:
            cursor.execute("ALTER TABLE aichat_cfg ADD COLUMN goods_or_service_description TEXT")
            changed = True
        if "goods_or_service_price" not in columns:
            cursor.execute("ALTER TABLE aichat_cfg ADD COLUMN goods_or_service_price VARCHAR(100)")
            changed = True

        if "route_points" not in columns:
            cursor.execute("ALTER TABLE aichat_cfg ADD COLUMN route_points TEXT")
            changed = True

        if changed:
            conn.commit()
            logger.info("Auto-migrated aichat_cfg: ensured goods/service columns")
    except Exception as e:
        logger.warning("Auto-migration for aichat_cfg goods/service columns failed: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _ensure_map_visit_columns(db_path: str) -> None:
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(map_visit)")
        columns = [row[1] for row in cursor.fetchall()]

        changed = False
        if "url" not in columns:
            cursor.execute("ALTER TABLE map_visit ADD COLUMN url TEXT")
            changed = True
        if "coord_key" not in columns:
            cursor.execute("ALTER TABLE map_visit ADD COLUMN coord_key TEXT")
            changed = True

        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_map_visit_coord_key ON map_visit(coord_key)"
        )

        if changed:
            conn.commit()
            logger.info("Auto-migrated map_visit: ensured url/coord_key columns")
    except Exception as e:
        logger.warning("Auto-migration for map_visit columns failed: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


async def close_db():
    """Close database connections (async)."""
    try:
        await engine.dispose()
        # Note: sync_engine is the shared DBFactory engine; disposing it affects all users
        logger.info("Async database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


def close_db_sync():
    """Close database connections (sync)."""
    # Note: sync_engine is the shared DBFactory engine; only dispose on full shutdown
    logger.info("Sync database connection close requested (shared engine)")
