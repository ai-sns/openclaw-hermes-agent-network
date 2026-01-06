"""
Async Task Queue

Provides in-memory task queue for async processing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedTask:
    """Task data structure"""
    task_id: str
    agent_id: str
    task_type: str
    input_data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    webhook_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None


class TaskQueue:
    """
    Async Task Queue

    In-memory task queue with:
    - Priority support
    - Async execution
    - Webhook callbacks
    - Progress tracking
    """

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize task queue.

        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, QueuedTask] = {}
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running_count = 0
        self._lock = asyncio.Lock()
        self._workers: List[asyncio.Task] = []
        self._running = False

    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        return f"task_{uuid.uuid4().hex[:16]}"

    async def start(self):
        """Start the task queue workers"""
        if self._running:
            return

        self._running = True
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        logger.info(f"Started {self.max_concurrent} task queue workers")

    async def stop(self):
        """Stop the task queue workers"""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()
        logger.info("Task queue stopped")

    async def enqueue(
        self,
        agent_id: str,
        task_type: str,
        input_data: Dict[str, Any],
        priority: int = 0,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueuedTask:
        """
        Add a task to the queue.

        Args:
            agent_id: Target agent ID
            task_type: Type of task
            input_data: Task input data
            priority: Task priority (higher = more urgent)
            webhook_url: Webhook URL for completion callback
            metadata: Additional metadata

        Returns:
            Created QueuedTask
        """
        task = QueuedTask(
            task_id=self._generate_task_id(),
            agent_id=agent_id,
            task_type=task_type,
            input_data=input_data,
            priority=priority,
            webhook_url=webhook_url,
            metadata=metadata or {}
        )

        self.tasks[task.task_id] = task

        # Add to priority queue (negative priority for max-heap behavior)
        await self.queue.put((-priority, task.created_at, task.task_id))

        logger.info(f"Task enqueued: {task.task_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True

        return False

    async def _worker(self, worker_id: str):
        """Worker coroutine that processes tasks"""
        logger.info(f"Worker {worker_id} started")

        while self._running:
            try:
                # Get task from queue with timeout
                try:
                    _, _, task_id = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue

                # Execute task
                await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: QueuedTask):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # Get agent and execute
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

            # Execute based on task type
            if task.task_type == "chat":
                message = task.input_data.get("message", "")
                messages = task.input_data.get("messages", [])
                response = agent.ask_it(message, messages, None, task.task_id)
                task.output_data = {"response": response}
            else:
                # Generic task execution
                task.output_data = await self._execute_generic_task(agent, task)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.execution_time_ms = int(
                (task.completed_at - task.started_at).total_seconds() * 1000
            )

            logger.info(f"Task completed: {task.task_id}")

            # Send webhook
            if task.webhook_url:
                await self._send_webhook(task)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task failed: {task.task_id} - {e}")

            # Send failure webhook
            if task.webhook_url:
                await self._send_webhook(task)

    async def _execute_generic_task(
        self,
        agent,
        task: QueuedTask
    ) -> Dict[str, Any]:
        """Execute a generic task"""
        # Override this for custom task types
        return {"status": "completed", "task_type": task.task_type}

    async def _send_webhook(self, task: QueuedTask):
        """Send webhook for task completion"""
        from agent_platform.gateway.handlers.webhook import get_webhook_dispatcher
        from agent_platform.gateway.schemas.requests import WebhookPayload, TaskStatus as SchemaTaskStatus

        try:
            dispatcher = get_webhook_dispatcher()

            status_map = {
                TaskStatus.COMPLETED: SchemaTaskStatus.COMPLETED,
                TaskStatus.FAILED: SchemaTaskStatus.FAILED,
                TaskStatus.CANCELLED: SchemaTaskStatus.CANCELLED
            }

            payload = WebhookPayload(
                event_type=f"task.{task.status.value}",
                task_id=task.task_id,
                status=status_map.get(task.status, SchemaTaskStatus.COMPLETED),
                output_data=task.output_data,
                error=task.error_message
            )

            await dispatcher.send_webhook(task.webhook_url, payload)
        except Exception as e:
            logger.error(f"Webhook failed for task {task.task_id}: {e}")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        status_counts = {}
        for task in self.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "queue_size": self.queue.qsize(),
            "status_counts": status_counts
        }


# Singleton instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get the task queue instance"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
