"""
Fraud detection API routes.

Implements async endpoints for fraud detection with proper
error handling, rate limiting, and backpressure management.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app import __version__
from app.core.task_queue import get_task_queue
from app.models.fraud import (
    BatchFraudAnalysisRequest,
    BatchFraudAnalysisResponse,
    FraudAnalysisRequest,
    FraudAnalysisResponse,
    TaskStatusResponse,
)
from app.services.fraud_detection import get_fraud_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["fraud-detection"])


@router.post(
    "/analyze",
    response_model=FraudAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze single transaction for fraud",
    description=(
        "Analyzes a single transaction for fraud using async processing. "
        "Returns fraud prediction with confidence score and explanation."
    ),
)
async def analyze_transaction(
    request: FraudAnalysisRequest,
) -> FraudAnalysisResponse:
    """
    Analyze a single transaction for fraud (async endpoint).

    Args:
        request: Fraud analysis request with transaction data

    Returns:
        FraudAnalysisResponse with prediction results

    Raises:
        HTTPException: If analysis fails
    """
    try:
        fraud_service = get_fraud_service()
        result = await fraud_service.analyze_transaction(request.transaction)

        logger.info(
            f"Transaction {request.transaction.transaction_id} analyzed: "
            f"fraud={result.prediction.is_fraud}, "
            f"risk={result.prediction.risk_score:.1f}"
        )

        return result

    except asyncio.TimeoutError:
        logger.error("Transaction analysis timeout")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is busy. Please try again later.",
        )
    except Exception as e:
        logger.exception(f"Transaction analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/analyze/batch",
    response_model=BatchFraudAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit batch analysis job",
    description=(
        "Submits a batch of transactions for asynchronous fraud analysis. "
        "Returns a task ID that can be used to check status and retrieve results."
    ),
)
async def analyze_batch(
    request: BatchFraudAnalysisRequest,
) -> BatchFraudAnalysisResponse:
    """
    Submit batch fraud analysis job (async task queue).

    Args:
        request: Batch analysis request with multiple transactions

    Returns:
        BatchFraudAnalysisResponse with task ID

    Raises:
        HTTPException: If submission fails (rate limit, queue full, etc.)
    """
    try:
        task_queue = await get_task_queue()
        fraud_service = get_fraud_service()

        # Submit batch analysis task
        task_id = await task_queue.submit_task(
            fraud_service.analyze_batch,
            request.transactions,
            client_id=request.client_id,
        )

        # Estimate completion time (rough estimate)
        estimated_time = len(request.transactions) * 0.15  # 150ms per transaction

        logger.info(
            f"Batch analysis submitted: task_id={task_id}, "
            f"transactions={len(request.transactions)}, "
            f"client={request.client_id}"
        )

        return BatchFraudAnalysisResponse(
            task_id=task_id,
            status="pending",
            message=f"Batch analysis of {len(request.transactions)} transactions submitted",
            estimated_completion_seconds=estimated_time,
        )

    except RuntimeError as e:
        # Rate limit exceeded
        if "Rate limit exceeded" in str(e):
            logger.warning(f"Rate limit exceeded: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
            )
        raise

    except asyncio.QueueFull as e:
        # Queue full (backpressure)
        logger.warning(f"Task queue full: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    except Exception as e:
        logger.exception(f"Batch submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task status",
    description="Retrieves the status and results of a batch analysis task.",
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Get status of a batch analysis task.

    Args:
        task_id: Task identifier

    Returns:
        TaskStatusResponse with task status and results

    Raises:
        HTTPException: If task not found
    """
    try:
        task_queue = await get_task_queue()
        task_result = await task_queue.get_task_status(task_id)

        if task_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

        return TaskStatusResponse(
            task_id=task_result.task_id,
            status=task_result.status.value,
            created_at=task_result.created_at,
            started_at=task_result.started_at,
            completed_at=task_result.completed_at,
            result=task_result.result if task_result.status.value == "completed" else None,
            error=task_result.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/stats",
    summary="Get fraud detection statistics",
    description="Returns service statistics including queue status and analysis metrics.",
)
async def get_stats():
    """
    Get fraud detection service statistics.

    Returns:
        Statistics dictionary
    """
    try:
        task_queue = await get_task_queue()
        fraud_service = get_fraud_service()

        queue_stats = task_queue.get_stats()
        service_stats = await fraud_service.get_stats()

        return {
            "queue": queue_stats,
            "service": service_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
