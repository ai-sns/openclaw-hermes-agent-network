from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Table

from db.base_class import Base


class Test(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    test = Column(String(10), nullable=False)
