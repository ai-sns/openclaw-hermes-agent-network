"""
Context Store

Manages conversation context with support for different storage backends.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import hashlib


@dataclass
class ContextEntry:
    """Single context entry"""
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime
    ttl_seconds: Optional[int] = None


class ContextStore:
    """
    Context Store

    Manages conversation context data with:
    - Key-value storage
    - Nested path access (e.g., "user.preferences.language")
    - TTL support
    - Context compression for long conversations
    """

    def __init__(self, max_context_size: int = 100000):
        """
        Initialize context store.

        Args:
            max_context_size: Maximum context size in characters
        """
        self.max_context_size = max_context_size
        self._contexts: Dict[str, Dict[str, ContextEntry]] = {}

    def _get_context_dict(self, session_id: str) -> Dict[str, ContextEntry]:
        """Get or create context dict for session"""
        if session_id not in self._contexts:
            self._contexts[session_id] = {}
        return self._contexts[session_id]

    def _parse_path(self, path: str) -> List[str]:
        """Parse a dot-separated path"""
        return path.split(".")

    def set(
        self,
        session_id: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set a context value.

        Args:
            session_id: Session ID
            key: Context key (supports dot notation)
            value: Value to store
            ttl_seconds: Time-to-live in seconds
        """
        context = self._get_context_dict(session_id)
        now = datetime.now()

        if key in context:
            entry = context[key]
            entry.value = value
            entry.updated_at = now
            entry.ttl_seconds = ttl_seconds
        else:
            context[key] = ContextEntry(
                key=key,
                value=value,
                created_at=now,
                updated_at=now,
                ttl_seconds=ttl_seconds
            )

    def get(
        self,
        session_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a context value.

        Args:
            session_id: Session ID
            key: Context key
            default: Default value if not found

        Returns:
            Stored value or default
        """
        context = self._get_context_dict(session_id)

        if key not in context:
            return default

        entry = context[key]

        # Check TTL
        if entry.ttl_seconds:
            elapsed = (datetime.now() - entry.updated_at).total_seconds()
            if elapsed > entry.ttl_seconds:
                del context[key]
                return default

        return entry.value

    def get_nested(
        self,
        session_id: str,
        path: str,
        default: Any = None
    ) -> Any:
        """
        Get a nested context value using dot notation.

        Args:
            session_id: Session ID
            path: Dot-separated path (e.g., "user.preferences.language")
            default: Default value

        Returns:
            Nested value or default
        """
        parts = self._parse_path(path)
        current = self.get(session_id, parts[0], default)

        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part, default)
            else:
                return default

        return current

    def set_nested(
        self,
        session_id: str,
        path: str,
        value: Any
    ) -> None:
        """
        Set a nested context value using dot notation.

        Args:
            session_id: Session ID
            path: Dot-separated path
            value: Value to set
        """
        parts = self._parse_path(path)

        if len(parts) == 1:
            self.set(session_id, parts[0], value)
            return

        # Get or create root
        root_key = parts[0]
        root = self.get(session_id, root_key, {})
        if not isinstance(root, dict):
            root = {}

        # Navigate/create nested structure
        current = root
        for part in parts[1:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]

        # Set final value
        current[parts[-1]] = value
        self.set(session_id, root_key, root)

    def delete(self, session_id: str, key: str) -> bool:
        """
        Delete a context value.

        Args:
            session_id: Session ID
            key: Key to delete

        Returns:
            True if deleted
        """
        context = self._get_context_dict(session_id)
        if key in context:
            del context[key]
            return True
        return False

    def get_all(self, session_id: str) -> Dict[str, Any]:
        """
        Get all context values for a session.

        Args:
            session_id: Session ID

        Returns:
            Dict of all context values
        """
        context = self._get_context_dict(session_id)
        result = {}

        for key, entry in context.items():
            # Check TTL
            if entry.ttl_seconds:
                elapsed = (datetime.now() - entry.updated_at).total_seconds()
                if elapsed > entry.ttl_seconds:
                    continue
            result[key] = entry.value

        return result

    def merge(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Merge data into context.

        Args:
            session_id: Session ID
            data: Data to merge
        """
        for key, value in data.items():
            self.set(session_id, key, value)

    def clear(self, session_id: str) -> None:
        """
        Clear all context for a session.

        Args:
            session_id: Session ID
        """
        if session_id in self._contexts:
            self._contexts[session_id] = {}

    def get_size(self, session_id: str) -> int:
        """
        Get context size in characters.

        Args:
            session_id: Session ID

        Returns:
            Size in characters
        """
        context = self.get_all(session_id)
        return len(json.dumps(context))

    def compress_if_needed(
        self,
        session_id: str,
        compression_ratio: float = 0.5
    ) -> bool:
        """
        Compress context if it exceeds max size.

        Args:
            session_id: Session ID
            compression_ratio: Target ratio (0.5 = reduce to 50%)

        Returns:
            True if compressed
        """
        current_size = self.get_size(session_id)
        if current_size <= self.max_context_size:
            return False

        context = self._get_context_dict(session_id)
        target_size = int(self.max_context_size * compression_ratio)

        # Sort entries by last update (oldest first)
        sorted_entries = sorted(
            context.items(),
            key=lambda x: x[1].updated_at
        )

        # Remove oldest entries until under target
        while self.get_size(session_id) > target_size and sorted_entries:
            key, _ = sorted_entries.pop(0)
            del context[key]

        return True

    def get_hash(self, session_id: str) -> str:
        """
        Get a hash of the context for verification.

        Args:
            session_id: Session ID

        Returns:
            SHA256 hash of context
        """
        context = self.get_all(session_id)
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()


# Singleton instance
_context_store: Optional[ContextStore] = None


def get_context_store() -> ContextStore:
    """Get the singleton context store instance"""
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store
