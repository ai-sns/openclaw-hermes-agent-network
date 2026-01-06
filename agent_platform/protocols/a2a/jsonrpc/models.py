"""
JSON-RPC 2.0 Models for A2A Protocol

Defines request/response models following JSON-RPC 2.0 specification.
Reference: https://www.jsonrpc.org/specification
"""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import IntEnum
from datetime import datetime


# ============== JSON-RPC 2.0 Error Codes ==============

class JSONRPCErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes"""
    # Standard errors
    PARSE_ERROR = -32700       # Invalid JSON
    INVALID_REQUEST = -32600   # Not a valid Request object
    METHOD_NOT_FOUND = -32601  # Method does not exist
    INVALID_PARAMS = -32602    # Invalid method parameters
    INTERNAL_ERROR = -32603    # Internal JSON-RPC error

    # Server errors (-32000 to -32099 reserved for implementation)
    SERVER_ERROR = -32000      # Generic server error
    TASK_NOT_FOUND = -32001    # Task not found
    AGENT_NOT_FOUND = -32002   # Agent not found
    UNAUTHORIZED = -32003      # Authentication required
    RATE_LIMITED = -32004      # Rate limit exceeded
    TASK_CANCELLED = -32005    # Task was cancelled
    TIMEOUT = -32006           # Operation timed out


# ============== JSON-RPC 2.0 Core Models ==============

class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 Error object"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def parse_error(cls, data: Any = None) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.PARSE_ERROR, message="Parse error", data=data)

    @classmethod
    def invalid_request(cls, data: Any = None) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.INVALID_REQUEST, message="Invalid Request", data=data)

    @classmethod
    def method_not_found(cls, method: str) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.METHOD_NOT_FOUND, message=f"Method not found: {method}")

    @classmethod
    def invalid_params(cls, data: Any = None) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.INVALID_PARAMS, message="Invalid params", data=data)

    @classmethod
    def internal_error(cls, data: Any = None) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.INTERNAL_ERROR, message="Internal error", data=data)

    @classmethod
    def task_not_found(cls, task_id: str) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.TASK_NOT_FOUND, message=f"Task not found: {task_id}")

    @classmethod
    def unauthorized(cls) -> "JSONRPCError":
        return cls(code=JSONRPCErrorCode.UNAUTHORIZED, message="Unauthorized")


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request object"""
    jsonrpc: Literal["2.0"] = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Method parameters")
    id: Optional[Union[str, int]] = Field(default=None, description="Request ID")

    model_config = ConfigDict(populate_by_name=True)

    def is_notification(self) -> bool:
        """Check if this is a notification (no id)"""
        return self.id is None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response object"""
    jsonrpc: Literal["2.0"] = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Any] = Field(default=None, description="Result on success")
    error: Optional[JSONRPCError] = Field(default=None, description="Error on failure")
    id: Optional[Union[str, int]] = Field(default=None, description="Request ID")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def success(cls, result: Any, id: Optional[Union[str, int]] = None) -> "JSONRPCResponse":
        """Create success response"""
        return cls(result=result, id=id)

    @classmethod
    def failure(cls, error: JSONRPCError, id: Optional[Union[str, int]] = None) -> "JSONRPCResponse":
        """Create error response"""
        return cls(error=error, id=id)


# ============== A2A Task Models (Google A2A spec) ==============

class MessagePart(BaseModel):
    """Message part containing text or data"""
    type: str = Field(default="text", description="Part type: text, inlineData, fileData")
    text: Optional[str] = Field(None, description="Text content")
    mimeType: Optional[str] = Field(None, description="MIME type for data")
    data: Optional[str] = Field(None, description="Base64 encoded data")
    fileUri: Optional[str] = Field(None, description="File URI reference")

    model_config = ConfigDict(populate_by_name=True)


class Message(BaseModel):
    """A2A Message (Google A2A spec)"""
    role: str = Field(..., description="Message role: user, assistant")
    parts: List[MessagePart] = Field(default_factory=list, description="Message parts")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_text(cls, role: str, text: str) -> "Message":
        """Create message from text"""
        return cls(role=role, parts=[MessagePart(type="text", text=text)])


class Artifact(BaseModel):
    """Task artifact (file, image, etc.)"""
    type: str = Field(..., description="Artifact type")
    name: Optional[str] = Field(None, description="Artifact name")
    mimeType: Optional[str] = Field(None, description="MIME type")
    data: Optional[str] = Field(None, description="Base64 encoded data")
    uri: Optional[str] = Field(None, description="URI reference")

    model_config = ConfigDict(populate_by_name=True)


class TaskStatus(BaseModel):
    """Task status (Google A2A spec)"""
    state: str = Field(..., description="Task state: pending, running, completed, failed, cancelled")
    message: Optional[Message] = Field(None, description="Status message")
    timestamp: Optional[str] = Field(None, description="Status timestamp")

    model_config = ConfigDict(populate_by_name=True)


class Task(BaseModel):
    """A2A Task (Google A2A spec)"""
    id: str = Field(..., description="Task ID")
    sessionId: Optional[str] = Field(None, description="Session ID")
    status: TaskStatus = Field(..., description="Task status")
    artifacts: List[Artifact] = Field(default_factory=list, description="Task artifacts")
    history: List[Message] = Field(default_factory=list, description="Message history")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")

    model_config = ConfigDict(populate_by_name=True)


# ============== JSON-RPC Method Parameters ==============

class TaskSendParams(BaseModel):
    """Parameters for tasks/send method"""
    id: str = Field(..., description="Task ID")
    sessionId: Optional[str] = Field(None, description="Session ID for context")
    message: Message = Field(..., description="Message to send")
    acceptedOutputModes: List[str] = Field(
        default_factory=lambda: ["text"],
        description="Accepted output modes"
    )
    pushNotification: Optional[Dict[str, Any]] = Field(None, description="Push notification config")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(populate_by_name=True)


class TaskSendSubscribeParams(TaskSendParams):
    """Parameters for tasks/sendSubscribe method (streaming)"""
    pass


class TaskGetParams(BaseModel):
    """Parameters for tasks/get method"""
    id: str = Field(..., description="Task ID")
    historyLength: Optional[int] = Field(None, description="Number of history items to return")

    model_config = ConfigDict(populate_by_name=True)


class TaskCancelParams(BaseModel):
    """Parameters for tasks/cancel method"""
    id: str = Field(..., description="Task ID")

    model_config = ConfigDict(populate_by_name=True)


class PushNotificationConfig(BaseModel):
    """Push notification configuration"""
    url: str = Field(..., description="Webhook URL")
    token: Optional[str] = Field(None, description="Authentication token")
    authentication: Optional[Dict[str, Any]] = Field(None, description="Auth config")

    model_config = ConfigDict(populate_by_name=True)


class PushNotificationParams(BaseModel):
    """Parameters for tasks/pushNotification/set method"""
    id: str = Field(..., description="Task ID")
    pushNotificationConfig: PushNotificationConfig = Field(..., description="Notification config")

    model_config = ConfigDict(populate_by_name=True)


class PushNotificationGetParams(BaseModel):
    """Parameters for tasks/pushNotification/get method"""
    id: str = Field(..., description="Task ID")

    model_config = ConfigDict(populate_by_name=True)


# ============== JSON-RPC Method Results ==============

class TaskSendResult(BaseModel):
    """Result for tasks/send method"""
    id: str = Field(..., description="Task ID")
    sessionId: Optional[str] = Field(None, description="Session ID")
    status: TaskStatus = Field(..., description="Task status")
    artifacts: List[Artifact] = Field(default_factory=list, description="Task artifacts")

    model_config = ConfigDict(populate_by_name=True)


class TaskGetResult(BaseModel):
    """Result for tasks/get method"""
    id: str = Field(..., description="Task ID")
    sessionId: Optional[str] = Field(None, description="Session ID")
    status: TaskStatus = Field(..., description="Task status")
    artifacts: List[Artifact] = Field(default_factory=list, description="Task artifacts")
    history: List[Message] = Field(default_factory=list, description="Message history")

    model_config = ConfigDict(populate_by_name=True)


class TaskCancelResult(BaseModel):
    """Result for tasks/cancel method"""
    id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Task status after cancellation")

    model_config = ConfigDict(populate_by_name=True)


class PushNotificationResult(BaseModel):
    """Result for tasks/pushNotification/set method"""
    id: str = Field(..., description="Task ID")
    pushNotificationConfig: PushNotificationConfig = Field(..., description="Applied config")

    model_config = ConfigDict(populate_by_name=True)


# ============== Batch Request ==============

class JSONRPCBatchRequest(BaseModel):
    """Batch of JSON-RPC requests"""
    requests: List[JSONRPCRequest] = Field(..., description="List of requests")

    model_config = ConfigDict(populate_by_name=True)


class JSONRPCBatchResponse(BaseModel):
    """Batch of JSON-RPC responses"""
    responses: List[JSONRPCResponse] = Field(..., description="List of responses")

    model_config = ConfigDict(populate_by_name=True)
