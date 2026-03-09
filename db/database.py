from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from core.conf import settings

Base = declarative_base()

SQL_URL = os.path.join(settings.SQL_URL, "db.sqlite")
SQLALCHEMY_DATABASE_URL = fr"sqlite:///{SQL_URL}"

# Reuse the single shared engine from db/DBFactory (NullPool + WAL + busy_timeout)
from db.DBFactory import engine, Session as SessionLocal  # unified sync engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
