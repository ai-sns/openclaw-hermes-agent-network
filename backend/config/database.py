"""
Database Configuration - 异步版本

Manages SQLAlchemy database connection and session.
Extracted from db/database.py for better organization.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Generator
import logging
import asyncio

from .settings import get_settings

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# SQLAlchemy Base
Base = declarative_base()

# 异步数据库 URL
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.database.full_path}"

# 创建异步引擎
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.debug
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 同步 Session 工厂（向后兼容）
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
SYNC_SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.database.full_path}"
sync_engine = create_engine(
    SYNC_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    echo=settings.debug
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入 - 异步数据库会话

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
    获取同步数据库会话（向后兼容）

    Usage:
        db = get_db_sync()
        try:
            # Use db
            db.commit()
        finally:
            db.close()
    """
    return SessionLocal()


# 向后兼容的别名
def get_db_session() -> Session:
    """
    获取同步数据库会话（旧名称，向后兼容）

    Deprecated: 使用 get_db_sync() 代替
    """
    return get_db_sync()


def get_db_sync_depends() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入 - 同步数据库会话（用于非异步操作）

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


# 为了向后兼容，提供一个非生成器版本的别名
# 但这不应该在 FastAPI Depends 中使用
get_db_legacy = get_db  # 这会覆盖异步生成器版本，所以需要重命名原来的 get_db


# 重新定义 get_db 为异步生成器（因为上面被覆盖了）
async def get_db_async_depends() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入 - 异步数据库会话（显式名称）

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_async_depends)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        yield session


# 为了向后兼容，让 get_db 指向异步版本
get_db = get_db_async_depends


def init_db():
    """
    初始化数据库表（同步）
    Creates all tables if they don't exist
    """
    try:
        # 导入所有模型以注册到 Base
        from backend.database.models import agent, chat, km, map, system

        # 创建所有表
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """关闭数据库连接（异步）"""
    try:
        await engine.dispose()
        sync_engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


def close_db_sync():
    """关闭数据库连接（同步）"""
    sync_engine.dispose()
    logger.info("Database connection closed")
