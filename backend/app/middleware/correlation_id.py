"""
Correlation ID Middleware.

Adds correlation IDs to requests for distributed tracing.
"""

import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests.

    Generates or uses existing correlation ID for request tracing.
    """

    CORRELATION_ID_HEADER = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add correlation ID.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with correlation ID header
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            self.CORRELATION_ID_HEADER,
            str(uuid.uuid4()),
        )

        # Store in request state
        request.state.correlation_id = correlation_id

        # Add to logger context (if using structured logging)
        logger.debug(f"Request correlation_id: {correlation_id}")

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[self.CORRELATION_ID_HEADER] = correlation_id

        return response


def get_correlation_id(request: Request) -> str:
    """
    Get correlation ID from request.

    Args:
        request: FastAPI request

    Returns:
        Correlation ID
    """
    return getattr(request.state, "correlation_id", "unknown")
