"""
SQLite storage layer for the AI SNS Engine memory system.

Uses the existing ``agent_memory`` table in db/db.sqlite via SQLAlchemy,
following the same session/model patterns as db.DBFactory.
"""

import json
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, desc, or_
from sqlalchemy import text as _text
from db.DBFactory import Base, Session, _commit_with_retry

logger = logging.getLogger(__name__)


def _ensure_agent_memory_table(session) -> None:
    try:
        session.execute(
            _text(
                """
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id VARCHAR(100),
                    memory_type VARCHAR(50),
                    key VARCHAR(500),
                    content TEXT,
                    metadata TEXT,
                    importance INTEGER DEFAULT 50,
                    access_count INTEGER DEFAULT 0,
                    last_accessed DATETIME,
                    created_at DATETIME,
                    expires_at DATETIME,
                    is_delete INTEGER DEFAULT 0
                )
                """
            )
        )
    except Exception as e:
        logger.warning("Failed to ensure agent_memory table: %s", e)


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class AgentMemory(Base):
    """ORM model for the agent_memory table."""

    __tablename__ = "agent_memory"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(100))
    memory_type = Column(String(50))
    key = Column(String(500))
    content = Column(Text)
    # 'metadata' is reserved by SQLAlchemy declarative; map via Column("metadata")
    meta_data = Column("metadata", Text)
    importance = Column(Integer, default=50)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_delete = Column(Integer, default=0)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def add_memory(
    agent_id: str,
    memory_type: str,
    key: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    importance: int = 50,
) -> Optional[int]:
    """Insert a new memory row. Returns the new row id or None on failure.

    The agent_memory table has a FK constraint on agent_id referencing
    agent_cfg(user_id).  During normal engine operation the agent_id is a
    valid user_id, but to avoid spurious failures (e.g. during tests or
    when the cfg row hasn't been created yet) we temporarily disable FK
    enforcement for the insert.
    """
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        # Temporarily disable FK checks for this connection
        session.execute(_text("PRAGMA foreign_keys=OFF"))
        record = AgentMemory(
            agent_id=agent_id,
            memory_type=memory_type,
            key=key,
            content=content,
            meta_data=json.dumps(metadata or {}, ensure_ascii=False),
            importance=importance,
            access_count=0,
            last_accessed=datetime.utcnow(),
            created_at=datetime.utcnow(),
            is_delete=0,
        )
        session.add(record)
        _commit_with_retry(session)
        new_id = record.id
        # Re-enable FK checks
        session.execute(_text("PRAGMA foreign_keys=ON"))
        return new_id
    except Exception as e:
        session.rollback()
        logger.error("Failed to add memory: %s", e, exc_info=True)
        return None
    finally:
        session.close()


def query_memories(
    agent_id: str,
    memory_type: Optional[str] = None,
    keyword: Optional[str] = None,
    max_results: int = 10,
    min_importance: int = 0,
) -> List[dict]:
    """
    Query memories with optional filters.

    Returns a list of dicts with all fields.
    Results are ordered by importance DESC, created_at DESC.
    """
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        q = session.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_delete == 0,
        )

        if memory_type:
            q = q.filter(AgentMemory.memory_type == memory_type)

        if min_importance > 0:
            q = q.filter(AgentMemory.importance >= min_importance)

        if keyword:
            pattern = f"%{keyword}%"
            q = q.filter(
                or_(
                    AgentMemory.key.ilike(pattern),
                    AgentMemory.content.ilike(pattern),
                )
            )

        q = q.order_by(desc(AgentMemory.importance), desc(AgentMemory.created_at))
        rows = q.limit(max_results).all()

        results = []
        for r in rows:
            results.append(_row_to_dict(r))
        return results
    except Exception as e:
        logger.error("Failed to query memories: %s", e, exc_info=True)
        return []
    finally:
        session.close()


def query_memories_by_types(
    agent_id: str,
    memory_types: List[str],
    max_results: int = 10,
) -> List[dict]:
    """Query memories filtered by multiple memory types."""
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        q = session.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_delete == 0,
            AgentMemory.memory_type.in_(memory_types),
        )
        q = q.order_by(desc(AgentMemory.importance), desc(AgentMemory.created_at))
        rows = q.limit(max_results).all()
        return [_row_to_dict(r) for r in rows]
    except Exception as e:
        logger.error("Failed to query memories by types: %s", e, exc_info=True)
        return []
    finally:
        session.close()


def query_memories_by_person(
    agent_id: str,
    person_account: str,
    memory_types: Optional[List[str]] = None,
    max_results: int = 5,
) -> List[dict]:
    """Query memories related to a specific person (by account in metadata or content)."""
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        pattern = f"%{person_account}%"
        q = session.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_delete == 0,
            or_(
                AgentMemory.content.ilike(pattern),
                AgentMemory.meta_data.ilike(pattern),
                AgentMemory.key.ilike(pattern),
            ),
        )
        if memory_types:
            q = q.filter(AgentMemory.memory_type.in_(memory_types))

        q = q.order_by(desc(AgentMemory.importance), desc(AgentMemory.created_at))
        rows = q.limit(max_results).all()
        return [_row_to_dict(r) for r in rows]
    except Exception as e:
        logger.error("Failed to query memories by person: %s", e, exc_info=True)
        return []
    finally:
        session.close()


def touch_memory(memory_id: int) -> None:
    """Increment access_count and update last_accessed timestamp."""
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        record = session.query(AgentMemory).filter_by(id=memory_id).first()
        if record:
            record.access_count = (record.access_count or 0) + 1
            record.last_accessed = datetime.utcnow()
            _commit_with_retry(session)
    except Exception as e:
        session.rollback()
        logger.error("Failed to touch memory %d: %s", memory_id, e)
    finally:
        session.close()


def count_memories(agent_id: str) -> int:
    """Return total non-deleted memory count for an agent."""
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        return session.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_delete == 0,
        ).count()
    except Exception:
        return 0
    finally:
        session.close()


def soft_delete_oldest(agent_id: str, keep_count: int) -> int:
    """Soft-delete the least important / oldest memories beyond *keep_count*."""
    session = Session()
    try:
        _ensure_agent_memory_table(session)
        total = session.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_delete == 0,
        ).count()

        if total <= keep_count:
            return 0

        excess = total - keep_count
        # Delete lowest-importance, oldest first
        rows = (
            session.query(AgentMemory)
            .filter(
                AgentMemory.agent_id == agent_id,
                AgentMemory.is_delete == 0,
            )
            .order_by(AgentMemory.importance, AgentMemory.created_at)
            .limit(excess)
            .all()
        )
        for r in rows:
            r.is_delete = 1
        _commit_with_retry(session)
        logger.info("Soft-deleted %d old memories for agent %s", len(rows), agent_id)
        return len(rows)
    except Exception as e:
        session.rollback()
        logger.error("Failed to soft-delete old memories: %s", e)
        return 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: AgentMemory) -> dict:
    """Convert an ORM row to a plain dict."""
    meta = {}
    if row.meta_data:
        try:
            meta = json.loads(row.meta_data)
        except (json.JSONDecodeError, TypeError):
            meta = {}

    return {
        "id": row.id,
        "agent_id": row.agent_id,
        "memory_type": row.memory_type,
        "key": row.key,
        "content": row.content,
        "metadata": meta,
        "importance": row.importance or 0,
        "access_count": row.access_count or 0,
        "last_accessed": str(row.last_accessed) if row.last_accessed else None,
        "created_at": str(row.created_at) if row.created_at else None,
    }
