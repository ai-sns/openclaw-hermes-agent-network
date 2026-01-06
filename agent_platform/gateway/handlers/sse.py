"""
SSE (Server-Sent Events) Handlers

Provides streaming responses using SSE.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import asyncio
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agent_platform.gateway.middleware.auth import get_current_api_key, get_optional_api_key
from agent_platform.security.api_key import APIKeyInfo


sse_router = APIRouter(prefix="/api/v1", tags=["SSE Streaming"])


class SSEStreamHandler:
    """
    Server-Sent Events Stream Handler

    Provides streaming responses for:
    - Chat responses (token by token)
    - Task progress updates
    - Real-time notifications
    """

    def __init__(self):
        self.active_streams = {}

    async def format_sse_message(
        self,
        data: dict,
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None
    ) -> str:
        """Format a message as SSE"""
        message = ""

        if id:
            message += f"id: {id}\n"
        if event:
            message += f"event: {event}\n"
        if retry:
            message += f"retry: {retry}\n"

        # Data must be JSON
        message += f"data: {json.dumps(data)}\n\n"

        return message

    async def stream_chat_response(
        self,
        agent_id: str,
        message: str,
        session_id: Optional[str] = None,
        history: Optional[list] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from agent.

        Yields SSE formatted messages.
        """
        from globals import global_agent_list
        from db.DBFactory import query_AgentCfg
        from agent_platform.session import get_session_manager

        try:
            # Get or create session
            session_manager = get_session_manager()
            if session_id:
                session = session_manager.get_session(session_id)
            else:
                session = session_manager.create_session(agent_id=agent_id)
                session_id = session.session_id

            # Send session info first
            yield await self.format_sse_message(
                {"type": "session", "session_id": session_id},
                event="session"
            )

            # Get agent
            agent_key = f"agent_{agent_id}"
            if agent_key not in global_agent_list:
                cfg = query_AgentCfg(user_id=agent_id)
                if not cfg:
                    yield await self.format_sse_message(
                        {"type": "error", "error": "Agent not found"},
                        event="error"
                    )
                    return

                from Agent import Agent
                agent = Agent(cfg)
                global_agent_list[agent_key] = agent
            else:
                agent = global_agent_list[agent_key]

            # Build messages
            messages = history or session.messages.copy() if session else []
            messages.append({"role": "user", "content": message})

            # Try to stream from agent
            # Note: This depends on the agent supporting streaming
            try:
                # Check if agent has stream method
                if hasattr(agent, 'stream_chat'):
                    async for chunk in agent.stream_chat(message, messages):
                        yield await self.format_sse_message(
                            {"type": "content", "content": chunk},
                            event="message"
                        )
                else:
                    # Fall back to non-streaming
                    response = agent.ask_it(message, messages, None, session_id)

                    # Simulate streaming by chunking
                    chunk_size = 20
                    for i in range(0, len(response), chunk_size):
                        chunk = response[i:i + chunk_size]
                        yield await self.format_sse_message(
                            {"type": "content", "content": chunk},
                            event="message"
                        )
                        await asyncio.sleep(0.05)  # Small delay for effect

                    # Save to session
                    session_manager.add_message(session_id, {
                        "role": "assistant",
                        "content": response
                    })

            except Exception as e:
                yield await self.format_sse_message(
                    {"type": "error", "error": str(e)},
                    event="error"
                )
                return

            # Send done event
            yield await self.format_sse_message(
                {"type": "done", "session_id": session_id},
                event="done"
            )

        except Exception as e:
            yield await self.format_sse_message(
                {"type": "error", "error": str(e)},
                event="error"
            )

    async def stream_task_progress(
        self,
        task_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream task progress updates.

        Yields SSE formatted messages with task status.
        """
        from agent_platform.async_tasks import get_task_queue

        task_queue = get_task_queue()
        last_status = None

        try:
            while True:
                task = await task_queue.get_task(task_id)

                if not task:
                    yield await self.format_sse_message(
                        {"type": "error", "error": "Task not found"},
                        event="error"
                    )
                    return

                # Send update if status changed
                if task.status != last_status:
                    last_status = task.status

                    yield await self.format_sse_message(
                        {
                            "type": "status",
                            "task_id": task.task_id,
                            "status": task.status.value if hasattr(task.status, 'value') else task.status,
                            "progress": task.progress if hasattr(task, 'progress') else None
                        },
                        event="status"
                    )

                # Check if completed
                if task.status in ["completed", "failed", "cancelled"]:
                    # Send final result
                    yield await self.format_sse_message(
                        {
                            "type": "result",
                            "task_id": task.task_id,
                            "status": task.status.value if hasattr(task.status, 'value') else task.status,
                            "output": task.output_data,
                            "error": task.error_message
                        },
                        event="done"
                    )
                    return

                # Poll interval
                await asyncio.sleep(1)

        except Exception as e:
            yield await self.format_sse_message(
                {"type": "error", "error": str(e)},
                event="error"
            )


# Create handler instance
_sse_handler = SSEStreamHandler()


def get_sse_handler() -> SSEStreamHandler:
    """Get SSE handler instance"""
    return _sse_handler


@sse_router.get("/chat/stream")
async def stream_chat(
    request: Request,
    agent_id: str = Query(..., description="Agent ID"),
    message: str = Query(..., description="User message"),
    session_id: Optional[str] = Query(None, description="Session ID"),
    api_key: Optional[str] = Query(None, description="API Key (for SSE)"),
    key_info: Optional[APIKeyInfo] = Depends(get_optional_api_key)
):
    """
    Stream chat response using SSE.

    Example usage with JavaScript:
    ```javascript
    const eventSource = new EventSource(
        '/api/v1/chat/stream?agent_id=agent_001&message=Hello&api_key=your_key'
    );

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'content') {
            console.log(data.content);
        }
    };

    eventSource.addEventListener('done', () => {
        eventSource.close();
    });
    ```
    """
    # Validate API key (from query param for SSE)
    if not key_info and api_key:
        from agent_platform.security.api_key import get_api_key_manager
        api_key_manager = get_api_key_manager()
        key_info = api_key_manager.validate_key(api_key)

    if not key_info:
        raise HTTPException(status_code=401, detail="API key required")

    handler = get_sse_handler()

    return StreamingResponse(
        handler.stream_chat_response(agent_id, message, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@sse_router.get("/tasks/{task_id}/stream")
async def stream_task_progress(
    task_id: str,
    api_key: Optional[str] = Query(None, description="API Key (for SSE)"),
    key_info: Optional[APIKeyInfo] = Depends(get_optional_api_key)
):
    """
    Stream task progress using SSE.

    Events:
    - status: Task status update
    - done: Task completed/failed
    - error: Error occurred
    """
    # Validate API key
    if not key_info and api_key:
        from agent_platform.security.api_key import get_api_key_manager
        api_key_manager = get_api_key_manager()
        key_info = api_key_manager.validate_key(api_key)

    if not key_info:
        raise HTTPException(status_code=401, detail="API key required")

    handler = get_sse_handler()

    return StreamingResponse(
        handler.stream_task_progress(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
