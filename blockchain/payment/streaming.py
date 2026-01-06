"""
Streaming Payment System

Provides continuous payment streaming for long-running tasks.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List, Callable
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class StreamStatus(str, Enum):
    """Payment stream status"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PaymentStream:
    """Payment stream record"""
    stream_id: str
    task_id: str
    sender_address: str
    recipient_address: str
    total_amount_wei: int
    streamed_amount_wei: int = 0
    rate_per_second_wei: int = 0
    status: StreamStatus = StreamStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    last_update: Optional[datetime] = None
    duration_seconds: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_amount_eth(self) -> Decimal:
        """Get total amount in ETH"""
        return Decimal(self.total_amount_wei) / Decimal(10**18)

    @property
    def streamed_amount_eth(self) -> Decimal:
        """Get streamed amount in ETH"""
        return Decimal(self.streamed_amount_wei) / Decimal(10**18)

    @property
    def remaining_amount_wei(self) -> int:
        """Get remaining amount in wei"""
        return self.total_amount_wei - self.streamed_amount_wei

    @property
    def progress_percent(self) -> float:
        """Get progress percentage"""
        if self.total_amount_wei == 0:
            return 0.0
        return (self.streamed_amount_wei / self.total_amount_wei) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stream_id": self.stream_id,
            "task_id": self.task_id,
            "sender_address": self.sender_address,
            "recipient_address": self.recipient_address,
            "total_amount_wei": str(self.total_amount_wei),
            "total_amount_eth": str(self.total_amount_eth),
            "streamed_amount_wei": str(self.streamed_amount_wei),
            "streamed_amount_eth": str(self.streamed_amount_eth),
            "remaining_wei": str(self.remaining_amount_wei),
            "rate_per_second_wei": str(self.rate_per_second_wei),
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat()
        }


class StreamingPayment:
    """
    Streaming Payment System

    Provides:
    - Continuous payment streaming
    - Real-time balance updates
    - Automatic stream completion
    - Stream pausing and resumption
    """

    def __init__(self, update_interval_seconds: int = 10):
        """
        Initialize streaming payment system.

        Args:
            update_interval_seconds: Balance update interval
        """
        self.update_interval = update_interval_seconds

        self._streams: Dict[str, PaymentStream] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []

    def _generate_stream_id(self, task_id: str) -> str:
        """Generate unique stream ID"""
        import hashlib
        hash_input = f"{task_id}_{datetime.now().isoformat()}"
        return f"stream_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

    async def start(self):
        """Start the streaming worker"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Streaming payment system started")

    async def stop(self):
        """Stop the streaming worker"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None
        logger.info("Streaming payment system stopped")

    def register_callback(self, callback: Callable):
        """Register a callback for stream events"""
        self._callbacks.append(callback)

    async def create_stream(
        self,
        task_id: str,
        sender_address: str,
        recipient_address: str,
        total_amount_wei: int,
        duration_seconds: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentStream:
        """
        Create a payment stream.

        Args:
            task_id: Associated task ID
            sender_address: Sender's address
            recipient_address: Recipient's address
            total_amount_wei: Total amount to stream
            duration_seconds: Stream duration
            metadata: Additional metadata

        Returns:
            PaymentStream
        """
        rate_per_second = total_amount_wei // duration_seconds if duration_seconds > 0 else 0

        stream = PaymentStream(
            stream_id=self._generate_stream_id(task_id),
            task_id=task_id,
            sender_address=sender_address,
            recipient_address=recipient_address,
            total_amount_wei=total_amount_wei,
            rate_per_second_wei=rate_per_second,
            duration_seconds=duration_seconds,
            metadata=metadata or {}
        )

        self._streams[stream.stream_id] = stream

        logger.info(f"Stream created: {stream.stream_id}, total: {stream.total_amount_eth} ETH")
        return stream

    async def start_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Start a payment stream.

        Args:
            stream_id: Stream ID

        Returns:
            Start result
        """
        stream = self._streams.get(stream_id)
        if not stream:
            return {"success": False, "error": "Stream not found"}

        if stream.status != StreamStatus.PENDING:
            return {"success": False, "error": "Stream already started or completed"}

        stream.status = StreamStatus.ACTIVE
        stream.start_time = datetime.now()
        stream.last_update = stream.start_time

        logger.info(f"Stream started: {stream_id}")

        return {
            "success": True,
            "stream": stream.to_dict()
        }

    async def pause_stream(self, stream_id: str) -> Dict[str, Any]:
        """Pause a stream"""
        stream = self._streams.get(stream_id)
        if not stream:
            return {"success": False, "error": "Stream not found"}

        if stream.status != StreamStatus.ACTIVE:
            return {"success": False, "error": "Stream not active"}

        # Update streamed amount before pausing
        await self._update_stream_balance(stream)

        stream.status = StreamStatus.PAUSED

        return {
            "success": True,
            "stream": stream.to_dict()
        }

    async def resume_stream(self, stream_id: str) -> Dict[str, Any]:
        """Resume a paused stream"""
        stream = self._streams.get(stream_id)
        if not stream:
            return {"success": False, "error": "Stream not found"}

        if stream.status != StreamStatus.PAUSED:
            return {"success": False, "error": "Stream not paused"}

        stream.status = StreamStatus.ACTIVE
        stream.last_update = datetime.now()

        return {
            "success": True,
            "stream": stream.to_dict()
        }

    async def cancel_stream(self, stream_id: str) -> Dict[str, Any]:
        """Cancel a stream"""
        stream = self._streams.get(stream_id)
        if not stream:
            return {"success": False, "error": "Stream not found"}

        if stream.status == StreamStatus.COMPLETED:
            return {"success": False, "error": "Stream already completed"}

        # Update final balance
        if stream.status == StreamStatus.ACTIVE:
            await self._update_stream_balance(stream)

        stream.status = StreamStatus.CANCELLED
        stream.end_time = datetime.now()

        logger.info(f"Stream cancelled: {stream_id}")

        return {
            "success": True,
            "stream": stream.to_dict(),
            "refund_amount_wei": str(stream.remaining_amount_wei)
        }

    async def complete_stream(self, stream_id: str) -> Dict[str, Any]:
        """Complete a stream"""
        stream = self._streams.get(stream_id)
        if not stream:
            return {"success": False, "error": "Stream not found"}

        # Final balance update
        stream.streamed_amount_wei = stream.total_amount_wei
        stream.status = StreamStatus.COMPLETED
        stream.end_time = datetime.now()

        logger.info(f"Stream completed: {stream_id}")

        # Notify callbacks
        await self._notify_callbacks(stream, "completed")

        return {
            "success": True,
            "stream": stream.to_dict()
        }

    async def get_stream(self, stream_id: str) -> Optional[PaymentStream]:
        """Get stream by ID"""
        stream = self._streams.get(stream_id)
        if stream and stream.status == StreamStatus.ACTIVE:
            await self._update_stream_balance(stream)
        return stream

    async def get_streams_for_task(self, task_id: str) -> List[PaymentStream]:
        """Get all streams for a task"""
        return [s for s in self._streams.values() if s.task_id == task_id]

    async def get_balance(self, stream_id: str) -> Dict[str, Any]:
        """Get current stream balance"""
        stream = self._streams.get(stream_id)
        if not stream:
            return {"success": False, "error": "Stream not found"}

        if stream.status == StreamStatus.ACTIVE:
            await self._update_stream_balance(stream)

        return {
            "success": True,
            "streamed_wei": str(stream.streamed_amount_wei),
            "remaining_wei": str(stream.remaining_amount_wei),
            "progress_percent": stream.progress_percent
        }

    async def _worker(self):
        """Background worker for updating stream balances"""
        logger.info("Streaming payment worker started")

        while self._running:
            try:
                # Update all active streams
                for stream in list(self._streams.values()):
                    if stream.status == StreamStatus.ACTIVE:
                        await self._update_stream_balance(stream)

                        # Check if stream should complete
                        if stream.streamed_amount_wei >= stream.total_amount_wei:
                            await self.complete_stream(stream.stream_id)

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Streaming worker error: {e}")
                await asyncio.sleep(self.update_interval)

        logger.info("Streaming payment worker stopped")

    async def _update_stream_balance(self, stream: PaymentStream):
        """Update stream balance based on elapsed time"""
        if not stream.last_update or stream.status != StreamStatus.ACTIVE:
            return

        now = datetime.now()
        elapsed = (now - stream.last_update).total_seconds()

        # Calculate streamed amount
        additional_amount = int(elapsed * stream.rate_per_second_wei)
        new_amount = min(
            stream.streamed_amount_wei + additional_amount,
            stream.total_amount_wei
        )

        stream.streamed_amount_wei = new_amount
        stream.last_update = now

        # Notify if significant change
        if additional_amount > 0:
            await self._notify_callbacks(stream, "update")

    async def _notify_callbacks(self, stream: PaymentStream, event: str):
        """Notify registered callbacks"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(stream, event)
                else:
                    callback(stream, event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        active_streams = [s for s in self._streams.values() if s.status == StreamStatus.ACTIVE]
        total_streaming = sum(s.total_amount_wei for s in active_streams)
        total_streamed = sum(s.streamed_amount_wei for s in active_streams)

        return {
            "total_streams": len(self._streams),
            "active_streams": len(active_streams),
            "total_streaming_wei": str(total_streaming),
            "total_streamed_wei": str(total_streamed),
            "running": self._running
        }


# Singleton instance
_streaming_payment: Optional[StreamingPayment] = None


def get_streaming_payment() -> StreamingPayment:
    """Get the streaming payment instance"""
    global _streaming_payment
    if _streaming_payment is None:
        _streaming_payment = StreamingPayment()
    return _streaming_payment
