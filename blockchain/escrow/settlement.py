"""
Settlement Engine

Automatic settlement for completed tasks.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blockchain.escrow.stake import StakeManager, get_stake_manager

logger = logging.getLogger(__name__)


class SettlementType(str, Enum):
    """Settlement types"""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"


class SettlementStatus(str, Enum):
    """Settlement status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SettlementJob:
    """Settlement job record"""
    job_id: str
    task_id: str
    settlement_type: SettlementType
    status: SettlementStatus = SettlementStatus.PENDING
    scheduled_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "job_id": self.job_id,
            "task_id": self.task_id,
            "settlement_type": self.settlement_type.value,
            "status": self.status.value,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "retries": self.retries,
            "created_at": self.created_at.isoformat()
        }


class SettlementEngine:
    """
    Settlement Engine

    Handles automatic settlement of escrow funds:
    - Immediate settlement on task completion
    - Delayed settlement with confirmation period
    - Scheduled batch settlements
    """

    def __init__(
        self,
        stake_manager: Optional[StakeManager] = None,
        default_delay_minutes: int = 15
    ):
        """
        Initialize settlement engine.

        Args:
            stake_manager: Stake manager instance
            default_delay_minutes: Default delay for delayed settlements
        """
        self.stake_manager = stake_manager or get_stake_manager()
        self.default_delay_minutes = default_delay_minutes

        self._jobs: Dict[str, SettlementJob] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []

    def _generate_job_id(self, task_id: str) -> str:
        """Generate unique job ID"""
        import hashlib
        hash_input = f"{task_id}_{datetime.now().isoformat()}"
        return f"settle_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

    async def start(self):
        """Start the settlement worker"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Settlement engine started")

    async def stop(self):
        """Stop the settlement worker"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None
        logger.info("Settlement engine stopped")

    def register_callback(self, callback: Callable):
        """Register a callback for settlement events"""
        self._callbacks.append(callback)

    async def settle_immediately(self, task_id: str) -> SettlementJob:
        """
        Settle a task immediately.

        Args:
            task_id: Task ID

        Returns:
            SettlementJob
        """
        job = SettlementJob(
            job_id=self._generate_job_id(task_id),
            task_id=task_id,
            settlement_type=SettlementType.IMMEDIATE
        )
        self._jobs[job.job_id] = job

        # Execute immediately
        await self._execute_settlement(job)

        return job

    async def settle_delayed(
        self,
        task_id: str,
        delay_minutes: Optional[int] = None
    ) -> SettlementJob:
        """
        Schedule a delayed settlement.

        Args:
            task_id: Task ID
            delay_minutes: Delay in minutes (uses default if not specified)

        Returns:
            SettlementJob
        """
        delay = delay_minutes or self.default_delay_minutes
        scheduled_at = datetime.now() + timedelta(minutes=delay)

        job = SettlementJob(
            job_id=self._generate_job_id(task_id),
            task_id=task_id,
            settlement_type=SettlementType.DELAYED,
            scheduled_at=scheduled_at
        )
        self._jobs[job.job_id] = job

        logger.info(f"Settlement scheduled: {job.job_id} at {scheduled_at}")
        return job

    async def cancel_settlement(self, job_id: str) -> bool:
        """
        Cancel a pending settlement.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status == SettlementStatus.PENDING:
            job.status = SettlementStatus.FAILED
            job.result = {"cancelled": True}

            # Refund stake
            await self.stake_manager.refund_stake(job.task_id)

            return True

        return False

    async def get_job(self, job_id: str) -> Optional[SettlementJob]:
        """Get settlement job by ID"""
        return self._jobs.get(job_id)

    async def get_jobs_for_task(self, task_id: str) -> List[SettlementJob]:
        """Get all settlement jobs for a task"""
        return [j for j in self._jobs.values() if j.task_id == task_id]

    async def _worker(self):
        """Background worker for processing scheduled settlements"""
        logger.info("Settlement worker started")

        while self._running:
            try:
                # Check for due settlements
                now = datetime.now()
                due_jobs = [
                    job for job in self._jobs.values()
                    if job.status == SettlementStatus.PENDING
                    and job.scheduled_at
                    and job.scheduled_at <= now
                ]

                for job in due_jobs:
                    await self._execute_settlement(job)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Settlement worker error: {e}")
                await asyncio.sleep(60)

        logger.info("Settlement worker stopped")

    async def _execute_settlement(self, job: SettlementJob):
        """Execute a settlement job"""
        job.status = SettlementStatus.PROCESSING
        job.executed_at = datetime.now()

        try:
            # Release stake
            result = await self.stake_manager.release_stake(job.task_id)

            if result.get("success"):
                job.status = SettlementStatus.COMPLETED
                job.result = result
                logger.info(f"Settlement completed: {job.job_id}")

                # Notify callbacks
                await self._notify_callbacks(job)
            else:
                # Retry if possible
                job.retries += 1
                if job.retries < job.max_retries:
                    job.status = SettlementStatus.PENDING
                    job.scheduled_at = datetime.now() + timedelta(minutes=5)
                    logger.warning(f"Settlement retry scheduled: {job.job_id}")
                else:
                    job.status = SettlementStatus.FAILED
                    job.result = result
                    logger.error(f"Settlement failed: {job.job_id}")

        except Exception as e:
            job.retries += 1
            if job.retries < job.max_retries:
                job.status = SettlementStatus.PENDING
                job.scheduled_at = datetime.now() + timedelta(minutes=5)
            else:
                job.status = SettlementStatus.FAILED
                job.result = {"error": str(e)}
            logger.error(f"Settlement error: {job.job_id} - {e}")

    async def _notify_callbacks(self, job: SettlementJob):
        """Notify registered callbacks"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get settlement statistics"""
        status_counts = {}
        for job in self._jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jobs": len(self._jobs),
            "status_counts": status_counts,
            "running": self._running
        }


# Singleton instance
_settlement_engine: Optional[SettlementEngine] = None


def get_settlement_engine() -> SettlementEngine:
    """Get the settlement engine instance"""
    global _settlement_engine
    if _settlement_engine is None:
        _settlement_engine = SettlementEngine()
    return _settlement_engine
