"""
Centralized database write queue for SQLite lock prevention.

All database write operations (add/update/delete/upsert) are serialized
through a single background daemon thread to eliminate concurrent write
contention on the SQLite database file.

Read operations are NOT affected and can still run concurrently via
SQLite WAL mode.
"""

import queue
import threading
import concurrent.futures
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

_logger = logging.getLogger(__name__)


@dataclass
class _WriteOp:
    """Internal representation of a queued write operation."""
    func: Callable
    future: concurrent.futures.Future = field(default_factory=concurrent.futures.Future)
    description: str = ""


class DbWriteQueue:
    """
    Singleton write queue that serializes ALL database write operations
    through a single background thread to prevent SQLite lock contention.

    Usage (sync caller):
        result = DbWriteQueue.get_instance().submit_write(lambda session: ..., description="add_record")

    Usage (async caller):
        result = await DbWriteQueue.get_instance().submit_write_async(lambda session: ..., description="add_record")
    """

    _instance: Optional["DbWriteQueue"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._queue: queue.Queue[Optional[_WriteOp]] = queue.Queue()
        self._session = None
        self._started = False
        self._shutting_down = False
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="db-write-queue-worker",
            daemon=True,
        )
        self._worker.start()
        self._started = True
        _logger.info("[DbWriteQueue] Worker thread started")

    @classmethod
    def get_instance(cls) -> "DbWriteQueue":
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Worker thread
    # ------------------------------------------------------------------

    def _get_session(self):
        """Lazy-create the worker-owned SQLAlchemy session."""
        if self._session is None:
            from db.DBFactory import Session
            self._session = Session()
            _logger.info("[DbWriteQueue] Worker session created")
        return self._session

    def _worker_loop(self):
        """Process write operations sequentially (runs in daemon thread)."""
        _logger.info("[DbWriteQueue] Worker loop running")
        while True:
            op: Optional[_WriteOp] = None
            try:
                op = self._queue.get()
                if op is None:
                    # Poison pill: shutdown signal
                    _logger.info("[DbWriteQueue] Received shutdown signal")
                    break

                session = self._get_session()
                try:
                    result = op.func(session)
                    session.commit()
                    op.future.set_result(result)
                except Exception as exc:
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    # If session is broken, recreate it
                    try:
                        session.close()
                    except Exception:
                        pass
                    self._session = None
                    if not op.future.done():
                        op.future.set_exception(exc)
                    desc = op.description or "unknown"
                    _logger.error(
                        "[DbWriteQueue] Write operation failed (%s): %s",
                        desc, exc, exc_info=True,
                    )
            except Exception as outer_exc:
                _logger.error(
                    "[DbWriteQueue] Unexpected error in worker loop: %s",
                    outer_exc, exc_info=True,
                )
                if op is not None and not op.future.done():
                    op.future.set_exception(outer_exc)
            finally:
                try:
                    self._queue.task_done()
                except ValueError:
                    pass

        # Cleanup on shutdown
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        _logger.info("[DbWriteQueue] Worker loop exited")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit_write(self, func: Callable, timeout: float = 30.0,
                     description: str = "") -> Any:
        """
        Submit a write operation and block until it completes.

        Args:
            func: Callable that receives a SQLAlchemy Session and performs
                  write operations. The session.commit() is handled by the
                  worker — do NOT call commit() inside func.
            timeout: Maximum seconds to wait for the result.
            description: Human-readable label for logging.

        Returns:
            Whatever ``func(session)`` returns.
        """
        if self._shutting_down:
            raise RuntimeError("[DbWriteQueue] Queue is shutting down")

        op = _WriteOp(func=func, description=description)
        self._queue.put(op)
        return op.future.result(timeout=timeout)

    async def submit_write_async(self, func: Callable, timeout: float = 30.0,
                                 description: str = "") -> Any:
        """
        Submit a write operation from an async context and await the result.

        Same semantics as submit_write but non-blocking for the event loop.
        """
        if self._shutting_down:
            raise RuntimeError("[DbWriteQueue] Queue is shutting down")

        op = _WriteOp(func=func, description=description)
        self._queue.put(op)
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            asyncio.wrap_future(op.future, loop=loop),
            timeout=timeout,
        )

    def queue_size(self) -> int:
        """Return the current number of pending write operations."""
        return self._queue.qsize()

    def shutdown(self, wait: bool = True, timeout: float = 10.0):
        """
        Gracefully shut down the worker thread.

        Args:
            wait: If True, block until the queue is drained.
            timeout: Max seconds to wait for the worker to finish.
        """
        self._shutting_down = True
        if wait:
            try:
                self._queue.join()
            except Exception:
                pass
        # Send poison pill
        self._queue.put(None)
        self._worker.join(timeout=timeout)
        _logger.info("[DbWriteQueue] Shutdown complete")


def db_write(func: Callable, timeout: float = 30.0, description: str = "") -> Any:
    """Convenience shortcut for sync callers."""
    return DbWriteQueue.get_instance().submit_write(func, timeout=timeout, description=description)


async def db_write_async(func: Callable, timeout: float = 30.0, description: str = "") -> Any:
    """Convenience shortcut for async callers."""
    return await DbWriteQueue.get_instance().submit_write_async(func, timeout=timeout, description=description)
