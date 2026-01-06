"""
gRPC Client for A2A Protocol

Provides async client for connecting to A2A gRPC servers.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Try to import grpc
try:
    import grpc
    from grpc import aio as grpc_aio
    GRPC_INSTALLED = True
except ImportError:
    GRPC_INSTALLED = False
    grpc = None
    grpc_aio = None


class A2AGrpcClient:
    """
    A2A gRPC Client

    Async client for communicating with A2A gRPC servers.

    Usage:
        async with A2AGrpcClient("localhost:50051") as client:
            response = await client.send_task(
                task_id="task-1",
                messages=[{"role": "user", "content": "Hello"}]
            )
    """

    def __init__(
        self,
        target: str,
        credentials: Optional[Any] = None,
        options: Optional[List[tuple]] = None
    ):
        """
        Initialize client.

        Args:
            target: Server address (host:port)
            credentials: gRPC credentials (None for insecure)
            options: gRPC channel options
        """
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed. Install grpcio package.")

        self.target = target
        self.credentials = credentials
        self.options = options or []
        self._channel = None
        self._stub = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Connect to server"""
        if self.credentials:
            self._channel = grpc_aio.secure_channel(
                self.target, self.credentials, options=self.options
            )
        else:
            self._channel = grpc_aio.insecure_channel(
                self.target, options=self.options
            )

        try:
            from . import a2a_pb2_grpc
            self._stub = a2a_pb2_grpc.AgentServiceStub(self._channel)
        except ImportError:
            raise RuntimeError("gRPC proto files not generated. Run generate_grpc_code() first.")

        logger.info(f"Connected to gRPC server at {self.target}")

    async def close(self):
        """Close connection"""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Disconnected from gRPC server")

    def _ensure_connected(self):
        """Ensure client is connected"""
        if not self._stub:
            raise RuntimeError("Client not connected. Call connect() first.")

    async def send_task(
        self,
        task_id: str,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        accepted_output_modes: Optional[List[str]] = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Send a task and wait for completion.

        Args:
            task_id: Task ID
            messages: List of messages with role and content
            session_id: Optional session ID
            metadata: Optional metadata
            accepted_output_modes: Accepted output types
            timeout: Request timeout in seconds

        Returns:
            Task response dictionary
        """
        self._ensure_connected()

        from . import a2a_pb2

        # Build request
        request = a2a_pb2.TaskRequest(
            id=task_id,
            session_id=session_id or "",
            accepted_output_modes=accepted_output_modes or ["text"]
        )

        # Add messages
        for msg in messages:
            proto_msg = a2a_pb2.Message(role=msg.get("role", "user"))
            proto_msg.parts.append(a2a_pb2.MessagePart(
                type="text",
                text=msg.get("content", "")
            ))
            request.messages.append(proto_msg)

        # Add metadata
        if metadata:
            for k, v in metadata.items():
                request.metadata[k] = str(v)

        # Send request
        response = await self._stub.SendTask(request, timeout=timeout)

        # Convert response
        return self._response_to_dict(response)

    async def stream_task(
        self,
        task_id: str,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a task with streaming updates.

        Args:
            task_id: Task ID
            messages: List of messages
            session_id: Optional session ID
            metadata: Optional metadata

        Yields:
            Task event dictionaries
        """
        self._ensure_connected()

        from . import a2a_pb2

        # Build request
        request = a2a_pb2.TaskRequest(
            id=task_id,
            session_id=session_id or ""
        )

        for msg in messages:
            proto_msg = a2a_pb2.Message(role=msg.get("role", "user"))
            proto_msg.parts.append(a2a_pb2.MessagePart(
                type="text",
                text=msg.get("content", "")
            ))
            request.messages.append(proto_msg)

        if metadata:
            for k, v in metadata.items():
                request.metadata[k] = str(v)

        # Stream response
        async for event in self._stub.StreamTask(request):
            yield self._event_to_dict(event)

    async def get_task(
        self,
        task_id: str,
        history_length: int = 0,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Get task status and history.

        Args:
            task_id: Task ID
            history_length: Max history items (0 for all)
            timeout: Request timeout

        Returns:
            Task response dictionary
        """
        self._ensure_connected()

        from . import a2a_pb2

        request = a2a_pb2.TaskQuery(
            id=task_id,
            history_length=history_length
        )

        response = await self._stub.GetTask(request, timeout=timeout)
        return self._response_to_dict(response)

    async def cancel_task(
        self,
        task_id: str,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Cancel a running task.

        Args:
            task_id: Task ID
            timeout: Request timeout

        Returns:
            Cancel response dictionary
        """
        self._ensure_connected()

        from . import a2a_pb2

        request = a2a_pb2.TaskQuery(id=task_id)
        response = await self._stub.CancelTask(request, timeout=timeout)

        return {
            "id": response.id,
            "success": response.success,
            "status": {
                "state": self._state_to_string(response.status.state),
                "message": response.status.message,
                "timestamp": response.status.timestamp
            }
        }

    async def chat(
        self,
        messages: AsyncIterator[Dict[str, str]],
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Bidirectional streaming chat.

        Args:
            messages: Async iterator of messages
            session_id: Optional session ID

        Yields:
            Response messages
        """
        self._ensure_connected()

        from . import a2a_pb2

        async def request_generator():
            async for msg in messages:
                proto_msg = a2a_pb2.Message(role=msg.get("role", "user"))
                proto_msg.parts.append(a2a_pb2.MessagePart(
                    type="text",
                    text=msg.get("content", "")
                ))
                yield a2a_pb2.ChatMessage(
                    session_id=session_id or "",
                    message=proto_msg
                )

        async for response in self._stub.Chat(request_generator()):
            content = ""
            for part in response.message.parts:
                if part.text:
                    content += part.text

            yield {
                "session_id": response.session_id,
                "role": response.message.role,
                "content": content,
                "is_final": response.is_final,
                "error": response.error if response.error else None
            }

    async def get_agent_card(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Get agent card.

        Args:
            timeout: Request timeout

        Returns:
            Agent card dictionary
        """
        self._ensure_connected()

        from . import a2a_pb2

        request = a2a_pb2.AgentCardRequest()
        response = await self._stub.GetAgentCard(request, timeout=timeout)

        return {
            "name": response.name,
            "description": response.description,
            "url": response.url,
            "version": response.version,
            "protocolVersion": response.protocol_version,
            "capabilities": {
                "streaming": response.capabilities.streaming,
                "pushNotifications": response.capabilities.push_notifications,
                "stateTransitionHistory": response.capabilities.state_transition_history
            },
            "skills": [
                {
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "tags": list(skill.tags),
                    "examples": list(skill.examples),
                    "inputModes": list(skill.input_modes),
                    "outputModes": list(skill.output_modes)
                }
                for skill in response.skills
            ],
            "defaultInputModes": list(response.default_input_modes),
            "defaultOutputModes": list(response.default_output_modes),
            "provider": {
                "organization": response.provider.organization,
                "url": response.provider.url
            } if response.HasField("provider") else None
        }

    def _response_to_dict(self, response) -> Dict[str, Any]:
        """Convert TaskResponse to dictionary"""
        from . import a2a_pb2

        history = []
        for msg in response.history:
            parts = []
            for part in msg.parts:
                parts.append({
                    "type": part.type,
                    "text": part.text
                })
            history.append({
                "role": msg.role,
                "parts": parts
            })

        return {
            "id": response.id,
            "sessionId": response.session_id,
            "status": {
                "state": self._state_to_string(response.status.state),
                "message": response.status.message,
                "timestamp": response.status.timestamp
            },
            "history": history,
            "artifacts": [],
            "metadata": dict(response.metadata)
        }

    def _event_to_dict(self, event) -> Dict[str, Any]:
        """Convert TaskEvent to dictionary"""
        message = None
        if event.HasField("message"):
            parts = []
            for part in event.message.parts:
                parts.append({"type": part.type, "text": part.text})
            message = {"role": event.message.role, "parts": parts}

        return {
            "eventType": event.event_type,
            "taskId": event.task_id,
            "status": {
                "state": self._state_to_string(event.status.state),
                "timestamp": event.status.timestamp
            } if event.HasField("status") else None,
            "progress": event.progress,
            "message": message,
            "errorMessage": event.error_message if event.error_message else None,
            "timestamp": event.timestamp
        }

    def _state_to_string(self, state: int) -> str:
        """Convert TaskState enum to string"""
        try:
            from . import a2a_pb2
            mapping = {
                a2a_pb2.TASK_STATE_UNKNOWN: "unknown",
                a2a_pb2.TASK_STATE_PENDING: "pending",
                a2a_pb2.TASK_STATE_RUNNING: "running",
                a2a_pb2.TASK_STATE_COMPLETED: "completed",
                a2a_pb2.TASK_STATE_FAILED: "failed",
                a2a_pb2.TASK_STATE_CANCELLED: "cancelled",
            }
            return mapping.get(state, "unknown")
        except ImportError:
            return "unknown"


async def create_client(
    target: str,
    secure: bool = False,
    **kwargs
) -> A2AGrpcClient:
    """
    Create and connect a gRPC client.

    Args:
        target: Server address
        secure: Whether to use TLS
        **kwargs: Additional client options

    Returns:
        Connected A2AGrpcClient
    """
    client = A2AGrpcClient(target, **kwargs)
    await client.connect()
    return client
