from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

from backend.config.settings import get_settings

Base = declarative_base()

_settings = get_settings()
_default_db_dir = Path(__file__).resolve().parent
_sql_dir = Path(getattr(_settings.database, "sql_url", str(_default_db_dir)))
SQL_URL = str((_sql_dir / "db.sqlite").resolve())
SQLALCHEMY_DATABASE_URL = fr"sqlite:///{SQL_URL}"

# Reuse the single shared engine from db/DBFactory (NullPool + WAL + busy_timeout)
from db.DBFactory import engine, Session as SessionLocal  # unified sync engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
