"""
Session Management with Redis.

Manages stateful agent sessions with persistence and expiration.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.state_machine import AgentState, StateMachine

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionManager:
    """
    Manages agent sessions with Redis backend.

    Provides session CRUD, state persistence, and automatic expiration.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize session manager.

        Args:
            redis_url: Redis connection URL (default: from settings)
        """
        self.redis_url = redis_url or settings.get_redis_url()
        self.redis_client: Optional[redis.Redis] = None
        self.session_ttl = settings.session_ttl_seconds

    async def connect(self):
        """Establish Redis connection."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info(f"Connected to Redis: {self.redis_url}")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"

    def _checkpoint_key(self, session_id: str) -> str:
        """Generate Redis key for checkpoint."""
        return f"checkpoint:{session_id}"

    def _idempotency_key(self, request_id: str) -> str:
        """Generate Redis key for idempotency token."""
        return f"idempotency:{request_id}"

    async def create_session(
        self,
        session_id: str,
        metadata: Optional[Dict] = None,
    ) -> StateMachine:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier
            metadata: Session metadata

        Returns:
            StateMachine instance
        """
        await self.connect()

        # Create state machine
        sm = StateMachine(session_id=session_id)
        if metadata:
            sm.metadata = metadata

        # Store in Redis
        key = self._session_key(session_id)
        await self.redis_client.setex(
            key,
            self.session_ttl,
            json.dumps(sm.to_dict()),
        )

        logger.info(f"Created session: {session_id}, TTL: {self.session_ttl}s")
        return sm

    async def get_session(self, session_id: str) -> Optional[StateMachine]:
        """
        Retrieve session by ID.

        Args:
            session_id: Session identifier

        Returns:
            StateMachine instance or None if not found
        """
        await self.connect()

        key = self._session_key(session_id)
        data = await self.redis_client.get(key)

        if not data:
            logger.warning(f"Session not found: {session_id}")
            return None

        # Deserialize state machine
        sm = StateMachine.from_dict(json.loads(data))
        logger.debug(f"Retrieved session: {session_id}, state: {sm.current_state}")
        return sm

    async def update_session(self, sm: StateMachine) -> bool:
        """
        Update existing session.

        Args:
            sm: StateMachine instance

        Returns:
            True if updated successfully
        """
        await self.connect()

        key = self._session_key(sm.session_id)

        # Check if session exists
        exists = await self.redis_client.exists(key)
        if not exists:
            logger.error(f"Cannot update non-existent session: {sm.session_id}")
            return False

        # Update with same TTL
        ttl = await self.redis_client.ttl(key)
        if ttl < 0:
            ttl = self.session_ttl

        await self.redis_client.setex(
            key,
            ttl,
            json.dumps(sm.to_dict()),
        )

        logger.debug(f"Updated session: {sm.session_id}, state: {sm.current_state}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted
        """
        await self.connect()

        key = self._session_key(session_id)
        deleted = await self.redis_client.delete(key)

        if deleted:
            logger.info(f"Deleted session: {session_id}")
        else:
            logger.warning(f"Session not found for deletion: {session_id}")

        return bool(deleted)

    async def extend_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """
        Extend session expiration.

        Args:
            session_id: Session identifier
            ttl: New TTL in seconds (default: session_ttl)

        Returns:
            True if extended
        """
        await self.connect()

        key = self._session_key(session_id)
        ttl = ttl or self.session_ttl

        extended = await self.redis_client.expire(key, ttl)

        if extended:
            logger.debug(f"Extended session: {session_id}, TTL: {ttl}s")
        else:
            logger.warning(f"Cannot extend non-existent session: {session_id}")

        return bool(extended)

    async def check_idempotency(self, request_id: str) -> Optional[Dict]:
        """
        Check if request has been processed (idempotency).

        Args:
            request_id: Unique request identifier

        Returns:
            Cached response if exists, None otherwise
        """
        await self.connect()

        key = self._idempotency_key(request_id)
        data = await self.redis_client.get(key)

        if data:
            logger.info(f"Idempotent request detected: {request_id}")
            return json.loads(data)

        return None

    async def store_idempotency_result(
        self,
        request_id: str,
        result: Dict,
        ttl: int = 3600,
    ) -> bool:
        """
        Store result for idempotency checking.

        Args:
            request_id: Unique request identifier
            result: Response to cache
            ttl: Time-to-live in seconds (default: 1 hour)

        Returns:
            True if stored
        """
        await self.connect()

        key = self._idempotency_key(request_id)
        await self.redis_client.setex(
            key,
            ttl,
            json.dumps(result),
        )

        logger.debug(f"Stored idempotency result: {request_id}, TTL: {ttl}s")
        return True

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (automatic with Redis TTL).

        Returns:
            Number of sessions cleaned (0 for Redis auto-cleanup)
        """
        # Redis handles TTL automatically
        logger.info("Redis auto-cleanup handles expired sessions")
        return 0


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
