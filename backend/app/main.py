"""
FinSight AI - FastAPI Application.

Main application with lifespan management for async task queue.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import fraud
from app.core.config import get_settings
from app.core.session import get_session_manager
from app.core.task_queue import get_task_queue
from app.middleware import CorrelationIdMiddleware, IdempotencyMiddleware
from app.models.fraud import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of async task queue.
    """
    # Startup
    logger.info("=" * 80)
    logger.info("FINSIGHT AI - STARTING UP")
    logger.info("=" * 80)

    settings = get_settings()
    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"Version: {__version__}")
    logger.info(f"Debug: {settings.debug}")
    logger.info(f"Max Workers: {settings.max_workers}")
    logger.info(f"Queue Max Size: {settings.task_queue_max_size}")
    logger.info(f"Rate Limit: {settings.rate_limit_per_minute}/min")
    logger.info(f"Redis URL: {settings.redis_url}")
    logger.info(f"Session TTL: {settings.session_ttl_seconds}s")

    # Initialize task queue
    task_queue = await get_task_queue()
    logger.info("✓ Task queue initialized")

    # Initialize session manager (Redis)
    session_manager = get_session_manager()
    await session_manager.connect()
    logger.info("✓ Session manager connected")

    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("FINSIGHT AI - SHUTTING DOWN")
    logger.info("=" * 80)

    # Stop task queue gracefully
    await task_queue.stop_workers(timeout=30.0)
    logger.info("✓ Task queue stopped")

    # Disconnect session manager
    session_manager = get_session_manager()
    await session_manager.disconnect()
    logger.info("✓ Session manager disconnected")

    logger.info("=" * 80)


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Async fraud detection API with task queue and concurrency controls",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(IdempotencyMiddleware)


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description="Returns API health status and queue statistics",
)
async def health_check():
    """Health check endpoint."""
    try:
        task_queue = await get_task_queue()
        queue_stats = task_queue.get_stats()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version=__version__,
            queue_stats=queue_stats,
        )
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": __version__,
                "error": str(e),
            },
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "message": "FinSight AI - Fraud Detection API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(fraud.router, prefix=settings.api_v1_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
