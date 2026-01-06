"""
Session Manager

Manages conversation sessions with ID tracking and expiration.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.database import SessionLocal
from db.models.platform_models import SessionRecord


@dataclass
class Session:
    """Session data structure"""
    session_id: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    thread_count: int = 0
    status: str = "active"
    context_data: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    message_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_activity_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    client_info: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    Session Manager

    Handles session lifecycle including creation, retrieval, and expiration.
    Sessions are stored in the database for persistence.
    """

    def __init__(self, default_expiry_hours: int = 24):
        """
        Initialize session manager.

        Args:
            default_expiry_hours: Default session expiration in hours
        """
        self.default_expiry_hours = default_expiry_hours
        # In-memory cache for quick access
        self._cache: Dict[str, Session] = {}

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"sess_{uuid.uuid4().hex}"

    def create_session(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        expires_in_hours: Optional[int] = None,
        client_info: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: Associated user ID
            agent_id: Primary agent ID
            context: Initial context data
            expires_in_hours: Custom expiration
            client_info: Client information (IP, User-Agent, etc.)

        Returns:
            Created Session object
        """
        session_id = self._generate_session_id()
        thread_id = f"thread_{uuid.uuid4().hex[:16]}"

        expiry = expires_in_hours or self.default_expiry_hours
        expires_at = datetime.now() + timedelta(hours=expiry)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            thread_id=thread_id,
            thread_count=1,
            context_data=context or {},
            expires_at=expires_at,
            client_info=client_info or {}
        )

        # Save to database
        db = SessionLocal()
        try:
            db_session = SessionRecord(
                session_id=session_id,
                user_id=user_id,
                agent_id=agent_id,
                thread_id=thread_id,
                thread_count=1,
                context_data=context or {},
                messages=[],
                message_count=0,
                status="active",
                expires_at=expires_at,
                client_info=client_info or {}
            )
            db.add(db_session)
            db.commit()
        finally:
            db.close()

        # Add to cache
        self._cache[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session object or None if not found/expired
        """
        # Check cache first
        if session_id in self._cache:
            session = self._cache[session_id]
            # Check if expired
            if session.expires_at and session.expires_at < datetime.now():
                self._cache.pop(session_id, None)
                return None
            return session

        # Query database
        db = SessionLocal()
        try:
            db_session = db.query(SessionRecord).filter(
                SessionRecord.session_id == session_id,
                SessionRecord.status == "active"
            ).first()

            if not db_session:
                return None

            # Check if expired
            if db_session.expires_at and db_session.expires_at < datetime.now():
                db_session.status = "expired"
                db.commit()
                return None

            # Convert to Session object
            session = Session(
                session_id=db_session.session_id,
                user_id=db_session.user_id,
                agent_id=db_session.agent_id,
                thread_id=db_session.thread_id,
                thread_count=db_session.thread_count,
                status=db_session.status,
                context_data=db_session.context_data or {},
                messages=db_session.messages or [],
                message_count=db_session.message_count,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at,
                last_activity_at=db_session.last_activity_at,
                expires_at=db_session.expires_at,
                metadata=db_session.session_metadata or {},
                client_info=db_session.client_info or {}
            )

            # Add to cache
            self._cache[session_id] = session

            return session
        finally:
            db.close()

    def update_session(
        self,
        session_id: str,
        context_data: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Session]:
        """
        Update a session.

        Args:
            session_id: Session ID
            context_data: Updated context (merged with existing)
            messages: Updated messages (appended or replaced)
            agent_id: Updated agent ID
            metadata: Updated metadata (merged with existing)

        Returns:
            Updated Session or None if not found
        """
        db = SessionLocal()
        try:
            db_session = db.query(SessionRecord).filter(
                SessionRecord.session_id == session_id
            ).first()

            if not db_session:
                return None

            # Update fields
            if context_data:
                current_context = db_session.context_data or {}
                current_context.update(context_data)
                db_session.context_data = current_context

            if messages:
                db_session.messages = messages
                db_session.message_count = len(messages)

            if agent_id:
                db_session.agent_id = agent_id

            if metadata:
                current_metadata = db_session.session_metadata or {}
                current_metadata.update(metadata)
                db_session.session_metadata = current_metadata

            db_session.updated_at = datetime.now()
            db_session.last_activity_at = datetime.now()
            db.commit()

            # Update cache
            session = self.get_session(session_id)
            return session
        finally:
            db.close()

    def add_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> Optional[Session]:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            message: Message to add

        Returns:
            Updated Session or None
        """
        db = SessionLocal()
        try:
            db_session = db.query(SessionRecord).filter(
                SessionRecord.session_id == session_id
            ).first()

            if not db_session:
                return None

            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()

            # Append message
            messages = db_session.messages or []
            messages.append(message)
            db_session.messages = messages
            db_session.message_count = len(messages)
            db_session.last_activity_at = datetime.now()
            db_session.updated_at = datetime.now()
            db.commit()

            # Invalidate cache
            self._cache.pop(session_id, None)

            return self.get_session(session_id)
        finally:
            db.close()

    def close_session(self, session_id: str) -> bool:
        """
        Close a session.

        Args:
            session_id: Session ID

        Returns:
            True if closed, False if not found
        """
        db = SessionLocal()
        try:
            db_session = db.query(SessionRecord).filter(
                SessionRecord.session_id == session_id
            ).first()

            if not db_session:
                return False

            db_session.status = "closed"
            db_session.updated_at = datetime.now()
            db.commit()

            # Remove from cache
            self._cache.pop(session_id, None)

            return True
        finally:
            db.close()

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = "active",
        limit: int = 20,
        offset: int = 0
    ) -> List[Session]:
        """
        List sessions with optional filters.

        Args:
            user_id: Filter by user ID
            agent_id: Filter by agent ID
            status: Filter by status
            limit: Max results
            offset: Offset for pagination

        Returns:
            List of Session objects
        """
        db = SessionLocal()
        try:
            query = db.query(SessionRecord)

            if user_id:
                query = query.filter(SessionRecord.user_id == user_id)
            if agent_id:
                query = query.filter(SessionRecord.agent_id == agent_id)
            if status:
                query = query.filter(SessionRecord.status == status)

            query = query.order_by(SessionRecord.last_activity_at.desc())
            query = query.offset(offset).limit(limit)

            sessions = []
            for db_session in query.all():
                sessions.append(Session(
                    session_id=db_session.session_id,
                    user_id=db_session.user_id,
                    agent_id=db_session.agent_id,
                    thread_id=db_session.thread_id,
                    thread_count=db_session.thread_count,
                    status=db_session.status,
                    context_data=db_session.context_data or {},
                    messages=db_session.messages or [],
                    message_count=db_session.message_count,
                    created_at=db_session.created_at,
                    updated_at=db_session.updated_at,
                    last_activity_at=db_session.last_activity_at,
                    expires_at=db_session.expires_at
                ))

            return sessions
        finally:
            db.close()

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        db = SessionLocal()
        try:
            result = db.query(SessionRecord).filter(
                SessionRecord.expires_at < datetime.now(),
                SessionRecord.status == "active"
            ).update({"status": "expired"})
            db.commit()

            # Clear cache
            self._cache.clear()

            return result
        finally:
            db.close()


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the singleton session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
