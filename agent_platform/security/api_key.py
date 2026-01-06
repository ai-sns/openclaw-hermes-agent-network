"""
API Key Management

Provides API key generation, validation, and management.
Supports both database-backed and in-memory storage modes.
"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Try to import database modules, but allow fallback to in-memory mode
HAS_DATABASE = False
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from db.database import SessionLocal
    from db.models.platform_models import APIKey
    HAS_DATABASE = True
except ImportError:
    logger.warning("Database modules not available, using in-memory storage")
    SessionLocal = None
    APIKey = None


@dataclass
class APIKeyInfo:
    """API Key information structure"""
    key_prefix: str
    name: str
    user_id: str
    scopes: List[str]
    rate_limit: int
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


@dataclass
class InMemoryAPIKey:
    """In-memory API Key record"""
    key_hash: str
    key_prefix: str
    name: str
    user_id: str
    scopes: List[str] = field(default_factory=list)
    rate_limit: int = 1000
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class APIKeyManager:
    """
    API Key Manager for generating and validating API keys.

    Key format: aisns_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (40 chars total)
    - Prefix: aisns_ (6 chars)
    - Random: 34 chars

    Supports both database-backed and in-memory storage modes.
    """

    KEY_PREFIX = "aisns_"
    KEY_LENGTH = 34  # Length of random part

    def __init__(self, use_database: bool = None):
        """
        Initialize API Key Manager.

        Args:
            use_database: Force database mode (None = auto-detect)
        """
        if use_database is None:
            self._use_db = HAS_DATABASE
        else:
            self._use_db = use_database and HAS_DATABASE

        # In-memory storage (used when database is not available)
        self._keys: Dict[str, InMemoryAPIKey] = {}

    def _generate_random_key(self) -> str:
        """Generate a random API key"""
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(self.KEY_LENGTH))
        return f"{self.KEY_PREFIX}{random_part}"

    def _hash_key(self, key: str) -> str:
        """Hash an API key using SHA256"""
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_key_prefix(self, key: str) -> str:
        """Get the prefix of an API key for identification"""
        # Return first 8 characters after the prefix
        return key[:len(self.KEY_PREFIX) + 8] if len(key) > len(self.KEY_PREFIX) + 8 else key

    def generate_key(
        self,
        name: str,
        user_id: str,
        scopes: Optional[List[str]] = None,
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = None
    ) -> str:
        """
        Generate a new API key.

        Args:
            name: Human-readable name for the key
            user_id: Owner user ID
            scopes: Permission scopes (default: ["*"])
            rate_limit: Requests per minute (default: 1000)
            expires_in_days: Days until expiration (None = never)

        Returns:
            The generated API key (only returned once, save it!)
        """
        if scopes is None:
            scopes = ["*"]

        # Generate key
        key = self._generate_random_key()
        key_hash = self._hash_key(key)
        key_prefix = self._get_key_prefix(key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        if self._use_db:
            # Save to database
            db = SessionLocal()
            try:
                api_key = APIKey(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=name,
                    user_id=user_id,
                    scopes=scopes,
                    rate_limit=rate_limit,
                    is_active=True,
                    expires_at=expires_at
                )
                db.add(api_key)
                db.commit()
            finally:
                db.close()
        else:
            # Store in memory
            self._keys[key_hash] = InMemoryAPIKey(
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=name,
                user_id=user_id,
                scopes=scopes,
                rate_limit=rate_limit,
                is_active=True,
                expires_at=expires_at
            )

        return key

    def validate_key(self, key: str) -> Optional[APIKeyInfo]:
        """
        Validate an API key.

        Args:
            key: The API key to validate

        Returns:
            APIKeyInfo if valid, None if invalid
        """
        if not key or not key.startswith(self.KEY_PREFIX):
            return None

        key_hash = self._hash_key(key)

        if self._use_db:
            db = SessionLocal()
            try:
                api_key = db.query(APIKey).filter(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True
                ).first()

                if not api_key:
                    return None

                # Check expiration
                if api_key.expires_at and api_key.expires_at < datetime.now():
                    return None

                # Update last used
                api_key.last_used_at = datetime.now()
                db.commit()

                return APIKeyInfo(
                    key_prefix=api_key.key_prefix,
                    name=api_key.name,
                    user_id=api_key.user_id,
                    scopes=api_key.scopes or [],
                    rate_limit=api_key.rate_limit,
                    is_active=api_key.is_active,
                    created_at=api_key.created_at,
                    last_used_at=api_key.last_used_at,
                    expires_at=api_key.expires_at
                )
            finally:
                db.close()
        else:
            # Check in-memory storage
            api_key = self._keys.get(key_hash)
            if not api_key or not api_key.is_active:
                return None

            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.now():
                return None

            # Update last used
            api_key.last_used_at = datetime.now()

            return APIKeyInfo(
                key_prefix=api_key.key_prefix,
                name=api_key.name,
                user_id=api_key.user_id,
                scopes=api_key.scopes,
                rate_limit=api_key.rate_limit,
                is_active=api_key.is_active,
                created_at=api_key.created_at,
                last_used_at=api_key.last_used_at,
                expires_at=api_key.expires_at
            )

    def revoke_key(self, key: str) -> bool:
        """
        Revoke an API key.

        Args:
            key: The API key to revoke

        Returns:
            True if revoked, False if not found
        """
        key_hash = self._hash_key(key)

        if self._use_db:
            db = SessionLocal()
            try:
                api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
                if not api_key:
                    return False

                api_key.is_active = False
                db.commit()
                return True
            finally:
                db.close()
        else:
            api_key = self._keys.get(key_hash)
            if not api_key:
                return False
            api_key.is_active = False
            return True

    def revoke_by_prefix(self, key_prefix: str) -> bool:
        """
        Revoke an API key by its prefix.

        Args:
            key_prefix: The key prefix (first 14 chars)

        Returns:
            True if revoked, False if not found
        """
        if self._use_db:
            db = SessionLocal()
            try:
                api_key = db.query(APIKey).filter(APIKey.key_prefix == key_prefix).first()
                if not api_key:
                    return False

                api_key.is_active = False
                db.commit()
                return True
            finally:
                db.close()
        else:
            for api_key in self._keys.values():
                if api_key.key_prefix == key_prefix:
                    api_key.is_active = False
                    return True
            return False

    def list_keys(self, user_id: str, include_inactive: bool = False) -> List[APIKeyInfo]:
        """
        List all API keys for a user.

        Args:
            user_id: User ID to list keys for
            include_inactive: Whether to include revoked keys

        Returns:
            List of APIKeyInfo objects
        """
        if self._use_db:
            db = SessionLocal()
            try:
                query = db.query(APIKey).filter(APIKey.user_id == user_id)

                if not include_inactive:
                    query = query.filter(APIKey.is_active == True)

                api_keys = query.all()

                return [
                    APIKeyInfo(
                        key_prefix=k.key_prefix,
                        name=k.name,
                        user_id=k.user_id,
                        scopes=k.scopes or [],
                        rate_limit=k.rate_limit,
                        is_active=k.is_active,
                        created_at=k.created_at,
                        last_used_at=k.last_used_at,
                        expires_at=k.expires_at
                    )
                    for k in api_keys
                ]
            finally:
                db.close()
        else:
            result = []
            for k in self._keys.values():
                if k.user_id == user_id:
                    if include_inactive or k.is_active:
                        result.append(APIKeyInfo(
                            key_prefix=k.key_prefix,
                            name=k.name,
                            user_id=k.user_id,
                            scopes=k.scopes,
                            rate_limit=k.rate_limit,
                            is_active=k.is_active,
                            created_at=k.created_at,
                            last_used_at=k.last_used_at,
                            expires_at=k.expires_at
                        ))
            return result

    def check_scope(self, key: str, required_scope: str) -> bool:
        """
        Check if an API key has a required scope.

        Args:
            key: API key or APIKeyInfo
            required_scope: Required scope (e.g., "agent:read")

        Returns:
            True if scope is allowed
        """
        if isinstance(key, str):
            key_info = self.validate_key(key)
            if not key_info:
                return False
        else:
            key_info = key

        if "*" in key_info.scopes:
            return True

        # Check exact match
        if required_scope in key_info.scopes:
            return True

        # Check wildcard (e.g., "agent:*" matches "agent:read")
        scope_parts = required_scope.split(":")
        if len(scope_parts) == 2:
            wildcard = f"{scope_parts[0]}:*"
            if wildcard in key_info.scopes:
                return True

        return False

    def update_rate_limit(self, key_prefix: str, rate_limit: int) -> bool:
        """
        Update rate limit for an API key.

        Args:
            key_prefix: Key prefix
            rate_limit: New rate limit

        Returns:
            True if updated
        """
        if self._use_db:
            db = SessionLocal()
            try:
                api_key = db.query(APIKey).filter(APIKey.key_prefix == key_prefix).first()
                if not api_key:
                    return False

                api_key.rate_limit = rate_limit
                db.commit()
                return True
            finally:
                db.close()
        else:
            for api_key in self._keys.values():
                if api_key.key_prefix == key_prefix:
                    api_key.rate_limit = rate_limit
                    return True
            return False

    def update_scopes(self, key_prefix: str, scopes: List[str]) -> bool:
        """
        Update scopes for an API key.

        Args:
            key_prefix: Key prefix
            scopes: New scopes list

        Returns:
            True if updated
        """
        if self._use_db:
            db = SessionLocal()
            try:
                api_key = db.query(APIKey).filter(APIKey.key_prefix == key_prefix).first()
                if not api_key:
                    return False

                api_key.scopes = scopes
                db.commit()
                return True
            finally:
                db.close()
        else:
            for api_key in self._keys.values():
                if api_key.key_prefix == key_prefix:
                    api_key.scopes = scopes
                    return True
            return False


# Singleton instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get the singleton API Key Manager instance"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
