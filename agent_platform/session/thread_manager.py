"""
Thread Manager

Manages conversation threads within sessions.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class Thread:
    """Thread data structure"""
    thread_id: str
    session_id: str
    parent_thread_id: Optional[str] = None
    name: Optional[str] = None
    status: str = "active"
    messages: List[Dict[str, Any]] = field(default_factory=list)
    message_count: int = 0
    context_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThreadManager:
    """
    Thread Manager

    Manages threads (sub-conversations) within sessions.
    Threads allow branching conversations.
    """

    def __init__(self):
        """Initialize thread manager"""
        # In-memory storage (can be extended to use database)
        self._threads: Dict[str, Thread] = {}
        self._session_threads: Dict[str, List[str]] = {}  # session_id -> [thread_ids]

    def _generate_thread_id(self) -> str:
        """Generate a unique thread ID"""
        return f"thread_{uuid.uuid4().hex[:16]}"

    def create_thread(
        self,
        session_id: str,
        parent_thread_id: Optional[str] = None,
        name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        initial_messages: Optional[List[Dict[str, Any]]] = None
    ) -> Thread:
        """
        Create a new thread.

        Args:
            session_id: Parent session ID
            parent_thread_id: Parent thread ID (for branching)
            name: Thread name
            context: Initial context
            initial_messages: Initial messages (e.g., from parent thread)

        Returns:
            Created Thread object
        """
        thread_id = self._generate_thread_id()

        # Copy messages from parent if branching
        messages = []
        if parent_thread_id and parent_thread_id in self._threads:
            parent = self._threads[parent_thread_id]
            messages = parent.messages.copy()

        if initial_messages:
            messages.extend(initial_messages)

        thread = Thread(
            thread_id=thread_id,
            session_id=session_id,
            parent_thread_id=parent_thread_id,
            name=name,
            messages=messages,
            message_count=len(messages),
            context_data=context or {}
        )

        # Store thread
        self._threads[thread_id] = thread

        # Track in session
        if session_id not in self._session_threads:
            self._session_threads[session_id] = []
        self._session_threads[session_id].append(thread_id)

        return thread

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Get a thread by ID.

        Args:
            thread_id: Thread ID

        Returns:
            Thread object or None
        """
        return self._threads.get(thread_id)

    def get_session_threads(self, session_id: str) -> List[Thread]:
        """
        Get all threads for a session.

        Args:
            session_id: Session ID

        Returns:
            List of Thread objects
        """
        thread_ids = self._session_threads.get(session_id, [])
        return [self._threads[tid] for tid in thread_ids if tid in self._threads]

    def add_message(
        self,
        thread_id: str,
        message: Dict[str, Any]
    ) -> Optional[Thread]:
        """
        Add a message to a thread.

        Args:
            thread_id: Thread ID
            message: Message to add

        Returns:
            Updated Thread or None
        """
        thread = self._threads.get(thread_id)
        if not thread:
            return None

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()

        thread.messages.append(message)
        thread.message_count = len(thread.messages)
        thread.updated_at = datetime.now()

        return thread

    def update_context(
        self,
        thread_id: str,
        context: Dict[str, Any]
    ) -> Optional[Thread]:
        """
        Update thread context.

        Args:
            thread_id: Thread ID
            context: Context data to merge

        Returns:
            Updated Thread or None
        """
        thread = self._threads.get(thread_id)
        if not thread:
            return None

        thread.context_data.update(context)
        thread.updated_at = datetime.now()

        return thread

    def branch_thread(
        self,
        thread_id: str,
        at_message_index: Optional[int] = None,
        name: Optional[str] = None
    ) -> Optional[Thread]:
        """
        Create a branch from an existing thread.

        Args:
            thread_id: Source thread ID
            at_message_index: Branch from this message (None = latest)
            name: Name for the new branch

        Returns:
            New Thread object or None
        """
        source_thread = self._threads.get(thread_id)
        if not source_thread:
            return None

        # Get messages up to the branch point
        messages = source_thread.messages.copy()
        if at_message_index is not None and at_message_index < len(messages):
            messages = messages[:at_message_index + 1]

        return self.create_thread(
            session_id=source_thread.session_id,
            parent_thread_id=thread_id,
            name=name or f"Branch from {thread_id}",
            context=source_thread.context_data.copy(),
            initial_messages=messages
        )

    def close_thread(self, thread_id: str) -> bool:
        """
        Close a thread.

        Args:
            thread_id: Thread ID

        Returns:
            True if closed
        """
        thread = self._threads.get(thread_id)
        if not thread:
            return False

        thread.status = "closed"
        thread.updated_at = datetime.now()
        return True

    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread.

        Args:
            thread_id: Thread ID

        Returns:
            True if deleted
        """
        if thread_id not in self._threads:
            return False

        thread = self._threads.pop(thread_id)

        # Remove from session tracking
        session_threads = self._session_threads.get(thread.session_id, [])
        if thread_id in session_threads:
            session_threads.remove(thread_id)

        return True

    def get_thread_history(
        self,
        thread_id: str,
        limit: Optional[int] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get message history for a thread.

        Args:
            thread_id: Thread ID
            limit: Max messages to return
            include_system: Whether to include system messages

        Returns:
            List of messages
        """
        thread = self._threads.get(thread_id)
        if not thread:
            return []

        messages = thread.messages
        if not include_system:
            messages = [m for m in messages if m.get("role") != "system"]

        if limit:
            messages = messages[-limit:]

        return messages


# Singleton instance
_thread_manager: Optional[ThreadManager] = None


def get_thread_manager() -> ThreadManager:
    """Get the singleton thread manager instance"""
    global _thread_manager
    if _thread_manager is None:
        _thread_manager = ThreadManager()
    return _thread_manager
