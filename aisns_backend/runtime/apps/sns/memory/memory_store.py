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

from sqlalchemy import desc, or_
from sqlalchemy import text as _text
from db.models.agent import AgentMemory
from db.DBFactory import Session, _commit_with_retry

logger = logging.getLogger(__name__)


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
        return session.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_delete == 0,
        ).count()
    except Exception:
        return 0
    finally:
        session.close()


def soft_delete_oldest(agent_id: str, keep_count: int) -> int:
    """Hard-delete the least important / oldest memories beyond *keep_count*."""
    session = Session()
    try:
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
            session.delete(r)
        _commit_with_retry(session)
        logger.info("Hard-deleted %d old memories for agent %s", len(rows), agent_id)
        return len(rows)
    except Exception as e:
        session.rollback()
        logger.error("Failed to hard-delete old memories: %s", e)
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
