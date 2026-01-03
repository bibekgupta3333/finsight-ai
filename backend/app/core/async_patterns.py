"""
Async & Production Patterns.

Implements worker pools, request queuing, background tasks, WebSocket/SSE streaming,
connection pooling, and resource cleanup.
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set

from fastapi import WebSocket
from pydantic import BaseModel, Field

try:
    from sse_starlette.sse import EventSourceResponse
    SSE_AVAILABLE = True
except ImportError:
    EventSourceResponse = None
    SSE_AVAILABLE = False

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Background task status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BackgroundTask(BaseModel):
    """Background task definition."""

    id: str
    name: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkerPoolConfig(BaseModel):
    """Worker pool configuration."""

    max_workers: int = 10
    queue_size: int = 100
    worker_timeout: float = 300.0  # 5 minutes
    enable_priority: bool = True


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""

    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    max_lifetime: float = 3600.0  # 1 hour


class WorkerPool:
    """
    Worker pool for background task processing.

    Manages concurrent workers with priority queue and resource limits.
    """

    def __init__(self, config: Optional[WorkerPoolConfig] = None):
        """
        Initialize worker pool.

        Args:
            config: Worker pool configuration
        """
        self.config = config or WorkerPoolConfig()

        # Task queues by priority
        self._queues: Dict[TaskPriority, Deque[BackgroundTask]] = {
            TaskPriority.CRITICAL: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque(),
        }

        # Task tracking
        self._tasks: Dict[str, BackgroundTask] = {}
        self._running_tasks: Set[str] = set()

        # Worker management
        self._workers: List[asyncio.Task] = []
        self._shutdown = False

        # Statistics
        self._total_processed = 0
        self._total_failed = 0
        self._total_cancelled = 0

        logger.info(f"WorkerPool initialized with {self.config.max_workers} workers")

    async def start(self) -> None:
        """Start worker pool."""
        self._shutdown = False

        # Start workers
        for i in range(self.config.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Started {self.config.max_workers} workers")

    async def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown worker pool.

        Args:
            wait: Wait for running tasks to complete
        """
        logger.info("Shutting down worker pool...")
        self._shutdown = True

        if wait:
            # Wait for running tasks
            while self._running_tasks:
                await asyncio.sleep(0.1)

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to stop
        await asyncio.gather(*self._workers, return_exceptions=True)

        logger.info("Worker pool shutdown complete")

    async def submit_task(
        self,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Submit a background task.

        Args:
            name: Task name
            func: Async function to execute
            *args: Function arguments
            priority: Task priority
            metadata: Additional metadata
            **kwargs: Function keyword arguments

        Returns:
            Task ID
        """
        if len(self._tasks) >= self.config.queue_size:
            raise RuntimeError("Task queue full")

        task_id = str(uuid.uuid4())

        task = BackgroundTask(
            id=task_id,
            name=name,
            priority=priority,
            created_at=datetime.now(),
            metadata=metadata or {},
        )

        # Store task function
        task.metadata["_func"] = func
        task.metadata["_args"] = args
        task.metadata["_kwargs"] = kwargs

        self._tasks[task_id] = task
        self._queues[priority].append(task)

        logger.info(f"Task submitted: {task_id} - {name} (priority: {priority})")
        return task_id

    async def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        task = self._tasks.get(task_id)
        if task:
            # Remove internal metadata
            task_copy = task.copy()
            task_copy.metadata = {
                k: v for k, v in task.metadata.items() if not k.startswith("_")
            }
            return task_copy
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False

        task.status = TaskStatus.CANCELLED
        self._total_cancelled += 1

        # Remove from queue
        for queue in self._queues.values():
            try:
                queue.remove(task)
            except ValueError:
                pass

        logger.info(f"Task cancelled: {task_id}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get worker pool statistics.

        Returns:
            Statistics
        """
        return {
            "workers": len(self._workers),
            "running_tasks": len(self._running_tasks),
            "queued_tasks": sum(len(q) for q in self._queues.values()),
            "total_tasks": len(self._tasks),
            "total_processed": self._total_processed,
            "total_failed": self._total_failed,
            "total_cancelled": self._total_cancelled,
            "queue_by_priority": {
                priority.value: len(queue) for priority, queue in self._queues.items()
            },
        }

    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker event loop.

        Args:
            worker_id: Worker ID
        """
        logger.info(f"Worker {worker_id} started")

        while not self._shutdown:
            # Get next task by priority
            task = self._get_next_task()

            if not task:
                # No tasks, sleep briefly
                await asyncio.sleep(0.1)
                continue

            # Execute task
            await self._execute_task(task, worker_id)

        logger.info(f"Worker {worker_id} stopped")

    def _get_next_task(self) -> Optional[BackgroundTask]:
        """
        Get next task from priority queues.

        Returns:
            Next task or None
        """
        # Check in priority order
        for priority in [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ]:
            queue = self._queues[priority]
            if queue:
                return queue.popleft()

        return None

    async def _execute_task(self, task: BackgroundTask, worker_id: int) -> None:
        """
        Execute a task.

        Args:
            task: Task to execute
            worker_id: Worker ID
        """
        if task.status == TaskStatus.CANCELLED:
            return

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self._running_tasks.add(task.id)

        logger.info(f"Worker {worker_id} executing task: {task.id} - {task.name}")

        try:
            # Get function and args
            func = task.metadata.get("_func")
            args = task.metadata.get("_args", [])
            kwargs = task.metadata.get("_kwargs", {})

            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.worker_timeout
            )

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.progress = 1.0
            self._total_processed += 1

            logger.info(f"Task completed: {task.id}")

        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = "Task timeout"
            self._total_failed += 1
            logger.error(f"Task timeout: {task.id}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._total_failed += 1
            logger.error(f"Task failed: {task.id} - {e}")

        finally:
            task.completed_at = datetime.now()
            self._running_tasks.remove(task.id)


class ConnectionPool:
    """
    Generic connection pool.

    Manages reusable connections with lifecycle management.
    """

    def __init__(
        self,
        name: str,
        create_func: Callable,
        close_func: Callable,
        config: Optional[ConnectionPoolConfig] = None,
    ):
        """
        Initialize connection pool.

        Args:
            name: Pool name
            create_func: Function to create connection
            close_func: Function to close connection
            config: Pool configuration
        """
        self.name = name
        self.create_func = create_func
        self.close_func = close_func
        self.config = config or ConnectionPoolConfig()

        # Connection tracking
        self._available: Deque[Any] = deque()
        self._in_use: Set[Any] = set()
        self._connection_times: Dict[Any, float] = {}

        # Statistics
        self._total_created = 0
        self._total_closed = 0
        self._total_acquired = 0
        self._total_released = 0

        logger.info(f"ConnectionPool '{name}' initialized")

    async def acquire(self) -> Any:
        """
        Acquire a connection from the pool.

        Returns:
            Connection
        """
        # Check for available connection
        while self._available:
            conn = self._available.popleft()

            # Check if connection is still valid
            age = time.time() - self._connection_times.get(conn, 0)
            if age > self.config.max_lifetime:
                # Connection too old, close it
                await self._close_connection(conn)
                continue

            # Connection is valid
            self._in_use.add(conn)
            self._total_acquired += 1
            return conn

        # No available connections, create new if under limit
        total = len(self._available) + len(self._in_use)
        if total < self.config.max_connections:
            conn = await self._create_connection()
            self._in_use.add(conn)
            self._total_acquired += 1
            return conn

        # Wait for connection to become available
        logger.warning(f"ConnectionPool '{self.name}' exhausted, waiting...")
        while True:
            await asyncio.sleep(0.1)
            if self._available:
                return await self.acquire()

    async def release(self, conn: Any) -> None:
        """
        Release a connection back to the pool.

        Args:
            conn: Connection to release
        """
        if conn not in self._in_use:
            logger.warning(f"Releasing unknown connection in pool '{self.name}'")
            return

        self._in_use.remove(conn)
        self._available.append(conn)
        self._total_released += 1

    async def close_all(self) -> None:
        """Close all connections."""
        logger.info(f"Closing all connections in pool '{self.name}'")

        # Close available connections
        while self._available:
            conn = self._available.popleft()
            await self._close_connection(conn)

        # Close in-use connections (force)
        for conn in list(self._in_use):
            await self._close_connection(conn)
            self._in_use.remove(conn)

        logger.info(f"ConnectionPool '{self.name}' closed")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Statistics
        """
        return {
            "name": self.name,
            "available": len(self._available),
            "in_use": len(self._in_use),
            "total_connections": len(self._available) + len(self._in_use),
            "total_created": self._total_created,
            "total_closed": self._total_closed,
            "total_acquired": self._total_acquired,
            "total_released": self._total_released,
        }

    async def _create_connection(self) -> Any:
        """Create a new connection."""
        conn = await self.create_func()
        self._connection_times[conn] = time.time()
        self._total_created += 1
        logger.debug(f"Created connection in pool '{self.name}'")
        return conn

    async def _close_connection(self, conn: Any) -> None:
        """Close a connection."""
        try:
            await self.close_func(conn)
            self._total_closed += 1
            if conn in self._connection_times:
                del self._connection_times[conn]
            logger.debug(f"Closed connection in pool '{self.name}'")
        except Exception as e:
            logger.error(f"Error closing connection in pool '{self.name}': {e}")


class WebSocketManager:
    """
    WebSocket connection manager.

    Manages WebSocket connections for real-time updates.
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        self._connections: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # topic -> client_ids

        logger.info("WebSocketManager initialized")

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """
        Connect a WebSocket client.

        Args:
            client_id: Client ID
            websocket: WebSocket connection
        """
        await websocket.accept()
        self._connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str) -> None:
        """
        Disconnect a WebSocket client.

        Args:
            client_id: Client ID
        """
        if client_id in self._connections:
            del self._connections[client_id]

        # Remove from all subscriptions
        for topic_clients in self._subscriptions.values():
            topic_clients.discard(client_id)

        logger.info(f"WebSocket client disconnected: {client_id}")

    async def subscribe(self, client_id: str, topic: str) -> None:
        """
        Subscribe client to topic.

        Args:
            client_id: Client ID
            topic: Topic name
        """
        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()

        self._subscriptions[topic].add(client_id)
        logger.info(f"Client {client_id} subscribed to {topic}")

    async def unsubscribe(self, client_id: str, topic: str) -> None:
        """
        Unsubscribe client from topic.

        Args:
            client_id: Client ID
            topic: Topic name
        """
        if topic in self._subscriptions:
            self._subscriptions[topic].discard(client_id)
            logger.info(f"Client {client_id} unsubscribed from {topic}")

    async def broadcast(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all subscribers.

        Args:
            topic: Topic name
            message: Message to broadcast
        """
        if topic not in self._subscriptions:
            return

        clients = self._subscriptions[topic]
        logger.info(f"Broadcasting to {len(clients)} clients on topic '{topic}'")

        for client_id in list(clients):
            websocket = self._connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {e}")
                    self.disconnect(client_id)

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific client.

        Args:
            client_id: Client ID
            message: Message to send

        Returns:
            True if sent successfully
        """
        websocket = self._connections.get(client_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            self.disconnect(client_id)
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get WebSocket statistics.

        Returns:
            Statistics
        """
        return {
            "total_connections": len(self._connections),
            "total_topics": len(self._subscriptions),
            "subscriptions_per_topic": {
                topic: len(clients) for topic, clients in self._subscriptions.items()
            },
        }


async def sse_event_generator(
    topic: str,
    interval: float = 1.0,
    max_events: Optional[int] = None,
):
    """
    Server-Sent Events generator.

    Args:
        topic: Topic to stream
        interval: Seconds between events
        max_events: Maximum events to send (None for infinite)

    Yields:
        Event data
    """
    if not SSE_AVAILABLE:
        raise ImportError("sse-starlette not installed. Install with: pip install sse-starlette")

    event_count = 0

    while max_events is None or event_count < max_events:
        # Generate event (placeholder - replace with actual event source)
        event_data = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "event_count": event_count,
            "data": f"Event {event_count} for topic {topic}",
        }

        yield event_data

        event_count += 1
        await asyncio.sleep(interval)


class ResourceManager:
    """
    Resource cleanup and garbage collection.

    Manages resource lifecycle and cleanup.
    """

    def __init__(self):
        """Initialize resource manager."""
        self._resources: Dict[str, Any] = {}
        self._cleanup_funcs: Dict[str, Callable] = {}
        self._last_access: Dict[str, float] = {}

        logger.info("ResourceManager initialized")

    def register(
        self,
        resource_id: str,
        resource: Any,
        cleanup_func: Callable,
    ) -> None:
        """
        Register a resource for management.

        Args:
            resource_id: Resource ID
            resource: Resource object
            cleanup_func: Cleanup function
        """
        self._resources[resource_id] = resource
        self._cleanup_funcs[resource_id] = cleanup_func
        self._last_access[resource_id] = time.time()

        logger.info(f"Resource registered: {resource_id}")

    async def cleanup(self, resource_id: str) -> bool:
        """
        Cleanup a specific resource.

        Args:
            resource_id: Resource ID

        Returns:
            True if cleaned up
        """
        if resource_id not in self._resources:
            return False

        resource = self._resources.pop(resource_id)
        cleanup_func = self._cleanup_funcs.pop(resource_id)
        self._last_access.pop(resource_id, None)

        try:
            await cleanup_func(resource)
            logger.info(f"Resource cleaned up: {resource_id}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up resource {resource_id}: {e}")
            return False

    async def cleanup_idle(self, idle_timeout: float = 300.0) -> int:
        """
        Cleanup idle resources.

        Args:
            idle_timeout: Seconds of inactivity before cleanup

        Returns:
            Number of resources cleaned up
        """
        current_time = time.time()
        cleaned_count = 0

        for resource_id in list(self._resources.keys()):
            last_access = self._last_access.get(resource_id, 0)
            if current_time - last_access > idle_timeout:
                if await self.cleanup(resource_id):
                    cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} idle resources")

        return cleaned_count

    async def cleanup_all(self) -> int:
        """
        Cleanup all resources.

        Returns:
            Number of resources cleaned up
        """
        cleaned_count = 0

        for resource_id in list(self._resources.keys()):
            if await self.cleanup(resource_id):
                cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} total resources")
        return cleaned_count

    def touch(self, resource_id: str) -> None:
        """
        Update last access time for resource.

        Args:
            resource_id: Resource ID
        """
        if resource_id in self._resources:
            self._last_access[resource_id] = time.time()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get resource statistics.

        Returns:
            Statistics
        """
        current_time = time.time()

        return {
            "total_resources": len(self._resources),
            "idle_resources": sum(
                1
                for last_access in self._last_access.values()
                if current_time - last_access > 300
            ),
            "resources": {
                resource_id: {
                    "idle_seconds": current_time - self._last_access.get(resource_id, 0)
                }
                for resource_id in self._resources
            },
        }
