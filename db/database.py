from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from core.conf import settings

Base = declarative_base()

SQL_URL = os.path.join(settings.SQL_URL, "db.sqlite")
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:99cloud@localhost:3306/demo?charset=utf8"
SQLALCHEMY_DATABASE_URL = fr"sqlite:///{SQL_URL}"
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL
# )
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
