"""
JSON-RPC 2.0 Handler for A2A Protocol

Handles JSON-RPC requests and dispatches them to appropriate methods.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Callable, AsyncGenerator, Union
from datetime import datetime
import logging

from .models import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    JSONRPCErrorCode,
    TaskSendParams,
    TaskSendSubscribeParams,
    TaskGetParams,
    TaskCancelParams,
    PushNotificationParams,
    TaskSendResult,
    TaskGetResult,
    TaskCancelResult,
    PushNotificationResult,
    TaskStatus,
    Message,
    MessagePart,
    Artifact,
)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

logger = logging.getLogger(__name__)


class JSONRPCHandler:
    """
    JSON-RPC 2.0 Request Handler

    Processes incoming JSON-RPC requests and routes them to appropriate methods.
    Supports both synchronous and streaming (SSE) responses.
    """

    # Supported methods
    SUPPORTED_METHODS = [
        "tasks/send",
        "tasks/sendSubscribe",
        "tasks/get",
        "tasks/cancel",
        "tasks/resubscribe",
        "tasks/pushNotification/set",
        "tasks/pushNotification/get",
    ]

    def __init__(self):
        """Initialize handler"""
        self._task_manager = None
        self._method_handlers: Dict[str, Callable] = {
            "tasks/send": self._handle_tasks_send,
            "tasks/sendSubscribe": self._handle_tasks_send_subscribe,
            "tasks/get": self._handle_tasks_get,
            "tasks/cancel": self._handle_tasks_cancel,
            "tasks/resubscribe": self._handle_tasks_resubscribe,
            "tasks/pushNotification/set": self._handle_push_notification_set,
            "tasks/pushNotification/get": self._handle_push_notification_get,
        }

    @property
    def task_manager(self):
        """Lazy load task manager"""
        if self._task_manager is None:
            from agent_platform.protocols.a2a.task_manager import get_a2a_task_manager
            self._task_manager = get_a2a_task_manager()
        return self._task_manager

    async def handle_request(
        self,
        request_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        api_key: Optional[str] = None
    ) -> Union[JSONRPCResponse, List[JSONRPCResponse], None]:
        """
        Handle incoming JSON-RPC request(s).

        Args:
            request_data: Single request or batch of requests
            api_key: Optional API key for authentication

        Returns:
            Response(s) or None for notifications
        """
        # Handle batch requests
        if isinstance(request_data, list):
            return await self._handle_batch(request_data, api_key)

        # Handle single request
        return await self._handle_single(request_data, api_key)

    async def _handle_batch(
        self,
        requests: List[Dict[str, Any]],
        api_key: Optional[str] = None
    ) -> List[JSONRPCResponse]:
        """Handle batch of requests"""
        if not requests:
            return [JSONRPCResponse.failure(JSONRPCError.invalid_request("Empty batch"))]

        responses = []
        for req_data in requests:
            response = await self._handle_single(req_data, api_key)
            if response is not None:  # Skip notifications
                responses.append(response)

        return responses

    async def _handle_single(
        self,
        request_data: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Optional[JSONRPCResponse]:
        """Handle single JSON-RPC request"""
        request_id = request_data.get("id")

        try:
            # Validate JSON-RPC version
            if request_data.get("jsonrpc") != "2.0":
                return JSONRPCResponse.failure(
                    JSONRPCError.invalid_request("Invalid JSON-RPC version"),
                    id=request_id
                )

            # Validate method
            method = request_data.get("method")
            if not method:
                return JSONRPCResponse.failure(
                    JSONRPCError.invalid_request("Missing method"),
                    id=request_id
                )

            # Check if method is supported
            if method not in self._method_handlers:
                return JSONRPCResponse.failure(
                    JSONRPCError.method_not_found(method),
                    id=request_id
                )

            # Parse request
            try:
                request = JSONRPCRequest(**request_data)
            except Exception as e:
                return JSONRPCResponse.failure(
                    JSONRPCError.invalid_request(str(e)),
                    id=request_id
                )

            # Check if this is a notification (no response needed)
            if request.is_notification():
                await self._method_handlers[method](request.params or {}, api_key)
                return None

            # Execute method
            handler = self._method_handlers[method]
            result = await handler(request.params or {}, api_key)

            return JSONRPCResponse.success(result, id=request.id)

        except Exception as e:
            logger.exception(f"Error handling JSON-RPC request: {e}")
            return JSONRPCResponse.failure(
                JSONRPCError.internal_error(str(e)),
                id=request_id
            )

    async def handle_streaming_request(
        self,
        request_data: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Handle streaming JSON-RPC request (for tasks/sendSubscribe).

        Yields SSE formatted events.
        """
        request_id = request_data.get("id")

        try:
            # Validate request
            if request_data.get("jsonrpc") != "2.0":
                yield self._format_sse_error(
                    JSONRPCError.invalid_request("Invalid JSON-RPC version"),
                    request_id
                )
                return

            method = request_data.get("method")
            if method != "tasks/sendSubscribe":
                yield self._format_sse_error(
                    JSONRPCError.invalid_request("Only tasks/sendSubscribe supports streaming"),
                    request_id
                )
                return

            params = request_data.get("params", {})

            # Create task and stream progress
            async for event in self._stream_task_execution(params, request_id, api_key):
                yield event

        except Exception as e:
            logger.exception(f"Error in streaming request: {e}")
            yield self._format_sse_error(JSONRPCError.internal_error(str(e)), request_id)

    def _format_sse_event(
        self,
        data: Dict[str, Any],
        event_type: str = "message",
        id: Optional[str] = None
    ) -> str:
        """Format data as SSE event"""
        lines = []
        if event_type:
            lines.append(f"event: {event_type}")
        if id:
            lines.append(f"id: {id}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")
        return "\n".join(lines) + "\n"

    def _format_sse_error(self, error: JSONRPCError, request_id: Optional[Union[str, int]]) -> str:
        """Format error as SSE event"""
        response = JSONRPCResponse.failure(error, id=request_id)
        return self._format_sse_event(response.model_dump(), event_type="error")

    # ============== Method Handlers ==============

    async def _handle_tasks_send(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/send method"""
        try:
            task_params = TaskSendParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}")

        # Extract message text
        message_text = ""
        for part in task_params.message.parts:
            if part.type == "text" and part.text:
                message_text += part.text

        # Create and execute task
        task = await self.task_manager.create_task(
            agent_id="default",
            messages=[{"role": task_params.message.role, "content": message_text}],
            metadata={
                "jsonrpc_task_id": task_params.id,
                "session_id": task_params.sessionId,
                **task_params.metadata
            }
        )

        # Execute task synchronously
        task = await self.task_manager.execute_task(task.task_id)

        # Build result
        return TaskSendResult(
            id=task_params.id,
            sessionId=task_params.sessionId,
            status=TaskStatus(
                state=task.status.value,
                message=Message.from_text(
                    "assistant",
                    task.output_message.content if task.output_message else ""
                ),
                timestamp=datetime.now().isoformat()
            ),
            artifacts=[]
        ).model_dump()

    async def _handle_tasks_send_subscribe(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/sendSubscribe method (non-streaming fallback)"""
        # For non-streaming context, behave like tasks/send
        return await self._handle_tasks_send(params, api_key)

    async def _stream_task_execution(
        self,
        params: Dict[str, Any],
        request_id: Optional[Union[str, int]],
        api_key: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream task execution progress"""
        try:
            task_params = TaskSendParams(**params)
        except Exception as e:
            yield self._format_sse_error(JSONRPCError.invalid_params(str(e)), request_id)
            return

        # Extract message text
        message_text = ""
        for part in task_params.message.parts:
            if part.type == "text" and part.text:
                message_text += part.text

        # Create task
        task = await self.task_manager.create_task(
            agent_id="default",
            messages=[{"role": task_params.message.role, "content": message_text}],
            metadata={
                "jsonrpc_task_id": task_params.id,
                "session_id": task_params.sessionId,
                **task_params.metadata
            }
        )

        # Send initial status
        yield self._format_sse_event({
            "jsonrpc": "2.0",
            "result": {
                "id": task_params.id,
                "status": {"state": "working", "timestamp": datetime.now().isoformat()}
            },
            "id": request_id
        }, event_type="status")

        # Stream task progress
        try:
            async for event in self.task_manager.stream_task_progress(task.task_id):
                event_data = event.get("data", {})
                status = event_data.get("status", "working")
                progress = event_data.get("progress", 0)
                output = event_data.get("output", "")

                yield self._format_sse_event({
                    "jsonrpc": "2.0",
                    "result": {
                        "id": task_params.id,
                        "status": {
                            "state": status,
                            "message": {"role": "assistant", "parts": [{"type": "text", "text": output}]} if output else None,
                            "timestamp": datetime.now().isoformat()
                        },
                        "progress": progress
                    },
                    "id": request_id
                }, event_type="progress")

                if status in ["completed", "failed", "cancelled"]:
                    break

        except Exception as e:
            yield self._format_sse_error(JSONRPCError.internal_error(str(e)), request_id)

        # Send final result
        final_task = await self.task_manager.get_task(task.task_id)
        yield self._format_sse_event({
            "jsonrpc": "2.0",
            "result": TaskSendResult(
                id=task_params.id,
                sessionId=task_params.sessionId,
                status=TaskStatus(
                    state=final_task.status.value if final_task else "failed",
                    message=Message.from_text(
                        "assistant",
                        final_task.output_message.content if final_task and final_task.output_message else ""
                    ),
                    timestamp=datetime.now().isoformat()
                ),
                artifacts=[]
            ).model_dump(),
            "id": request_id
        }, event_type="result")

    async def _handle_tasks_get(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/get method"""
        try:
            task_params = TaskGetParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}")

        # Find task by jsonrpc_task_id in metadata
        task = None
        for t in self.task_manager._tasks.values():
            if t.metadata.get("jsonrpc_task_id") == task_params.id:
                task = t
                break

        if not task:
            raise ValueError(f"Task not found: {task_params.id}")

        # Build history
        history = []
        for msg in task.input_messages:
            history.append(Message.from_text(msg.role, msg.content))
        if task.output_message:
            history.append(Message.from_text("assistant", task.output_message.content))

        # Apply history length limit
        if task_params.historyLength and len(history) > task_params.historyLength:
            history = history[-task_params.historyLength:]

        return TaskGetResult(
            id=task_params.id,
            sessionId=task.metadata.get("session_id"),
            status=TaskStatus(
                state=task.status.value,
                message=Message.from_text(
                    "assistant",
                    task.output_message.content if task.output_message else ""
                ),
                timestamp=task.completed_at.isoformat() if task.completed_at else datetime.now().isoformat()
            ),
            artifacts=[],
            history=history
        ).model_dump()

    async def _handle_tasks_cancel(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/cancel method"""
        try:
            task_params = TaskCancelParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}")

        # Find and cancel task
        task = None
        for t in self.task_manager._tasks.values():
            if t.metadata.get("jsonrpc_task_id") == task_params.id:
                task = t
                break

        if not task:
            raise ValueError(f"Task not found: {task_params.id}")

        await self.task_manager.cancel_task(task.task_id)

        return TaskCancelResult(
            id=task_params.id,
            status=TaskStatus(
                state="cancelled",
                timestamp=datetime.now().isoformat()
            )
        ).model_dump()

    async def _handle_tasks_resubscribe(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/resubscribe method"""
        # For non-streaming context, return current task status
        return await self._handle_tasks_get(params, api_key)

    async def _handle_push_notification_set(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/pushNotification/set method"""
        try:
            notification_params = PushNotificationParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}")

        # Find task
        task = None
        for t in self.task_manager._tasks.values():
            if t.metadata.get("jsonrpc_task_id") == notification_params.id:
                task = t
                break

        if not task:
            raise ValueError(f"Task not found: {notification_params.id}")

        # Update task webhook
        task.webhook_url = notification_params.pushNotificationConfig.url
        task.webhook_secret = notification_params.pushNotificationConfig.token

        return PushNotificationResult(
            id=notification_params.id,
            pushNotificationConfig=notification_params.pushNotificationConfig
        ).model_dump()

    async def _handle_push_notification_get(
        self,
        params: Dict[str, Any],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle tasks/pushNotification/get method"""
        task_id = params.get("id")
        if not task_id:
            raise ValueError("Missing task id")

        # Find task
        task = None
        for t in self.task_manager._tasks.values():
            if t.metadata.get("jsonrpc_task_id") == task_id:
                task = t
                break

        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if not task.webhook_url:
            raise ValueError("No push notification configured for this task")

        return {
            "id": task_id,
            "pushNotificationConfig": {
                "url": task.webhook_url,
                "token": task.webhook_secret
            }
        }


# Singleton instance
_handler: Optional[JSONRPCHandler] = None


def get_jsonrpc_handler() -> JSONRPCHandler:
    """Get the JSON-RPC handler instance"""
    global _handler
    if _handler is None:
        _handler = JSONRPCHandler()
    return _handler
