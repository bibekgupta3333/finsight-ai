"""
Async task queue implementation using asyncio.Queue.

Provides a high-performance, in-memory task queue for async operations.
For production, consider Redis-based queue (Celery) or cloud-native solutions.
"""

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult(BaseModel):
    """Task result model."""

    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True


class AsyncTaskQueue:
    """
    Async task queue with backpressure handling and rate limiting.

    Features:
    - Bounded queue size (backpressure)
    - Worker pool management
    - Task status tracking
    - Graceful shutdown
    - Rate limiting per client
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_workers: int = 10,
        rate_limit_per_minute: int = 100,
    ):
        """
        Initialize async task queue.

        Args:
            max_size: Maximum queue size (backpressure threshold)
            max_workers: Maximum number of concurrent workers
            rate_limit_per_minute: Rate limit per client per minute
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.max_workers = max_workers
        self.rate_limit_per_minute = rate_limit_per_minute

        # Task tracking
        self.tasks: Dict[str, TaskResult] = {}
        self.workers: list[asyncio.Task] = []

        # Rate limiting (client_id -> list of timestamps)
        self.rate_limiter: Dict[str, list[datetime]] = defaultdict(list)

        # Shutdown event
        self.shutdown_event = asyncio.Event()

        # Lock for thread-safe operations
        self.lock = asyncio.Lock()

        logger.info(
            f"Initialized AsyncTaskQueue: "
            f"max_size={max_size}, max_workers={max_workers}, "
            f"rate_limit={rate_limit_per_minute}/min"
        )

    async def start_workers(self) -> None:
        """Start worker pool."""
        logger.info(f"Starting {self.max_workers} worker(s)...")

        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(worker_id=i), name=f"worker-{i}")
            self.workers.append(worker)

        logger.info(f"✓ {self.max_workers} worker(s) started")

    async def stop_workers(self, timeout: float = 30.0) -> None:
        """
        Stop worker pool gracefully.

        Args:
            timeout: Shutdown timeout in seconds
        """
        logger.info("Stopping workers gracefully...")
        self.shutdown_event.set()

        # Wait for queue to be processed
        try:
            await asyncio.wait_for(self.queue.join(), timeout=timeout)
            logger.info("✓ All tasks processed")
        except asyncio.TimeoutError:
            logger.warning(f"Shutdown timeout after {timeout}s, forcing stop")

        # Cancel workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("✓ Workers stopped")

    async def _worker(self, worker_id: int) -> None:
        """
        Worker coroutine that processes tasks from the queue.

        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started")

        while not self.shutdown_event.is_set():
            try:
                # Get task with timeout
                task_id, func, args, kwargs = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                # Update task status
                async with self.lock:
                    if task_id in self.tasks:
                        self.tasks[task_id].status = TaskStatus.RUNNING
                        self.tasks[task_id].started_at = datetime.utcnow()

                logger.debug(f"Worker {worker_id} processing task {task_id}")

                try:
                    # Execute task
                    result = await func(*args, **kwargs)

                    # Update task status - success
                    async with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].status = TaskStatus.COMPLETED
                            self.tasks[task_id].result = result
                            self.tasks[task_id].completed_at = datetime.utcnow()

                    logger.debug(f"✓ Task {task_id} completed")

                except Exception as e:
                    # Update task status - failure
                    async with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].status = TaskStatus.FAILED
                            self.tasks[task_id].error = str(e)
                            self.tasks[task_id].completed_at = datetime.utcnow()

                    logger.error(f"✗ Task {task_id} failed: {e}")

                finally:
                    self.queue.task_done()

            except asyncio.TimeoutError:
                # No task available, continue
                continue
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {e}")

        logger.info(f"Worker {worker_id} stopped")

    async def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if client has exceeded rate limit.

        Args:
            client_id: Client identifier

        Returns:
            True if within rate limit, False otherwise
        """
        async with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=1)

            # Clean old timestamps
            self.rate_limiter[client_id] = [
                ts for ts in self.rate_limiter[client_id] if ts > cutoff
            ]

            # Check limit
            if len(self.rate_limiter[client_id]) >= self.rate_limit_per_minute:
                return False

            # Add current timestamp
            self.rate_limiter[client_id].append(now)
            return True

    async def submit_task(
        self,
        func: Callable,
        *args,
        client_id: str = "default",
        **kwargs,
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            client_id: Client identifier for rate limiting
            **kwargs: Keyword arguments for func

        Returns:
            Task ID

        Raises:
            asyncio.QueueFull: If queue is full (backpressure)
            RuntimeError: If rate limit exceeded
        """
        # Check rate limit
        if not await self.check_rate_limit(client_id):
            raise RuntimeError(
                f"Rate limit exceeded for client {client_id}: "
                f"{self.rate_limit_per_minute} requests/minute"
            )

        # Generate task ID
        task_id = str(uuid4())

        # Create task result
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        # Store task
        async with self.lock:
            self.tasks[task_id] = task_result

        # Submit to queue (non-blocking, raises QueueFull if full)
        try:
            self.queue.put_nowait((task_id, func, args, kwargs))
            logger.debug(f"Task {task_id} submitted (queue size: {self.queue.qsize()})")
        except asyncio.QueueFull:
            # Remove from tracking
            async with self.lock:
                del self.tasks[task_id]
            raise asyncio.QueueFull(
                f"Task queue is full (max_size={self.queue.maxsize}). " "Please try again later."
            )

        return task_id

    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """
        Get task status.

        Args:
            task_id: Task identifier

        Returns:
            TaskResult or None if not found
        """
        async with self.lock:
            return self.tasks.get(task_id)

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue stats
        """
        total_tasks = len(self.tasks)

        status_counts = defaultdict(int)
        for task in self.tasks.values():
            status_counts[task.status] += 1

        return {
            "queue_size": self.queue.qsize(),
            "queue_max_size": self.queue.maxsize,
            "active_workers": len(self.workers),
            "total_tasks": total_tasks,
            "pending_tasks": status_counts[TaskStatus.PENDING],
            "running_tasks": status_counts[TaskStatus.RUNNING],
            "completed_tasks": status_counts[TaskStatus.COMPLETED],
            "failed_tasks": status_counts[TaskStatus.FAILED],
            "cancelled_tasks": status_counts[TaskStatus.CANCELLED],
        }


# Global task queue instance
_task_queue: Optional[AsyncTaskQueue] = None


async def get_task_queue() -> AsyncTaskQueue:
    """
    Get global task queue instance.

    Returns:
        AsyncTaskQueue instance
    """
    global _task_queue
    if _task_queue is None:
        from app.core.config import get_settings

        settings = get_settings()

        _task_queue = AsyncTaskQueue(
            max_size=settings.task_queue_max_size,
            max_workers=settings.max_workers,
            rate_limit_per_minute=settings.rate_limit_per_minute,
        )
        await _task_queue.start_workers()

    return _task_queue


@asynccontextmanager
async def task_queue_lifespan():
    """
    Context manager for task queue lifecycle.

    Usage:
        async with task_queue_lifespan():
            # Use task queue
            pass
    """
    queue = await get_task_queue()
    try:
        yield queue
    finally:
        await queue.stop_workers()
