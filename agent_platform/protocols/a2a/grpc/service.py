"""
gRPC Service Implementation for A2A Protocol

Implements the AgentService gRPC service with streaming support.
"""

import asyncio
import logging
from typing import Optional, AsyncIterator, Dict, Any
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

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))


class A2AGrpcService:
    """
    A2A gRPC Service Implementation

    Provides gRPC interface for A2A protocol operations.
    """

    def __init__(self):
        """Initialize service"""
        self._task_manager = None
        self._agent_card_manager = None

    @property
    def task_manager(self):
        """Lazy load task manager"""
        if self._task_manager is None:
            from agent_platform.protocols.a2a.task_manager import get_a2a_task_manager
            self._task_manager = get_a2a_task_manager()
        return self._task_manager

    @property
    def agent_card_manager(self):
        """Lazy load agent card manager"""
        if self._agent_card_manager is None:
            from agent_platform.protocols.a2a.agent_card import get_agent_card_manager
            self._agent_card_manager = get_agent_card_manager()
        return self._agent_card_manager

    async def SendTask(self, request, context):
        """
        Send a task and wait for completion.

        Args:
            request: TaskRequest protobuf message
            context: gRPC context

        Returns:
            TaskResponse protobuf message
        """
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed")

        try:
            # Import proto types
            from . import a2a_pb2

            # Extract messages
            messages = []
            for msg in request.messages:
                parts = []
                for part in msg.parts:
                    if part.text:
                        parts.append(part.text)
                messages.append({
                    "role": msg.role,
                    "content": " ".join(parts)
                })

            # Create task
            task = await self.task_manager.create_task(
                agent_id="default",
                messages=messages,
                metadata={
                    "grpc_task_id": request.id,
                    "session_id": request.session_id,
                    **dict(request.metadata)
                }
            )

            # Execute task
            task = await self.task_manager.execute_task(task.task_id)

            # Build response
            response = a2a_pb2.TaskResponse(
                id=request.id,
                session_id=request.session_id,
                status=a2a_pb2.TaskStatus(
                    state=self._map_status(task.status.value),
                    message=task.output_message.content if task.output_message else "",
                    timestamp=int(time.time())
                ),
                metadata=request.metadata
            )

            # Add output message to history
            if task.output_message:
                msg = a2a_pb2.Message(
                    role="assistant",
                    timestamp=int(time.time())
                )
                msg.parts.append(a2a_pb2.MessagePart(
                    type="text",
                    text=task.output_message.content
                ))
                response.history.append(msg)

            return response

        except Exception as e:
            logger.exception(f"Error in SendTask: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def StreamTask(self, request, context):
        """
        Send a task with streaming updates.

        Yields TaskEvent messages as the task progresses.
        """
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed")

        try:
            from . import a2a_pb2

            # Extract messages
            messages = []
            for msg in request.messages:
                parts = []
                for part in msg.parts:
                    if part.text:
                        parts.append(part.text)
                messages.append({
                    "role": msg.role,
                    "content": " ".join(parts)
                })

            # Create task
            task = await self.task_manager.create_task(
                agent_id="default",
                messages=messages,
                metadata={
                    "grpc_task_id": request.id,
                    "session_id": request.session_id,
                    **dict(request.metadata)
                }
            )

            # Send initial status
            yield a2a_pb2.TaskEvent(
                event_type="status",
                task_id=request.id,
                status=a2a_pb2.TaskStatus(
                    state=a2a_pb2.TASK_STATE_PENDING,
                    message="Task created",
                    timestamp=int(time.time())
                ),
                progress=0.0,
                timestamp=int(time.time())
            )

            # Stream task progress
            async for event in self.task_manager.stream_task_progress(task.task_id):
                event_data = event.get("data", {})
                status = event_data.get("status", "working")
                progress = event_data.get("progress", 0)
                output = event_data.get("output", "")

                # Create message if output available
                message = None
                if output:
                    message = a2a_pb2.Message(role="assistant")
                    message.parts.append(a2a_pb2.MessagePart(type="text", text=output))

                yield a2a_pb2.TaskEvent(
                    event_type="progress" if status == "working" else "status",
                    task_id=request.id,
                    status=a2a_pb2.TaskStatus(
                        state=self._map_status(status),
                        timestamp=int(time.time())
                    ),
                    progress=progress,
                    message=message,
                    timestamp=int(time.time())
                )

                if status in ["completed", "failed", "cancelled"]:
                    break

            # Send final result
            final_task = await self.task_manager.get_task(task.task_id)
            final_message = a2a_pb2.Message(role="assistant")
            if final_task and final_task.output_message:
                final_message.parts.append(a2a_pb2.MessagePart(
                    type="text",
                    text=final_task.output_message.content
                ))

            yield a2a_pb2.TaskEvent(
                event_type="completed",
                task_id=request.id,
                status=a2a_pb2.TaskStatus(
                    state=self._map_status(final_task.status.value if final_task else "failed"),
                    timestamp=int(time.time())
                ),
                progress=1.0,
                message=final_message,
                timestamp=int(time.time())
            )

        except Exception as e:
            logger.exception(f"Error in StreamTask: {e}")
            from . import a2a_pb2
            yield a2a_pb2.TaskEvent(
                event_type="error",
                task_id=request.id,
                error_message=str(e),
                timestamp=int(time.time())
            )

    async def GetTask(self, request, context):
        """Get task status and history"""
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed")

        try:
            from . import a2a_pb2

            # Find task by grpc_task_id
            task = None
            for t in self.task_manager._tasks.values():
                if t.metadata.get("grpc_task_id") == request.id:
                    task = t
                    break

            if not task:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Task not found: {request.id}")
                return a2a_pb2.TaskResponse()

            # Build response
            response = a2a_pb2.TaskResponse(
                id=request.id,
                session_id=task.metadata.get("session_id", ""),
                status=a2a_pb2.TaskStatus(
                    state=self._map_status(task.status.value),
                    message=task.output_message.content if task.output_message else "",
                    timestamp=int(task.completed_at.timestamp()) if task.completed_at else int(time.time())
                )
            )

            # Add history
            for msg in task.input_messages:
                proto_msg = a2a_pb2.Message(role=msg.role)
                proto_msg.parts.append(a2a_pb2.MessagePart(type="text", text=msg.content))
                response.history.append(proto_msg)

            if task.output_message:
                proto_msg = a2a_pb2.Message(role="assistant")
                proto_msg.parts.append(a2a_pb2.MessagePart(type="text", text=task.output_message.content))
                response.history.append(proto_msg)

            # Apply history length limit
            if request.history_length > 0 and len(response.history) > request.history_length:
                del response.history[:-request.history_length]

            return response

        except Exception as e:
            logger.exception(f"Error in GetTask: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def CancelTask(self, request, context):
        """Cancel a running task"""
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed")

        try:
            from . import a2a_pb2

            # Find task
            task = None
            for t in self.task_manager._tasks.values():
                if t.metadata.get("grpc_task_id") == request.id:
                    task = t
                    break

            if not task:
                return a2a_pb2.CancelResponse(
                    id=request.id,
                    success=False,
                    status=a2a_pb2.TaskStatus(
                        state=a2a_pb2.TASK_STATE_UNKNOWN,
                        message="Task not found"
                    )
                )

            # Cancel task
            success = await self.task_manager.cancel_task(task.task_id)

            return a2a_pb2.CancelResponse(
                id=request.id,
                success=success,
                status=a2a_pb2.TaskStatus(
                    state=a2a_pb2.TASK_STATE_CANCELLED if success else self._map_status(task.status.value),
                    timestamp=int(time.time())
                )
            )

        except Exception as e:
            logger.exception(f"Error in CancelTask: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    async def Chat(self, request_iterator, context):
        """
        Bidirectional streaming chat.

        Receives messages from client and yields responses.
        """
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed")

        try:
            from . import a2a_pb2

            session_id = None

            async for chat_msg in request_iterator:
                session_id = chat_msg.session_id or session_id or f"chat-{int(time.time())}"

                # Extract message content
                content = ""
                for part in chat_msg.message.parts:
                    if part.text:
                        content += part.text

                # Create and execute task
                task = await self.task_manager.create_task(
                    agent_id="default",
                    messages=[{"role": chat_msg.message.role, "content": content}],
                    metadata={"session_id": session_id}
                )
                task = await self.task_manager.execute_task(task.task_id)

                # Send response
                response_msg = a2a_pb2.Message(role="assistant")
                if task.output_message:
                    response_msg.parts.append(a2a_pb2.MessagePart(
                        type="text",
                        text=task.output_message.content
                    ))

                yield a2a_pb2.ChatMessage(
                    session_id=session_id,
                    message=response_msg,
                    is_final=True
                )

        except Exception as e:
            logger.exception(f"Error in Chat: {e}")
            from . import a2a_pb2
            yield a2a_pb2.ChatMessage(
                session_id=session_id or "",
                error=str(e)
            )

    async def GetAgentCard(self, request, context):
        """Get agent card"""
        if not GRPC_INSTALLED:
            raise RuntimeError("gRPC not installed")

        try:
            from . import a2a_pb2

            # Get card from manager
            card = self.agent_card_manager.get_card("default")
            if not card:
                from agent_platform.protocols.a2a.agent_card import AgentCard, AgentCapabilities, EndpointConfig
                card = AgentCard(
                    name="AI-SNS Agent",
                    description="AI Agent Open Platform",
                    url="http://localhost:8000/a2a",
                    capabilities=AgentCapabilities(),
                    endpoint=EndpointConfig(base_url="http://localhost:8000")
                )

            # Build response
            response = a2a_pb2.AgentCardResponse(
                name=card.name,
                description=card.description,
                url=card.url,
                version=card.version,
                protocol_version=card.protocolVersion,
                capabilities=a2a_pb2.AgentCapabilities(
                    streaming=card.capabilities.streaming,
                    push_notifications=card.capabilities.pushNotifications,
                    state_transition_history=card.capabilities.stateTransitionHistory
                ),
                default_input_modes=card.defaultInputModes,
                default_output_modes=card.defaultOutputModes
            )

            # Add skills
            for skill in card.skills:
                response.skills.append(a2a_pb2.AgentSkill(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description or "",
                    tags=skill.tags,
                    examples=skill.examples,
                    input_modes=skill.inputModes,
                    output_modes=skill.outputModes
                ))

            # Add provider
            if card.provider:
                response.provider.CopyFrom(a2a_pb2.ProviderInfo(
                    organization=card.provider.organization,
                    url=card.provider.url or ""
                ))

            return response

        except Exception as e:
            logger.exception(f"Error in GetAgentCard: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise

    def _map_status(self, status: str) -> int:
        """Map status string to proto enum"""
        try:
            from . import a2a_pb2
            mapping = {
                "pending": a2a_pb2.TASK_STATE_PENDING,
                "running": a2a_pb2.TASK_STATE_RUNNING,
                "working": a2a_pb2.TASK_STATE_RUNNING,
                "completed": a2a_pb2.TASK_STATE_COMPLETED,
                "failed": a2a_pb2.TASK_STATE_FAILED,
                "cancelled": a2a_pb2.TASK_STATE_CANCELLED,
            }
            return mapping.get(status.lower(), a2a_pb2.TASK_STATE_UNKNOWN)
        except ImportError:
            return 0


# ============== Server Management ==============

_grpc_server = None


async def start_grpc_server(
    port: int = 50051,
    host: str = "0.0.0.0",
    max_workers: int = 10
) -> Optional[Any]:
    """
    Start gRPC server.

    Args:
        port: Port to listen on
        host: Host to bind to
        max_workers: Maximum worker threads

    Returns:
        gRPC server instance or None if gRPC not available
    """
    global _grpc_server

    if not GRPC_INSTALLED:
        logger.warning("gRPC not installed. Install grpcio to enable gRPC support.")
        return None

    try:
        from . import a2a_pb2_grpc

        _grpc_server = grpc_aio.server()

        # Add service
        service = A2AGrpcService()
        a2a_pb2_grpc.add_AgentServiceServicer_to_server(service, _grpc_server)

        # Start server
        listen_addr = f"{host}:{port}"
        _grpc_server.add_insecure_port(listen_addr)
        await _grpc_server.start()

        logger.info(f"gRPC server started on {listen_addr}")
        return _grpc_server

    except ImportError:
        logger.warning("gRPC proto files not generated. Run generate_grpc_code() first.")
        return None
    except Exception as e:
        logger.exception(f"Failed to start gRPC server: {e}")
        return None


async def stop_grpc_server(grace_period: float = 5.0):
    """Stop gRPC server"""
    global _grpc_server

    if _grpc_server:
        await _grpc_server.stop(grace_period)
        _grpc_server = None
        logger.info("gRPC server stopped")


def get_grpc_server():
    """Get current gRPC server instance"""
    return _grpc_server
