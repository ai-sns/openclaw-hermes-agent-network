from db.base_class import Base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean


class ConfigItem(Base):
    __tablename__ = 'config_items'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
    description = Column(String)
