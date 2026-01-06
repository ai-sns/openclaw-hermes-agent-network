"""
A2A Task Manager

Manages task lifecycle for Agent-to-Agent (A2A) protocol.
Supports async task execution, streaming, and status tracking.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


logger = logging.getLogger(__name__)


class A2ATaskStatus(str, Enum):
    """A2A Task status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class A2ATaskType(str, Enum):
    """A2A Task type enumeration"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    TOOL_CALL = "tool_call"
    MULTI_STEP = "multi_step"


@dataclass
class A2AMessage:
    """A2A Message structure"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class A2ATask:
    """A2A Task data structure"""
    task_id: str
    agent_id: str
    task_type: A2ATaskType
    status: A2ATaskStatus = A2ATaskStatus.PENDING

    # Input/Output
    input_messages: List[A2AMessage] = field(default_factory=list)
    output_message: Optional[A2AMessage] = None
    output_chunks: List[str] = field(default_factory=list)

    # Caller information
    caller_agent_id: Optional[str] = None
    caller_task_id: Optional[str] = None

    # Webhook
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    progress: float = 0.0

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "input_messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "name": m.name,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in self.input_messages
            ],
            "output_message": {
                "role": self.output_message.role,
                "content": self.output_message.content,
                "timestamp": self.output_message.timestamp.isoformat()
            } if self.output_message else None,
            "caller_agent_id": self.caller_agent_id,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "metadata": self.metadata
        }


class A2ATaskManager:
    """
    A2A Task Manager

    Manages the complete lifecycle of A2A tasks:
    - Task creation and queuing
    - Async execution with progress tracking
    - Streaming support
    - Webhook notifications
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize task manager.

        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, A2ATask] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running_count = 0
        self._lock = asyncio.Lock()
        self._stream_queues: Dict[str, asyncio.Queue] = {}
        self._workers: List[asyncio.Task] = []
        self._running = False

    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        return f"a2a_{uuid.uuid4().hex[:16]}"

    async def start(self):
        """Start task workers"""
        if self._running:
            return

        self._running = True
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"a2a-worker-{i}"))
            self._workers.append(worker)
        logger.info(f"Started {self.max_concurrent} A2A task workers")

    async def stop(self):
        """Stop task workers"""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()
        logger.info("A2A task manager stopped")

    async def create_task(
        self,
        agent_id: str,
        messages: List[Dict[str, str]],
        task_type: A2ATaskType = A2ATaskType.CHAT,
        caller_agent_id: Optional[str] = None,
        caller_task_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300
    ) -> A2ATask:
        """
        Create a new A2A task.

        Args:
            agent_id: Target agent ID
            messages: List of input messages
            task_type: Type of task
            caller_agent_id: Calling agent ID (for A2A calls)
            caller_task_id: Calling task ID
            webhook_url: Webhook URL for completion
            webhook_secret: Webhook signing secret
            metadata: Additional metadata
            timeout_seconds: Task timeout

        Returns:
            Created A2ATask
        """
        # Convert messages
        input_messages = [
            A2AMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                name=m.get("name")
            )
            for m in messages
        ]

        task = A2ATask(
            task_id=self._generate_task_id(),
            agent_id=agent_id,
            task_type=task_type,
            input_messages=input_messages,
            caller_agent_id=caller_agent_id,
            caller_task_id=caller_task_id,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            metadata=metadata or {},
            timeout_seconds=timeout_seconds
        )

        self._tasks[task.task_id] = task

        # Add to queue
        await self._task_queue.put(task.task_id)
        task.status = A2ATaskStatus.QUEUED

        logger.info(f"A2A task created: {task.task_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[A2ATask]:
        """Get task by ID"""
        return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending/queued task"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in [A2ATaskStatus.PENDING, A2ATaskStatus.QUEUED]:
            task.status = A2ATaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return True

        return False

    async def execute_task(self, task_id: str) -> A2ATask:
        """
        Execute a task immediately (synchronous execution).

        Args:
            task_id: Task ID

        Returns:
            Updated A2ATask
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        await self._execute_task(task)
        return task

    async def stream_task_progress(
        self,
        task_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream task progress via SSE.

        Args:
            task_id: Task ID

        Yields:
            Progress events
        """
        task = self._tasks.get(task_id)
        if not task:
            yield {"event": "error", "data": {"message": "Task not found"}}
            return

        # Create stream queue
        stream_queue: asyncio.Queue = asyncio.Queue()
        self._stream_queues[task_id] = stream_queue

        try:
            # Send initial status
            yield {
                "event": "status",
                "data": {
                    "task_id": task_id,
                    "status": task.status.value,
                    "progress": task.progress
                }
            }

            # Stream updates
            while task.status not in [
                A2ATaskStatus.COMPLETED,
                A2ATaskStatus.FAILED,
                A2ATaskStatus.CANCELLED,
                A2ATaskStatus.TIMEOUT
            ]:
                try:
                    event = await asyncio.wait_for(
                        stream_queue.get(),
                        timeout=1.0
                    )
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": {"timestamp": datetime.now().isoformat()}
                    }

            # Send final result
            yield {
                "event": "complete",
                "data": task.to_dict()
            }

        finally:
            # Cleanup stream queue
            if task_id in self._stream_queues:
                del self._stream_queues[task_id]

    async def _worker(self, worker_id: str):
        """Worker coroutine for processing tasks"""
        logger.info(f"A2A worker {worker_id} started")

        while self._running:
            try:
                # Get task from queue
                try:
                    task_id = await asyncio.wait_for(
                        self._task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                task = self._tasks.get(task_id)
                if not task or task.status != A2ATaskStatus.QUEUED:
                    continue

                # Execute task
                await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"A2A worker {worker_id} error: {e}")

        logger.info(f"A2A worker {worker_id} stopped")

    async def _execute_task(self, task: A2ATask):
        """Execute a single A2A task"""
        task.status = A2ATaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # Notify stream listeners
            await self._send_stream_event(task.task_id, {
                "event": "started",
                "data": {"task_id": task.task_id}
            })

            # Get agent
            from globals import global_agent_list
            from db.DBFactory import query_AgentCfg

            agent_key = f"agent_{task.agent_id}"
            if agent_key not in global_agent_list:
                cfg = query_AgentCfg(user_id=task.agent_id)
                if not cfg:
                    raise ValueError(f"Agent not found: {task.agent_id}")

                from Agent import Agent
                agent = Agent(cfg)
                global_agent_list[agent_key] = agent
            else:
                agent = global_agent_list[agent_key]

            # Build message
            message = ""
            messages = []
            for msg in task.input_messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
                if msg.role == "user":
                    message = msg.content

            # Execute based on task type
            if task.task_type == A2ATaskType.CHAT:
                # Check if agent supports streaming
                if hasattr(agent, 'stream_chat') and task.task_id in self._stream_queues:
                    # Streaming execution
                    task.status = A2ATaskStatus.STREAMING
                    response_text = ""

                    async for chunk in agent.stream_chat(message, messages):
                        response_text += chunk
                        task.output_chunks.append(chunk)
                        task.progress = min(0.9, task.progress + 0.1)

                        await self._send_stream_event(task.task_id, {
                            "event": "chunk",
                            "data": {"content": chunk}
                        })

                    task.output_message = A2AMessage(
                        role="assistant",
                        content=response_text
                    )
                else:
                    # Synchronous execution
                    response = agent.ask_it(message, messages, None, task.task_id)
                    task.output_message = A2AMessage(
                        role="assistant",
                        content=response
                    )

            elif task.task_type == A2ATaskType.TOOL_CALL:
                # Tool call execution
                tool_name = task.metadata.get("tool_name")
                tool_params = task.metadata.get("tool_params", {})

                if hasattr(agent, 'execute_tool'):
                    result = await agent.execute_tool(tool_name, tool_params)
                    task.output_message = A2AMessage(
                        role="tool",
                        content=json.dumps(result),
                        name=tool_name
                    )
                else:
                    raise ValueError("Agent does not support tool execution")

            else:
                # Generic execution
                response = agent.ask_it(message, messages, None, task.task_id)
                task.output_message = A2AMessage(
                    role="assistant",
                    content=response
                )

            task.status = A2ATaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 1.0

            logger.info(f"A2A task completed: {task.task_id}")

            # Send webhook
            if task.webhook_url:
                await self._send_webhook(task)

        except asyncio.TimeoutError:
            task.status = A2ATaskStatus.TIMEOUT
            task.error_message = "Task execution timed out"
            task.completed_at = datetime.now()
            logger.warning(f"A2A task timeout: {task.task_id}")

        except Exception as e:
            task.status = A2ATaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            logger.error(f"A2A task failed: {task.task_id} - {e}")

            # Send failure webhook
            if task.webhook_url:
                await self._send_webhook(task)

    async def _send_stream_event(self, task_id: str, event: Dict[str, Any]):
        """Send event to stream listeners"""
        if task_id in self._stream_queues:
            await self._stream_queues[task_id].put(event)

    async def _send_webhook(self, task: A2ATask):
        """Send webhook notification"""
        from agent_platform.gateway.handlers.webhook import get_webhook_dispatcher

        try:
            dispatcher = get_webhook_dispatcher()

            payload = {
                "event": f"a2a.task.{task.status.value}",
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "status": task.status.value,
                "output": task.output_message.content if task.output_message else None,
                "error": task.error_message,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }

            await dispatcher.send_webhook_raw(
                url=task.webhook_url,
                payload=payload,
                secret=task.webhook_secret
            )
        except Exception as e:
            logger.error(f"A2A webhook failed for task {task.task_id}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        status_counts = {}
        for task in self._tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "queue_size": self._task_queue.qsize(),
            "active_streams": len(self._stream_queues),
            "status_counts": status_counts
        }


# Singleton instance
_task_manager: Optional[A2ATaskManager] = None


def get_a2a_task_manager() -> A2ATaskManager:
    """Get the A2A task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = A2ATaskManager()
    return _task_manager
