"""Base repository with common CRUD operations."""
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.config.database import Base, get_db_session

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        """Initialize repository with model class."""
        self.model = model

    def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            obj = _model(**kwargs)
            session.add(obj)
            session.flush()
            session.refresh(obj)
            return obj
        return db_write(_do, description=f"repo_create_{self.model.__tablename__}")

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get record by ID."""
        session = get_db_session()
        try:
            return session.query(self.model).filter_by(id=id).first()
        finally:
            session.close()

    def get_all(self, **filters) -> List[ModelType]:
        """Get all records with optional filters."""
        session = get_db_session()
        try:
            query = session.query(self.model)
            if filters:
                query = query.filter_by(**filters)
            return query.all()
        finally:
            session.close()

    def get_one(self, **filters) -> Optional[ModelType]:
        """Get one record with filters."""
        session = get_db_session()
        try:
            return session.query(self.model).filter_by(**filters).first()
        finally:
            session.close()

    def update(self, id: int, **kwargs) -> bool:
        """Update a record by ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            obj = session.query(_model).filter_by(id=id).first()
            if obj:
                for key, value in kwargs.items():
                    setattr(obj, key, value)
                return True
            return False
        return db_write(_do, description=f"repo_update_{self.model.__tablename__}")

    def update_by_filter(self, filters: Dict[str, Any], **kwargs) -> bool:
        """Update a record by custom filters."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            obj = session.query(_model).filter_by(**filters).first()
            if obj:
                for key, value in kwargs.items():
                    setattr(obj, key, value)
                return True
            return False
        return db_write(_do, description=f"repo_update_by_filter_{self.model.__tablename__}")

    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            obj = session.query(_model).filter_by(id=id).first()
            if obj:
                session.delete(obj)
                return True
            return False
        return db_write(_do, description=f"repo_delete_{self.model.__tablename__}")

    def delete_by_filter(self, **filters) -> bool:
        """Delete a record by custom filters."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            obj = session.query(_model).filter_by(**filters).first()
            if obj:
                session.delete(obj)
                return True
            return False
        return db_write(_do, description=f"repo_delete_by_filter_{self.model.__tablename__}")

    def count(self, **filters) -> int:
        """Count records with optional filters."""
        session = get_db_session()
        try:
            query = session.query(self.model)
            if filters:
                query = query.filter_by(**filters)
            return query.count()
        finally:
            session.close()

    def exists(self, **filters) -> bool:
        """Check if record exists."""
        session = get_db_session()
        try:
            return session.query(self.model).filter_by(**filters).first() is not None
        finally:
            session.close()
