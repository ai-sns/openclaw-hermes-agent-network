"""Database session management and base configuration."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Base class for ORM models
Base = declarative_base()

# Database path configuration
DBPath = os.path.join(Path(__file__).resolve().parent.parent.parent, "db", "db.sqlite")
print("DBPath", DBPath)
SQL_DATABASE_URL = fr"sqlite:///{DBPath}"

# Create engine with connection pool settings
# 注意：对于SQLite，不建议设置太大的连接池
# 如果需要更高并发，应考虑迁移到PostgreSQL/MySQL
engine = create_engine(
    SQL_DATABASE_URL,
    pool_size=10,           # 常驻连接数（建议10-20）
    max_overflow=20,        # 溢出连接数（建议20-30）
    pool_timeout=60,        # 连接等待超时（秒）
    pool_recycle=3600,      # 连接回收时间（1小时）
    pool_pre_ping=True,     # 检查连接健康状态
    echo=False,             # 生产环境关闭SQL日志
    connect_args={
        "check_same_thread": False,  # 允许SQLite跨线程使用
        "timeout": 30                # SQLite锁超时时间（秒）
    }
)

# 如果需要更高并发，可以调整为：
# pool_size=20, max_overflow=30  → 总共50个连接
# pool_size=30, max_overflow=50  → 总共80个连接
# 但注意：SQLite写入仍然是单线程的，增加连接池不会提高写入性能

# Session factory
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()


def create_all_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(engine)
