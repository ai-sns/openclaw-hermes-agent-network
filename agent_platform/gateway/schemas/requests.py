"""
Request/Response Schemas

Pydantic models for API requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from enum import Enum


# Generic type for paginated responses
T = TypeVar('T')


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============ Common Response Models ============

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ============ Chat Models ============

class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: user/assistant/system/tool")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Name for tool messages")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool responses")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    agent_id: str = Field(..., description="Target agent ID")
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    thread_id: Optional[str] = Field(None, description="Thread ID for sub-conversation")

    # Optional context
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    history: Optional[List[ChatMessage]] = Field(None, description="Conversation history")

    # Options
    stream: bool = Field(False, description="Enable streaming response")
    max_tokens: Optional[int] = Field(None, description="Max tokens for response")
    temperature: Optional[float] = Field(None, description="Temperature for sampling")

    # Tools
    tools: Optional[List[str]] = Field(None, description="Tools to enable")

    # Webhook for async
    webhook_url: Optional[str] = Field(None, description="Webhook URL for async callback")

    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent_001",
                "message": "Hello, how are you?",
                "stream": True
            }
        }


class ChatResponse(BaseModel):
    """Chat response model"""
    message: str = Field(..., description="Assistant response")
    role: str = Field(default="assistant", description="Message role")

    # Session info
    session_id: str = Field(..., description="Session ID")
    thread_id: Optional[str] = Field(None, description="Thread ID")

    # Usage
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage")

    # Tool calls (if any)
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made")

    # Timing
    latency_ms: Optional[int] = Field(None, description="Response latency in ms")
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamChunk(BaseModel):
    """SSE stream chunk"""
    type: str = Field(..., description="Chunk type: content/tool_call/done/error")
    content: Optional[str] = Field(None, description="Content chunk")
    tool_call: Optional[Dict[str, Any]] = Field(None, description="Tool call data")
    done: bool = Field(False, description="Whether stream is complete")
    error: Optional[str] = Field(None, description="Error message if any")


# ============ Task Models ============

class TaskRequest(BaseModel):
    """Async task request"""
    agent_id: str = Field(..., description="Target agent ID")
    task_type: str = Field(default="chat", description="Task type")
    input_data: Dict[str, Any] = Field(..., description="Task input data")

    priority: int = Field(0, description="Task priority (higher = more urgent)")

    # Callback
    webhook_url: Optional[str] = Field(None, description="Webhook URL for completion callback")

    # Options
    timeout_seconds: Optional[int] = Field(None, description="Task timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TaskResponse(BaseModel):
    """Task response model"""
    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Task status")

    # Result (if completed)
    output_data: Optional[Dict[str, Any]] = Field(None, description="Task output")
    error: Optional[str] = Field(None, description="Error message if failed")

    # Progress
    progress: Optional[float] = Field(None, description="Progress percentage 0-100")

    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    execution_time_ms: Optional[int] = Field(None)


class TaskStatusUpdate(BaseModel):
    """Task status update for SSE"""
    task_id: str
    status: TaskStatus
    progress: Optional[float] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ============ Agent Models ============

class AgentInfo(BaseModel):
    """Agent information"""
    id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")

    # Capabilities
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    tools: List[str] = Field(default_factory=list, description="Available tools")

    # Model info
    model: Optional[str] = Field(None, description="LLM model")

    # Status
    is_active: bool = Field(True, description="Whether agent is active")

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentListResponse(BaseModel):
    """Agent list response"""
    agents: List[AgentInfo]
    total: int


# ============ File Models ============

class FileUploadRequest(BaseModel):
    """File upload metadata"""
    session_id: Optional[str] = None
    description: Optional[str] = None
    expires_in_hours: Optional[int] = Field(24, description="File expiration in hours")


class FileUploadResponse(BaseModel):
    """File upload response"""
    file_id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")

    download_url: str = Field(..., description="Download URL")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")

    created_at: datetime = Field(default_factory=datetime.now)


class FileInfo(BaseModel):
    """File information"""
    file_id: str
    filename: str
    file_size: int
    mime_type: Optional[str]
    download_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    download_count: int = 0


# ============ Session Models ============

class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    thread_id: Optional[str]
    agent_id: Optional[str]

    status: str = "active"
    message_count: int = 0

    created_at: datetime
    last_activity_at: datetime
    expires_at: Optional[datetime]


class CreateSessionRequest(BaseModel):
    """Create session request"""
    agent_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    expires_in_hours: Optional[int] = Field(24, description="Session expiration in hours")


class CreateSessionResponse(BaseModel):
    """Create session response"""
    session_id: str
    thread_id: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)


# ============ Webhook Models ============

class WebhookPayload(BaseModel):
    """Webhook callback payload"""
    event_type: str = Field(..., description="Event type: task.completed/task.failed/etc.")
    task_id: str
    status: TaskStatus

    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    timestamp: datetime = Field(default_factory=datetime.now)

    # Signature for verification
    signature: Optional[str] = Field(None, description="HMAC signature")


# ============ API Key Models ============

class APIKeyInfo(BaseModel):
    """API Key information (without the actual key)"""
    key_prefix: str = Field(..., description="Key prefix for identification")
    name: str
    scopes: List[str]
    rate_limit: int
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


class CreateAPIKeyRequest(BaseModel):
    """Create API Key request"""
    name: str = Field(..., description="Key name")
    scopes: List[str] = Field(default_factory=lambda: ["*"], description="Permission scopes")
    rate_limit: int = Field(1000, description="Requests per minute")
    expires_in_days: Optional[int] = Field(None, description="Expiration in days (null = never)")


class CreateAPIKeyResponse(BaseModel):
    """Create API Key response (includes the actual key, only shown once)"""
    key: str = Field(..., description="API Key (save this, won't be shown again)")
    key_prefix: str
    name: str
    scopes: List[str]
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime]
