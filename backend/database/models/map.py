"""Map-related ORM models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from backend.config.database import Base


class MapTrade(Base):
    """Map trade model."""
    __tablename__ = 'map_trade'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(50), doc="Trade ID")
    trade_type = Column(String(100), doc="Trade type")
    title = Column(String(500), doc="Title")
    detail = Column(Text, doc="Detail")
    link = Column(Text, doc="Link")
    trade_with_name = Column(String(200), doc="Trade with name")
    trade_with_account = Column(String(200), doc="Trade with account")
    trade_with_company = Column(Boolean, default=False, doc="Trade with company")
    pay = Column(Float, default=100, doc="Pay")
    pay_method = Column(Text, default="as_coin", doc="Pay method")
    status = Column(Integer, default=0, doc="Status")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapVisit(Base):
    """Map visit model."""
    __tablename__ = 'map_visit'

    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String(50), doc="Visit ID")
    title = Column(String(500), doc="Title")
    detail = Column(Text, doc="Detail")
    place_type = Column(String(100), doc="Place type")
    address = Column(Text, doc="Address")
    lng = Column(Float, doc="Longitude")
    lat = Column(Float, doc="Latitude")
    url = Column(Text, doc="Place intro URL")
    coord_key = Column(String(80), doc="Normalized coordinate key")
    owner_name = Column(String(200), doc="Owner name")
    owner_account = Column(String(100), doc="Owner account")
    owner_type = Column(String(50), doc="Owner type")
    is_free = Column(Boolean, default=True, doc="Is free")
    trade_id = Column(String(100), doc="Trade ID")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapActivity(Base):
    """Map activity model."""
    __tablename__ = 'map_activity'

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(50), doc="Activity ID")
    content = Column(Text, doc="Content")
    type = Column(String(100), doc="Type")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")


class MapPresetMsg(Base):
    """Map preset message model."""
    __tablename__ = 'map_preset_msg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, doc="Content")
    position = Column(Integer, default=0, doc="Position")
    create_time = Column(DateTime, default=datetime.now, doc="Create time")
    is_delete = Column(Boolean, default=False, doc="Soft delete")
