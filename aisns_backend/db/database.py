"""
Database Configuration - Async version

Manages SQLAlchemy database connection and session.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Generator
import logging
import asyncio
import sqlite3
from sqlalchemy import event

from runtime.config.settings import get_settings
from db.base import Base

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

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


# Backward-compatible aliases for the async generator above.
# These all point to the same `get_db` defined earlier in this file.
get_db_async_depends = get_db
get_db_legacy = get_db


def init_db():
    """
    Initialize database tables (sync)
    Creates all tables if they don't exist and loads seed data if tables are empty
    """
    try:
        # Import all models to register them to Base
        from db.models import agent, aisns, km, tools, web, system

        # Create all tables
        Base.metadata.create_all(bind=sync_engine)

        _ensure_aisns_cfg_goods_service_columns(settings.database.full_path)
        _ensure_map_visit_columns(settings.database.full_path)

        # Load seed data if tables are empty (new database)
        _load_seed_data_if_empty()

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def _ensure_aisns_cfg_goods_service_columns(db_path: str) -> None:
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(aisns_cfg)")
        columns = [row[1] for row in cursor.fetchall()]

        changed = False
        if "goods_or_service_description" not in columns:
            cursor.execute("ALTER TABLE aisns_cfg ADD COLUMN goods_or_service_description TEXT")
            changed = True
        if "goods_or_service_price" not in columns:
            cursor.execute("ALTER TABLE aisns_cfg ADD COLUMN goods_or_service_price VARCHAR(100)")
            changed = True

        if "route_points" not in columns:
            cursor.execute("ALTER TABLE aisns_cfg ADD COLUMN route_points TEXT")
            changed = True
        if "agent_id" not in columns:
            cursor.execute("ALTER TABLE aisns_cfg ADD COLUMN agent_id INTEGER")
            changed = True

        if changed:
            conn.commit()
            logger.info("Auto-migrated aisns_cfg: ensured goods/service columns")
    except Exception as e:
        logger.warning("Auto-migration for aisns_cfg goods/service columns failed: %s", e)
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


def _load_seed_data_if_empty():
    """
    Load seed data into tables if they are empty (for new database initialization).
    This function populates tables with template data extracted from the reference database.
    """
    from datetime import datetime
    from sqlalchemy import select, func
    from db.models.agent import AgentCfg, Prompt, LLMConfig, RoleConfig
    from db.models.aisns import AISnsCfg
    from db.models.system import SystemCfg, SystemInit
    from db.models.web import WebMng
    from db.models.tools import McpMng
    from db.models.km import KMCfg
    from db.seed_data import (
        AGENT_CFG_SEED,
        AISNS_CFG_SEED,
        SYSTEM_INIT_SEED,
        SYSTEM_CFG_SEED,
        PROMPTS_SEED,
        WEB_MNG_SEED,
        LLM_CONFIG_SEED,
        ROLE_CONFIG_SEED,
        MCP_MNG_SEED,
        KM_CFG_SEED,
    )

    def _convert_datetime(data: dict, datetime_fields: list) -> dict:
        """Convert datetime string fields to datetime objects."""
        result = data.copy()
        for field in datetime_fields:
            if field in result and isinstance(result[field], str):
                try:
                    # Try multiple datetime formats
                    for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                        try:
                            result[field] = datetime.strptime(result[field], fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    # If conversion fails, keep original value
                    pass
        return result

    session = SessionLocal()
    try:
        # Check and populate agent_cfg
        count = session.scalar(select(func.count()).select_from(AgentCfg))
        if count == 0 and AGENT_CFG_SEED:
            for data in AGENT_CFG_SEED:
                converted = _convert_datetime(data, ["borndate", "create_time"])
                record = AgentCfg(**converted)
                session.add(record)
            logger.info("Seed data loaded: agent_cfg (%d records)", len(AGENT_CFG_SEED))

        # Check and populate aisns_cfg
        count = session.scalar(select(func.count()).select_from(AISnsCfg))
        if count == 0 and AISNS_CFG_SEED:
            for data in AISNS_CFG_SEED:
                converted = _convert_datetime(data, ["borndate", "create_time"])
                record = AISnsCfg(**converted)
                session.add(record)
            logger.info("Seed data loaded: aisns_cfg (%d records)", len(AISNS_CFG_SEED))

        # Check and populate system_init
        count = session.scalar(select(func.count()).select_from(SystemInit))
        if count == 0 and SYSTEM_INIT_SEED:
            for data in SYSTEM_INIT_SEED:
                converted = _convert_datetime(data, ["create_time"])
                record = SystemInit(**converted)
                session.add(record)
            logger.info("Seed data loaded: system_init (%d records)", len(SYSTEM_INIT_SEED))

        # Check and populate system_cfg
        count = session.scalar(select(func.count()).select_from(SystemCfg))
        if count == 0 and SYSTEM_CFG_SEED:
            for data in SYSTEM_CFG_SEED:
                converted = _convert_datetime(data, ["create_time"])
                record = SystemCfg(**converted)
                session.add(record)
            logger.info("Seed data loaded: system_cfg (%d records)", len(SYSTEM_CFG_SEED))

        # Check and populate prompts (no datetime fields)
        count = session.scalar(select(func.count()).select_from(Prompt))
        if count == 0 and PROMPTS_SEED:
            for data in PROMPTS_SEED:
                record = Prompt(**data)
                session.add(record)
            logger.info("Seed data loaded: prompts (%d records)", len(PROMPTS_SEED))

        # Check and populate web_mng
        count = session.scalar(select(func.count()).select_from(WebMng))
        if count == 0 and WEB_MNG_SEED:
            for data in WEB_MNG_SEED:
                converted = _convert_datetime(data, ["create_time"])
                record = WebMng(**converted)
                session.add(record)
            logger.info("Seed data loaded: web_mng (%d records)", len(WEB_MNG_SEED))

        # Check and populate llm_config
        count = session.scalar(select(func.count()).select_from(LLMConfig))
        if count == 0 and LLM_CONFIG_SEED:
            for data in LLM_CONFIG_SEED:
                converted = _convert_datetime(data, ["create_time", "update_time"])
                record = LLMConfig(**converted)
                session.add(record)
            logger.info("Seed data loaded: llm_config (%d records)", len(LLM_CONFIG_SEED))

        # Check and populate role_config
        count = session.scalar(select(func.count()).select_from(RoleConfig))
        if count == 0 and ROLE_CONFIG_SEED:
            for data in ROLE_CONFIG_SEED:
                converted = _convert_datetime(data, ["create_time", "update_time"])
                record = RoleConfig(**converted)
                session.add(record)
            logger.info("Seed data loaded: role_config (%d records)", len(ROLE_CONFIG_SEED))

        # Check and populate mcp_mng
        count = session.scalar(select(func.count()).select_from(McpMng))
        if count == 0 and MCP_MNG_SEED:
            for data in MCP_MNG_SEED:
                converted = _convert_datetime(data, ["create_time"])
                record = McpMng(**converted)
                session.add(record)
            logger.info("Seed data loaded: mcp_mng (%d records)", len(MCP_MNG_SEED))

        # Check and populate km_cfg
        count = session.scalar(select(func.count()).select_from(KMCfg))
        if count == 0 and KM_CFG_SEED:
            for data in KM_CFG_SEED:
                converted = _convert_datetime(data, ["create_time"])
                record = KMCfg(**converted)
                session.add(record)
            logger.info("Seed data loaded: km_cfg (%d records)", len(KM_CFG_SEED))

        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning("Failed to load seed data: %s", e)
    finally:
        session.close()

