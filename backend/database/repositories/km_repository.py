"""Knowledge management repository with specialized CRUD operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, asc, or_
from .base import BaseRepository
from ..models.km import KMCfg, KMData, NoteMng
from backend.config.database import get_db_session as get_session


class KMCfgRepository(BaseRepository[KMCfg]):
    """Knowledge base configuration repository."""

    def __init__(self):
        super().__init__(KMCfg)

    def get_all_ordered(self, **kwargs) -> List[KMCfg]:
        """Get all KM configurations ordered by position."""
        session = get_session()
        try:
            return session.query(self.model).filter_by(**kwargs).order_by(asc(KMCfg.position)).all()
        finally:
            session.close()

    def update_by_km_id(self, km_id: str, **kwargs):
        """Update KM configuration by km_id."""
        self.update_by_filter({'km_id': km_id}, **kwargs)

    def delete_by_km_id(self, km_id: str):
        """Delete KM configuration by km_id."""
        self.delete_by_filter(km_id=km_id)


class KMDataRepository(BaseRepository[KMData]):
    """Knowledge base data repository."""

    def __init__(self):
        super().__init__(KMData)

    def create_with_id(self, **kwargs) -> int:
        """Create KM data and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            data = _model(**kwargs)
            session.add(data)
            session.flush()
            return data.id
        return db_write(_do, description="repo_create_km_data")


class NoteMngRepository(BaseRepository[NoteMng]):
    """Note management repository."""

    def __init__(self):
        super().__init__(NoteMng)

    def create_with_id(self, **kwargs) -> int:
        """Create note and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            note = _model(**kwargs)
            session.add(note)
            session.flush()
            return note.id
        return db_write(_do, description="repo_create_note_mng")

    def get_all_with_label_filter(self, count: int, label: bool = False, **kwargs) -> List[NoteMng]:
        """Get all notes with optional label filter and limit."""
        session = get_session()
        try:
            query = session.query(self.model)

            if label:
                query = query.filter(NoteMng.label.isnot(None))

            query = query.filter_by(**kwargs).order_by(
                desc(NoteMng.stick_time), desc(NoteMng.create_time)
            )

            if count == -1:
                return query.all()
            else:
                return query.limit(count).all()
        finally:
            session.close()

    def get_labels_by_km_id(self, km_id: str) -> List[str]:
        """Get distinct labels for a KM."""
        session = get_session()
        try:
            res = session.query(NoteMng.label).filter(
                NoteMng.km_id == km_id
            ).distinct().all()
            return [i.label for i in res if i.label is not None]
        finally:
            session.close()

    def search_content(self, count: int, label: bool = False, **kwargs) -> List[NoteMng]:
        """Search notes by title or content."""
        session = get_session()
        try:
            title_keyword = kwargs.get('title')
            content_keyword = kwargs.get('content')

            query = session.query(self.model)

            if label:
                query = query.filter(NoteMng.label.isnot(None))

            search_terms = []
            if title_keyword:
                search_terms.append(NoteMng.title.contains(title_keyword))
            if content_keyword:
                search_terms.append(NoteMng.content.contains(content_keyword))

            if search_terms:
                query = query.filter(or_(*search_terms))

            query = query.order_by(desc(NoteMng.stick_time), desc(NoteMng.create_time))

            if count == -1:
                return query.limit(50000).all()
            else:
                return query.limit(count).all()
        finally:
            session.close()

    def update_stick_time(self, id: int, value: Optional[datetime] = None):
        """Update stick time."""
        self.update(id, stick_time=value)

    def update_by_note_id(self, note_id: str, **kwargs):
        """Update note by note_id."""
        self.update_by_filter({'note_id': note_id}, **kwargs)
