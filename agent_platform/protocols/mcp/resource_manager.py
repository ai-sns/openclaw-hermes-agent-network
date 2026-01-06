"""
MCP Resource Manager

Manages resources for the Model Context Protocol.
Resources can be files, databases, APIs, or any external data source.
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import aiofiles
import asyncio

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)


class MCPResourceType(str, Enum):
    """Resource types"""
    FILE = "file"
    URL = "url"
    DATABASE = "database"
    API = "api"
    MEMORY = "memory"
    EMBEDDING = "embedding"
    CUSTOM = "custom"


class MCPResourceStatus(str, Enum):
    """Resource status"""
    AVAILABLE = "available"
    LOADING = "loading"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class MCPResource:
    """MCP Resource definition"""
    resource_id: str
    name: str
    resource_type: MCPResourceType
    uri: str  # file path, URL, connection string, etc.
    description: str = ""
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    status: MCPResourceStatus = MCPResourceStatus.AVAILABLE
    content: Optional[Any] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type.value,
            "uri": self.uri,
            "description": self.description,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count
        }

    def is_expired(self) -> bool:
        """Check if resource is expired"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False


@dataclass
class ResourceQuery:
    """Query for filtering resources"""
    resource_type: Optional[MCPResourceType] = None
    tags: Optional[List[str]] = None
    name_contains: Optional[str] = None
    status: Optional[MCPResourceStatus] = None
    limit: int = 100
    offset: int = 0


class MCPResourceManager:
    """
    MCP Resource Manager

    Manages external resources for agent context:
    - File resources (documents, images, etc.)
    - URL resources (web pages, APIs)
    - Database connections
    - In-memory data
    - Vector embeddings
    """

    def __init__(self, storage_path: str = "mcp_resources"):
        """
        Initialize resource manager.

        Args:
            storage_path: Path for storing resource data
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        self._resources: Dict[str, MCPResource] = {}
        self._resource_content: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _generate_resource_id(self, uri: str) -> str:
        """Generate unique resource ID"""
        hash_input = f"{uri}_{datetime.now().isoformat()}"
        return f"res_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

    async def register_resource(
        self,
        name: str,
        resource_type: MCPResourceType,
        uri: str,
        description: str = "",
        mime_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        load_content: bool = False
    ) -> MCPResource:
        """
        Register a new resource.

        Args:
            name: Resource name
            resource_type: Type of resource
            uri: Resource URI (path, URL, etc.)
            description: Resource description
            mime_type: MIME type
            metadata: Additional metadata
            tags: Resource tags
            load_content: Load content immediately

        Returns:
            Created MCPResource
        """
        resource_id = self._generate_resource_id(uri)

        resource = MCPResource(
            resource_id=resource_id,
            name=name,
            resource_type=resource_type,
            uri=uri,
            description=description,
            mime_type=mime_type,
            metadata=metadata or {},
            tags=tags or []
        )

        # Load content if requested
        if load_content:
            await self.load_resource_content(resource)

        async with self._lock:
            self._resources[resource_id] = resource

        logger.info(f"Registered resource: {name} ({resource_id})")
        return resource

    async def register_file(
        self,
        file_path: str,
        name: Optional[str] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> MCPResource:
        """Register a file resource"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = name or os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        return await self.register_resource(
            name=file_name,
            resource_type=MCPResourceType.FILE,
            uri=file_path,
            description=description,
            mime_type=mime_type,
            metadata={"file_size": file_size},
            tags=tags,
            load_content=False
        )

    async def register_memory(
        self,
        name: str,
        content: Any,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> MCPResource:
        """Register an in-memory resource"""
        resource = await self.register_resource(
            name=name,
            resource_type=MCPResourceType.MEMORY,
            uri=f"memory://{name}",
            description=description,
            mime_type="application/json",
            tags=tags
        )

        # Store content
        self._resource_content[resource.resource_id] = content
        resource.content = content
        resource.status = MCPResourceStatus.AVAILABLE

        # Calculate size
        content_str = json.dumps(content) if not isinstance(content, str) else content
        resource.size_bytes = len(content_str.encode())
        resource.content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        return resource

    async def get_resource(self, resource_id: str) -> Optional[MCPResource]:
        """Get resource by ID"""
        resource = self._resources.get(resource_id)
        if resource:
            resource.access_count += 1
            resource.updated_at = datetime.now()
        return resource

    async def get_resource_by_name(self, name: str) -> Optional[MCPResource]:
        """Get resource by name"""
        for resource in self._resources.values():
            if resource.name == name:
                resource.access_count += 1
                return resource
        return None

    async def load_resource_content(
        self,
        resource: MCPResource,
        force: bool = False
    ) -> Any:
        """
        Load resource content.

        Args:
            resource: Resource to load
            force: Force reload even if cached

        Returns:
            Resource content
        """
        # Check cache
        if not force and resource.resource_id in self._resource_content:
            return self._resource_content[resource.resource_id]

        resource.status = MCPResourceStatus.LOADING

        try:
            if resource.resource_type == MCPResourceType.FILE:
                content = await self._load_file_content(resource)
            elif resource.resource_type == MCPResourceType.URL:
                content = await self._load_url_content(resource)
            elif resource.resource_type == MCPResourceType.MEMORY:
                content = self._resource_content.get(resource.resource_id)
            else:
                content = None

            if content is not None:
                self._resource_content[resource.resource_id] = content
                resource.content = content
                resource.status = MCPResourceStatus.AVAILABLE

                # Update hash
                content_str = str(content)
                resource.content_hash = hashlib.sha256(content_str.encode()).hexdigest()

            return content

        except Exception as e:
            resource.status = MCPResourceStatus.ERROR
            resource.metadata["error"] = str(e)
            logger.error(f"Failed to load resource {resource.resource_id}: {e}")
            raise

    async def _load_file_content(self, resource: MCPResource) -> Any:
        """Load file content"""
        file_path = resource.uri

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine how to read based on MIME type
        if resource.mime_type.startswith("text/") or resource.mime_type == "application/json":
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                if resource.mime_type == "application/json":
                    content = json.loads(content)
        else:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()

        resource.size_bytes = os.path.getsize(file_path)
        return content

    async def _load_url_content(self, resource: MCPResource) -> Any:
        """Load URL content"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(resource.uri, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                content = response.json()
            else:
                content = response.text

            resource.size_bytes = len(response.content)
            return content

    async def query_resources(self, query: ResourceQuery) -> List[MCPResource]:
        """
        Query resources.

        Args:
            query: Query parameters

        Returns:
            List of matching resources
        """
        results = []

        for resource in self._resources.values():
            # Check expiration
            if resource.is_expired():
                resource.status = MCPResourceStatus.EXPIRED
                continue

            # Apply filters
            if query.resource_type and resource.resource_type != query.resource_type:
                continue

            if query.status and resource.status != query.status:
                continue

            if query.name_contains and query.name_contains.lower() not in resource.name.lower():
                continue

            if query.tags:
                if not any(tag in resource.tags for tag in query.tags):
                    continue

            results.append(resource)

        # Apply pagination
        start = query.offset
        end = start + query.limit
        return results[start:end]

    async def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource"""
        if resource_id in self._resources:
            del self._resources[resource_id]
            self._resource_content.pop(resource_id, None)
            return True
        return False

    async def update_resource(
        self,
        resource_id: str,
        updates: Dict[str, Any]
    ) -> Optional[MCPResource]:
        """Update resource metadata"""
        resource = self._resources.get(resource_id)
        if not resource:
            return None

        # Update allowed fields
        allowed_fields = ["name", "description", "tags", "metadata"]
        for field in allowed_fields:
            if field in updates:
                setattr(resource, field, updates[field])

        resource.updated_at = datetime.now()
        return resource

    def get_stats(self) -> Dict[str, Any]:
        """Get resource manager statistics"""
        type_counts = {}
        status_counts = {}
        total_size = 0

        for resource in self._resources.values():
            type_counts[resource.resource_type.value] = type_counts.get(
                resource.resource_type.value, 0
            ) + 1
            status_counts[resource.status.value] = status_counts.get(
                resource.status.value, 0
            ) + 1
            total_size += resource.size_bytes

        return {
            "total_resources": len(self._resources),
            "cached_contents": len(self._resource_content),
            "type_counts": type_counts,
            "status_counts": status_counts,
            "total_size_bytes": total_size
        }


# Singleton instance
_resource_manager: Optional[MCPResourceManager] = None


def get_mcp_resource_manager() -> MCPResourceManager:
    """Get the MCP resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = MCPResourceManager()
    return _resource_manager
