"""Map repository with specialized CRUD operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc
from .base import BaseRepository
from ..models.map import (
    MapCfg, MapTask, MapTool, MapTrade, MapVisit,
    MapActivity, MapPresetMsg, ChatPresetMsg
)
from backend.config.database import get_db_session as get_session


class MapCfgRepository(BaseRepository[MapCfg]):
    """Map configuration repository."""

    def __init__(self):
        super().__init__(MapCfg)

    def create_with_id(self, **kwargs) -> int:
        """Create map configuration and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            cfg = _model(**kwargs)
            session.add(cfg)
            session.flush()
            return cfg.id
        return db_write(_do, description="repo_create_map_cfg")

    def get_all_ordered(self, **kwargs) -> List[MapCfg]:
        """Get all map configurations ordered by create time."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapCfg.create_time)).all()
        finally:
            session.close()

    def get_single(self, **kwargs) -> Optional[MapCfg]:
        """Get single map configuration."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapCfg.create_time)).first()
        finally:
            session.close()


class MapTaskRepository(BaseRepository[MapTask]):
    """Map task repository."""

    def __init__(self):
        super().__init__(MapTask)

    def create_with_id(self, **kwargs) -> int:
        """Create map task and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            task = _model(**kwargs)
            session.add(task)
            session.flush()
            return task.id
        return db_write(_do, description="repo_create_map_task")

    def get_all_ordered(self, **kwargs) -> List[MapTask]:
        """Get all map tasks ordered by create time."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapTask.create_time)).all()
        finally:
            session.close()

    def get_single(self, **kwargs) -> Optional[MapTask]:
        """Get single map task."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapTask.create_time)).first()
        finally:
            session.close()


class MapToolRepository(BaseRepository[MapTool]):
    """Map tool repository."""

    def __init__(self):
        super().__init__(MapTool)

    def create_with_id(self, **kwargs) -> int:
        """Create map tool and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            tool = _model(**kwargs)
            session.add(tool)
            session.flush()
            return tool.id
        return db_write(_do, description="repo_create_map_tool")

    def get_all_ordered(self, **kwargs) -> List[MapTool]:
        """Get all map tools ordered by create time."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapTool.create_time)).all()
        finally:
            session.close()

    def get_single(self, **kwargs) -> Optional[MapTool]:
        """Get single map tool."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapTool.create_time)).first()
        finally:
            session.close()


class MapTradeRepository(BaseRepository[MapTrade]):
    """Map trade repository."""

    def __init__(self):
        super().__init__(MapTrade)

    def create_with_id(self, **kwargs) -> int:
        """Create map trade and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            trade = _model(**kwargs)
            session.add(trade)
            session.flush()
            return trade.id
        return db_write(_do, description="repo_create_map_trade")

    def get_all_ordered(self, **kwargs) -> List[MapTrade]:
        """Get all map trades ordered by create time."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapTrade.create_time)).all()
        finally:
            session.close()

    def get_single(self, **kwargs) -> Optional[MapTrade]:
        """Get single map trade."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapTrade.create_time)).first()
        finally:
            session.close()

    def update_by_trade_id(self, trade_id: str, **kwargs):
        """Update map trade by trade_id."""
        self.update_by_filter({'trade_id': trade_id}, **kwargs)


class MapVisitRepository(BaseRepository[MapVisit]):
    """Map visit repository."""

    def __init__(self):
        super().__init__(MapVisit)

    def create_with_id(self, **kwargs) -> int:
        """Create map visit and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            visit = _model(**kwargs)
            session.add(visit)
            session.flush()
            return visit.id
        return db_write(_do, description="repo_create_map_visit")

    def get_all_ordered(self, **kwargs) -> List[MapVisit]:
        """Get all map visits ordered by create time."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapVisit.create_time)).all()
        finally:
            session.close()

    def get_single(self, **kwargs) -> Optional[MapVisit]:
        """Get single map visit."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(MapVisit.create_time)).first()
        finally:
            session.close()


class MapActivityRepository(BaseRepository[MapActivity]):
    """Map activity repository."""

    def __init__(self):
        super().__init__(MapActivity)

    def get_previous_activities(self, last_record_id: Optional[int] = None, count: int = 20,
                                type_str: Optional[str] = None) -> List[MapActivity]:
        """Get previous activities with pagination and optional type filter."""
        session = get_session()
        try:
            query = session.query(self.model)

            if last_record_id is not None:
                query = query.filter(MapActivity.id < last_record_id)
            if type_str:
                query = query.filter(MapActivity.type == type_str)

            return query.order_by(MapActivity.id.desc()).limit(count).all()
        finally:
            session.close()

    def update_by_activity_id(self, activity_id: str, **kwargs):
        """Update activity by activity_id."""
        self.update_by_filter({'activity_id': activity_id}, **kwargs)

    def delete_by_activity_id(self, activity_id: str):
        """Delete activity by activity_id."""
        self.delete_by_filter(activity_id=activity_id)


class MapPresetMsgRepository(BaseRepository[MapPresetMsg]):
    """Map preset message repository."""

    def __init__(self):
        super().__init__(MapPresetMsg)

    def get_previous_messages(self, last_record_id: Optional[int] = None, count: int = 20) -> List[MapPresetMsg]:
        """Get previous preset messages with pagination."""
        session = get_session()
        try:
            query = session.query(self.model)
            if last_record_id is not None:
                query = query.filter(MapPresetMsg.id < last_record_id)
            return query.order_by(MapPresetMsg.id.desc()).limit(count).all()
        finally:
            session.close()

    def update_by_msg_id(self, msg_id: int, **kwargs):
        """Update preset message by ID."""
        self.update(msg_id, **kwargs)

    def delete_by_content(self, content: str):
        """Delete preset message by content."""
        self.delete_by_filter(content=content)


class ChatPresetMsgRepository(BaseRepository[ChatPresetMsg]):
    """Chat preset message repository."""

    def __init__(self):
        super().__init__(ChatPresetMsg)

    def get_previous_messages(self, last_record_id: Optional[int] = None, count: int = 20) -> List[ChatPresetMsg]:
        """Get previous preset messages with pagination."""
        session = get_session()
        try:
            query = session.query(self.model)
            if last_record_id is not None:
                query = query.filter(ChatPresetMsg.id < last_record_id)
            return query.order_by(ChatPresetMsg.id.desc()).limit(count).all()
        finally:
            session.close()

    def update_by_msg_id(self, msg_id: int, **kwargs):
        """Update preset message by ID."""
        self.update(msg_id, **kwargs)

    def delete_by_content(self, content: str):
        """Delete preset message by content."""
        self.delete_by_filter(content=content)
