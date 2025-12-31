"""
Idempotency Middleware.

Ensures API requests are idempotent using request IDs.
"""

import json
import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.session import get_session_manager

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure idempotent requests.

    Uses Idempotency-Key header to deduplicate requests.
    """

    IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
    IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with idempotency check.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response (cached or fresh)
        """
        # Only apply to mutating operations
        if request.method not in self.IDEMPOTENT_METHODS:
            return await call_next(request)

        # Get idempotency key from header
        idempotency_key = request.headers.get(self.IDEMPOTENCY_KEY_HEADER)

        if not idempotency_key:
            # No idempotency key, process normally
            return await call_next(request)

        # Check if request has been processed
        session_manager = get_session_manager()
        cached_response = await session_manager.check_idempotency(idempotency_key)

        if cached_response:
            logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
            return JSONResponse(
                content=cached_response["body"],
                status_code=cached_response["status_code"],
                headers={"X-Idempotent-Replay": "true"},
            )

        # Process request
        response = await call_next(request)

        # Cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Parse body
            try:
                body_json = json.loads(body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                body_json = {}

            # Store in cache
            await session_manager.store_idempotency_result(
                request_id=idempotency_key,
                result={
                    "status_code": response.status_code,
                    "body": body_json,
                },
                ttl=3600,  # 1 hour
            )

            # Reconstruct response with body
            return JSONResponse(
                content=body_json,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        return response
